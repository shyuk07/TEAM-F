import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from auth.application.service import AuthApplicationService
from auth.domain.point_log import PointType
from auth.domain.user import Role
from auth.infrastructure.settings import get_auth_settings
from main import app
from tests.helpers import bearer, login, signup, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]


async def test_signup_ok(client):
    r = await signup(client, phone="010-1234-5678")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "user@test.com" and body["users_point"] == 0
    assert body["role"] == "CUSTOMER" and "password_hash" not in body
    uuid.UUID(body["id"])
    assert datetime.fromisoformat(body["created_at"]).tzinfo is not None


async def test_signup_owner_ok(client):
    assert (await signup(client, role="OWNER")).json()["role"] == "OWNER"


async def test_signup_errors(client):
    for payload in [
        {"email": "a@b.com", "password": "password123", "role": "ADMIN"},
        {"email": "a@b.com", "password": "password123"},
        {"password": "password123", "role": "CUSTOMER"},
        {"email": "a@b.com", "password": "short", "role": "CUSTOMER"},
        {"email": "not-an-email", "password": "password123", "role": "CUSTOMER"},
        {"email": "a@b.com", "password": "password123", "role": "HACKER"},
    ]:
        r = await client.post("/v1/auth/signup", json=payload)
        assert r.status_code == 400, payload
        assert r.json()["error_code"] == "VALIDATION_ERROR"
        assert r.json()["success"] is False


async def test_signup_duplicate_case_insensitive(client):
    await signup(client, "user@test.com")
    r = await signup(client, "USER@Test.com")
    assert r.status_code == 409
    assert r.json() == {
        "success": False, "error_code": "EMAIL_DUPLICATED", "message": "이미 가입된 이메일입니다."
    }


async def test_login_ok_and_token_content(client):
    await signup(client)
    r = await login(client)
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    payload = jwt.decode(r.json()["access_token"], get_auth_settings().secret_key,
                         algorithms=["HS256"])
    assert payload["role"] == "CUSTOMER" and payload["jti"]
    assert 29 * 60 < payload["exp"] - datetime.now(timezone.utc).timestamp() <= 30 * 60


async def test_login_failures_identical(client):
    await signup(client)
    wrong = await login(client, password="wrongpass1")
    unknown = await login(client, email="none@test.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["error_code"] == "INVALID_CREDENTIALS"
    assert wrong.json()["message"] == "이메일 또는 비밀번호가 올바르지 않습니다."


async def test_login_missing_fields(client):
    r = await client.post("/v1/auth/login", json={"email": "a@b.com"})
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


async def test_login_form_rejected(client):
    await signup(client)
    r = await client.post(
        "/v1/auth/login", data={"username": "user@test.com", "password": "password123"}
    )
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


async def test_basic_scheme_is_unauthorized(client):
    token = await token_for(client)
    r = await client.get("/v1/users/me", headers={"Authorization": f"Basic {token}"})
    assert r.status_code == 401 and r.json()["error_code"] == "UNAUTHORIZED"
    assert r.json()["message"] == "로그인이 필요합니다."
    assert r.headers["www-authenticate"] == "Bearer"


async def test_me(client):
    token = await token_for(client)
    r = await client.get("/v1/users/me", headers=bearer(token))
    assert r.status_code == 200
    assert r.json()["email"] == "user@test.com" and "business_number" not in r.json()


async def test_me_unauthorized_variants(client):
    r = await client.get("/v1/users/me")
    assert r.status_code == 401 and r.json()["error_code"] == "UNAUTHORIZED"
    assert r.json()["message"] == "로그인이 필요합니다."
    assert r.headers["www-authenticate"] == "Bearer"
    assert (await client.get("/v1/users/me", headers=bearer("forged"))).status_code == 401
    secret = get_auth_settings().secret_key
    expired = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "CUSTOMER", "jti": "j",
         "exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())},
        secret, algorithm="HS256")
    r = await client.get("/v1/users/me", headers=bearer(expired))
    assert r.status_code == 401 and r.json()["error_code"] == "UNAUTHORIZED"
    wrong_secret = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "ADMIN", "jti": "j",
         "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())},
        "x" * 40, algorithm="HS256")
    assert (await client.get("/v1/users/me", headers=bearer(wrong_secret))).status_code == 401
    # 존재하지 않는 회원의 유효한 서명 토큰
    ghost = jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "CUSTOMER", "jti": "g",
         "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())},
        secret, algorithm="HS256")
    assert (await client.get("/v1/users/me", headers=bearer(ghost))).status_code == 401


async def test_logout_then_reuse(client):
    token = await token_for(client)
    assert (await client.get("/v1/users/me", headers=bearer(token))).status_code == 200
    r = await client.post("/v1/auth/logout", headers=bearer(token))
    assert r.status_code == 204 and r.content == b""
    r = await client.get("/v1/users/me", headers=bearer(token))
    assert r.status_code == 401
    assert r.json() == {
        "success": False, "error_code": "TOKEN_REVOKED", "message": "로그아웃된 토큰입니다."
    }
    r = await client.post("/v1/auth/logout", headers=bearer(token))
    assert r.status_code == 401 and r.json()["error_code"] == "TOKEN_REVOKED"
    # 다른 로그인 토큰은 계속 유효
    token2 = (await login(client)).json()["access_token"]
    assert (await client.get("/v1/users/me", headers=bearer(token2))).status_code == 200


