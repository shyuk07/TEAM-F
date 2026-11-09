"""GET /v1/stores/me (stores.md 17.6, T1~T11). PostgreSQL 필요."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import text

from auth.infrastructure import models as auth_models  # noqa: F401
from catalog.infrastructure import models as catalog_models  # noqa: F401
from stores.infrastructure import models as stores_models  # noqa: F401
from tests.admin.test_api_db import admin_headers
from tests.catalog.test_admin_api_db import suspend_store_row
from tests.catalog.test_api_db import owner_with_store
from tests.helpers import bearer, login, signup, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]

KEYS = {
    "id", "owner_id", "name", "pickup_address", "latitude", "longitude",
    "created_at", "approval_at", "closed_at", "status",
}
NOT_FOUND = {"success": False, "error_code": "NOT_FOUND", "message": "상점을 찾을 수 없습니다."}


async def _me(c, token=None):
    return await c.get("/v1/stores/me", headers=bearer(token) if token else {})


async def _sql(c, sql, **params):
    async with c.session_factory() as s:
        await s.execute(text(sql), params)
        await s.commit()


async def test_my_store_ok(client):  # T1, T11
    token, sid = await owner_with_store(client)
    r = await _me(client, token)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == KEYS
    assert body["status"] == "ACTIVE" and body["id"] == sid and body["closed_at"] is None
    assert datetime.fromisoformat(body["created_at"]).tzinfo is not None
    assert datetime.fromisoformat(body["approval_at"]).tzinfo is not None
    # 기존 /stores/{store_id}/... 경로는 그대로 동작한다 (me가 가로채지 않음)
    r2 = await client.get(f"/v1/stores/{sid}/products", headers=bearer(token))
    assert r2.status_code == 200, r2.text


async def test_my_store_unauthorized(client):  # T2
    r = await _me(client)
    assert r.status_code == 401 and r.json()["success"] is False
    assert r.headers["www-authenticate"] == "Bearer"


async def test_my_store_customer_and_admin_forbidden(client):  # T3
    token = await token_for(client, "c@test.com", "CUSTOMER")
    r = await _me(client, token)
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"
    assert r.json()["success"] is False
    r = await client.get("/v1/stores/me", headers=await admin_headers(client))  # 실제 관리자 토큰
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"


async def test_my_store_suspended_owner_account_allowed(client):  # T4
    token, sid = await owner_with_store(client)
    await _sql(
        client,
        "UPDATE users SET status='SUSPENDED', suspended_reason='x', suspended_at=now() "
        "WHERE email='owner@test.com'",
    )
    r = await _me(client, token)
    assert r.status_code == 200, r.text
    assert r.json()["id"] == sid
    close = await client.post(f"/v1/stores/{sid}/close", headers=bearer(token))
    assert close.status_code == 403 and close.json()["message"] == "정지된 계정입니다."


async def test_my_store_missing_is_404(client):  # T5
    token = await token_for(client, "o@test.com", "OWNER")
    r = await _me(client, token)
    assert r.status_code == 404 and r.json() == NOT_FOUND
    await signup(client, "p@test.com", "OWNER")  # PENDING
    pending = (await login(client, "p@test.com")).json()["access_token"]
    r = await _me(client, pending)
    assert r.status_code == 404 and r.json() == NOT_FOUND


async def test_my_store_closed(client):  # T6
    token, sid = await owner_with_store(client)
    assert (await client.post(f"/v1/stores/{sid}/close", headers=bearer(token))).status_code == 200
    r = await _me(client, token)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CLOSED" and r.json()["closed_at"] is not None


async def test_my_store_suspended_hides_reason(client):  # T7
    token, sid = await owner_with_store(client)
    await suspend_store_row(client, sid)
    r = await _me(client, token)
    assert r.status_code == 200, r.text
    assert set(r.json()) == KEYS and r.json()["status"] == "SUSPENDED"
    assert "정책 위반" not in r.text


async def test_my_store_closed_beats_suspended(client):  # T8
    token, sid = await owner_with_store(client)
    await suspend_store_row(client, sid)
    await _sql(client, "UPDATE stores SET closed_at=now() WHERE id=:i", i=uuid.UUID(sid))
    r = await _me(client, token)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CLOSED"


async def test_my_store_each_owner_gets_own(client):  # T9
    ta, sa = await owner_with_store(client, "a@test.com")
    tb, sb = await owner_with_store(client, "b@test.com")
    assert sa != sb
    assert (await _me(client, ta)).json()["id"] == sa
    assert (await _me(client, tb)).json()["id"] == sb


async def test_my_store_null_coordinates(client):  # T10
    token, sid = await owner_with_store(client)
    await _sql(
        client, "UPDATE stores SET latitude=NULL, longitude=NULL WHERE id=:i", i=uuid.UUID(sid)
    )
    r = await _me(client, token)
    assert r.status_code == 200, r.text
    assert r.json()["latitude"] is None and r.json()["longitude"] is None
