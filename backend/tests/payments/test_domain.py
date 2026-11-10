import uuid
from datetime import UTC, datetime

import pytest

from payments.domain.cancellation_policy import FullRefundPolicy
from payments.domain.exceptions import (
    InvalidPaymentTransitionError,
    PaymentAccessDeniedError,
    PaymentAlreadyExistsError,
    PaymentAlreadyRefundedError,
    PaymentConflictError,
    PaymentFailedError,
    PaymentNotFoundError,
    PaymentNotRefundableError,
    RefundAccessDeniedError,
    RefundNotFoundError,
    ReservationNotFoundError,
    ReservationNotPayableError,
)
from payments.domain.payment import Payment, PaymentStatus
from payments.domain.refund import Refund, RefundStatus
from payments.domain.reservation_snapshot import ReservationSnapshot
from payments.domain.rules import (
    DEFAULT_CANCELLATION_POLICY,
    REFUNDABLE_RESERVATION_STATUSES,
    RESERVATION_PAID_STATUS,
    RESERVATION_PAYABLE_STATUS,
)

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
USER = uuid.uuid4()
OTHER = uuid.uuid4()


def make_payment(status: PaymentStatus = PaymentStatus.READY, amount: int = 12000) -> Payment:
    """상태에 맞는 시간 값을 채워 결제를 만든다."""
    return Payment(
        id=uuid.uuid4(),
        reservation_id=uuid.uuid4(),
        user_id=USER,
        amount=amount,
        status=status,
        paid_at=NOW if status in (PaymentStatus.PAID, PaymentStatus.REFUNDED) else None,
        failed_at=NOW if status == PaymentStatus.FAILED else None,
    )


def make_snapshot(status: str = RESERVATION_PAYABLE_STATUS, user_id: uuid.UUID = USER):
    return ReservationSnapshot(
        id=uuid.uuid4(), user_id=user_id, total_price=12000, status=status
    )


# ---------- Payment 생성자 ----------
def test_payment_defaults_to_ready():
    p = Payment(uuid.uuid4(), USER, 1000)
    assert p.status == PaymentStatus.READY and p.id is None and p.paid_at is None


def test_zero_amount_is_allowed():
    assert Payment(uuid.uuid4(), USER, 0).amount == 0


@pytest.mark.parametrize("amount", [-1, 1.5, "1000", None, True])
def test_invalid_amount_rejected(amount):
    with pytest.raises(ValueError):
        Payment(uuid.uuid4(), USER, amount)


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        Payment(
            uuid.uuid4(), USER, 1000, status=PaymentStatus.PAID, paid_at=datetime(2026, 1, 1)
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": PaymentStatus.PAID},  # paid_at 없음
        {"status": PaymentStatus.REFUNDED},  # paid_at 없음
        {"status": PaymentStatus.FAILED},  # failed_at 없음
        {"status": PaymentStatus.READY, "paid_at": NOW},  # READY인데 paid_at 있음
    ],
)
def test_status_time_mismatch_rejected(kwargs):
    with pytest.raises(ValueError):
        Payment(uuid.uuid4(), USER, 1000, **kwargs)


def test_unknown_status_rejected():
    with pytest.raises(ValueError):
        Payment(uuid.uuid4(), USER, 1000, status="PENDING")


def test_status_is_str_enum():
    assert PaymentStatus.READY == "READY"
    assert {s.value for s in PaymentStatus} == {"READY", "PAID", "FAILED", "REFUNDED"}
    assert {s.value for s in RefundStatus} == {"COMPLETED"}


# ---------- Payment.request ----------
def test_request_uses_total_price_as_amount():
    p = Payment.request(uuid.uuid4(), USER, 12000)
    assert p.amount == 12000 and p.status == PaymentStatus.READY and p.created_at is not None


@pytest.mark.parametrize("total", [None, -1])
def test_request_with_bad_total_price_is_not_payable(total):
    with pytest.raises(ReservationNotPayableError):
        Payment.request(uuid.uuid4(), USER, total)


# ---------- 상태 전이표 ----------
ALL = list(PaymentStatus)
ALLOWED = {
    ("approve", PaymentStatus.READY): PaymentStatus.PAID,
    ("fail", PaymentStatus.READY): PaymentStatus.FAILED,
    ("refund", PaymentStatus.PAID): PaymentStatus.REFUNDED,
}


def _act(payment: Payment, action: str):
    if action == "approve":
        return payment.approve("pg_1", now=NOW)
    if action == "fail":
        return payment.fail({"code": "X"}, now=NOW)
    return payment.refund(0, "단순 변심", now=NOW)


