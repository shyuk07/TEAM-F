import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from auth.infrastructure import models as auth_models  # noqa: F401
from catalog.infrastructure import models as catalog_models
from reservations.infrastructure.models import PickupReservationModel
from stores.infrastructure import models as stores_models  # noqa: F401
from tests.helpers import bearer, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]

H = timedelta(hours=1)


def err(error_code, message):
    return {"success": False, "error_code": error_code, "message": message}


async def seed_offer(c, stock=10, email="owner@test.com"):
    now = datetime.now(timezone.utc)
    owner = await token_for(c, email, "OWNER")
    r = await c.post(
        "/v1/stores",
        json={"pickup_address": f"서울 강남구 {email}"},  # STORE_DUPLICATED 방지
        headers=bearer(owner),
    )
    assert r.status_code == 201, r.text
    store_id = r.json()["id"]
    r = await c.post(
        f"/v1/stores/{store_id}/products",
        json={"name": "샌드위치", "original_price": 6000},
        headers=bearer(owner),
    )
    assert r.status_code == 201, r.text
    r = await c.post(
        f"/v1/products/{r.json()['id']}/offers",
        json={
            "sale_price": 3000, "initial_stock": stock,
            "sales_end": (now + 2 * H).isoformat(),
            "pickup_start": (now + H).isoformat(), "pickup_end": (now + 3 * H).isoformat(),
        },
        headers=bearer(owner),
    )
    assert r.status_code == 201, r.text
    return owner, r.json()["id"], store_id


async def reserve(c, token, offer_id, quantity=2):
    return await c.post(
        "/v1/reservations", json={"offer_id": offer_id, "quantity": quantity}, headers=bearer(token)
    )


async def set_status(c, reservation_id, status):
    async with c.session_factory() as s:
        m = await s.get(PickupReservationModel, uuid.UUID(reservation_id))
        m.status = status
        await s.commit()


# ── #22 예약 생성 ──
async def test_create_reservation_ok(client):
    _, offer_id, _ = await seed_offer(client)
    cust = await token_for(client, "c@test.com")
    r = await reserve(client, cust, offer_id, 2)
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {
        "id", "user_id", "offer_id", "quantity", "unit_price", "total_price", "status",
        "created_at", "store_name", "product_name",
    }
    assert body["offer_id"] == offer_id and body["quantity"] == 2
    assert (body["unit_price"], body["total_price"]) == (3000, 6000)
    assert body["status"] == "PENDING_PAYMENT" and body["product_name"] == "샌드위치"
    assert body["created_at"].endswith("+00:00") or body["created_at"].endswith("Z")
    async with client.session_factory() as s:
        row = (await s.execute(select(PickupReservationModel))).scalar_one()
        assert str(row.id) == body["id"] and row.pickup_code and len(row.pickup_code) == 6


async def test_create_reservation_errors(client):
    _, offer_id, _ = await seed_offer(client)
    cust = await token_for(client, "c@test.com")
    r = await reserve(client, cust, offer_id, 0)
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    r = await client.post("/v1/reservations", json={"offer_id": offer_id, "quantity": "x"}, headers=bearer(cust))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    r = await client.post("/v1/reservations", json={"offer_id": offer_id, "quantity": 1})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    r = await reserve(client, cust, str(uuid.uuid4()), 1)
    assert r.status_code == 404 and r.json() == err("NOT_FOUND", "할인 상품을 찾을 수 없습니다.")
    r = await reserve(client, cust, offer_id, 11)
    assert r.status_code == 409 and r.json() == err("OUT_OF_STOCK", "재고가 부족합니다.")


async def test_create_reservation_offer_not_reservable(client):
    owner, offer_id, _ = await seed_offer(client)
    cust = await token_for(client, "c@test.com")
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(offer_id))
        m.is_active = False
        await s.commit()
    r = await reserve(client, cust, offer_id, 1)
    assert r.status_code == 409
    assert r.json() == err("OFFER_NOT_RESERVABLE", "예약할 수 없는 상품입니다.")


