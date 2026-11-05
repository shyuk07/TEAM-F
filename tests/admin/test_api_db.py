"""admin 9개 EP DB 테스트 (admin.md 6.2, 9절). skip은 통과가 아니다 (R16).

ADMIN 계정은 가입 경로가 없으므로 기존 ensure_admin 경로로 만든다 (D29).
EP 4는 DELETE 본문이 있어 client.request("DELETE", ..., json=)을 쓴다 (B-9).
예약 취소·남은 예약 검사의 DB 통합은 tests/reservations/test_withdrawal_db.py에서 한다.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from auth.infrastructure import models as auth_models  # noqa: F401
from auth.infrastructure.models import PointLogModel, UserModel
from catalog.infrastructure import models as catalog_models
from container import build_auth_service
from stores.infrastructure import models as stores_models
from tests.catalog.test_api_db import make_offer, make_product, owner_with_store
from tests.helpers import bearer, login, signup, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]

ADMIN_EMAIL = "root@test.com"
ADMIN_PASSWORD = "adminpass123"
H = timedelta(hours=1)


# ── 헬퍼 ──
async def admin_headers(c):
    async with c.session_factory() as s:
        await build_auth_service(s).ensure_admin(ADMIN_EMAIL, ADMIN_PASSWORD)
    r = await login(c, ADMIN_EMAIL, ADMIN_PASSWORD)
    assert r.status_code == 200, r.text
    return bearer(r.json()["access_token"])


async def user_id(c, email):
    async with c.session_factory() as s:
        return (await s.execute(select(UserModel.id).where(UserModel.email == email))).scalar_one()


async def customer(c, email="cust@test.com"):
    await signup(c, email, "CUSTOMER")
    return str(await user_id(c, email))


async def pending_owner(c, email="pend@test.com"):
    await signup(c, email, "OWNER")
    return str(await user_id(c, email))


def assert_error(r, status, error_code, message=None):
    assert r.status_code == status, r.text
    body = r.json()
    assert set(body) == {"success", "error_code", "message"}
    assert body["success"] is False and body["error_code"] == error_code
    if message is not None:
        assert body["message"] == message


async def store_row(c, store_id):
    async with c.session_factory() as s:
        return await s.get(stores_models.StoreModel, uuid.UUID(store_id))


async def user_row(c, uid):
    async with c.session_factory() as s:
        return await s.get(UserModel, uuid.UUID(str(uid)))


async def offer_row(c, offer_id):
    async with c.session_factory() as s:
        return await s.get(catalog_models.DiscountOfferModel, uuid.UUID(offer_id))


# ── 인증·권한: 9개 EP 전부 ──
RANDOM = "00000000-0000-4000-8000-000000000001"
ENDPOINTS = [
    ("PATCH", f"/v1/admin/owners/{RANDOM}/approve", None),
    ("PATCH", f"/v1/admin/owners/{RANDOM}/reject", {"reason": "x"}),
    ("PATCH", f"/v1/admin/users/{RANDOM}/suspend", {"reason": "x"}),
    ("DELETE", f"/v1/admin/users/{RANDOM}", {"reason": "x"}),
    ("PATCH", f"/v1/admin/stores/{RANDOM}/suspend", {"reason": "x"}),
    ("PATCH", f"/v1/admin/stores/{RANDOM}/close", {"reason": "x"}),
    ("PATCH", f"/v1/admin/offers/{RANDOM}/suspend", {"reason": "x"}),
    ("GET", f"/v1/admin/users/{RANDOM}/points", None),
    ("POST", f"/v1/admin/users/{RANDOM}/points", {"amount": 1, "reason": "x"}),
]


@pytest.mark.parametrize("method,url,body", ENDPOINTS)
async def test_requires_login(client, method, url, body):
    r = await client.request(method, url, json=body)
    assert_error(r, 401, "UNAUTHORIZED")
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("role", ["CUSTOMER", "OWNER"])
@pytest.mark.parametrize("method,url,body", ENDPOINTS)
async def test_non_admin_forbidden(client, method, url, body, role):
    token = await token_for(client, "x@test.com", role)
    r = await client.request(method, url, json=body, headers=bearer(token))
    assert_error(r, 403, "FORBIDDEN")


@pytest.mark.parametrize("method,url,body", ENDPOINTS)
async def test_unknown_target_404(client, method, url, body):
    h = await admin_headers(client)
    r = await client.request(method, url, json=body, headers=h)
    assert_error(r, 404, "NOT_FOUND")


@pytest.mark.parametrize("method,url,body", ENDPOINTS)
async def test_invalid_uuid_400(client, method, url, body):
    h = await admin_headers(client)
    r = await client.request(method, url.replace(RANDOM, "not-a-uuid"), json=body, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR")


async def test_old_prefix_is_gone_and_auth_admin_endpoints_coexist(client):
    h = await admin_headers(client)
    cid = await customer(client)
    assert (await client.patch(f"/admin/owners/{RANDOM}/approve", headers=h)).status_code == 404
    r = await client.get(f"/v1/admin/users/{cid}", headers=h)  # auth 라우터의 기존 EP (D42)
    assert r.status_code == 200 and r.json()["id"] == cid
    r = await client.post("/v1/admin/token-blacklist/purge", headers=h)
    assert r.status_code == 200
    r = await client.request("DELETE", f"/v1/admin/users/{cid}", json={"reason": "탈퇴"}, headers=h)
    assert r.status_code == 200  # 같은 경로, 다른 메서드


# ── EP 1 ──
async def test_approve_owner(client):
    h = await admin_headers(client)
    oid = await pending_owner(client)
    r = await client.patch(f"/v1/admin/owners/{oid}/approve", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"id", "email", "name", "role", "status", "approved_at"}
    assert body["id"] == oid and body["role"] == "OWNER" and body["status"] == "APPROVED"
    assert body["approved_at"] is not None
    # 승인 후 상점 개설 가능, 두 번째 승인은 400
    token = (await login(client, "pend@test.com")).json()["access_token"]
    r = await client.post("/v1/stores", json={"pickup_address": "서울"}, headers=bearer(token))
    assert r.status_code == 201
    r = await client.patch(f"/v1/admin/owners/{oid}/approve", headers=h)
    assert_error(r, 400, "OWNER_NOT_PENDING", "승인 대기 중인 상점주가 아닙니다.")


async def test_approve_non_owner_is_404(client):
    h = await admin_headers(client)
    cid = await customer(client)
    r = await client.patch(f"/v1/admin/owners/{cid}/approve", headers=h)
    assert_error(r, 404, "NOT_FOUND", "상점주를 찾을 수 없습니다.")


# ── EP 2 ──
async def test_reject_owner(client):
    h = await admin_headers(client)
    oid = await pending_owner(client)
    r = await client.patch(f"/v1/admin/owners/{oid}/reject", json={"reason": " 서류 미비 "}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "id", "email", "name", "role", "status", "rejected_reason", "rejected_at",
    }
    assert body["status"] == "REJECTED" and body["rejected_reason"] == "서류 미비"
    assert body["rejected_at"] is not None
    r = await client.patch(f"/v1/admin/owners/{oid}/reject", json={"reason": "again"}, headers=h)
    assert_error(r, 400, "OWNER_NOT_PENDING")
    r = await client.patch(f"/v1/admin/owners/{oid}/approve", headers=h)
    assert_error(r, 400, "OWNER_NOT_PENDING")  # REJECTED는 종단


async def test_reject_owner_empty_reason_checked_before_state(client):
    h = await admin_headers(client)
    oid = await pending_owner(client)
    r = await client.patch(f"/v1/admin/owners/{oid}/reject", json={"reason": "  "}, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR", "거부 사유를 입력해 주세요.")
    r = await client.patch(f"/v1/admin/owners/{oid}/reject", json={}, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR")


# ── EP 3 ──
async def test_suspend_customer_blocks_login(client):
    h = await admin_headers(client)
    cid = await customer(client)
    until = (datetime.now(timezone.utc) + 2 * H).isoformat()
    r = await client.patch(
        f"/v1/admin/users/{cid}/suspend", json={"reason": " 스팸 ", "suspended_until": until}, headers=h
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "id", "email", "role", "status", "suspended_reason", "suspended_at", "suspended_until",
    }
    assert body["status"] == "SUSPENDED" and body["suspended_reason"] == "스팸"
    assert body["suspended_until"] is not None
    r = await login(client, "cust@test.com")
    assert_error(r, 403, "FORBIDDEN", "정지된 계정입니다.")
    r = await login(client, "cust@test.com", "wrong-password")
    assert_error(r, 401, "INVALID_CREDENTIALS")  # 계정 열거 방지 (D8)


async def test_suspended_token_blocked_on_protected_api(client):
    h = await admin_headers(client)
    cid = await customer(client)
    token = (await login(client, "cust@test.com")).json()["access_token"]
    r = await client.patch(f"/v1/admin/users/{cid}/suspend", json={"reason": "x"}, headers=h)
    assert r.status_code == 200
    r = await client.get("/v1/users/me/points", headers=bearer(token))
    assert_error(r, 403, "FORBIDDEN", "정지된 계정입니다.")


async def test_suspend_errors(client):
    h = await admin_headers(client)
    cid = await customer(client)
    url = f"/v1/admin/users/{cid}/suspend"
    r = await client.patch(url, json={"reason": " "}, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR", "정지 사유를 입력해 주세요.")
    past = (datetime.now(timezone.utc) - H).isoformat()
    r = await client.patch(url, json={"reason": "x", "suspended_until": past}, headers=h)
    assert_error(r, 400, "INVALID_SUSPENSION_END", "정지 종료 시각은 현재 이후여야 합니다.")
    naive = (datetime.now() + 2 * H).replace(tzinfo=None).isoformat()
    r = await client.patch(url, json={"reason": "x", "suspended_until": naive}, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR")
    assert (await client.patch(url, json={"reason": "x"}, headers=h)).status_code == 200
    r = await client.patch(url, json={"reason": "x"}, headers=h)
    assert_error(r, 400, "USER_ALREADY_SUSPENDED", "이미 정지된 회원입니다.")


async def test_suspend_admin_withdrawn_and_pending_owner_rejected(client):
    h = await admin_headers(client)
    admin_id = str(await user_id(client, ADMIN_EMAIL))
    r = await client.patch(f"/v1/admin/users/{admin_id}/suspend", json={"reason": "x"}, headers=h)
    assert_error(r, 400, "ADMIN_ACCOUNT_PROTECTED", "관리자 계정은 정지할 수 없습니다.")
    oid = await pending_owner(client)
    r = await client.patch(f"/v1/admin/users/{oid}/suspend", json={"reason": "x"}, headers=h)
    assert_error(r, 400, "USER_NOT_SUSPENDABLE", "승인된 회원만 정지할 수 있습니다.")
    cid = await customer(client)
    r = await client.request("DELETE", f"/v1/admin/users/{cid}", json={"reason": "x"}, headers=h)
    assert r.status_code == 200
    r = await client.patch(f"/v1/admin/users/{cid}/suspend", json={"reason": "x"}, headers=h)
    assert_error(r, 400, "USER_WITHDRAWN", "탈퇴한 회원입니다.")


async def test_suspend_owner_cascades_to_store_and_login_rules(client):
    h = await admin_headers(client)
    token, store_id = await owner_with_store(client, "owner@test.com")
    oid = str(await user_id(client, "owner@test.com"))
    r = await client.patch(f"/v1/admin/users/{oid}/suspend", json={"reason": "위반"}, headers=h)
    assert r.status_code == 200, r.text
    store = await store_row(client, store_id)
    assert store.suspended_at is not None and store.suspended_reason == "위반"
    # 정지된 OWNER는 로그인 가능(D39), status로 정지를 알린다(D40)
    r = await login(client, "owner@test.com")
    assert r.status_code == 200 and r.json()["status"] == "SUSPENDED"
    # 그 토큰으로도 일반 보호 API는 403 (D35: 픽업 EP만 예외)
    r = await client.get("/v1/users/me/points", headers=bearer(r.json()["access_token"]))
    assert_error(r, 403, "FORBIDDEN", "정지된 계정입니다.")
    r = await client.get("/v1/users/me/points", headers=bearer(token))
    assert_error(r, 403, "FORBIDDEN")


async def test_suspend_owner_with_closed_or_suspended_store_skips_cascade(client):
    h = await admin_headers(client)
    _, store_id = await owner_with_store(client, "owner@test.com")
    r = await client.patch(f"/v1/admin/stores/{store_id}/suspend", json={"reason": "먼저"}, headers=h)
    assert r.status_code == 200
    before = (await store_row(client, store_id)).suspended_at
    oid = str(await user_id(client, "owner@test.com"))
    r = await client.patch(f"/v1/admin/users/{oid}/suspend", json={"reason": "나중"}, headers=h)
    assert r.status_code == 200  # 이미 정지된 상점은 건너뜀 (D11)
    store = await store_row(client, store_id)
    assert store.suspended_at == before and store.suspended_reason == "먼저"


async def test_owner_without_store_suspend_ok(client):
    h = await admin_headers(client)
    await token_for(client, "o2@test.com", "OWNER")
    oid = str(await user_id(client, "o2@test.com"))
    r = await client.patch(f"/v1/admin/users/{oid}/suspend", json={"reason": "x"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "SUSPENDED"


async def test_expired_suspension_allows_login_again(client):
    h = await admin_headers(client)
    cid = await customer(client)
    until = (datetime.now(timezone.utc) + 2 * H).isoformat()
    r = await client.patch(
        f"/v1/admin/users/{cid}/suspend", json={"reason": "x", "suspended_until": until}, headers=h
    )
    assert r.status_code == 200
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    async with client.session_factory() as s:
        await s.execute(
            text("UPDATE users SET suspended_until = :u, suspended_at = :a WHERE id = :i"),
            {"u": past, "a": past - H, "i": uuid.UUID(cid)},
        )
        await s.commit()
    r = await login(client, "cust@test.com")
    assert r.status_code == 200 and r.json()["status"] == "APPROVED"


# ── EP 4 ──
async def test_withdraw_customer(client):
    h = await admin_headers(client)
    cid = await customer(client)
    r = await client.request("DELETE", f"/v1/admin/users/{cid}", json={"reason": " 약관 위반 "}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"id", "status", "deleted_at", "cancelled_reservation_count"}
    assert body["status"] == "WITHDRAWN" and body["deleted_at"] is not None
    assert body["cancelled_reservation_count"] == 0  # 예약이 없는 회원
    row = await user_row(client, cid)
    assert row.status == "WITHDRAWN" and row.deleted_reason == "약관 위반"
    assert_error(await login(client, "cust@test.com"), 401, "INVALID_CREDENTIALS")
    r = await signup(client, "cust@test.com", "CUSTOMER")
    assert r.status_code == 409  # soft delete라 행이 남는다 (D9)


async def test_withdraw_errors(client):
    h = await admin_headers(client)
    cid = await customer(client)
    url = f"/v1/admin/users/{cid}"
    r = await client.request("DELETE", url, json={"reason": ""}, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR", "탈퇴 사유를 입력해 주세요.")
    r = await client.request("DELETE", url, json={}, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR")
    assert (await client.request("DELETE", url, json={"reason": "x"}, headers=h)).status_code == 200
    r = await client.request("DELETE", url, json={"reason": "x"}, headers=h)
    assert_error(r, 400, "USER_ALREADY_WITHDRAWN", "이미 탈퇴한 회원입니다.")
    admin_id = str(await user_id(client, ADMIN_EMAIL))
    r = await client.request("DELETE", f"/v1/admin/users/{admin_id}", json={"reason": "x"}, headers=h)
    assert_error(r, 400, "ADMIN_ACCOUNT_PROTECTED", "관리자 계정은 탈퇴시킬 수 없습니다.")
    assert (await user_row(client, admin_id)).status == "APPROVED"


async def test_withdraw_owner_closes_store_and_ends_sales(client):
    h = await admin_headers(client)
    token, store_id = await owner_with_store(client, "owner@test.com")
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    oid = str(await user_id(client, "owner@test.com"))
    r = await client.request("DELETE", f"/v1/admin/users/{oid}", json={"reason": "폐업"}, headers=h)
    assert r.status_code == 200, r.text
    store = await store_row(client, store_id)
    assert store.closed_at is not None and store.closed_reason == "폐업"
    offer = await offer_row(client, o["id"])
    assert offer.is_active is False and offer.status == "CLOSED"
    assert (await user_row(client, oid)).status == "WITHDRAWN"


async def test_withdraw_owner_without_store_and_with_closed_store(client):
    h = await admin_headers(client)
    await token_for(client, "o2@test.com", "OWNER")
    o2 = str(await user_id(client, "o2@test.com"))
    r = await client.request("DELETE", f"/v1/admin/users/{o2}", json={"reason": "x"}, headers=h)
    assert r.status_code == 200
    _, store_id = await owner_with_store(client, "owner@test.com")
    assert (
        await client.patch(f"/v1/admin/stores/{store_id}/close", json={"reason": "먼저"}, headers=h)
    ).status_code == 200
    oid = str(await user_id(client, "owner@test.com"))
    r = await client.request("DELETE", f"/v1/admin/users/{oid}", json={"reason": "나중"}, headers=h)
    assert r.status_code == 200
    assert (await store_row(client, store_id)).closed_reason == "먼저"  # 이미 폐점이면 건드리지 않는다


# ── EP 5 ──
async def test_suspend_store(client):
    h = await admin_headers(client)
    _, store_id = await owner_with_store(client, "owner@test.com")
    r = await client.patch(f"/v1/admin/stores/{store_id}/suspend", json={"reason": " 위생 "}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"id", "owner_id", "name", "status", "suspended_reason", "suspended_at"}
    assert body["id"] == store_id and body["status"] == "SUSPENDED"
    assert body["suspended_reason"] == "위생" and body["owner_id"] == str(
        await user_id(client, "owner@test.com")
    )
    r = await client.patch(f"/v1/admin/stores/{store_id}/suspend", json={"reason": "x"}, headers=h)
    assert_error(r, 400, "STORE_ALREADY_SUSPENDED", "이미 정지된 상점입니다.")


async def test_suspend_store_errors(client):
    h = await admin_headers(client)
    _, store_id = await owner_with_store(client, "owner@test.com")
    url = f"/v1/admin/stores/{store_id}/suspend"
    assert_error(
        await client.patch(url, json={"reason": ""}, headers=h),
        400, "VALIDATION_ERROR", "정지 사유를 입력해 주세요.",
    )
    assert (
        await client.patch(f"/v1/admin/stores/{store_id}/close", json={"reason": "x"}, headers=h)
    ).status_code == 200
    assert_error(
        await client.patch(url, json={"reason": "x"}, headers=h),
        400, "STORE_CLOSED", "폐점된 상점입니다.",
    )
    unknown = await client.patch(
        f"/v1/admin/stores/{RANDOM}/suspend", json={"reason": "x"}, headers=h
    )
    assert_error(unknown, 404, "NOT_FOUND", "상점을 찾을 수 없습니다.")


# ── EP 6 ──
async def test_close_store_ends_open_offers(client):
    h = await admin_headers(client)
    token, store_id = await owner_with_store(client, "owner@test.com")
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    r = await client.patch(f"/v1/admin/stores/{store_id}/close", json={"reason": " 폐업 "}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"id", "owner_id", "name", "status", "closed_reason", "closed_at"}
    assert body["status"] == "CLOSED" and body["closed_reason"] == "폐업"
    offer = await offer_row(client, o["id"])
    assert offer.is_active is False and offer.status == "CLOSED"
    assert offer.remaining_stock == offer.initial_stock  # 재고 불변 (D18)


async def test_close_suspended_store_allowed_and_errors(client):
    h = await admin_headers(client)
    _, store_id = await owner_with_store(client, "owner@test.com")
    url = f"/v1/admin/stores/{store_id}/close"
    assert_error(
        await client.patch(url, json={"reason": " "}, headers=h),
        400, "VALIDATION_ERROR", "폐점 사유를 입력해 주세요.",
    )
    assert (
        await client.patch(f"/v1/admin/stores/{store_id}/suspend", json={"reason": "x"}, headers=h)
    ).status_code == 200
    r = await client.patch(url, json={"reason": "폐업"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "CLOSED"
    assert_error(
        await client.patch(url, json={"reason": "again"}, headers=h),
        400, "STORE_ALREADY_CLOSED", "이미 폐점된 상점입니다.",
    )


# ── EP 7 ──
async def test_suspend_offer(client):
    h = await admin_headers(client)
    token, store_id = await owner_with_store(client, "owner@test.com")
    p = await make_product(client, token, store_id, name="샌드위치")
    o = await make_offer(client, token, p["id"])
    r = await client.patch(f"/v1/admin/offers/{o['id']}/suspend", json={"reason": " 위생 "}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"id", "store_id", "title", "status", "suspended_reason", "suspended_at"}
    assert body["id"] == o["id"] and body["store_id"] == store_id
    assert body["title"] == "샌드위치" and body["status"] == "SUSPENDED"
    assert body["suspended_reason"] == "위생"
    r = await client.patch(f"/v1/admin/offers/{o['id']}/suspend", json={"reason": "x"}, headers=h)
    assert_error(r, 400, "OFFER_ALREADY_SUSPENDED", "이미 정지된 상품입니다.")


async def test_suspend_offer_errors(client):
    h = await admin_headers(client)
    token, store_id = await owner_with_store(client, "owner@test.com")
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    url = f"/v1/admin/offers/{o['id']}/suspend"
    assert_error(
        await client.patch(url, json={"reason": ""}, headers=h),
        400, "VALIDATION_ERROR", "정지 사유를 입력해 주세요.",
    )
    r = await client.post(
        f"/v1/offers/{o['id']}/deactivate", json={"reason": "품절"}, headers=bearer(token)
    )
    assert r.status_code == 200, r.text
    assert_error(
        await client.patch(url, json={"reason": "x"}, headers=h),
        400, "OFFER_SALES_ENDED", "판매가 종료된 상품입니다.",
    )


# ── EP 8, 9 ──
async def test_grant_and_list_points(client):
    h = await admin_headers(client)
    admin_id = str(await user_id(client, ADMIN_EMAIL))
    cid = await customer(client)
    r = await client.post(
        f"/v1/admin/users/{cid}/points", json={"amount": 500, "reason": " 이벤트 "}, headers=h
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {
        "id", "user_id", "amount", "type", "reason", "balance_after", "created_by", "created_at",
    }
    assert body["user_id"] == cid and body["amount"] == 500 and body["type"] == "GRANT"
    assert body["reason"] == "이벤트" and body["balance_after"] == 500
    assert body["created_by"] == admin_id
    r = await client.post(
        f"/v1/admin/users/{cid}/points", json={"amount": 300, "reason": "추가"}, headers=h
    )
    assert r.status_code == 201 and r.json()["balance_after"] == 800
    r = await client.get(f"/v1/admin/users/{cid}/points", headers=h)
    assert r.status_code == 200, r.text
    page = r.json()
    assert set(page) == {"user_id", "balance", "history", "page", "size", "total"}
    assert page["balance"] == 800 and page["total"] == 2 and page["page"] == 1 and page["size"] == 20
    assert [i["amount"] for i in page["history"]] == [300, 500]  # 최신순
    assert set(page["history"][0]) == {
        "id", "amount", "type", "reason", "balance_after", "created_by", "created_at",
    }
    r = await client.get(f"/v1/admin/users/{cid}/points?page=2&size=1", headers=h)
    assert [i["amount"] for i in r.json()["history"]] == [500] and r.json()["total"] == 2
    r = await client.get(f"/v1/admin/users/{cid}/points?page=3&size=1", headers=h)
    assert r.status_code == 200 and r.json()["history"] == []


async def test_grant_points_balance_and_log_are_consistent_in_db(client):
    h = await admin_headers(client)
    cid = await customer(client)
    await client.post(f"/v1/admin/users/{cid}/points", json={"amount": 70, "reason": "a"}, headers=h)
    async with client.session_factory() as s:
        user = await s.get(UserModel, uuid.UUID(cid))
        logs = (await s.execute(select(PointLogModel).where(PointLogModel.user_id == user.id))).scalars().all()
    assert user.users_point == 70 and len(logs) == 1 and logs[0].balance_after == 70


async def test_list_points_errors(client):
    h = await admin_headers(client)
    cid = await customer(client)
    for q in ("page=0", "size=0", "size=101", "page=-1"):
        r = await client.get(f"/v1/admin/users/{cid}/points?{q}", headers=h)
        assert_error(r, 400, "INVALID_PAGE", "페이지 값이 올바르지 않습니다.")
    r = await client.get(f"/v1/admin/users/{cid}/points?page=abc", headers=h)
    assert_error(r, 400, "VALIDATION_ERROR")
    r = await client.get(f"/v1/admin/users/{RANDOM}/points", headers=h)
    assert_error(r, 404, "NOT_FOUND", "회원을 찾을 수 없습니다.")


async def test_grant_points_errors(client):
    h = await admin_headers(client)
    cid = await customer(client)
    url = f"/v1/admin/users/{cid}/points"
    for amount in (0, -5):
        r = await client.post(url, json={"amount": amount, "reason": "x"}, headers=h)
        assert_error(r, 400, "VALIDATION_ERROR", "지급 포인트는 1 이상이어야 합니다.")
    r = await client.post(url, json={"amount": 10, "reason": "  "}, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR", "지급 사유를 입력해 주세요.")
    r = await client.post(url, json={"amount": "ten", "reason": "x"}, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR")
    r = await client.post(url, json={"amount": 2_147_483_647, "reason": "x"}, headers=h)
    assert r.status_code == 201
    r = await client.post(url, json={"amount": 1, "reason": "x"}, headers=h)
    assert_error(r, 400, "VALIDATION_ERROR", "포인트 잔액이 한도를 넘습니다.")
    assert (await user_row(client, cid)).users_point == 2_147_483_647  # 실패한 지급은 반영 안 됨


async def test_grant_points_to_withdrawn_user_rejected(client):
    h = await admin_headers(client)
    cid = await customer(client)
    await client.request("DELETE", f"/v1/admin/users/{cid}", json={"reason": "x"}, headers=h)
    r = await client.post(f"/v1/admin/users/{cid}/points", json={"amount": 5, "reason": "x"}, headers=h)
    assert_error(r, 400, "USER_WITHDRAWN", "탈퇴한 회원입니다.")
