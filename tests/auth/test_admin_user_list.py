"""관리자 회원 목록 테스트: 도메인(T-D1), 서비스(T-S1), API(T-A1~A3). DB 테스트는 test_admin_user_list_db.py."""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI

from auth.domain.user import Role, User, UserStatus
from auth.domain.user_search import UserSearchCriteria
from auth.presentation.dependencies import provide_auth_service
from auth.presentation.router import router
from error_handlers import register_exception_handlers
from tests.auth.fakes import T0
from tests.auth.test_admin_api import add_user, hdr
from tests.auth.test_optional_user import Env

pytestmark = pytest.mark.anyio

ITEM_KEYS = {"id", "email", "name", "phone", "role", "users_point", "created_at", "status"}


@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_user(email="a@x.com", role=Role.CUSTOMER, status=UserStatus.APPROVED, until=None, created=None):
    extra = {}
    if status is UserStatus.SUSPENDED:
        extra = dict(suspended_reason="r", suspended_at=T0 - timedelta(days=30))
    u = User(email=email, password_hash="h", role=role, name="n", phone="010", status=status,
             suspended_until=until, created_at=created, **extra)
    u.id = uuid.uuid4()
    return u


# ── T-D1 도메인 ──
def test_criteria_normalizes_keyword():
    assert UserSearchCriteria.of(None, None, "  ABC@X.com ").email_keyword == "abc@x.com"


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_criteria_blank_is_none(raw):
    assert UserSearchCriteria.of(None, None, raw).email_keyword is None


def test_criteria_length_limit():
    assert UserSearchCriteria.of(None, None, "a" * 255).email_keyword == "a" * 255
    with pytest.raises(ValueError):
        UserSearchCriteria.of(None, None, "a" * 256)


@pytest.mark.parametrize("bad", ["a\x00b", "a\nb", "a\tb", "a\x7fb"])
def test_criteria_control_chars_rejected(bad):
    with pytest.raises(ValueError):
        UserSearchCriteria.of(None, None, bad)


def test_criteria_keeps_special_chars():
    assert UserSearchCriteria.of(None, None, "a%_/b @x.c").email_keyword == "a%_/b @x.c"


def test_matches_role_status_effective():
    expired = make_user(status=UserStatus.SUSPENDED, until=T0 - timedelta(days=1))
    boundary = make_user(status=UserStatus.SUSPENDED, until=T0)
    active = make_user(status=UserStatus.SUSPENDED, until=T0 + timedelta(days=1))
    approved = UserSearchCriteria.of(None, UserStatus.APPROVED, None)
    suspended = UserSearchCriteria.of(None, UserStatus.SUSPENDED, None)
    assert approved.matches(expired, T0) and approved.matches(boundary, T0)
    assert not approved.matches(active, T0)
    assert suspended.matches(active, T0) and not suspended.matches(boundary, T0)
    assert not UserSearchCriteria.of(Role.OWNER, None, None).matches(active, T0)
    assert UserSearchCriteria.of(None, None, "A@X").matches(active, T0)


# ── T-S1 서비스 ──
@pytest.fixture
def env():
    e = Env()
    e.admin = add_user(e, "ADMIN", "admin@b.com")
    e.owner = add_user(e, "OWNER", "o@b.com")
    for u in (e.user, e.admin, e.owner):
        u.created_at = T0 - timedelta(days=1)  # 목록 응답의 created_at은 필수
    return e


async def test_service_list_users_paging_and_effective_status(env):
    expired = make_user("e@x.com", status=UserStatus.SUSPENDED, until=T0 - timedelta(seconds=1),
                        created=T0 - timedelta(days=1))
    env.users.items[expired.id] = expired
    calls = []
    orig = env.users.find_page

    async def spy(criteria, *, now, offset, limit):
        calls.append((now, offset, limit))
        return await orig(criteria, now=now, offset=offset, limit=limit)

    env.users.find_page = spy
    page = await env.service.list_users(None, None, "e@x", 2, 5)
    assert calls == [(T0, 10, 5)]
    assert page.page == 2 and page.size == 5 and page.items == []
    assert page.total_elements == 1
    page = await env.service.list_users(None, UserStatus.APPROVED, "e@x", 0, 5)
    assert [i.status for i in page.items] == ["APPROVED"]


@pytest.mark.parametrize("page,size", [(-1, 20), (0, 0), (0, 101)])
async def test_service_invalid_paging(env, page, size):
    with pytest.raises(ValueError):
        await env.service.list_users(None, None, None, page, size)


# ── T-A1~A3 API ──
@pytest.fixture
async def client(env):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[provide_auth_service] = lambda: env.service
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


def admin_hdr(env):
    return hdr(env, env.admin, "ADMIN")


async def test_api_list_shape_and_no_secrets(client, env):
    r = await client.get("/v1/admin/users", headers=admin_hdr(env))
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"users", "page", "size", "total_elements"}
    assert body["page"] == 0 and body["size"] == 20 and body["total_elements"] == len(body["users"]) == 3
    for item in body["users"]:
        assert set(item) == ITEM_KEYS


async def test_api_auth_errors(client, env):
    r = await client.get("/v1/admin/users")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    r = await client.get("/v1/admin/users?size=0")
    assert r.status_code == 401
    r = await client.get("/v1/admin/users", headers=hdr(env, env.user, "CUSTOMER"))
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"


@pytest.mark.parametrize(
    "qs",
    ["role=BOSS", "status=X", "page=-1", "size=0", "size=101", "email=" + "a" * 256, "email=a%00b"],
)
async def test_api_validation_400(client, env, qs):
    r = await client.get(f"/v1/admin/users?{qs}", headers=admin_hdr(env))
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False and body["error_code"] == "VALIDATION_ERROR" and body["message"]


async def test_api_filters_forwarded_and_empty(client, env):
    r = await client.get("/v1/admin/users?role=OWNER&size=100", headers=admin_hdr(env))
    assert r.status_code == 200 and [u["email"] for u in r.json()["users"]] == ["o@b.com"]
    r = await client.get("/v1/admin/users?email=nomatch&page=3&size=5", headers=admin_hdr(env))
    assert r.status_code == 200
    assert r.json() == {"users": [], "page": 3, "size": 5, "total_elements": 0}
