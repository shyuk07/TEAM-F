import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI

from auth.application.service import AuthApplicationService
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import PasswordHasher
from auth.domain.user import User
from auth.infrastructure.security import JwtTokenProvider
from auth.infrastructure.settings import AuthSettings
from auth.presentation.dependencies import OptionalUser, provide_auth_service
from tests.auth.fakes import FakeClock
from error_handlers import register_exception_handlers

pytestmark = pytest.mark.anyio

SECRET = "k" * 40


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeSession:
    async def commit(self):
        pass

    async def rollback(self):
        pass


class FakeHasher(PasswordHasher):
    def hash(self, raw):
        return "hashed:" + raw

    def verify(self, raw, hashed):
        return hashed == "hashed:" + raw

    def dummy_verify(self, raw):
        pass


class FakeUsers(UserRepository):
    def __init__(self):
        self.items = {}

    async def find_by_id(self, user_id, for_update=False):
        return self.items.get(user_id)

    async def find_by_email(self, email):
        return None

    async def exists_by_email(self, email):
        return False

    async def save(self, user):
        if user.id is None:
            user.id = uuid.uuid4()
        self.items[user.id] = user
        return user

    async def find_all(self, query, now):
        return []

    async def count_all(self, query, now):
        return 0


class FakeLogs(PointLogRepository):
    async def add(self, log):
        return log

    async def find_by_user(self, user_id, *, point_type=None, offset=0, limit=20):
        return []

    async def count_by_user(self, user_id, *, point_type=None):
        return 0


class FakeBlacklist(TokenBlacklistRepository):
    def __init__(self):
        self.jtis = set()

    async def add(self, token):
        self.jtis.add(token.jti)

    async def exists(self, jti):
        return jti in self.jtis

    async def delete_expired(self, now=None):
        return 0


class CountingService(AuthApplicationService):
    calls = 0

    async def authenticate(self, token, **kwargs):
        self.calls += 1
        return await super().authenticate(token, **kwargs)


class Env:
    def __init__(self):
        self.users = FakeUsers()
        self.blacklist = FakeBlacklist()
        self.tokens = JwtTokenProvider(AuthSettings(secret_key=SECRET))
        self.service = CountingService(
            FakeSession(), self.users, FakeLogs(), self.blacklist, FakeHasher(), self.tokens,
            FakeClock(),
        )
        self.user = User.register(
            email="a@b.com", password_hash="x", role="CUSTOMER", name="n", phone="010-1"
        )
        self.user.id = uuid.uuid4()
        self.users.items[self.user.id] = self.user

    def token(self, user_id=None, now=None):
        return self.tokens.issue(user_id or self.user.id, "CUSTOMER", now=now)


@pytest.fixture
def env():
    return Env()


@pytest.fixture
async def client(env):
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/probe")
    async def probe(viewer: OptionalUser):
        return {"user_id": str(viewer.id) if viewer else None}

    app.dependency_overrides[provide_auth_service] = lambda: env.service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as c:
        yield c


def assert_401(r, code, message=None):
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    body = r.json()
    assert body["success"] is False and body["error_code"] == code
    if message:
        assert body["message"] == message


async def test_t1_no_header(client, env):
    r = await client.get("/probe")
    assert r.status_code == 200 and r.json() == {"user_id": None}
    assert env.service.calls == 0


@pytest.mark.parametrize("value", ["", "   "])
async def test_t2_blank_header(client, env, value):
    r = await client.get("/probe", headers={"Authorization": value})
    assert r.status_code == 200 and r.json() == {"user_id": None}
    assert env.service.calls == 0


async def test_t3_valid_token(client, env):
    token, _ = env.token()
    r = await client.get("/probe", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and r.json() == {"user_id": str(env.user.id)}


@pytest.mark.parametrize("kind", ["wrong_key", "forged"])
async def test_t4_forged(client, env, kind):
    if kind == "forged":
        token = "forged"
    else:
        token = JwtTokenProvider(AuthSettings(secret_key="z" * 40)).issue(env.user.id, "CUSTOMER")[0]
    r = await client.get("/probe", headers={"Authorization": f"Bearer {token}"})
    assert_401(r, "UNAUTHORIZED", "유효하지 않은 토큰입니다.")


async def test_t5_expired(client, env):
    token, _ = env.token(now=datetime.now(timezone.utc) - timedelta(hours=2))
    r = await client.get("/probe", headers={"Authorization": f"Bearer {token}"})
    assert_401(r, "UNAUTHORIZED", "토큰이 만료되었습니다.")


async def test_t6_logged_out(client, env):
    token, claims = env.token()
    await env.service.logout(claims)
    r = await client.get("/probe", headers={"Authorization": f"Bearer {token}"})
    assert_401(r, "TOKEN_REVOKED")


async def test_t7_unknown_user(client, env):
    token, _ = env.token(user_id=uuid.uuid4())
    r = await client.get("/probe", headers={"Authorization": f"Bearer {token}"})
    assert_401(r, "UNAUTHORIZED", "유효하지 않은 토큰입니다.")


async def test_t8_non_bearer_scheme(client, env):
    token, _ = env.token()
    for value in (f"Basic {token}", f"Token {token}"):
        r = await client.get("/probe", headers={"Authorization": value})
        assert_401(r, "UNAUTHORIZED", "로그인이 필요합니다.")
    assert env.service.calls == 0


@pytest.mark.parametrize("value", ["Bearer", "Bearer ", "Bearer   ", "Bearer\ttok"])
async def test_t9_bearer_without_token(client, env, value):
    r = await client.get("/probe", headers={"Authorization": value})
    assert_401(r, "UNAUTHORIZED", "로그인이 필요합니다.")
    assert env.service.calls == 0


async def test_t10_lowercase_scheme(client, env):
    token, _ = env.token()
    r = await client.get("/probe", headers={"Authorization": f"bearer {token}"})
    assert r.status_code == 200 and r.json() == {"user_id": str(env.user.id)}