async def test_logout_without_token(client):
    r = await client.post("/v1/auth/logout")
    assert r.status_code == 401 and r.json()["error_code"] == "UNAUTHORIZED"


async def _seed_points(client, email):
    me = (await client.get("/v1/users/me", headers=bearer(
        (await login(client, email)).json()["access_token"]))).json()
    uid = uuid.UUID(me["id"])
    async with client.session_factory() as db:
        svc = AuthApplicationService(db)
        await svc.earn_points(uid, 500)
        await svc.use_points(uid, 200)
        await svc.earn_points(uid, 40)
        await svc.restore_points(uid, 100)
        await svc.revoke_points(uid, 50)
    return uid


async def test_points_list_filter_paging(client):
    token = await token_for(client)
    await _seed_points(client, "user@test.com")
    r = await client.get("/v1/users/me/points", headers=bearer(token))
    body = r.json()
    assert r.status_code == 200
    assert body["users_point"] == 390 and body["total_elements"] == 5
    assert body["page"] == 0 and body["size"] == 20
    assert [x["point_type"] for x in body["logs"]] == ["REVOKE", "RESTORE", "EARN", "USE", "EARN"]
    assert body["logs"][3]["amount"] == -200 and body["logs"][1]["amount"] == 100
    r = await client.get("/v1/users/me/points?type=EARN", headers=bearer(token))
    assert r.json()["total_elements"] == 2 and len(r.json()["logs"]) == 2
    r = await client.get("/v1/users/me/points?page=1&size=2", headers=bearer(token))
    assert [x["point_type"] for x in r.json()["logs"]] == ["EARN", "USE"]
    assert r.json()["total_elements"] == 5
    r = await client.get("/v1/users/me/points?page=9&size=2", headers=bearer(token))
    assert r.json()["logs"] == []


@pytest.mark.parametrize("qs", ["type=BAD", "page=-1", "size=0", "size=101", "page=x"])
async def test_points_bad_query(client, qs):
    token = await token_for(client)
    r = await client.get(f"/v1/users/me/points?{qs}", headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


async def test_points_requires_auth(client):
    assert (await client.get("/v1/users/me/points")).status_code == 401


async def test_points_idor(client):
    t1 = await token_for(client, "a@test.com")
    t2 = await token_for(client, "b@test.com")
    await _seed_points(client, "a@test.com")
    body = (await client.get("/v1/users/me/points", headers=bearer(t2))).json()
    assert body["logs"] == [] and body["users_point"] == 0 and body["total_elements"] == 0
    assert (await client.get("/v1/users/me/points", headers=bearer(t1))).json()["total_elements"] == 5


async def test_require_roles(client):
    from fastapi import Depends
    from auth.presentation.dependencies import AdminUser, OwnerUser, require_roles

    @app.get("/_t/owner")
    async def owner_only(u: OwnerUser):
        return {"ok": True}

    @app.get("/_t/multi")
    async def multi(u=Depends(require_roles(Role.OWNER, Role.CUSTOMER))):
        return {"ok": True}

    @app.get("/_t/admin")
    async def admin_only(u: AdminUser):
        return {"ok": True}

    try:
        cust = await token_for(client, "c@test.com", "CUSTOMER")
        owner = await token_for(client, "o@test.com", "OWNER")
        assert (await client.get("/_t/owner", headers=bearer(owner))).status_code == 200
        r = await client.get("/_t/owner", headers=bearer(cust))
        assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"
        assert (await client.get("/_t/multi", headers=bearer(cust))).status_code == 200
        assert (await client.get("/_t/admin", headers=bearer(owner))).status_code == 403
        assert (await client.get("/_t/owner")).status_code == 401
    finally:
        app.router.routes[:] = [r for r in app.router.routes
                                if not getattr(r, "path", "").startswith("/_t/")]


async def test_concurrent_use_points_never_negative(client):
    await signup(client)
    me = (await client.get("/v1/users/me", headers=bearer(
        (await login(client)).json()["access_token"]))).json()
    uid = uuid.UUID(me["id"])
    async with client.session_factory() as db:
        await AuthApplicationService(db).earn_points(uid, 300)

    async def attempt():
        async with client.session_factory() as db:
            try:
                await AuthApplicationService(db).use_points(uid, 100)
                return True
            except ValueError:
                await db.rollback()
                return False

    results = await asyncio.gather(*(attempt() for _ in range(8)))
    assert sum(results) == 3
    async with client.session_factory() as db:
        svc = AuthApplicationService(db)
        assert (await svc.get_user(uid)).users_point == 0
        page = await svc.list_point_logs(await svc.get_user(uid), PointType.USE, 0, 100)
        assert page.total_elements == 3


async def test_purge_expired_tokens(client):
    token = await token_for(client)
    await client.post("/v1/auth/logout", headers=bearer(token))
    async with client.session_factory() as db:
        svc = AuthApplicationService(db)
        assert await svc.purge_expired_tokens() == 0
        far = datetime.now(timezone.utc) + timedelta(hours=1)
        assert await svc.purge_expired_tokens(far) == 1
