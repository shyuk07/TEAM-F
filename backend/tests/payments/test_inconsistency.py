"""데이터 불일치(RD-38·RD-39) 도메인·서비스 테스트. DB 없음.

불일치는 PaymentStateInconsistentError(500 DATA_INCONSISTENT)다. 409/400/403/404 예외를 상속하지 않는다.
검사 순서(pay/refund): 404 -> 403 -> 500 -> 409 -> 400.
"""

import logging
import uuid
from datetime import UTC, datetime

import pytest

from payments.domain.exceptions import (
    InconsistencyKind,
    PaymentAccessDeniedError,
    PaymentAlreadyExistsError,
    PaymentAlreadyRefundedError,
    PaymentConflictError,
    PaymentStateInconsistentError,
    RefundAccessDeniedError,
    ReservationNotFoundError,
    ReservationNotPayableError,
)
from payments.domain.payment import Payment, PaymentStatus
from payments.domain.refund import Refund
from tests.payments.fakes import FAR_FUTURE
from tests.payments.test_service import OTHER, USER, Env, paid

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
K = InconsistencyKind


@pytest.fixture
def anyio_backend():
    return "asyncio"


def make_payment(status="PAID"):
    payment = Payment.request(uuid.uuid4(), USER, 1000, NOW)
    payment.id = uuid.uuid4()
    if status == "PAID":
        payment.approve("pg", NOW)
    elif status == "REFUNDED":
        payment.approve("pg", NOW)
        payment.refund(0, "x", NOW)
    elif status == "FAILED":
        payment.fail({"c": 1}, NOW)
    return payment


def error_records(caplog):
    return [r for r in caplog.records if r.levelno >= logging.ERROR]


# ══ 도메인 ══
def test_exception_is_not_any_other_handled_family():
    error = PaymentStateInconsistentError(K.PAYMENT_MISSING)
    for family in (PaymentConflictError, ValueError, PermissionError, LookupError, RuntimeError):
        assert not isinstance(error, family)
    assert error.error_code == "DATA_INCONSISTENT"
    assert str(error) == "예약과 결제 상태가 일치하지 않습니다. 관리자에게 문의해 주세요."


@pytest.mark.parametrize(
    "status,has_refund,expected",
    [
        ("PAID", False, None),
        ("REFUNDED", False, K.PAYMENT_ALREADY_REFUNDED),
        ("REFUNDED", True, K.PAYMENT_ALREADY_REFUNDED),
        ("READY", False, K.PAYMENT_NOT_PAID),
        ("FAILED", False, K.PAYMENT_NOT_PAID),
        ("PAID", True, K.REFUND_ROW_WITH_PAID_PAYMENT),
    ],
)
def test_ensure_cancel_refundable_combinations(status, has_refund, expected):
    payment = make_payment(status)
    if expected is None:
        payment.ensure_cancel_refundable("RESERVED", has_refund)
        return
    with pytest.raises(PaymentStateInconsistentError) as e:
        payment.ensure_cancel_refundable("RESERVED", has_refund)
    assert e.value.kind == expected
    assert (e.value.reservation_id, e.value.payment_id) == (payment.reservation_id, payment.id)


@pytest.mark.parametrize("reservation_status", ["PENDING_PAYMENT", "CANCELLED", "PICKED_UP"])
def test_ensure_cancel_refundable_rejects_other_reservation_status(reservation_status):
    with pytest.raises(PaymentStateInconsistentError) as e:
        make_payment("PAID").ensure_cancel_refundable(reservation_status, False)
    assert e.value.kind == K.RESERVATION_STATUS_NOT_REFUNDABLE


@pytest.mark.parametrize(
    "payment_status,reservation_status,expected",
    [
        ("PAID", "RESERVED", None),  # 정상
        ("PAID", "PICKED_UP", None),  # 정상
        ("PAID", "CANCELLED", K.PAID_PAYMENT_ON_CANCELLED_RESERVATION),
        ("PAID", "PENDING_PAYMENT", K.PAID_PAYMENT_ON_PENDING_RESERVATION),
        ("READY", "PENDING_PAYMENT", None),
        ("FAILED", "PENDING_PAYMENT", None),
        ("REFUNDED", "PENDING_PAYMENT", K.REFUNDED_PAYMENT_ON_PENDING_RESERVATION),  # RD-40 결정(REQ-35): 불일치
        ("REFUNDED", "CANCELLED", None),  # 정상
    ],
)
def test_ensure_consistent_with_reservation_combinations(payment_status, reservation_status, expected):
    payment = make_payment(payment_status)
    if expected is None:
        payment.ensure_consistent_with_reservation(reservation_status)
        return
    with pytest.raises(PaymentStateInconsistentError) as e:
        payment.ensure_consistent_with_reservation(reservation_status)
    assert e.value.kind == expected


