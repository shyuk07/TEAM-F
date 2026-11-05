"""예약 -> 결제 -> 픽업 / 취소 전체 흐름 통합 테스트 (실제 API를 순서대로 호출, 단계마다 DB를 다시 읽어 확인)."""

import uuid

import pytest
from sqlalchemy import text

from tests.helpers import bearer, token_for
from tests.reservations.test_api_db import reserve, seed_offer
from tests.reservations.test_stock_db import cancel, pay, refund, scalar, stock_state

pytestmark = [pytest.mark.db, pytest.mark.anyio]


async def one(c, sql, **params):
    async with c.session_factory() as s:
        return (await s.execute(text(sql), params)).one()


async def reservation_row(c, rid):
    return await one(
        c,
        "SELECT status, quantity, total_price, pickup_code, picked_up_at, cancelled_at "
        "FROM pickup_reservations WHERE id = :i",
        i=uuid.UUID(rid),
    )


async def payment_row(c, pid):
    return await one(
        c, "SELECT status, amount, reservation_id FROM payments WHERE id = :i", i=uuid.UUID(pid)
    )


async def counts(c):
    return (
        await scalar(c, "SELECT count(*) FROM payments"),
        await scalar(c, "SELECT count(*) FROM refunds"),
    )


async def test_reserve_pay_pickup_flow(client):
    qty = 2
    owner, offer_id, _ = await seed_offer(client, stock=5)
    me = await token_for(client, "me@test.com")

    # 1) 예약 생성
    r = await reserve(client, me, offer_id, qty)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    row = await reservation_row(client, rid)
    assert row.status == "PENDING_PAYMENT" and row.quantity == qty
    assert row.total_price == 3000 * qty == r.json()["total_price"]
    remaining, _, _, total, count = await stock_state(client, offer_id)
    assert remaining == 5 - qty and total == remaining and count == 2  # +5, -q
    assert await scalar(client, "SELECT amount FROM stock_log WHERE amount < 0") == -qty
    assert await scalar(client, "SELECT reason FROM stock_log WHERE amount < 0") == "예약 생성"
    assert await counts(client) == (0, 0)
    stock_after_reserve = await stock_state(client, offer_id)

    # 2) 결제
    r = await pay(client, me, rid)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    pay_row = await payment_row(client, pid)
    assert pay_row.status == "PAID" and pay_row.amount == row.total_price
    assert str(pay_row.reservation_id) == rid
    assert (await reservation_row(client, rid)).status == "RESERVED"
    assert await stock_state(client, offer_id) == stock_after_reserve
    assert await counts(client) == (1, 0)

    # 3) 픽업 (점주). 생성 응답에 pickup_code가 없으면 DB에서 읽는다.
    code = r_code = (await reservation_row(client, rid)).pickup_code
    assert r_code
    r = await client.post(
        f"/v1/reservations/{rid}/pickup", json={"pickup_code": code}, headers=bearer(owner)
    )
    assert r.status_code == 200, r.text
    row = await reservation_row(client, rid)
    assert row.status == "PICKED_UP" and row.picked_up_at is not None
    assert (await payment_row(client, pid)).status == "PAID"
    assert await counts(client) == (1, 0)
    assert await stock_state(client, offer_id) == stock_after_reserve

    # 4) 픽업 이후: 취소 409, 환불 400, 아무것도 바뀌지 않음
    r = await cancel(client, me, rid)
    assert r.status_code == 409, r.text
    assert r.json()["error_code"] == "RESERVATION_ALREADY_PICKED_UP"
    r = await refund(client, me, pid)
    assert r.status_code == 400, r.text
    assert r.json()["error_code"] == "PAYMENT_NOT_REFUNDABLE"
    assert (await reservation_row(client, rid)).status == "PICKED_UP"
    assert (await payment_row(client, pid)).status == "PAID"
    assert await counts(client) == (1, 0)
    assert await stock_state(client, offer_id) == stock_after_reserve


async def test_reserve_pay_cancel_refund_restores_stock_flow(client):
    qty = 3
    _, offer_id, _ = await seed_offer(client, stock=5)
    me = await token_for(client, "me@test.com")

    r = await reserve(client, me, offer_id, qty)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert (await stock_state(client, offer_id))[0] == 5 - qty

    r = await pay(client, me, rid)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert (await reservation_row(client, rid)).status == "RESERVED"
    assert (await payment_row(client, pid)).status == "PAID"
    assert await counts(client) == (1, 0)

    r = await cancel(client, me, rid)
    assert r.status_code == 200, r.text
    row = await reservation_row(client, rid)
    assert row.status == "CANCELLED" and row.cancelled_at is not None
    pay_row = await payment_row(client, pid)
    assert pay_row.status == "REFUNDED"
    assert await counts(client) == (1, 1)
    refund_row = await one(client, "SELECT refund_amount, penalty_amount, payment_id FROM refunds")
    assert refund_row.penalty_amount == 0 and refund_row.refund_amount == pay_row.amount
    assert str(refund_row.payment_id) == pid

    remaining, status, initial, total, _ = await stock_state(client, offer_id)
    assert remaining == 5 == initial and status == "ON_SALE" and total == remaining
    amounts = (
        await _amounts(client)
    )
    assert amounts == [5, -qty, qty]


async def _amounts(c):
    async with c.session_factory() as s:
        rows = await s.execute(text("SELECT amount FROM stock_log ORDER BY created_at"))
        return [x[0] for x in rows]
