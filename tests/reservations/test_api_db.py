"""예약 API + 실제 PostgreSQL 테스트 (작성만, 실행은 DB 안전 확인 뒤 사용자 승인 하에서만).

점주·매장·상품·할인은 공개 API로 만들고, 인증은 실제 JWT를 쓴다(tests/helpers).
임시 재고 포트는 재고 연동 전이라 예약 생성을 503 STOCK_NOT_CONNECTED로 거부한다.
그래서 예약이 필요한 테스트는 저장소로 직접 만든다(seed). 재고 동시성은 여기서 검증하지 않는다.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from sqlalchemy import select, text

from auth.infrastructure import models as auth_models  # noqa: F401
from catalog.infrastructure import models as catalog_models
from reservations.domain.offer_ref import OfferRef
from reservations.domain.pickup_reservation import PickupReservation
from reservations.infrastructure.models import PickupReservationModel
from reservations.infrastructure.repositories import SqlAlchemyReservationRepository
from stores.infrastructure import models as stores_models  # noqa: F401
from tests.helpers import bearer, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]

H = timedelta(hours=1)


def err(error_code, message):
    return {"success": False, "error_code": error_code, "message": message}


async def seed_offer(c, stock=10, email="owner@test.com"):
    now = datetime.now(timezone.utc)
    owner = await token_for(c, email, "OWNER")
    r = await c.post("/v1/stores", json={"pickup_address": "서울 강남구"}, headers=bearer(owner))
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


async def seed(c, token, offer_id, quantity=2, paid=False):
    """생성 API가 503이라 저장소로 예약을 직접 만든다. (예약 id str, 예약번호) 반환."""
    user_id = uuid.UUID(jwt.decode(token, options={"verify_signature": False})["sub"])
    now = datetime.now(timezone.utc)
    ref = OfferRef.from_info(
        SimpleNamespace(
            offer_id=uuid.UUID(offer_id), owner_id=uuid.uuid4(), store_name="마감 베이커리",
            product_name="샌드위치", pickup_address="서울 강남구", sale_price=3000,
            pickup_start=now + H, pickup_end=now + 3 * H,
        )
    )
    reservation = PickupReservation.create(user_id, ref, quantity, "AB3DE9", now)
    if paid:
        reservation.mark_paid()
    async with c.session_factory() as session:
        saved = await SqlAlchemyReservationRepository(session).save(reservation)
        await session.commit()
        return str(saved.id), reservation.pickup_code


async def count_rows(c):
    async with c.session_factory() as s:
        return (await s.execute(text("SELECT count(*) FROM pickup_reservations"))).scalar_one()


# ── 생성: 재고 미연동 503 ──
async def test_create_is_503_and_saves_nothing(client):
    _, offer_id, _ = await seed_offer(client)
    cust = await token_for(client, "c@test.com")
    r = await reserve(client, cust, offer_id, 2)
    assert r.status_code == 503, r.text
    assert r.json() == err(
        "STOCK_NOT_CONNECTED", "재고 연동이 아직 준비되지 않아 예약을 생성할 수 없습니다."
    )
    assert await count_rows(client) == 0
    async with client.session_factory() as s:
        offer = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(offer_id))
        assert offer.remaining_stock == 10


async def test_create_errors(client):
    _, offer_id, _ = await seed_offer(client)
    cust = await token_for(client, "c@test.com")
    for bad in (0, "x", True, 1.5):
        r = await client.post(
            "/v1/reservations", json={"offer_id": offer_id, "quantity": bad}, headers=bearer(cust)
        )
        assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR", bad
    r = await client.post("/v1/reservations", json={"offer_id": offer_id, "quantity": 1})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    r = await reserve(client, cust, str(uuid.uuid4()), 1)
    assert r.status_code == 404 and r.json() == err("NOT_FOUND", "할인 상품을 찾을 수 없습니다.")
    r = await reserve(client, cust, offer_id, 11)
    assert r.status_code == 409 and r.json() == err("OUT_OF_STOCK", "재고가 부족합니다.")
    assert await count_rows(client) == 0


async def test_create_offer_not_reservable(client):
    _, offer_id, _ = await seed_offer(client)
    cust = await token_for(client, "c@test.com")
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(offer_id))
        m.is_active = False
        await s.commit()
    r = await reserve(client, cust, offer_id, 1)
    assert r.status_code == 409
    assert r.json() == err("OFFER_NOT_RESERVABLE", "예약할 수 없는 상품입니다.")


# ── 목록 ──
async def test_list_my_reservations(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    other = await token_for(client, "other@test.com")
    for _ in range(3):
        await seed(client, me, offer_id, 1)
    await seed(client, other, offer_id, 1)

    r = await client.get("/v1/users/me/reservations", headers=bearer(me))
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["page"], body["size"], body["total"]) == (1, 20, 3) and len(body["reservations"]) == 3
    assert set(body["reservations"][0]) == {
        "id", "offer_id", "store_name", "product_name", "quantity", "total_price", "status",
        "created_at", "pickup_code", "pickup_address",
    }
    r = await client.get("/v1/users/me/reservations?page=2&size=2", headers=bearer(me))
    assert len(r.json()["reservations"]) == 1 and r.json()["total"] == 3
    r = await client.get("/v1/users/me/reservations")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


# ── 취소 ──
async def test_cancel_unpaid_ok_and_errors(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    other = await token_for(client, "other@test.com")
    rid, _ = await seed(client, me, offer_id)
    url = f"/v1/reservations/{rid}/cancel"

    r = await client.post(url, headers=bearer(other))
    assert r.status_code == 403 and r.json() == err("FORBIDDEN", "본인 예약만 취소할 수 있습니다.")
    r = await client.post(url)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    r = await client.post(f"/v1/reservations/{uuid.uuid4()}/cancel", headers=bearer(me))
    assert r.status_code == 404 and r.json() == err("NOT_FOUND", "예약 정보를 찾을 수 없습니다.")

    r = await client.post(url, headers=bearer(me))
    assert r.status_code == 200, r.text
    assert r.json()["id"] == rid and r.json()["status"] == "CANCELLED"
    r = await client.post(url, headers=bearer(me))
    assert r.status_code == 409
    assert r.json() == err("RESERVATION_ALREADY_CANCELLED", "이미 취소된 예약입니다.")


async def test_concurrent_cancel_only_one_succeeds(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)

    results = await asyncio.gather(
        client.post(f"/v1/reservations/{rid}/cancel", headers=bearer(me)),
        client.post(f"/v1/reservations/{rid}/cancel", headers=bearer(me)),
    )

    assert sorted(r.status_code for r in results) == [200, 409]


async def test_cancel_paid_is_503_and_row_unchanged(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id, paid=True)

    r = await client.post(f"/v1/reservations/{rid}/cancel", headers=bearer(me))

    assert r.status_code == 503
    assert r.json() == err(
        "REFUND_NOT_CONNECTED", "환불 연동이 아직 준비되지 않아 결제된 예약은 취소할 수 없습니다."
    )
    async with client.session_factory() as s:
        row = (await s.execute(select(PickupReservationModel))).scalar_one()
        assert row.status == "RESERVED" and row.cancelled_at is None


# ── 픽업 ──
async def test_pickup_flow(client):
    owner, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, code = await seed(client, me, offer_id)
    url = f"/v1/reservations/{rid}/pickup"
    body = {"pickup_code": code}

    r = await client.post(url, json=body, headers=bearer(owner))  # 결제 전
    assert r.status_code == 409
    assert r.json() == err("RESERVATION_NOT_PAID", "결제가 완료되지 않은 예약입니다.")

    rid, code = await seed(client, me, offer_id, paid=True)
    url = f"/v1/reservations/{rid}/pickup"
    r = await client.post(url, json={"pickup_code": "ZZZZZZ"}, headers=bearer(owner))
    assert r.status_code == 400 and r.json()["error_code"] == "PICKUP_CODE_MISMATCH"
    r = await client.post(url, json={"pickup_code": code})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    r = await client.post(url, json={"pickup_code": code}, headers=bearer(me))  # 역할 불일치
    assert r.status_code == 403
    r = await client.post(
        f"/v1/reservations/{uuid.uuid4()}/pickup", json={"pickup_code": code}, headers=bearer(owner)
    )
    assert r.status_code == 404

    r = await client.post(url, json={"pickup_code": code.lower()}, headers=bearer(owner))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PICKED_UP"
    r = await client.post(url, json={"pickup_code": code}, headers=bearer(owner))
    assert r.status_code == 409
    assert r.json() == err("RESERVATION_ALREADY_PICKED_UP", "이미 픽업 완료된 예약입니다.")


async def test_concurrent_pickup_only_one_succeeds(client):
    owner, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, code = await seed(client, me, offer_id, paid=True)

    results = await asyncio.gather(
        *[
            client.post(
                f"/v1/reservations/{rid}/pickup", json={"pickup_code": code}, headers=bearer(owner)
            )
            for _ in range(2)
        ]
    )

    assert sorted(r.status_code for r in results) == [200, 409]
