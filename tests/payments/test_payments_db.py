"""결제 ↔ 예약 ↔ 환불 + 실제 PostgreSQL 테스트 (작성만. 실행은 DB 안전 확인 뒤 사용자 승인 하에서만).

예약은 저장소로 직접 만들고(tests.reservations.test_api_db.seed), 결제·환불·취소는 공개 API로 부른다.
임시 재고 포트는 복구하지 못하므로 결제된 예약의 취소·환불은 503 STOCK_NOT_CONNECTED다.
"""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from payments.domain.exceptions import PaymentAlreadyExistsError, ReservationNotFoundError
from payments.domain.payment import Payment
from payments.infrastructure.repositories import SqlAlchemyPaymentRepository
from tests.helpers import bearer, token_for
from tests.reservations.test_api_db import err, seed, seed_offer

pytestmark = [pytest.mark.db, pytest.mark.anyio]

STOCK_503 = err(
    "STOCK_NOT_CONNECTED",
    "재고 연동이 아직 준비되지 않아 결제된 예약의 취소·환불을 처리할 수 없습니다.",
)


async def scalar(c, sql, **params):
    async with c.session_factory() as s:
        return (await s.execute(text(sql), params)).scalar_one()


async def pay(c, token, rid):
    return await c.post("/v1/payments", json={"reservation_id": rid}, headers=bearer(token))


async def test_pay_confirms_reservation(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)

    r = await pay(client, me, rid)

    assert r.status_code == 201, r.text
    assert r.json()["status"] == "PAID"
    assert await scalar(client, "SELECT status FROM pickup_reservations WHERE id = :i", i=uuid.UUID(rid)) == "RESERVED"
    assert await scalar(client, "SELECT count(*) FROM payments") == 1


async def test_concurrent_pay_only_one_succeeds(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)

    results = await asyncio.gather(pay(client, me, rid), pay(client, me, rid))

    assert sorted(r.status_code for r in results) == [201, 409]
    assert await scalar(client, "SELECT count(*) FROM payments") == 1


async def test_payment_fk_violation_is_distinguished_from_duplicate(client):
    """예약이 없으면 FK 위반(404 계열), 같은 예약에 두 번째 저장은 UNIQUE 위반(409 계열)."""
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    def approved(reservation_id):
        payment = Payment.request(reservation_id, user_id, 6000, now)
        payment.approve("pg_1", now)
        return payment

    async with client.session_factory() as s:
        with pytest.raises(ReservationNotFoundError):
            await SqlAlchemyPaymentRepository(s).save(approved(uuid.uuid4()))
        await s.rollback()
    async with client.session_factory() as s:
        await SqlAlchemyPaymentRepository(s).save(approved(uuid.UUID(rid)))
        with pytest.raises(PaymentAlreadyExistsError):
            await SqlAlchemyPaymentRepository(s).save(approved(uuid.UUID(rid)))


async def test_refund_api_is_503_and_nothing_saved(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)
    payment_id = (await pay(client, me, rid)).json()["id"]

    r = await client.post(
        f"/v1/payments/{payment_id}/refunds", json={"reason": "변심"}, headers=bearer(me)
    )

    assert r.status_code == 503 and r.json() == STOCK_503
    assert await scalar(client, "SELECT count(*) FROM refunds") == 0
    assert await scalar(client, "SELECT status FROM payments") == "PAID"
    assert await scalar(client, "SELECT status FROM pickup_reservations") == "RESERVED"


async def test_cancel_paid_reservation_is_503_and_nothing_saved(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)
    await pay(client, me, rid)

    r = await client.post(f"/v1/reservations/{rid}/cancel", headers=bearer(me))

    assert r.status_code == 503 and r.json() == STOCK_503
    assert await scalar(client, "SELECT count(*) FROM refunds") == 0
    assert await scalar(client, "SELECT status FROM payments") == "PAID"
    assert await scalar(client, "SELECT status FROM pickup_reservations") == "RESERVED"


async def test_cancel_unpaid_reservation_is_200(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)

    r = await client.post(f"/v1/reservations/{rid}/cancel", headers=bearer(me))

    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert await scalar(client, "SELECT count(*) FROM refunds") == 0