@pytest.mark.parametrize("action", ["approve", "fail", "refund"])
@pytest.mark.parametrize("start", ALL)
def test_transition_table(start, action):
    payment = make_payment(start)
    if (action, start) in ALLOWED:
        _act(payment, action)
        assert payment.status == ALLOWED[(action, start)]
        return
    with pytest.raises(Exception) as exc:
        _act(payment, action)
    assert payment.status == start  # 거부되면 상태가 바뀌지 않는다
    if action == "refund":
        expected = (
            PaymentAlreadyRefundedError
            if start == PaymentStatus.REFUNDED
            else PaymentNotRefundableError
        )
        assert type(exc.value) is expected
    else:
        assert type(exc.value) is InvalidPaymentTransitionError


def test_approve_records_provider_id_and_paid_at():
    p = make_payment()
    p.approve("pg_9", now=NOW)
    assert p.provider_payment_id == "pg_9" and p.paid_at == NOW


def test_fail_records_response_and_failed_at():
    p = make_payment()
    p.fail({"code": "DECLINED"}, now=NOW)
    assert p.failed_response == {"code": "DECLINED"} and p.failed_at == NOW


# ---------- 환불 ----------
def test_refund_amount_calculation():
    p = make_payment(PaymentStatus.PAID, amount=12000)
    refund = p.refund(2000, "단순 변심", now=NOW)
    assert refund.refund_amount == 10000
    assert refund.penalty_amount == 2000
    assert refund.refund_amount + refund.penalty_amount == 12000
    assert refund.status == RefundStatus.COMPLETED and refund.completed_at == NOW
    assert refund.payment_id == p.id and refund.reason == "단순 변심"
    assert p.status == PaymentStatus.REFUNDED


def test_refund_with_zero_penalty_is_full_refund():
    refund = make_payment(PaymentStatus.PAID).refund(0, "사유")
    assert refund.refund_amount == 12000 and refund.penalty_amount == 0


@pytest.mark.parametrize("penalty", [-1, 12001, 1.5])
def test_refund_penalty_out_of_range(penalty):
    p = make_payment(PaymentStatus.PAID, amount=12000)
    with pytest.raises(ValueError):
        p.refund(penalty, "사유")
    assert p.status == PaymentStatus.PAID


@pytest.mark.parametrize("reason", ["", "   ", "가" * 201])
def test_refund_reason_invalid(reason):
    p = make_payment(PaymentStatus.PAID)
    with pytest.raises(ValueError):
        p.refund(0, reason)
    assert p.status == PaymentStatus.PAID  # 실패하면 상태가 바뀌지 않는다


def test_refund_reason_200_chars_ok():
    assert make_payment(PaymentStatus.PAID).refund(0, "가" * 200)