# ══ ①②③ refund_for_cancelled_reservation: 환불·결제 저장 0, commit·rollback 0, 로그 0(호출한 쪽이 기록) ══
async def call(env, reservation_id, status="RESERVED"):
    return await env.service.refund_for_cancelled_reservation(
        reservation_id, reservation_status=status, pickup_start=None, reason="x",
        cancellable_until=FAR_FUTURE,  # 시간 제한(REQ-6) 밖의 불일치 시나리오
    )


async def test_cancel_refund_inconsistencies_write_nothing_and_do_not_log(caplog):
    with caplog.at_level("DEBUG"):
        # ① 결제 없음
        env = Env()
        with pytest.raises(PaymentStateInconsistentError) as e:
            await call(env, uuid.uuid4())
        assert e.value.kind == K.PAYMENT_MISSING and e.value.payment_id is None
        assert env.refunds.items == {} and (env.db.commits, env.db.rollbacks) == (0, 0)

        # ② 이미 REFUNDED
        env = Env()
        payment = await paid(env)
        await call(env, payment.reservation_id)
        commits = env.db.commits
        with pytest.raises(PaymentStateInconsistentError) as e:
            await call(env, payment.reservation_id)
        assert e.value.kind == K.PAYMENT_ALREADY_REFUNDED
        assert len(env.refunds.items) == 1 and env.db.commits == commits

        # ③ 환불 행이 있는데 PAID
        env = Env()
        payment = await paid(env)
        await env.refunds.save(Refund(payment.id, payment.amount, 0, "x", completed_at=NOW))
        with pytest.raises(PaymentStateInconsistentError) as e:
            await call(env, payment.reservation_id)
        assert e.value.kind == K.REFUND_ROW_WITH_PAID_PAYMENT
        assert env.payments.items[payment.id].status == PaymentStatus.PAID
        assert len(env.refunds.items) == 1
    assert caplog.records == []  # payments 서비스는 이 경로에서 로그를 남기지 않는다(중복 방지)


# ══ ④ ensure_no_paid_payment_for_reservation (읽기 전용) ══
async def test_ensure_no_paid_payment_passes_without_payment_or_when_not_paid():
    env = Env()
    await env.service.ensure_no_paid_payment_for_reservation(uuid.uuid4())  # 결제 없음

    for status in ("READY", "FAILED"):
        env = Env()
        payment = make_payment(status)
        await env.payments.save(payment)
        await env.service.ensure_no_paid_payment_for_reservation(payment.reservation_id)
        assert (env.db.commits, env.db.rollbacks) == (0, 0)


async def test_ensure_no_paid_payment_raises_for_refunded_and_writes_nothing(caplog):
    """RD-40 결정(payments REQ-35): 결제 대기 예약에 REFUNDED 결제가 있으면 불일치. 쓰기·로그 없음(호출한 쪽이 기록)."""
    env = Env()
    payment = make_payment("REFUNDED")
    await env.payments.save(payment)
    commits, saved = env.db.commits, dict(env.payments.items)
    with caplog.at_level("DEBUG"):
        with pytest.raises(PaymentStateInconsistentError) as e:
            await env.service.ensure_no_paid_payment_for_reservation(payment.reservation_id)
    assert e.value.kind == K.REFUNDED_PAYMENT_ON_PENDING_RESERVATION
    assert env.db.commits == commits and env.db.rollbacks == 0
    assert env.payments.items == saved and env.refunds.items == {}
    assert caplog.records == []


async def test_ensure_no_paid_payment_raises_for_paid_and_writes_nothing(caplog):
    env = Env()
    payment = await paid(env)
    commits, saved = env.db.commits, dict(env.payments.items)
    with caplog.at_level("DEBUG"):
        with pytest.raises(PaymentStateInconsistentError) as e:
            await env.service.ensure_no_paid_payment_for_reservation(payment.reservation_id)
    assert e.value.kind == K.PAID_PAYMENT_ON_PENDING_RESERVATION
    assert env.db.commits == commits and env.db.rollbacks == 0
    assert env.payments.items == saved and env.refunds.items == {}
    assert caplog.records == []


