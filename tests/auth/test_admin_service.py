"""auth 서비스의 관리자용 메서드·로그인·인증 상태 처리 (fake 주입, DB 없음)."""

import uuid
from datetime import timedelta

import pytest

from auth.domain.exceptions import (
    AccountSuspendedError,
    AuthenticationError,
    InvalidCredentialsError,
    InvalidPageError,
    OwnerNotFoundError,
    OwnerNotPendingError,
    UserNotFoundError,
)
from auth.domain.point_log import PointType
from auth.domain.user import Role, User, UserStatus
from tests.auth.fakes import T0
from tests.auth.test_service import build

pytestmark = pytest.mark.anyio

ADMIN = uuid.uuid4()


@pytest.fixture
def anyio_backend():
    return "asyncio"


def put(parts, role=Role.CUSTOMER, **kw):
    u = User(email=f"{uuid.uuid4().hex[:8]}@b.com", password_hash="hashed:password1", role=role, **kw)
    u.id = uuid.uuid4()
    parts["users"].items[u.id] = u
    return u


# ── 승인·거부 ──
async def test_approve_owner_commit_flag():
    svc, db, parts = build()
    o = await svc.signup("o@b.com", "password1", "OWNER", name="n", phone="010-0000-0000")
    assert o.status is UserStatus.PENDING and db.commits == 1
    res = await svc.approve_owner(o.id, now=T0, commit=False)
    assert res.status is UserStatus.APPROVED and res.approved_at == T0 and db.commits == 1
    with pytest.raises(OwnerNotPendingError):
        await svc.approve_owner(o.id, now=T0)
    assert db.commits == 1  # 실패 시 commit 없음


async def test_approve_commit_default_and_errors():
    svc, db, parts = build()
    o = put(parts, Role.OWNER, status=UserStatus.PENDING)
    await svc.approve_owner(o.id, now=T0)
    assert db.commits == 1
    with pytest.raises(OwnerNotFoundError):
        await svc.approve_owner(put(parts).id, now=T0)  # 고객 ID
    with pytest.raises(UserNotFoundError):
        await svc.approve_owner(uuid.uuid4(), now=T0)


async def test_reject_owner():
    svc, db, parts = build()
    o = put(parts, Role.OWNER, status=UserStatus.PENDING)
    with pytest.raises(ValueError, match="거부 사유를 입력해 주세요."):
        await svc.reject_owner(o.id, " ", now=T0)
    res = await svc.reject_owner(o.id, "서류 미비", now=T0, commit=False)
    assert res.status is UserStatus.REJECTED and db.commits == 0


# ── 정지·탈퇴 ──
async def test_suspend_user_and_check_withdrawable():
    svc, db, parts = build()
    u = put(parts)
    res = await svc.suspend_user(u.id, "욕설", T0 + timedelta(days=1), now=T0, commit=False)
    assert res.status is UserStatus.SUSPENDED and db.commits == 0
    await svc.suspend_user(put(parts).id, "r", None, now=T0)
    assert db.commits == 1
    await svc.check_withdrawable(u.id, "r")
    assert u.status is UserStatus.SUSPENDED  # 부수 효과 없음
    with pytest.raises(ValueError, match="탈퇴 사유"):
        await svc.check_withdrawable(u.id, "")
    with pytest.raises(UserNotFoundError):
        await svc.check_withdrawable(uuid.uuid4(), "r")


async def test_withdraw_user():
    svc, db, parts = build()
    u = put(parts)
    res = await svc.withdraw_user(u.id, "약관 위반", now=T0, commit=False)
    assert res.status is UserStatus.WITHDRAWN and res.deleted_at == T0 and db.commits == 0
    admin = put(parts, Role.ADMIN)
    with pytest.raises(ValueError):
        await svc.withdraw_user(admin.id, "r", now=T0)
    assert db.commits == 0


# ── 포인트 ──
async def test_grant_points_writes_log_with_balance():
    svc, db, parts = build()
    u = put(parts, users_point=30)
    log = await svc.grant_points(u.id, 70, " 이벤트 ", ADMIN, now=T0, commit=False)
    assert u.users_point == 100 and db.commits == 0
    assert (log.point_type, log.amount, log.reason, log.balance_after, log.created_by) == (
        PointType.GRANT, 70, "이벤트", 100, ADMIN,
    )
    assert parts["point_logs"].items == [log]
    await svc.grant_points(u.id, 1, "r", ADMIN, now=T0)
    assert db.commits == 1


async def test_grant_failure_leaves_no_log():
    svc, db, parts = build()
    u = put(parts, status=UserStatus.WITHDRAWN, deleted_at=T0)
    with pytest.raises(ValueError):
        await svc.grant_points(u.id, 10, "r", ADMIN, now=T0)
    assert parts["point_logs"].items == [] and db.commits == 0
    with pytest.raises(UserNotFoundError):
        await svc.grant_points(uuid.uuid4(), 10, "r", ADMIN, now=T0)


async def test_all_point_logs_record_balance_after():
    svc, _, parts = build()
    u = await svc.signup("a@b.com", "password1", "CUSTOMER", name="n", phone="010-0000-0000")
    await svc.earn_points(u.id, 500)
    await svc.use_points(u.id, 200)
    await svc.restore_points(u.id, 100)
    await svc.revoke_points(u.id, 10_000)
    assert [x.balance_after for x in parts["point_logs"].items] == [500, 300, 400, 0]


