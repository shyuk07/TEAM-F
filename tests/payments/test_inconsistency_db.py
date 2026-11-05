"""데이터 불일치(RD-38·RD-39) + 실제 PostgreSQL 테스트 (작성만. 실행은 DB 안전 확인 뒤 사용자 승인 하에서만).

예약·결제·환불 행을 DB에 직접 만들어 불일치 상태를 재현하고, 500 DATA_INCONSISTENT와 행 불변을 확인한다.
불일치는 환불 확인이 재고 복구보다 먼저라 재고를 건드리기 전에 500으로 중단되고 전부 롤백된다.
"""

import logging
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from payments.domain.payment import Payment
from payments.domain.refund import Refund
from payments.infrastructure.repositories import SqlAlchemyPaymentRepository, SqlAlchemyRefundRepository
from tests.helpers import bearer, token_for
from tests.reservations.test_api_db import err, seed, seed_offer

pytestmark = [pytest.mark.db, pytest.mark.anyio]

INCONSISTENT = err(
    "DATA_INCONSISTENT", "예약과 결제 상태가 일치하지 않습니다. 관리자에게 문의해 주세요."
)


async def scalar(c, sql, **params):
    async with c.session_factory() as s:
        return (await s.execute(text(sql), params)).scalar_one()


async def snapshot(c):
    """불변 확인용: 예약 상태, 결제 상태, 환불 수, 재고."""
    return (
        sorted((await _rows(c, "SELECT status FROM pickup_reservations"))),
        sorted((await _rows(c, "SELECT status FROM payments"))),
        await scalar(c, "SELECT count(*) FROM refunds"),
        await _rows(c, "SELECT remaining_stock FROM discount_offers"),
    )


async def _rows(c, sql):
    async with c.session_factory() as s:
        return [row[0] for row in (await s.execute(text(sql))).all()]


async def make_payment(c, rid, user_token, *, status="PAID", refund_row=False):
    """결제(와 환불 행)를 저장소로 직접 만든다. status: READY / PAID / FAILED / REFUNDED."""
    now = datetime.now(UTC)
    from jwt import decode

    user_id = uuid.UUID(decode(user_token, options={"verify_signature": False})["sub"])
    payment = Payment.request(uuid.UUID(rid), user_id, 6000, now)
    if status in ("PAID", "REFUNDED"):
        payment.approve("pg_x", now)
    elif status == "FAILED":
        payment.fail({"code": "DECLINED"}, now)
    refund = None
    if status == "REFUNDED":
        refund = payment.refund(0, "x", now)
    async with c.session_factory() as s:
        saved = await SqlAlchemyPaymentRepository(s).save(payment)
        if refund is not None or refund_row:
            row = refund or Refund(saved.id, 6000, 0, "x", completed_at=now)
            row.payment_id = saved.id
            await SqlAlchemyRefundRepository(s).save(row)
        await s.commit()
        return saved


async def set_reservation_status(c, rid, status):
    async with c.session_factory() as s:
        extra = ", cancelled_at = now()" if status == "CANCELLED" else ""
        await s.execute(
            text(f"UPDATE pickup_reservations SET status = :st{extra} WHERE id = :i"),
            {"st": status, "i": uuid.UUID(rid)},
        )
        await s.commit()


async def cancel(c, token, rid):
    return await c.post(f"/v1/reservations/{rid}/cancel", headers=bearer(token))


def errors(caplog):
    return [r for r in caplog.records if r.levelno >= logging.ERROR]


@pytest.mark.parametrize("case", ["no_payment", "payment_refunded", "refund_row_with_paid"])
async def test_cancel_reserved_inconsistent_is_500_and_rows_unchanged(client, caplog, case):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id, paid=True)  # RESERVED
    if case == "payment_refunded":
        await make_payment(client, rid, me, status="REFUNDED")
    elif case == "refund_row_with_paid":
        await make_payment(client, rid, me, status="PAID", refund_row=True)
    before = await snapshot(client)

    with caplog.at_level(logging.DEBUG):
        r = await cancel(client, me, rid)

    assert r.status_code == 500, r.text
    assert r.json() == INCONSISTENT and rid not in r.text
    assert await snapshot(client) == before  # 예약·결제·환불·재고 불변
    assert len(errors(caplog)) == 1 and "me@test.com" not in caplog.text


async def test_cancel_pending_with_paid_payment_is_500_and_rows_unchanged(client, caplog):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)  # PENDING_PAYMENT
    await make_payment(client, rid, me, status="PAID")
    before = await snapshot(client)

    with caplog.at_level(logging.DEBUG):
        r = await cancel(client, me, rid)

    assert r.status_code == 500 and r.json() == INCONSISTENT
    assert await snapshot(client) == before
    assert len(errors(caplog)) == 1


# FAILED는 뺐다: 현재 payments 테이블에 failed_at 컬럼이 없어 FAILED 행을 DB에서 읽으면
# Payment 생성자 검증(FAILED면 failed_at 필수)으로 400이 난다. 실제 서비스는 FAILED 결제를
# 저장하지 않는다(D-11/D-23). FAILED 판단은 DB 없는 tests/payments/test_domain.py의
# test_status_time_mismatch_rejected(FAILED + failed_at 없음)와 test_fail_records_response_and_failed_at에서 검증한다.
@pytest.mark.parametrize("payment_status", [None, "READY", "REFUNDED"])
async def test_cancel_pending_without_paid_payment_is_still_200(client, payment_status):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)
    if payment_status:
        await make_payment(client, rid, me, status=payment_status)

    r = await cancel(client, me, rid)

    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"


@pytest.mark.parametrize("reservation_status", ["CANCELLED", "PENDING_PAYMENT"])
async def test_pay_and_refund_with_paid_payment_on_inactive_reservation_are_500(
    client, caplog, reservation_status
):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id, paid=True)
    payment = await make_payment(client, rid, me, status="PAID")
    await set_reservation_status(client, rid, reservation_status)
    before = await snapshot(client)

    with caplog.at_level(logging.DEBUG):
        r1 = await client.post("/v1/payments", json={"reservation_id": rid}, headers=bearer(me))
        r2 = await client.post(
            f"/v1/payments/{payment.id}/refunds", json={"reason": "변심"}, headers=bearer(me)
        )

    assert r1.status_code == 500 and r1.json() == INCONSISTENT
    assert r2.status_code == 500 and r2.json() == INCONSISTENT
    assert await snapshot(client) == before
    assert len(errors(caplog)) == 2  # 요청당 1건씩


async def test_normal_duplicate_pay_is_still_409(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id, paid=True)
    await make_payment(client, rid, me, status="PAID")

    r = await client.post("/v1/payments", json={"reservation_id": rid}, headers=bearer(me))

    assert r.status_code == 409