# ── #23 목록 ──
async def test_list_my_reservations(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    other = await token_for(client, "other@test.com")
    for _ in range(3):
        assert (await reserve(client, me, offer_id, 1)).status_code == 201
    assert (await reserve(client, other, offer_id, 1)).status_code == 201

    r = await client.get("/v1/users/me/reservations", headers=bearer(me))
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["page"], body["size"], body["total"]) == (1, 20, 3) and len(body["reservations"]) == 3
    item = body["reservations"][0]
    assert set(item) == {
        "id", "offer_id", "store_name", "product_name", "quantity", "total_price", "status",
        "created_at", "pickup_code", "pickup_address",
    }
    created = [i["created_at"] for i in body["reservations"]]
    assert created == sorted(created, reverse=True)

    r = await client.get("/v1/users/me/reservations?page=2&size=2", headers=bearer(me))
    assert len(r.json()["reservations"]) == 1 and r.json()["total"] == 3
    r = await client.get("/v1/users/me/reservations?status=RESERVED", headers=bearer(me))
    assert r.json()["reservations"] == [] and r.json()["total"] == 0
    r = await client.get("/v1/users/me/reservations?status=PENDING_PAYMENT", headers=bearer(me))
    assert r.json()["total"] == 3

    for q in ("status=BAD", "page=0", "size=0", "size=101"):
        r = await client.get(f"/v1/users/me/reservations?{q}", headers=bearer(me))
        assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR", q
    r = await client.get("/v1/users/me/reservations")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


# ── #24 취소 ──
async def test_cancel_reservation_ok_and_errors(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    other = await token_for(client, "other@test.com")
    rid = (await reserve(client, me, offer_id, 1)).json()["id"]
    url = f"/v1/reservations/{rid}/cancel"

    r = await client.post(url, headers=bearer(other))
    assert r.status_code == 403 and r.json() == err("FORBIDDEN", "본인 예약만 취소할 수 있습니다.")
    r = await client.post(url)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    r = await client.post(f"/v1/reservations/{uuid.uuid4()}/cancel", headers=bearer(me))
    assert r.status_code == 404 and r.json() == err("NOT_FOUND", "예약 정보를 찾을 수 없습니다.")
    r = await client.post("/v1/reservations/not-a-uuid/cancel", headers=bearer(me))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"

    r = await client.post(url, headers=bearer(me))
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"id", "status", "cancelled_at"}
    assert r.json()["id"] == rid and r.json()["status"] == "CANCELLED" and r.json()["cancelled_at"]

    r = await client.post(url, headers=bearer(me))
    assert r.status_code == 409
    assert r.json() == err("RESERVATION_ALREADY_CANCELLED", "이미 취소된 예약입니다.")


async def test_cancel_picked_up_is_409(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 1)).json()["id"]
    async with client.session_factory() as s:
        m = await s.get(PickupReservationModel, uuid.UUID(rid))
        m.status = "PICKED_UP"
        m.picked_up_at = datetime.now(timezone.utc)
        await s.commit()
    r = await client.post(f"/v1/reservations/{rid}/cancel", headers=bearer(me))
    assert r.status_code == 409
    assert r.json() == err("RESERVATION_ALREADY_PICKED_UP", "이미 픽업 완료된 예약입니다.")


# ── #25 픽업 ──
async def test_pickup_flow(client):
    owner, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    other_owner = await token_for(client, "o2@test.com", "OWNER")
    rid = (await reserve(client, me, offer_id, 1)).json()["id"]
    async with client.session_factory() as s:
        code = (await s.get(PickupReservationModel, uuid.UUID(rid))).pickup_code
    url = f"/v1/reservations/{rid}/pickup"
    body = {"pickup_code": code}

    r = await client.post(url, json=body, headers=bearer(owner))  # 결제 전
    assert r.status_code == 409
    assert r.json() == err("RESERVATION_NOT_PAID", "결제가 완료되지 않은 예약입니다.")

    await set_status(client, rid, "RESERVED")
    r = await client.post(url, json={"pickup_code": "ZZZZZZ"}, headers=bearer(owner))
    assert r.status_code == 400 and r.json() == err("PICKUP_CODE_MISMATCH", "예약번호가 일치하지 않습니다.")
    r = await client.post(url, json=body)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    r = await client.post(url, json=body, headers=bearer(me))  # 역할 불일치
    assert r.status_code == 403
    r = await client.post(url, json=body, headers=bearer(other_owner))  # 다른 매장
    assert r.status_code == 403
    assert r.json() == err("FORBIDDEN", "해당 매장의 상점주만 픽업 완료 처리할 수 있습니다.")
    r = await client.post(f"/v1/reservations/{uuid.uuid4()}/pickup", json=body, headers=bearer(owner))
    assert r.status_code == 404 and r.json() == err("NOT_FOUND", "예약 정보를 찾을 수 없습니다.")
    r = await client.post(url, json={}, headers=bearer(owner))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"

    r = await client.post(url, json={"pickup_code": code.lower()}, headers=bearer(owner))
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"id", "pickup_code", "status", "picked_up_at"}
    assert r.json()["status"] == "PICKED_UP" and r.json()["pickup_code"] == code

    r = await client.post(url, json=body, headers=bearer(owner))
    assert r.status_code == 409
    assert r.json() == err("RESERVATION_ALREADY_PICKED_UP", "이미 픽업 완료된 예약입니다.")
