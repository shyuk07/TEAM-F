import uuid

import httpx
import pytest
from fastapi import FastAPI

from auth.domain.user import Role, User
from auth.presentation.dependencies import provide_auth_service
from auth.presentation.router import router
from error_handlers import register_exception_handlers
from tests.auth.test_optional_user import Env

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class PurgeCounter:
    def __init__(self, blacklist):
        self.calls = 0
        self._orig = blacklist.delete_expired
        blacklist.delete_expired = self.delete_expired

    async def delete_expired(self, now=None):
        self.calls += 1
        return 4


def add_user(env, role, email):
    u = User(email=email, password_hash="h", role=Role(role), name="n", phone="010")
    u.id = uuid.uuid4()
    u.business_number = "123-45-67890"
    env.users.items[u.id] = u
    return u


@pytest.fixture
def env():
    e = Env()
    e.admin = add_user(e, "ADMIN", "admin@b.com")
    e.owner = add_user(e, "OWNER", "o@b.com")
    return e


@pytest.fixture
async def client(env):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[provide_auth_service] = lambda: env.service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as c:
        yield c


def hdr(env, user, role):
    token, _ = env.tokens.issue(user.id, role)
    return {"Authorization": f"Bearer {token}"}


async def test_admin_get_user(client, env):
    r = await client.get(f"/v1/admin/users/{env.user.id}", headers=hdr(env, env.admin, "ADMIN"))
    assert r.status_code == 200
    assert set(r.json()) == {"id", "email", "name", "phone", "role", "users_point", "created_at", "status"}
    assert r.json()["id"] == str(env.user.id)


async def test_non_admin_forbidden(client, env):
    url = f"/v1/admin/users/{env.user.id}"
    for user, role in ((env.user, "CUSTOMER"), (env.owner, "OWNER")):
        r = await client.get(url, headers=hdr(env, user, role))
        assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"
        r = await client.post("/v1/admin/token-blacklist/purge", headers=hdr(env, user, role))
        assert r.status_code == 403


async def test_unauthenticated_and_revoked(client, env):
    url = f"/v1/admin/users/{env.user.id}"
    r = await client.get(url)
    assert r.status_code == 401 and r.json()["error_code"] == "UNAUTHORIZED"
    assert r.headers["www-authenticate"] == "Bearer"
    token, claims = env.tokens.issue(env.admin.id, "ADMIN")
    await env.service.logout(claims)
    r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401 and r.json()["error_code"] == "TOKEN_REVOKED"
    assert r.headers["www-authenticate"] == "Bearer"


async def test_unknown_user_404(client, env):
    r = await client.get(f"/v1/admin/users/{uuid.uuid4()}", headers=hdr(env, env.admin, "ADMIN"))
    assert r.status_code == 404 and r.json()["error_code"] == "NOT_FOUND"


async def test_invalid_uuid_admin_400(client, env):
    r = await client.get("/v1/admin/users/not-a-uuid", headers=hdr(env, env.admin, "ADMIN"))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


async def test_invalid_uuid_without_token_401(client):
    r = await client.get("/v1/admin/users/not-a-uuid")
    assert r.status_code == 401


async def test_purge(client, env):
    counter = PurgeCounter(env.blacklist)
    r = await client.post("/v1/admin/token-blacklist/purge", headers=hdr(env, env.admin, "ADMIN"))
    assert r.status_code == 200 and r.json() == {"deleted_count": 4}
    assert counter.calls == 1
    r = await client.post("/v1/admin/token-blacklist/purge")
    assert r.status_code == 401 and counter.calls == 1
