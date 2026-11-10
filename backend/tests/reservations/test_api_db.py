"""예약 API + 실제 PostgreSQL 테스트 (작성만, 실행은 DB 안전 확인 뒤 사용자 승인 하에서만).

점주·매장·상품·할인은 공개 API로 만들고, 인증은 실제 JWT를 쓴다(tests/helpers).
예약 생성은 실제 재고 어댑터(catalog 할인 잠금 -> 차감 -> stock_log)로 동작한다.
다른 테스트가 상태별 예약을 쉽게 만들도록 seed()는 저장소로 예약을 직접 만들되, 생성 API와 같게 재고 차감과 stock_log(-수량)도 반영한다.
재고 동시성·복구·불일치는 tests/reservations/test_stock_db.py에서 검증한다.
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


async def seed(c, token, offer_id, quantity=2, paid=False):
    """저장소로 예약을 직접 만든다(상태를 고르기 쉽게). 생성 API와 같게 재고 차감과 stock_log(-수량)도 반영한다.

    (예약 id str, 예약번호) 반환. 차감이 없으면 취소 때 재고 복구가 상한을 넘어 500이 된다(데이터 이상 재현용이 아님).
    """
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
        await session.execute(
            text("UPDATE discount_offers SET remaining_stock = remaining_stock - :q WHERE id = :o"),
            {"q": quantity, "o": uuid.UUID(offer_id)},
        )
        session.add(
            catalog_models.StockLogModel(
                offer_id=uuid.UUID(offer_id), user_id=user_id, amount=-quantity, reason="예약 생성"
            )
        )
        await session.commit()
        return str(saved.id), reservation.pickup_code


async def count_rows(c):
    async with c.session_factory() as s:
        return (await s.execute(text("SELECT count(*) FROM pickup_reservations"))).scalar_one()


# ── 생성: 실제 재고 차감 ──
async def test_create_is_201_deducts_stock_and_writes_stock_log(client):
    _, offer_id, _ = await seed_offer(client)
    cust = await token_for(client, "c@test.com")
    r = await reserve(client, cust, offer_id, 2)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "PENDING_PAYMENT" and r.json()["quantity"] == 2
    assert await count_rows(client) == 1
    async with client.session_factory() as s:
        offer = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(offer_id))
        assert offer.remaining_stock == 8 and offer.initial_stock == 10
        amounts = (await s.execute(text("SELECT amount FROM stock_log ORDER BY created_at"))).scalars().all()
        assert amounts == [10, -2]  # 최초 입고 +10, 예약 -2
        assert sum(amounts) == offer.remaining_stock


async def test_create_errors(client):
    _, offer_id, _ = await seed_offer(client, stock=4)  # 수량 상한(5) 안에서 재고 부족을 만든다(R-REQ1)
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
    r = await reserve(client, cust, offer_id, 5)
    assert r.status_code == 409 and r.json() == err("OUT_OF_STOCK", "재고가 부족합니다.")
    r = await reserve(client, cust, offer_id, 6)
    assert r.status_code == 400 and r.json() == err("VALIDATION_ERROR", "수량은 5개 이하여야 합니다.")
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


async def test_cancel_paid_refunds_restores_stock_and_logs(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id, paid=True)
    # RESERVED인데 결제 기록이 없으면 불일치 500(RD-38 ①)이므로 PAID 결제도 함께 저장한다.
    # (tests/payments/test_inconsistency_db.py가 이 파일을 import하므로 순환을 피해 여기서 지연 import)
    from payments.domain.payment import Payment
    from payments.infrastructure.repositories import SqlAlchemyPaymentRepository

    user_id = uuid.UUID(jwt.decode(me, options={"verify_signature": False})["sub"])
    now = datetime.now(timezone.utc)
    payment = Payment.request(uuid.UUID(rid), user_id, 6000, now)
    payment.approve("pg_x", now)
    async with client.session_factory() as s:
        await SqlAlchemyPaymentRepository(s).save(payment)
        await s.commit()

    r = await client.post(f"/v1/reservations/{rid}/cancel", headers=bearer(me))

    assert r.status_code == 200, r.text
    async with client.session_factory() as s:
        row = (await s.execute(select(PickupReservationModel))).scalar_one()
        assert row.status == "CANCELLED" and row.cancelled_at is not None
        assert (await s.execute(text("SELECT status FROM payments"))).scalars().all() == ["REFUNDED"]
        assert (await s.execute(text("SELECT count(*) FROM refunds"))).scalar_one() == 1
        offer = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(offer_id))
        assert offer.remaining_stock == 10  # 차감 -2 후 복구 +2


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