def test_refund_requires_completed_at_and_aware_time():
    pid = uuid.uuid4()
    with pytest.raises(ValueError):
        Refund(pid, 1000, 0, "사유")  # COMPLETED인데 completed_at 없음
    with pytest.raises(ValueError):
        Refund(pid, 1000, 0, "사유", completed_at=datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        Refund(pid, -1, 0, "사유", completed_at=NOW)
    with pytest.raises(ValueError):
        Refund(pid, 1000, 0, "사유", status="PENDING", completed_at=NOW)


# ---------- 예외 계층 ----------
@pytest.mark.parametrize(
    "exc_class, parent",
    [
        (PaymentNotFoundError, LookupError),
        (RefundNotFoundError, LookupError),
        (ReservationNotFoundError, LookupError),
        (PaymentAccessDeniedError, PermissionError),
        (RefundAccessDeniedError, PermissionError),
        (ReservationNotPayableError, ValueError),
        (PaymentNotRefundableError, ValueError),
        (InvalidPaymentTransitionError, ValueError),
        (PaymentFailedError, ValueError),
        (PaymentAlreadyExistsError, PaymentConflictError),
        (PaymentAlreadyRefundedError, PaymentConflictError),
    ],
)
def test_exception_hierarchy(exc_class, parent):
    assert issubclass(exc_class, parent)


def test_conflict_error_is_not_value_error():
    # ValueError를 상속하면 전역 핸들러가 409가 아닌 400으로 바꾼다.
    assert not issubclass(PaymentConflictError, ValueError)
    assert not issubclass(PaymentAlreadyExistsError, ValueError)
    assert not issubclass(PaymentAlreadyRefundedError, ValueError)
    assert not issubclass(PaymentConflictError, (LookupError, PermissionError))
    assert issubclass(PaymentConflictError, Exception)


def test_400_exceptions_have_error_codes():
    assert ReservationNotPayableError.error_code == "RESERVATION_NOT_PAYABLE"
    assert PaymentNotRefundableError.error_code == "PAYMENT_NOT_REFUNDABLE"
    assert PaymentFailedError.error_code == "PAYMENT_FAILED"
    assert PaymentAlreadyExistsError.error_code == "PAYMENT_ALREADY_EXISTS"
    assert PaymentAlreadyRefundedError.error_code == "PAYMENT_ALREADY_REFUNDED"


# ---------- ReservationSnapshot ----------
def test_snapshot_payable_by_owner_only():
    snap = make_snapshot()
    snap.ensure_payable_by(USER)
    with pytest.raises(PaymentAccessDeniedError):
        snap.ensure_payable_by(OTHER)


def test_snapshot_ownership_check_does_not_check_state():
    # 소유 확인(403)과 상태 확인(400)은 분리되어 있다 (중복 409를 사이에 끼우기 위해)
    make_snapshot(status="CANCELLED").ensure_payable_by(USER)


def test_snapshot_payable_state():
    make_snapshot(RESERVATION_PAYABLE_STATUS).ensure_payable_state()
    for status in (RESERVATION_PAID_STATUS, "CANCELLED", "PICKED_UP"):
        with pytest.raises(ReservationNotPayableError):
            make_snapshot(status).ensure_payable_state()


def test_snapshot_view_and_refund_owner_only():
    snap = make_snapshot()
    snap.ensure_viewable_by(USER)
    snap.ensure_refund_viewable_by(USER)
    snap.ensure_refundable_by(USER)
    with pytest.raises(PaymentAccessDeniedError):
        snap.ensure_viewable_by(OTHER)
    with pytest.raises(RefundAccessDeniedError):
        snap.ensure_refund_viewable_by(OTHER)
    with pytest.raises(RefundAccessDeniedError):
        snap.ensure_refundable_by(OTHER)


def test_snapshot_refundable_state():
    for status in REFUNDABLE_RESERVATION_STATUSES:
        make_snapshot(status).ensure_refundable_state()
    for status in (RESERVATION_PAYABLE_STATUS, "CANCELLED", "PICKED_UP"):
        with pytest.raises(PaymentNotRefundableError):
            make_snapshot(status).ensure_refundable_state()


def test_snapshot_is_frozen():
    snap = make_snapshot()
    with pytest.raises(AttributeError):
        snap.status = "X"  # type: ignore[misc]


# ---------- 위약금 정책 ----------
def test_default_policy_is_zero_penalty():
    assert isinstance(DEFAULT_CANCELLATION_POLICY, FullRefundPolicy)
    assert DEFAULT_CANCELLATION_POLICY.penalty(12000, None, NOW) == 0
    assert FullRefundPolicy().penalty(12000, NOW, NOW) == 0


# ---------- 포인트 (REQ-42~50) ----------
from payments.domain.exceptions import InvalidPointAmountError  # noqa: E402


@pytest.mark.parametrize(
    ("total", "use", "amount"),
    [(10000, 0, 10000), (10000, 100, 9900), (10000, 10000, 0), (1050, 1000, 50)],
)
def test_request_with_use_point(total, use, amount):
    payment = Payment.request(uuid.uuid4(), uuid.uuid4(), total, use_point=use)
    assert payment.amount == amount and payment.point_used == use


@pytest.mark.parametrize("use", [10001, -1, True, 1.5, "100", None])
def test_request_invalid_use_point(use):
    with pytest.raises(InvalidPointAmountError) as error:
        Payment.request(uuid.uuid4(), uuid.uuid4(), 10000, use_point=use)
    assert error.value.error_code == "INVALID_POINT_AMOUNT"
    assert isinstance(error.value, ValueError)


def test_request_invalid_total_still_not_payable():
    with pytest.raises(ReservationNotPayableError):
        Payment.request(uuid.uuid4(), uuid.uuid4(), None, use_point=0)


@pytest.mark.parametrize(
    ("amount", "earn"), [(0, 0), (99, 0), (100, 1), (199, 1), (200, 2), (5000, 50)]
)
def test_earn_point_amount(amount, earn):
    assert Payment(uuid.uuid4(), uuid.uuid4(), amount).earn_point_amount() == earn


def test_earn_excludes_used_point_and_restorable_is_point_used():
    payment = Payment.request(uuid.uuid4(), uuid.uuid4(), 10000, use_point=5000)
    assert payment.amount == 5000
    assert payment.earn_point_amount() == 50
    assert payment.restorable_point_amount() == 5000


@pytest.mark.parametrize("bad", [-1, True, 1.5])
def test_constructor_rejects_invalid_point_used(bad):
    with pytest.raises(ValueError):
        Payment(uuid.uuid4(), uuid.uuid4(), 100, point_used=bad)
