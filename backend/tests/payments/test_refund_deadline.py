"""결제 완료 예약의 고객 취소·환불 시간 제한 (payments REQ-6, reservations REQ-26). DB 없음.

- 마감 시각은 Catalog 취소 정책(pickup_start - 1시간)으로 계산된 값을 받는다. 같은 순간은 허용, 지나면 거절
- 직접 환불 API(refund)와 고객 취소가 부르는 환불(refund_for_cancelled_reservation) 양쪽에 적용
- 일괄 취소(waive_penalty=True: 상점주 사유·탈퇴)는 제외
- 데이터 불일치(500)·중복 환불(409)·상태(400) 검사가 시간 제한보다 먼저
- 거절되면 환불·결제·포인트·예약이 바뀌지 않는다
"""

from datetime import UTC, datetime, timedelta

import pytest

from payments.domain.cancellation_policy import ensure_before_refund_deadline
from payments.domain.exceptions import (
    PaymentAlreadyRefundedError,
    PaymentStateInconsistentError,
    RefundDeadlinePassedError,
)
from payments.domain.rules import RESERVATION_PAID_STATUS
from tests.payments.test_service import USER, Env

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)  # FixedClock 기본값
TICK = timedelta(microseconds=1)


def test_boundary_is_inclusive_and_missing_deadline_is_rejected():
    ensure_before_refund_deadline(NOW, NOW)  # 정확히 마감 시각: 허용
    ensure_before_refund_deadline(NOW + TICK, NOW)
    with pytest.raises(RefundDeadlinePassedError) as e:
        ensure_before_refund_deadline(NOW - TICK, NOW)  # 지난 직후: 거절
    assert e.value.error_code == "CANCELLATION_DEADLINE_PASSED"
    with pytest.raises(RuntimeError):
        ensure_before_refund_deadline(None, NOW)  # 판단 불가: 막는다(fail-closed)


async def paid_with_deadline(env, cancellable_until):
    rid = env.reservations.add(USER, total_price=10000, cancellable_until=cancellable_until)
    payment = await env.service.pay(USER, rid, use_point=2000)
    env.reservations.set_status(rid, RESERVATION_PAID_STATUS)
    env.auth.calls.clear()
    return rid, payment


def state(env):
    return (
        dict(env.payments.items),
        dict(env.refunds.items),
        list(env.auth.calls),
        env.db.commits,
        list(env.reservations.cancel_calls),
    )


# ── 직접 환불 API ──
async def test_refund_api_at_deadline_succeeds():
    env = Env()
    _, payment = await paid_with_deadline(env, NOW)
    refund = await env.service.refund(USER, payment.id, "변심")
    assert refund.refund_amount == payment.amount


async def test_refund_api_after_deadline_is_rejected_and_changes_nothing():
    env = Env()
    _, payment = await paid_with_deadline(env, NOW - TICK)
    before = state(env)
    with pytest.raises(RefundDeadlinePassedError):
        await env.service.refund(USER, payment.id, "변심")
    assert state(env) == before  # 환불·결제·포인트·예약 취소 호출 없음


async def test_refund_api_duplicate_409_beats_deadline():
    env = Env()
    _, payment = await paid_with_deadline(env, NOW)
    await env.service.refund(USER, payment.id, "변심")
    env.clock.current = NOW + timedelta(hours=5)  # 마감 지난 뒤 다시 환불
    with pytest.raises(PaymentAlreadyRefundedError):
        await env.service.refund(USER, payment.id, "변심")


async def test_refund_api_inconsistency_500_beats_deadline():
    env = Env()
    rid, payment = await paid_with_deadline(env, NOW - TICK)
    env.reservations.set_status(rid, "PENDING_PAYMENT")  # 결제 PAID + 예약 결제 대기(RD-38)
    before = state(env)
    with pytest.raises(PaymentStateInconsistentError):
        await env.service.refund(USER, payment.id, "변심")
    assert state(env)[:3] == before[:3]


# ── 고객 취소가 부르는 환불 ──
async def call(env, rid, cancellable_until, waive=False):
    return await env.service.refund_for_cancelled_reservation(
        rid, reservation_status=RESERVATION_PAID_STATUS, pickup_start=None, reason="x",
        cancellable_until=cancellable_until, waive_penalty=waive,
    )


async def test_customer_cancel_refund_at_deadline_succeeds_and_after_is_rejected():
    env = Env()
    rid, _ = await paid_with_deadline(env, NOW)
    await call(env, rid, NOW)

    env = Env()
    rid, _ = await paid_with_deadline(env, NOW)
    before = state(env)
    with pytest.raises(RefundDeadlinePassedError):
        await call(env, rid, NOW - TICK)
    assert state(env) == before


@pytest.mark.parametrize("deadline", [None, NOW - timedelta(days=1)])
async def test_bulk_cancel_refund_ignores_deadline(deadline):
    """판매 중단·탈퇴 일괄 취소(waive_penalty=True)는 시간 제한이 없다. 마감 정보가 없어도 된다."""
    env = Env()
    rid, payment = await paid_with_deadline(env, NOW)
    refund = await call(env, rid, deadline, waive=True)
    assert refund.refund_amount == payment.amount and refund.penalty_amount == 0


async def test_customer_cancel_inconsistency_500_beats_deadline():
    env = Env()
    rid, payment = await paid_with_deadline(env, NOW)
    await env.service.refund(USER, payment.id, "변심")  # 결제 REFUNDED
    with pytest.raises(PaymentStateInconsistentError):
        await call(env, rid, NOW - timedelta(days=1))  # 예약은 RESERVED라 가정 -> 이미 환불됨 불일치가 먼저
