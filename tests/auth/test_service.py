import uuid

import pytest

from auth.application.service import AuthApplicationService
from auth.domain.exceptions import (
    AuthenticationError,
    EmailDuplicatedError,
    InvalidCredentialsError,
    TokenRevokedError,
)
from auth.domain.point_log import PointLog, PointType
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import PasswordHasher
from auth.domain.user import Role, User
from auth.infrastructure.security import JwtTokenProvider
from auth.infrastructure.settings import AuthSettings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class FakeHasher(PasswordHasher):
    def __init__(self):
        self.dummy_calls = 0
        self.hash_calls = 0

    def hash(self, raw):
        self.hash_calls += 1
        return "hashed:" + raw

    def verify(self, raw, hashed):
        return hashed == "hashed:" + raw

    def dummy_verify(self, raw):
        self.dummy_calls += 1


class FakeUsers(UserRepository):
    def __init__(self, race=False):
        self.items = {}
        self.race = race
        self.race_row = None  # 경쟁 시 저장 실패 뒤에 보이게 되는 다른 요청의 행

    async def find_by_id(self, user_id, for_update=False):
        return self.items.get(user_id)

    async def find_by_email(self, email):
        return next((u for u in self.items.values() if u.email == email), None)

    async def exists_by_email(self, email):
        return False if self.race else await self.find_by_email(email) is not None

    async def save(self, user):
        if self.race:
            if self.race_row is not None:
                self.items[self.race_row.id] = self.race_row
            raise EmailDuplicatedError()
        if user.id is None:
            user.id = uuid.uuid4()
        self.items[user.id] = user
        return user


class FakeLogs(PointLogRepository):
    def __init__(self):
        self.items: list[PointLog] = []

    async def add(self, log):
        self.items.append(log)
        return log

    async def find_by_user(self, user_id, *, point_type=None, offset=0, limit=20):
        r = [x for x in self.items if x.user_id == user_id and (point_type is None or x.point_type == point_type)]
        return r[offset:offset + limit]

    async def count_by_user(self, user_id, *, point_type=None):
        return len(await self.find_by_user(user_id, point_type=point_type, limit=10**6))


class FakeBlacklist(TokenBlacklistRepository):
    def __init__(self):
        self.jtis = set()

    async def add(self, token):
        self.jtis.add(token.jti)

    async def exists(self, jti):
        return jti in self.jtis

    async def delete_expired(self, now=None):
        return 3


def build(race=False):
    db = FakeSession()
    parts = dict(users=FakeUsers(race), point_logs=FakeLogs(), blacklist=FakeBlacklist(),
                 hasher=FakeHasher(), tokens=JwtTokenProvider(AuthSettings(secret_key="k" * 40)))
    return AuthApplicationService(db, **parts), db, parts


async def test_signup_ok_and_commit():
    svc, db, _ = build()
    u = await svc.signup("A@b.com", "password1", "CUSTOMER", name="n")
    assert u.email == "a@b.com" and u.id and db.commits == 1


async def test_signup_admin_rejected_before_hashing():
    svc, _, p = build()
    with pytest.raises(ValueError):
        await svc.signup("a@b.com", "password1", "ADMIN")
    assert p["hasher"].hash_calls == 0


async def test_signup_weak_password():
    svc, _, _ = build()
    with pytest.raises(ValueError):
        await svc.signup("a@b.com", "short", "CUSTOMER")


async def test_signup_duplicate():
    svc, db, _ = build()
    await svc.signup("a@b.com", "password1", "CUSTOMER")
    with pytest.raises(EmailDuplicatedError):
        await svc.signup("A@B.com", "password1", "CUSTOMER")


async def test_signup_race_rolls_back():
    svc, db, _ = build(race=True)
    with pytest.raises(EmailDuplicatedError):
        await svc.signup("a@b.com", "password1", "CUSTOMER")
    assert db.rollbacks == 1 and db.commits == 0


async def test_login_paths():
    svc, _, p = build()
    await svc.signup("a@b.com", "password1", "CUSTOMER")
    token = await svc.login("  A@b.com", "password1")
    assert (await svc.authenticate(token)).user.email == "a@b.com"
    with pytest.raises(InvalidCredentialsError) as e1:
        await svc.login("a@b.com", "wrongpass1")
    with pytest.raises(InvalidCredentialsError) as e2:
        await svc.login("none@b.com", "password1")
    assert str(e1.value) == str(e2.value)
    assert p["hasher"].dummy_calls == 1


async def test_authenticate_revoked_and_unknown_user():
    svc, db, p = build()
    await svc.signup("a@b.com", "password1", "CUSTOMER")
    token = await svc.login("a@b.com", "password1")
    principal = await svc.authenticate(token)
    await svc.logout(principal.claims)
    with pytest.raises(TokenRevokedError):
        await svc.authenticate(token)
    token2, _ = svc.tokens.issue(uuid.uuid4(), "CUSTOMER")
    with pytest.raises(AuthenticationError):
        await svc.authenticate(token2)