async def test_list_points_pagination():
    svc, _, parts = build()
    u = put(parts, users_point=5)
    for i in range(3):
        await svc.grant_points(u.id, 1, f"r{i}", ADMIN, now=T0)
    page = await svc.list_points(u.id, 2, 2)
    assert (page.user_id, page.balance, page.page, page.size, page.total) == (u.id, 8, 2, 2, 3)
    assert len(page.history) == 1


@pytest.mark.parametrize("page,size", [(0, 20), (-1, 20), (1, 0), (1, 101)])
async def test_list_points_invalid_page(page, size):
    svc, _, parts = build()
    u = put(parts)
    with pytest.raises(InvalidPageError) as e:
        await svc.list_points(u.id, page, size)
    assert e.value.error_code == "INVALID_PAGE"


async def test_list_points_page_check_before_lookup_and_404():
    svc, _, _ = build()
    with pytest.raises(InvalidPageError):
        await svc.list_points(uuid.uuid4(), 0, 20)
    with pytest.raises(UserNotFoundError):
        await svc.list_points(uuid.uuid4(), 1, 20)


# ── 로그인 ──
async def test_login_status_values_and_clock():
    svc, _, parts = build()
    cust = await svc.signup("c@b.com", "password1", "CUSTOMER", name="n", phone="010-0000-0000")
    owner = await svc.signup("o@b.com", "password1", "OWNER", name="n", phone="010-0000-0000")
    assert (await svc.login("c@b.com", "password1")).status == "APPROVED"
    assert (await svc.login("o@b.com", "password1")).status == "PENDING"  # D5: 로그인 허용
    with pytest.raises(ValueError):  # PENDING은 정지 불가 (D36)
        await svc.suspend_user(owner.id, "r", None, now=T0)
    owner.status = UserStatus.APPROVED
    await svc.suspend_user(owner.id, "r", T0 + timedelta(days=1), now=T0)
    assert (await svc.login("o@b.com", "password1")).status == "SUSPENDED"  # D39
    svc.clock.advance(days=2)
    assert (await svc.login("o@b.com", "password1")).status == "APPROVED"  # 만료
    assert cust.status is UserStatus.APPROVED


async def test_login_suspended_customer_403_after_password_check():
    svc, _, _ = build()
    c = await svc.signup("c@b.com", "password1", "CUSTOMER", name="n", phone="010-0000-0000")
    await svc.suspend_user(c.id, "r", None, now=T0)
    with pytest.raises(AccountSuspendedError):
        await svc.login("c@b.com", "password1")
    with pytest.raises(InvalidCredentialsError):  # 틀린 비밀번호는 상태와 무관 (계정 열거 방지)
        await svc.login("c@b.com", "wrongpass1")


async def test_login_withdrawn_is_invalid_credentials_for_each_role():
    svc, _, _ = build()
    for email, role in (("c@b.com", "CUSTOMER"), ("o@b.com", "OWNER")):
        u = await svc.signup(email, "password1", role, name="n", phone="010-0000-0000")
        await svc.withdraw_user(u.id, "r", now=T0)
        with pytest.raises(InvalidCredentialsError):
            await svc.login(email, "password1")


# ── authenticate ──
async def test_authenticate_suspended_and_allow_flag():
    svc, _, _ = build()
    o = await svc.signup("o@b.com", "password1", "OWNER", name="n", phone="010-0000-0000")
    token = (await svc.login("o@b.com", "password1")).token
    o.status = UserStatus.APPROVED
    await svc.suspend_user(o.id, "r", None, now=T0)
    with pytest.raises(AccountSuspendedError):
        await svc.authenticate(token)
    assert (await svc.authenticate(token, allow_suspended=True)).user is o


async def test_authenticate_withdrawn_always_401():
    svc, _, _ = build()
    o = await svc.signup("o@b.com", "password1", "OWNER", name="n", phone="010-0000-0000")
    token = (await svc.login("o@b.com", "password1")).token
    await svc.withdraw_user(o.id, "r", now=T0)
    for allow in (False, True):
        with pytest.raises(AuthenticationError, match="유효하지 않은 토큰입니다."):
            await svc.authenticate(token, allow_suspended=allow)


async def test_authenticate_expired_suspension_passes():
    svc, _, _ = build()
    c = await svc.signup("c@b.com", "password1", "CUSTOMER", name="n", phone="010-0000-0000")
    token = (await svc.login("c@b.com", "password1")).token
    await svc.suspend_user(c.id, "r", T0 + timedelta(hours=1), now=T0)
    with pytest.raises(AccountSuspendedError):
        await svc.authenticate(token)
    svc.clock.advance(hours=1)
    await svc.authenticate(token)


async def test_signup_owner_pending_customer_approved():
    svc, _, _ = build()
    assert (await svc.signup("o@b.com", "password1", "OWNER", name="n", phone="010-0000-0000")).status is UserStatus.PENDING
    assert (await svc.signup("c@b.com", "password1", "CUSTOMER", name="n", phone="010-0000-0000")).status is UserStatus.APPROVED


async def test_get_account():
    svc, _, parts = build()
    u = put(parts)
    assert await svc.get_account(u.id) is u
    with pytest.raises(UserNotFoundError):
        await svc.get_account(uuid.uuid4())
