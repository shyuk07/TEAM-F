"""상점주용 예약 목록 조회 API (요구조건 reservations R-REQ24·25) + 실제 PostgreSQL.

권한(본인 상점·고객·관리자·비로그인), 상태 필터, 취소 예약 포함, 페이지네이션, 빈 목록,
고객 개인정보·픽업 코드 비노출을 확인한다. 상점·상품·할인은 공개 API로, 상태별 예약은 seed()로 만든다.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from tests.helpers import bearer, token_for
from tests.reservations.test_api_db import seed, seed_offer

pytestmark = [pytest.mark.db, pytest.mark.anyio]

ALLOWED_KEYS = {"id", "product_name", "quantity", "total_price", "status", "created_at"}


def url(store_id, **params):
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"/v1/stores/{store_id}/reservations" + (f"?{query}" if query else "")


async def set_status(c, reservation_id, status):
    """취소·픽업 완료 상태 예약을 만든다(시각 컬럼을 상태에 맞춤)."""
    now = datetime.now(timezone.utc)
    cancelled = now if status == "CANCELLED" else None
    picked = now if status == "PICKED_UP" else None
    async with c.session_factory() as s:
        await s.execute(
            text(
                "UPDATE pickup_reservations SET status = :st, cancelled_at = :ca, picked_up_at = :pa "
                "WHERE id = :id"
            ),
            {"st": status, "ca": cancelled, "pa": picked, "id": uuid.UUID(reservation_id)},
        )
        await s.commit()


async def set_created_at(c, reservation_id, created_at):
    async with c.session_factory() as s:
        await s.execute(
            text("UPDATE pickup_reservations SET created_at = :t WHERE id = :id"),
            {"t": created_at, "id": uuid.UUID(reservation_id)},
        )
        await s.commit()


async def four_states(c):
    """한 상점에 상태 4가지 예약을 하나씩 만든다."""
    owner, offer_id, store_id = await seed_offer(c, stock=20)
    cust = await token_for(c, "cust@test.com")
    ids = {}
    ids["PENDING_PAYMENT"], _ = await seed(c, cust, offer_id, 1)
    ids["RESERVED"], _ = await seed(c, cust, offer_id, 2, paid=True)
    ids["PICKED_UP"], _ = await seed(c, cust, offer_id, 3, paid=True)
    await set_status(c, ids["PICKED_UP"], "PICKED_UP")
    ids["CANCELLED"], _ = await seed(c, cust, offer_id, 4)
    await set_status(c, ids["CANCELLED"], "CANCELLED")
    return owner, store_id, ids


# 1, 7, 10, 11
async def test_owner_lists_own_store_all_statuses_without_private_fields(client):
    owner, store_id, ids = await four_states(client)
    r = await client.get(url(store_id), headers=bearer(owner))
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"reservations", "page", "size", "total"}
    assert body["page"] == 1 and body["size"] == 20 and body["total"] == 4
    got = {item["id"]: item for item in body["reservations"]}
    assert set(got) == set(ids.values())
    assert {item["status"] for item in got.values()} == set(ids)  # 취소 예약 포함
    for item in body["reservations"]:
        assert set(item) == ALLOWED_KEYS  # 고객 ID·이메일·전화번호·픽업 코드·주소 없음
        assert item["product_name"] == "샌드위치"
        assert item["total_price"] == 3000 * item["quantity"]
    raw = r.text
    for secret in ("cust@test.com", "010-0000-0000", "AB3DE9", "pickup_code", "user_id", "email", "phone"):
        assert secret not in raw


# 2
async def test_other_owner_is_forbidden_and_unknown_store_is_404(client):
    _, _, store_id = await seed_offer(client, email="a@test.com")
    other, _, _ = await seed_offer(client, email="b@test.com")
    r = await client.get(url(store_id), headers=bearer(other))
    assert r.status_code == 403
    assert r.json() == {"success": False, "error_code": "FORBIDDEN", "message": "본인 상점의 예약만 조회할 수 있습니다."}
    r = await client.get(url(uuid.uuid4()), headers=bearer(other))
    assert r.status_code == 404 and r.json()["message"] == "상점을 찾을 수 없습니다."


# 3, 4, 5
async def test_customer_admin_and_anonymous_are_rejected(client):
    _, _, store_id = await seed_offer(client)
    cust = await token_for(client, "cust@test.com")
    r = await client.get(url(store_id), headers=bearer(cust))
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"

    await token_for(client, "admin@test.com")
    async with client.session_factory() as s:
        await s.execute(text("UPDATE users SET role = 'ADMIN' WHERE email = 'admin@test.com'"))
        await s.commit()
    admin = (await client.post("/v1/auth/login", json={"email": "admin@test.com", "password": "password123"})).json()["access_token"]
    r = await client.get(url(store_id), headers=bearer(admin))
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"

    r = await client.get(url(store_id))
    assert r.status_code == 401


# 6
async def test_status_filter_and_total_counts_filtered_rows(client):
    owner, store_id, ids = await four_states(client)
    for status, rid in ids.items():
        r = await client.get(url(store_id, status=status), headers=bearer(owner))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 1 and [i["id"] for i in body["reservations"]] == [rid]
        assert body["reservations"][0]["status"] == status
    r = await client.get(url(store_id, status="UNKNOWN"), headers=bearer(owner))
    assert r.status_code == 400


# 8
async def test_pagination_is_stable_and_bounded(client):
    owner, offer_id, store_id = await seed_offer(client, stock=30)
    cust = await token_for(client, "cust@test.com")
    base = datetime(2026, 11, 1, tzinfo=timezone.utc)
    created = []
    for i in range(5):
        rid, _ = await seed(client, cust, offer_id, 1)
        await set_created_at(client, rid, base + timedelta(minutes=i))
        created.append(rid)
    expected = list(reversed(created))  # 예약 시각 내림차순
    pages = []
    for page in (1, 2, 3):
        r = await client.get(url(store_id, page=page, size=2), headers=bearer(owner))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["page"] == page and body["size"] == 2 and body["total"] == 5
        pages.append([i["id"] for i in body["reservations"]])
    assert pages == [expected[0:2], expected[2:4], expected[4:5]]
    again = await client.get(url(store_id, page=1, size=2), headers=bearer(owner))
    assert [i["id"] for i in again.json()["reservations"]] == expected[0:2]  # 같은 데이터면 같은 순서
    r = await client.get(url(store_id, page=4, size=2), headers=bearer(owner))
    assert r.json()["reservations"] == [] and r.json()["total"] == 5
    for bad in ({"page": 0}, {"size": 0}, {"size": 101}):
        r = await client.get(url(store_id, **bad), headers=bearer(owner))
        assert r.status_code == 400, bad
    r = await client.get(url(store_id, size=100), headers=bearer(owner))
    assert r.status_code == 200


# 9
async def test_store_without_reservations_returns_empty_list(client):
    owner, _, store_id = await seed_offer(client)
    r = await client.get(url(store_id), headers=bearer(owner))
    assert r.status_code == 200
    assert r.json() == {"reservations": [], "page": 1, "size": 20, "total": 0}


async def test_other_store_reservations_are_not_mixed_in(client):
    owner_a, offer_a, store_a = await seed_offer(client, email="a@test.com")
    _, offer_b, _ = await seed_offer(client, email="b@test.com")
    cust = await token_for(client, "cust@test.com")
    mine, _ = await seed(client, cust, offer_a, 1)
    await seed(client, cust, offer_b, 1)
    r = await client.get(url(store_a), headers=bearer(owner_a))
    assert [i["id"] for i in r.json()["reservations"]] == [mine] and r.json()["total"] == 1


async def test_listing_changes_nothing(client):
    owner, store_id, _ = await four_states(client)

    async def snapshot():
        async with client.session_factory() as s:
            rows = (await s.execute(text("SELECT id, status, quantity FROM pickup_reservations ORDER BY id"))).all()
            stock = (await s.execute(text("SELECT remaining_stock FROM discount_offers"))).scalars().all()
            logs = (await s.execute(text("SELECT count(*) FROM stock_log"))).scalar_one()
        return rows, stock, logs

    before = await snapshot()
    await client.get(url(store_id), headers=bearer(owner))
    assert await snapshot() == before


# 정지·탈퇴 상점주 (픽업 EP와 같은 정책, D-38)
async def test_suspended_owner_lists_own_store_only_and_withdrawn_owner_gets_401(client):
    from tests.admin.test_api_db import admin_headers, user_id
    from tests.reservations.test_withdrawal_db import withdraw

    owner, offer_id, store_id = await seed_offer(client, email="owner@test.com")
    _, _, other_store = await seed_offer(client, email="other@test.com")
    cust = await token_for(client, "cust@test.com")
    rid, code = await seed(client, cust, offer_id, 1)
    admin = await admin_headers(client)
    owner_id = str(await user_id(client, "owner@test.com"))
    r = await client.patch(
        f"/v1/admin/users/{owner_id}/suspend", json={"reason": "점검", "suspended_until": None}, headers=admin
    )
    assert r.status_code == 200, r.text

    # 정지된 상점주: 본인 매장 200, 개인정보·픽업 코드 없음
    r = await client.get(url(store_id), headers=bearer(owner))
    assert r.status_code == 200, r.text
    assert [i["id"] for i in r.json()["reservations"]] == [rid]
    assert set(r.json()["reservations"][0]) == ALLOWED_KEYS
    assert code not in r.text and "cust@test.com" not in r.text
    # 정지된 상점주도 다른 매장은 403
    r = await client.get(url(other_store), headers=bearer(owner))
    assert r.status_code == 403 and r.json()["message"] == "본인 상점의 예약만 조회할 수 있습니다."

    # 정지된 고객은 여전히 403
    cust_id = str(await user_id(client, "cust@test.com"))
    assert (await client.patch(
        f"/v1/admin/users/{cust_id}/suspend", json={"reason": "x", "suspended_until": None}, headers=admin
    )).status_code == 200
    assert (await client.get(url(store_id), headers=bearer(cust))).status_code == 403

    # 탈퇴한 상점주 토큰은 401 (RESERVED가 없어야 탈퇴할 수 있음: 위 예약은 결제 대기)
    assert (await withdraw(client, admin, owner_id)).status_code == 200
    r = await client.get(url(store_id), headers=bearer(owner))
    assert r.status_code == 401, r.text