async def test_points_flow_and_logs():
    svc, db, p = build()
    u = await svc.signup("a@b.com", "password1", "CUSTOMER")
    await svc.earn_points(u.id, 500)
    await svc.use_points(u.id, 200)
    await svc.restore_points(u.id, 100)
    assert await svc.revoke_points(u.id, 10_000) == 400
    assert await svc.revoke_points(u.id, 10) == 0
    types = [(x.point_type, x.amount) for x in p["point_logs"].items]
    assert types == [(PointType.EARN, 500), (PointType.USE, -200),
                     (PointType.RESTORE, 100), (PointType.REVOKE, -400)]
    page = await svc.list_point_logs(u, PointType.EARN, 0, 10)
    assert page.total_elements == 1 and page.users_point == 0


async def test_points_commit_false():
    svc, db, _ = build()
    u = await svc.signup("a@b.com", "password1", "CUSTOMER")
    before = db.commits
    await svc.earn_points(u.id, 100, commit=False)
    assert db.commits == before


async def test_points_errors():
    svc, _, _ = build()
    with pytest.raises(LookupError):
        await svc.earn_points(uuid.uuid4(), 100)
    u = await svc.signup("a@b.com", "password1", "CUSTOMER")
    with pytest.raises(ValueError):
        await svc.use_points(u.id, 100)
    with pytest.raises(LookupError):
        await svc.get_user(uuid.uuid4())


@pytest.mark.parametrize("page,size", [(-1, 20), (0, 0), (0, 101)])
async def test_list_point_logs_bounds(page, size):
    svc, _, _ = build()
    u = User("a@b.com", "h", Role.CUSTOMER, id=uuid.uuid4())
    with pytest.raises(ValueError):
        await svc.list_point_logs(u, None, page, size)


async def test_purge():
    svc, db, _ = build()
    assert await svc.purge_expired_tokens() == 3 and db.commits == 1


def test_constructor_requires_all_dependencies():
    # R8: 기본 구현체를 만들지 않는다
    with pytest.raises(TypeError):
        AuthApplicationService(FakeSession())


async def test_missing_user_raises_user_not_found_error():
    from auth.domain.exceptions import UserNotFoundError

    svc, _, _ = build()
    with pytest.raises(UserNotFoundError, match="회원을 찾을 수 없습니다."):
        await svc.earn_points(uuid.uuid4(), 100)
    with pytest.raises(UserNotFoundError, match="회원을 찾을 수 없습니다."):
        await svc.get_user(uuid.uuid4())


# ── ensure_admin (T-S1~S5) ──
def seeded(svc, parts, role="CUSTOMER", email="admin@b.com"):
    u = User(email=email, password_hash="h", role=Role(role))
    u.id = uuid.uuid4()
    parts["users"].items[u.id] = u
    return u


async def test_ensure_admin_creates():
    svc, db, parts = build()
    user, created = await svc.ensure_admin("Admin@B.com", "password1", name="관리자")
    assert created is True and user.role is Role.ADMIN and user.email == "admin@b.com"
    assert user.id in parts["users"].items
    assert parts["hasher"].hash_calls == 1 and db.commits == 1


async def test_ensure_admin_existing_admin_is_noop():
    svc, db, parts = build()
    existing = seeded(svc, parts, "ADMIN")
    user, created = await svc.ensure_admin("admin@b.com", "another-password")
    assert created is False and user is existing
    assert parts["hasher"].hash_calls == 0 and db.commits == 0
    assert existing.password_hash == "h"


async def test_ensure_admin_does_not_promote_non_admin():
    svc, db, parts = build()
    existing = seeded(svc, parts, "CUSTOMER")
    with pytest.raises(EmailDuplicatedError):
        await svc.ensure_admin("admin@b.com", "password1")
    assert existing.role is Role.CUSTOMER and db.commits == 0


@pytest.mark.parametrize("pw", ["short", "        ", ""])
async def test_ensure_admin_weak_password_rejected_before_lookup(pw):
    svc, db, parts = build()
    seeded(svc, parts, "ADMIN")
    with pytest.raises(ValueError):
        await svc.ensure_admin("admin@b.com", pw)
    assert parts["hasher"].hash_calls == 0 and db.commits == 0


async def test_ensure_admin_race_other_is_admin():
    svc, db, parts = build(race=True)
    other = User(email="admin@b.com", password_hash="h", role=Role.ADMIN)
    other.id = uuid.uuid4()
    parts["users"].race_row = other
    user, created = await svc.ensure_admin("admin@b.com", "password1")
    assert created is False and user is other
    assert db.rollbacks == 1 and db.commits == 0


async def test_ensure_admin_race_other_is_customer():
    svc, db, parts = build(race=True)
    other = User(email="admin@b.com", password_hash="h", role=Role.CUSTOMER)
    other.id = uuid.uuid4()
    parts["users"].race_row = other
    with pytest.raises(EmailDuplicatedError):
        await svc.ensure_admin("admin@b.com", "password1")
    assert db.rollbacks == 1


async def test_ensure_admin_race_without_row_reraises():
    svc, db, _ = build(race=True)
    with pytest.raises(EmailDuplicatedError):
        await svc.ensure_admin("admin@b.com", "password1")
    assert db.rollbacks == 1