# ══ ⑤ pay(): 예약 CANCELLED/PENDING_PAYMENT + PAID 결제 ══
@pytest.mark.parametrize(
    "status,kind",
    [
        ("CANCELLED", K.PAID_PAYMENT_ON_CANCELLED_RESERVATION),
        ("PENDING_PAYMENT", K.PAID_PAYMENT_ON_PENDING_RESERVATION),
    ],
)
async def test_pay_with_paid_payment_on_inactive_reservation_is_500_before_409(caplog, status, kind):
    env = Env()
    payment = await paid(env)
    env.reservations.set_status(payment.reservation_id, status)
    commits, rollbacks = env.db.commits, env.db.rollbacks

    with caplog.at_level("DEBUG"):
        with pytest.raises(PaymentStateInconsistentError) as e:
            await env.service.pay(USER, payment.reservation_id)

    assert not isinstance(e.value, PaymentAlreadyExistsError)  # 409가 아니다
    assert e.value.kind == kind
    assert env.db.commits == commits and env.db.rollbacks == rollbacks + 1
    assert len(env.payments.items) == 1 and len(env.reservations.mark_paid_calls) == 1  # 결제·예약 저장 0
    assert env.refunds.items == {}
    [record] = error_records(caplog)  # ERROR 로그 정확히 1건
    text = record.getMessage()
    assert f"kind={kind}" in text and str(payment.reservation_id) in text and str(payment.id) in text
    assert "@" not in text


async def test_pay_regression_normal_duplicate_is_still_409():
    env = Env()
    payment = await paid(env)  # 예약 RESERVED + 결제 PAID
    with pytest.raises(PaymentAlreadyExistsError):
        await env.service.pay(USER, payment.reservation_id)
    assert env.db.rollbacks == 0


async def test_pay_check_order_404_403_before_500():
    env = Env()
    with pytest.raises(ReservationNotFoundError):  # 404
        await env.service.pay(USER, uuid.uuid4())
    payment = await paid(env)
    env.reservations.set_status(payment.reservation_id, "CANCELLED")
    with pytest.raises(PaymentAccessDeniedError):  # 403이 500보다 먼저
        await env.service.pay(OTHER, payment.reservation_id)


async def test_pay_cancelled_reservation_without_payment_is_still_400():
    env = Env()
    rid = env.reservations.add(USER, status="CANCELLED")
    with pytest.raises(ReservationNotPayableError):
        await env.service.pay(USER, rid)


# ══ ⑥ refund(): 예약 CANCELLED/PENDING_PAYMENT + 결제 PAID ══
@pytest.mark.parametrize(
    "status,kind",
    [
        ("CANCELLED", K.PAID_PAYMENT_ON_CANCELLED_RESERVATION),
        ("PENDING_PAYMENT", K.PAID_PAYMENT_ON_PENDING_RESERVATION),
    ],
)
async def test_refund_with_paid_payment_on_inactive_reservation_is_500_before_409(caplog, status, kind):
    env = Env()
    payment = await paid(env)
    env.reservations.set_status(payment.reservation_id, status)
    commits, rollbacks = env.db.commits, env.db.rollbacks

    with caplog.at_level("DEBUG"):
        with pytest.raises(PaymentStateInconsistentError) as e:
            await env.service.refund(USER, payment.id, "사유")

    assert not isinstance(e.value, PaymentAlreadyRefundedError)
    assert e.value.kind == kind
    assert env.db.commits == commits and env.db.rollbacks == rollbacks + 1
    assert env.refunds.items == {} and env.reservations.cancel_calls == []
    assert env.payments.items[payment.id].status == PaymentStatus.PAID
    [record] = error_records(caplog)
    assert f"kind={kind}" in record.getMessage() and "@" not in record.getMessage()


async def test_refund_regression_normal_duplicate_is_still_409():
    env = Env()
    payment = await paid(env)
    await env.service.refund(USER, payment.id, "사유")  # 예약 CANCELLED + 결제 REFUNDED
    rollbacks = env.db.rollbacks
    with pytest.raises(PaymentAlreadyRefundedError):
        await env.service.refund(USER, payment.id, "사유")
    assert env.db.rollbacks == rollbacks and len(env.refunds.items) == 1


async def test_refund_check_order_403_before_500():
    env = Env()
    payment = await paid(env)
    env.reservations.set_status(payment.reservation_id, "CANCELLED")
    with pytest.raises(RefundAccessDeniedError):
        await env.service.refund(OTHER, payment.id, "사유")


async def test_get_apis_do_not_check_inconsistency():
    env = Env()
    payment = await paid(env)
    env.reservations.set_status(payment.reservation_id, "CANCELLED")
    assert (await env.service.get_payment(USER, payment.id)).id == payment.id  # 조회는 검사하지 않는다
