"""재고 연동(차감·복구·일괄 취소·불일치) + 실제 PostgreSQL 테스트 (작성만. 실행은 DB 안전 확인 뒤 사용자 승인 하에서만).

점주·매장·상품·할인은 공개 API로 만들고, 예약은 생성 API(실제 재고 차감)로 만든다.
재고 검증은 항상 세 가지를 함께 본다: discount_offers.remaining_stock, stock_log 합계, 음수 없음.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from tests.helpers import bearer, token_for
from tests.reservations.test_api_db import err, reserve, seed, seed_offer

pytestmark = [pytest.mark.db, pytest.mark.anyio]

H = timedelta(hours=1)
INCONSISTENT = err(
    "DATA_INCONSISTENT", "예약과 결제 상태가 일치하지 않습니다. 관리자에게 문의해 주세요."
)


async def scalar(c, sql, **params):
    async with c.session_factory() as s:
        return (await s.execute(text(sql), params)).scalar_one()


async def execute(c, sql, **params):
    async with c.session_factory() as s:
        await s.execute(text(sql), params)
        await s.commit()


async def stock_state(c, offer_id):
    """(남은 재고, 상태, 최초 수량, stock_log 합계, stock_log 건수)."""
    async with c.session_factory() as s:
        row = (
            await s.execute(
                text("SELECT remaining_stock, status, initial_stock FROM discount_offers WHERE id = :i"),
                {"i": uuid.UUID(offer_id)},
            )
        ).one()
        total, count = (
            await s.execute(
                text("SELECT coalesce(sum(amount), 0), count(*) FROM stock_log WHERE offer_id = :i"),
                {"i": uuid.UUID(offer_id)},
            )
        ).one()
    return row[0], row[1], row[2], total, count


async def pay(c, token, rid):
    return await c.post("/v1/payments", json={"reservation_id": rid}, headers=bearer(token))


async def cancel(c, token, rid):
    return await c.post(f"/v1/reservations/{rid}/cancel", headers=bearer(token))


async def refund(c, token, payment_id):
    return await c.post(
        f"/v1/payments/{payment_id}/refunds", json={"reason": "변심"}, headers=bearer(token)
    )


async def deactivate(c, owner, offer_id, cancel_reservations=True):
    return await c.post(
        f"/v1/offers/{offer_id}/deactivate",
        json={"reason": "재료 소진", "cancel_reservations": cancel_reservations},
        headers=bearer(owner),
    )


async def reservation_status(c, rid):
    return await scalar(c, "SELECT status FROM pickup_reservations WHERE id = :i", i=uuid.UUID(rid))


# ══ 차감 ══
async def test_reserve_deducts_and_stock_log_sum_equals_remaining(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    r = await reserve(client, me, offer_id, 3)
    assert r.status_code == 201, r.text
    remaining, status, initial, total, count = await stock_state(client, offer_id)
    assert (remaining, status, initial) == (7, "ON_SALE", 10)
    assert total == remaining and count == 2  # 최초 +10, 예약 -3
    assert await scalar(client, "SELECT amount FROM stock_log WHERE amount < 0") == -3
    assert await scalar(client, "SELECT reason FROM stock_log WHERE amount < 0") == "예약 생성"


async def test_reserve_more_than_remaining_is_409_out_of_stock_and_changes_nothing(client):
    _, offer_id, _ = await seed_offer(client, stock=2)
    me = await token_for(client, "me@test.com")
    r = await reserve(client, me, offer_id, 3)
    assert r.status_code == 409 and r.json() == err("OUT_OF_STOCK", "재고가 부족합니다.")
    assert (await stock_state(client, offer_id))[0] == 2
    assert await scalar(client, "SELECT count(*) FROM pickup_reservations") == 0


async def test_reserve_all_stock_makes_sold_out_then_409_not_reservable(client):
    _, offer_id, _ = await seed_offer(client, stock=2)
    me = await token_for(client, "me@test.com")
    assert (await reserve(client, me, offer_id, 2)).status_code == 201
    assert (await stock_state(client, offer_id))[:2] == (0, "SOLD_OUT")
    r = await reserve(client, me, offer_id, 1)
    assert r.status_code == 409
    assert r.json() == err("OFFER_NOT_RESERVABLE", "예약할 수 없는 상품입니다.")


@pytest.mark.parametrize("case", ["before_sales", "after_sales", "inactive"])
async def test_reserve_not_on_sale_is_409_and_changes_nothing(client, case):
    _, offer_id, _ = await seed_offer(client, stock=5)
    me = await token_for(client, "me@test.com")
    now = datetime.now(timezone.utc)
    if case == "before_sales":
        await execute(client, "UPDATE discount_offers SET sales_start = :t WHERE id = :i",
                      t=now + H, i=uuid.UUID(offer_id))
    elif case == "after_sales":
        await execute(client, "UPDATE discount_offers SET sales_start = :a, sales_end = :b WHERE id = :i",
                      a=now - 2 * H, b=now - H, i=uuid.UUID(offer_id))
    else:
        await execute(client, "UPDATE discount_offers SET is_active = false WHERE id = :i", i=uuid.UUID(offer_id))
    r = await reserve(client, me, offer_id, 1)
    assert r.status_code == 409
    assert r.json() == err("OFFER_NOT_RESERVABLE", "예약할 수 없는 상품입니다.")
    assert (await stock_state(client, offer_id))[0] == 5
    assert await scalar(client, "SELECT count(*) FROM pickup_reservations") == 0


async def test_concurrent_reserve_last_unit_only_one_succeeds(client):
    _, offer_id, _ = await seed_offer(client, stock=1)
    a = await token_for(client, "a@test.com")
    b = await token_for(client, "b@test.com")
    results = await asyncio.gather(reserve(client, a, offer_id, 1), reserve(client, b, offer_id, 1))
    assert sorted(r.status_code for r in results) == [201, 409]
    remaining, status, _, total, _ = await stock_state(client, offer_id)
    assert (remaining, status) == (0, "SOLD_OUT") and total == 0
    assert await scalar(client, "SELECT count(*) FROM pickup_reservations") == 1


async def test_n_stock_m_requests_succeed_exactly_n_and_never_negative(client):
    stock, requests = 3, 8
    _, offer_id, _ = await seed_offer(client, stock=stock)
    tokens = [await token_for(client, f"u{i}@test.com") for i in range(requests)]
    results = await asyncio.gather(*(reserve(client, t, offer_id, 1) for t in tokens))
    codes = [r.status_code for r in results]
    assert codes.count(201) == stock and codes.count(409) == requests - stock
    remaining, _, _, total, _ = await stock_state(client, offer_id)
    assert remaining == 0 and total == remaining  # 음수 없음, 로그 합계 일치
    assert await scalar(client, "SELECT count(*) FROM pickup_reservations") == stock


# ══ 복구 ══
async def test_cancel_unpaid_restores_stock_and_logs_positive(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 3)).json()["id"]
    r = await cancel(client, me, rid)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    remaining, _, _, total, count = await stock_state(client, offer_id)
    assert remaining == 10 and total == 10 and count == 3  # +10, -3, +3
    assert await scalar(client, "SELECT reason FROM stock_log WHERE amount = 3") == "예약 취소 복구"


async def test_cancel_sold_out_offer_becomes_on_sale_again(client):
    _, offer_id, _ = await seed_offer(client, stock=2)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 2)).json()["id"]
    assert (await stock_state(client, offer_id))[:2] == (0, "SOLD_OUT")
    assert (await cancel(client, me, rid)).status_code == 200
    assert (await stock_state(client, offer_id))[:2] == (2, "ON_SALE")


async def test_concurrent_double_cancel_restores_once(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 3)).json()["id"]
    results = await asyncio.gather(cancel(client, me, rid), cancel(client, me, rid))
    assert sorted(r.status_code for r in results) == [200, 409]
    remaining, _, _, total, _ = await stock_state(client, offer_id)
    assert remaining == 10 and total == 10  # 복구는 한 번뿐
    assert await scalar(client, "SELECT count(*) FROM stock_log WHERE amount = 3") == 1


async def test_cancel_paid_restores_once_and_refunds(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 3)).json()["id"]
    assert (await pay(client, me, rid)).status_code == 201
    r = await cancel(client, me, rid)
    assert r.status_code == 200, r.text
    assert await reservation_status(client, rid) == "CANCELLED"
    assert await scalar(client, "SELECT status FROM payments") == "REFUNDED"
    assert await scalar(client, "SELECT count(*) FROM refunds") == 1
    remaining, _, _, total, _ = await stock_state(client, offer_id)
    assert remaining == 10 and total == 10


async def test_refund_api_restores_once(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 3)).json()["id"]
    payment_id = (await pay(client, me, rid)).json()["id"]
    r = await refund(client, me, payment_id)
    assert r.status_code == 201, r.text
    assert await reservation_status(client, rid) == "CANCELLED"
    remaining, _, _, total, _ = await stock_state(client, offer_id)
    assert remaining == 10 and total == 10
    assert (await refund(client, me, payment_id)).status_code == 409  # 두 번째는 복구하지 않는다
    assert (await stock_state(client, offer_id))[0] == 10


async def test_concurrent_cancel_and_refund_restore_once(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 3)).json()["id"]
    payment_id = (await pay(client, me, rid)).json()["id"]
    results = await asyncio.gather(cancel(client, me, rid), refund(client, me, payment_id))
    assert all(r.status_code < 500 for r in results), [r.text for r in results]
    remaining, _, _, total, _ = await stock_state(client, offer_id)
    assert remaining == 10 and total == 10  # 어느 쪽이 먼저든 복구는 정확히 한 번
    assert await scalar(client, "SELECT count(*) FROM stock_log WHERE amount = 3") == 1
    assert await scalar(client, "SELECT count(*) FROM refunds") == 1


async def test_refund_failure_rolls_back_everything(client, monkeypatch):
    from payments.application.service import PaymentApplicationService

    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 3)).json()["id"]
    assert (await pay(client, me, rid)).status_code == 201

    async def boom(self, *args, **kwargs):
        raise RuntimeError("환불 실패")

    monkeypatch.setattr(PaymentApplicationService, "refund_for_cancelled_reservation", boom)
    with pytest.raises(RuntimeError, match="환불 실패"):
        await cancel(client, me, rid)

    assert await reservation_status(client, rid) == "RESERVED"  # 취소 롤백
    assert await scalar(client, "SELECT status FROM payments") == "PAID"
    assert await scalar(client, "SELECT count(*) FROM refunds") == 0
    remaining, _, _, total, count = await stock_state(client, offer_id)
    assert (remaining, total, count) == (7, 7, 2)  # 재고 복구·로그 없음


async def test_cancel_on_closed_offer_keeps_stock_and_logs(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 3)).json()["id"]
    assert (await deactivate(client, owner, offer_id, cancel_reservations=False)).status_code == 200
    before = await stock_state(client, offer_id)
    r = await cancel(client, me, rid)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert await stock_state(client, offer_id) == before  # 닫힌 할인: 재고·로그 불변 (D40)


async def test_cancel_paid_on_closed_offer_refunds_but_keeps_stock(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 3)).json()["id"]
    assert (await pay(client, me, rid)).status_code == 201
    assert (await deactivate(client, owner, offer_id, cancel_reservations=False)).status_code == 200
    before = await stock_state(client, offer_id)
    r = await cancel(client, me, rid)
    assert r.status_code == 200, r.text
    assert await scalar(client, "SELECT status FROM payments") == "REFUNDED"
    assert await stock_state(client, offer_id) == before


# ══ 판매 중단 일괄 취소 ══
async def test_deactivate_with_cancel_cancels_all_refunds_and_keeps_stock(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    a = await token_for(client, "a@test.com")
    b = await token_for(client, "b@test.com")
    ra = (await reserve(client, a, offer_id, 2)).json()["id"]
    rb = (await reserve(client, b, offer_id, 3)).json()["id"]
    assert (await pay(client, a, ra)).status_code == 201  # 하나는 결제, 하나는 미결제
    before = await stock_state(client, offer_id)

    r = await deactivate(client, owner, offer_id)

    assert r.status_code == 200, r.text
    assert r.json()["cancelled_reservation_count"] == 2
    assert await reservation_status(client, ra) == "CANCELLED" and await reservation_status(client, rb) == "CANCELLED"
    assert await scalar(client, "SELECT status FROM payments") == "REFUNDED"
    after = await stock_state(client, offer_id)
    # 일괄 취소는 재고를 복구하지 않는다(D40). 상태(인덱스 1)는 판매 중단으로 CLOSED가 되는 것이 정상이라 따로 확인한다.
    assert after[1] == "CLOSED"
    assert after[:1] + after[2:] == before[:1] + before[2:]
    assert await scalar(client, "SELECT is_active FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id)) is False


async def test_deactivate_with_picked_up_reservation_is_400_and_changes_nothing(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id, paid=True)
    await execute(client, "UPDATE pickup_reservations SET status = 'PICKED_UP', picked_up_at = now() WHERE id = :i",
                  i=uuid.UUID(rid))
    before = await stock_state(client, offer_id)
    r = await deactivate(client, owner, offer_id)
    assert r.status_code == 400 and r.json()["error_code"] == "PICKED_UP_RESERVATION_EXISTS"
    assert await reservation_status(client, rid) == "PICKED_UP"
    assert await scalar(client, "SELECT is_active FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id)) is True
    assert await stock_state(client, offer_id) == before


async def test_deactivate_with_inconsistent_data_is_500_json_and_rolls_back_all(client, caplog):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    good = await token_for(client, "good@test.com")
    bad = await token_for(client, "bad@test.com")
    rid_good, _ = await seed(client, good, offer_id, paid=False)
    rid_bad, _ = await seed(client, bad, offer_id, paid=True)  # RESERVED인데 결제 기록 없음 -> 불일치
    before = await stock_state(client, offer_id)

    with caplog.at_level(logging.DEBUG):
        r = await deactivate(client, owner, offer_id)

    assert r.status_code == 500 and r.json() == INCONSISTENT
    assert rid_bad not in r.text
    assert await reservation_status(client, rid_good) == "PENDING_PAYMENT"  # 전부 롤백
    assert await reservation_status(client, rid_bad) == "RESERVED"
    assert await scalar(client, "SELECT is_active FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id)) is True
    assert await scalar(client, "SELECT count(*) FROM refunds") == 0
    assert await stock_state(client, offer_id) == before
    errors = [x for x in caplog.records if x.levelno >= logging.ERROR]
    assert len(errors) == 1 and rid_bad in errors[0].getMessage()  # 로그는 예약 서비스 1건


async def test_deactivate_races_with_reserve_and_cancel_without_deadlock(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    users = [await token_for(client, f"u{i}@test.com") for i in range(3)]
    rid = (await reserve(client, users[0], offer_id, 1)).json()["id"]

    async def run():
        return await asyncio.gather(
            deactivate(client, owner, offer_id),
            reserve(client, users[1], offer_id, 1),
            reserve(client, users[2], offer_id, 1),
            cancel(client, users[0], rid),
        )

    results = await asyncio.wait_for(run(), timeout=30)  # 교착이면 시간 초과로 실패한다
    assert all(r.status_code in (200, 201, 400, 409) for r in results), [(r.status_code, r.text) for r in results]
    remaining, _, initial, total, _ = await stock_state(client, offer_id)
    assert 0 <= remaining <= initial  # 음수·초과 없음
    closed = await scalar(
        client, "SELECT NOT is_active FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id)
    )
    if not closed:  # 닫힌 뒤에는 복구가 없어 로그 합계와 다를 수 있다(D40)
        assert total == remaining


async def test_edit_offer_with_reservation_is_rejected(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    assert (await reserve(client, me, offer_id, 1)).status_code == 201
    r = await client.patch(f"/v1/offers/{offer_id}", json={"sale_price": 2500}, headers=bearer(owner))
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_HAS_RESERVATIONS"
    assert (await stock_state(client, offer_id))[0] == 9


# ══ 데이터 이상: 복구 상한 초과 ══
async def _make_over_limit(client, paid):
    """차감 기록 없이 예약만 있는 상태를 만든다: 복구하면 remaining이 initial_stock을 넘는다."""
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id, paid=False)
    await execute(client, "UPDATE discount_offers SET remaining_stock = initial_stock WHERE id = :i",
                  i=uuid.UUID(offer_id))
    payment_id = None
    if paid:
        payment_id = (await pay(client, me, rid)).json()["id"]
    return me, offer_id, rid, payment_id


async def test_cancel_restore_over_limit_is_500_and_rolls_back(client, caplog):
    me, offer_id, rid, _ = await _make_over_limit(client, paid=False)
    before = await stock_state(client, offer_id)
    with caplog.at_level(logging.DEBUG):
        r = await cancel(client, me, rid)
    assert r.status_code == 500 and r.json() == INCONSISTENT
    assert rid not in r.text
    assert await reservation_status(client, rid) == "PENDING_PAYMENT"
    assert await stock_state(client, offer_id) == before
    errors = [x for x in caplog.records if x.levelno >= logging.ERROR]
    assert len(errors) == 1 and "STOCK_RESTORE_OVER_LIMIT" in errors[0].getMessage()


async def test_paid_cancel_restore_over_limit_is_500_and_rolls_back_refund(client, caplog):
    me, offer_id, rid, _ = await _make_over_limit(client, paid=True)
    before = await stock_state(client, offer_id)
    with caplog.at_level(logging.DEBUG):
        r = await cancel(client, me, rid)
    assert r.status_code == 500 and r.json() == INCONSISTENT
    assert await reservation_status(client, rid) == "RESERVED"
    assert await scalar(client, "SELECT status FROM payments") == "PAID"
    assert await scalar(client, "SELECT count(*) FROM refunds") == 0
    assert await stock_state(client, offer_id) == before
    errors = [x for x in caplog.records if x.levelno >= logging.ERROR]
    assert len(errors) == 1 and "STOCK_RESTORE_OVER_LIMIT" in errors[0].getMessage()


async def test_refund_api_restore_over_limit_is_500_and_rolls_back(client, caplog):
    me, offer_id, rid, payment_id = await _make_over_limit(client, paid=True)
    before = await stock_state(client, offer_id)
    with caplog.at_level(logging.DEBUG):
        r = await refund(client, me, payment_id)
    assert r.status_code == 500 and r.json() == INCONSISTENT
    assert await reservation_status(client, rid) == "RESERVED"
    assert await scalar(client, "SELECT status FROM payments") == "PAID"
    assert await scalar(client, "SELECT count(*) FROM refunds") == 0
    assert await stock_state(client, offer_id) == before
    errors = [x for x in caplog.records if x.levelno >= logging.ERROR]
    assert len(errors) == 1 and "STOCK_RESTORE_OVER_LIMIT" in errors[0].getMessage()
