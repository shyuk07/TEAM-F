import uuid
from datetime import UTC, datetime
from enum import StrEnum

from payments.domain.exceptions import (
    InconsistencyKind,
    InvalidPaymentTransitionError,
    InvalidPointAmountError,
    PaymentAlreadyRefundedError,
    PaymentNotRefundableError,
    PaymentStateInconsistentError,
    ReservationNotPayableError,
)
from payments.domain.refund import Refund, RefundStatus
from payments.domain.rules import (
    POINT_EARN_PERCENT,
    PAID_PAYMENT_CONFLICT_RESERVATION_STATUSES,
    REFUNDABLE_RESERVATION_STATUSES,
    RESERVATION_CANCELLED_STATUS,
    RESERVATION_PAYABLE_STATUS,
)


class PaymentStatus(StrEnum):
    READY = "READY"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


def _ensure_aware(name: str, value: datetime | None) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{name}에는 timezone이 필요합니다.")


class Payment:
    """결제.

    허용 전이: READY -> PAID(approve), READY -> FAILED(fail), PAID -> REFUNDED(refund).
    FAILED와 REFUNDED는 종단 상태다.
    """

    def __init__(
        self,
        reservation_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: int,
        status: PaymentStatus = PaymentStatus.READY,
        id: uuid.UUID | None = None,
        provider_payment_id: str | None = None,
        created_at: datetime | None = None,
        paid_at: datetime | None = None,
        failed_at: datetime | None = None,
        failed_response: dict | None = None,
        point_used: int = 0,
    ):
        # 0원 결제도 허용한다(D-19).
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError("결제 금액은 0원 이상의 정수여야 합니다.")
        if not isinstance(point_used, int) or isinstance(point_used, bool) or point_used < 0:
            raise ValueError("사용 포인트는 0 이상의 정수여야 합니다.")
        status = PaymentStatus(status)
        for name, value in (
            ("created_at", created_at),
            ("paid_at", paid_at),
            ("failed_at", failed_at),
        ):
            _ensure_aware(name, value)
        if status in (PaymentStatus.PAID, PaymentStatus.REFUNDED) and paid_at is None:
            raise ValueError("결제 완료 상태에는 paid_at이 필요합니다.")
        if status == PaymentStatus.FAILED and failed_at is None:
            raise ValueError("결제 실패 상태에는 failed_at이 필요합니다.")
        if status == PaymentStatus.READY and paid_at is not None:
            raise ValueError("결제 대기 상태에는 paid_at이 있을 수 없습니다.")

        self.id = id
        self.reservation_id = reservation_id
        self.user_id = user_id
        self.amount = amount
        self.point_used = point_used
        self.status = status
        self.provider_payment_id = provider_payment_id
        self.created_at = created_at
        self.paid_at = paid_at
        self.failed_at = failed_at
        self.failed_response = failed_response

    @classmethod
    def request(
        cls,
        reservation_id: uuid.UUID,
        user_id: uuid.UUID,
        total_price: int | None,
        now: datetime | None = None,
        *,
        use_point: int = 0,
    ) -> "Payment":
        """READY 결제를 만든다. amount = 예약 총액 - use_point, point_used = use_point (REQ-43·44).

        100P 단위·잔액 검사는 auth User.use_points가 한다(단위 정본은 auth).
        """
        if (
            not isinstance(total_price, int)
            or isinstance(total_price, bool)
            or total_price < 0
        ):
            raise ReservationNotPayableError()
        if (
            not isinstance(use_point, int)
            or isinstance(use_point, bool)
            or use_point < 0
            or use_point > total_price
        ):
            raise InvalidPointAmountError()
        return cls(
            reservation_id=reservation_id,
            user_id=user_id,
            amount=total_price - use_point,
            point_used=use_point,
            created_at=now or datetime.now(UTC),
        )

    def approve(self, provider_payment_id: str, now: datetime | None = None) -> None:
        """READY -> PAID"""
        if self.status != PaymentStatus.READY:
            raise InvalidPaymentTransitionError(
                f"{self.status} 상태의 결제는 승인할 수 없습니다."
            )
        self.status = PaymentStatus.PAID
        self.provider_payment_id = provider_payment_id
        self.paid_at = now or datetime.now(UTC)

    def fail(self, response: dict | None = None, now: datetime | None = None) -> None:
        """READY -> FAILED"""
        if self.status != PaymentStatus.READY:
            raise InvalidPaymentTransitionError(
                f"{self.status} 상태의 결제는 실패 처리할 수 없습니다."
            )
        self.status = PaymentStatus.FAILED
        self.failed_response = dict(response) if response else None
        self.failed_at = now or datetime.now(UTC)

    def earn_point_amount(self) -> int:
        """적립 포인트(REQ-46·47·50). 포인트 사용분을 뺀 결제 금액의 1%, 정수 연산. 위약금과 무관."""
        return (self.amount * POINT_EARN_PERCENT) // 100

    def restorable_point_amount(self) -> int:
        """환불 시 복구할 포인트(REQ-49). 결제 때 쓴 포인트 전액, 위약금과 무관."""
        return self.point_used

    @property
    def is_paid(self) -> bool:
        return self.status == PaymentStatus.PAID

    def ensure_refundable(self) -> None:
        """409(이미 환불) -> 400(환불 불가 상태) 순서로 검사한다."""
        if self.status == PaymentStatus.REFUNDED:
            raise PaymentAlreadyRefundedError()
        if self.status != PaymentStatus.PAID:
            raise PaymentNotRefundableError()

    def ensure_cancel_refundable(self, reservation_status: str, has_refund: bool) -> None:
        """예약 취소가 부르는 환불의 정방향 불일치 검사(RD-38 ①②③).

        호출자는 예약이 결제 완료(RESERVED)일 때만 부른다. 그런데 결제가 REFUNDED이거나 PAID가 아니거나,
        환불 행이 이미 있으면 데이터 불일치다. 새 환불을 만들지 않고 중단한다.
        """
        if reservation_status not in REFUNDABLE_RESERVATION_STATUSES:
            raise self._inconsistent(InconsistencyKind.RESERVATION_STATUS_NOT_REFUNDABLE)
        if self.status == PaymentStatus.REFUNDED:
            raise self._inconsistent(InconsistencyKind.PAYMENT_ALREADY_REFUNDED)
        if self.status != PaymentStatus.PAID:
            raise self._inconsistent(InconsistencyKind.PAYMENT_NOT_PAID)
        if has_refund:
            raise self._inconsistent(InconsistencyKind.REFUND_ROW_WITH_PAID_PAYMENT)

    def ensure_consistent_with_reservation(self, reservation_status: str) -> None:
        """반대 방향 불일치 검사.

        - RD-38 ④, RD-39: 결제가 PAID인데 예약이 CANCELLED/PENDING_PAYMENT면 불일치.
        - RD-40(사용자 결정, payments REQ-35): 결제가 REFUNDED인데 예약이 PENDING_PAYMENT면 불일치.
          환불은 예약 취소와 함께 일어나므로 정상 흐름에서는 생기지 않는다.
        READY/FAILED 결제와 REFUNDED + CANCELLED(정상 환불 결과)는 막지 않는다.
        """
        if self.status == PaymentStatus.REFUNDED and reservation_status == RESERVATION_PAYABLE_STATUS:
            raise self._inconsistent(InconsistencyKind.REFUNDED_PAYMENT_ON_PENDING_RESERVATION)
        if self.is_paid and reservation_status in PAID_PAYMENT_CONFLICT_RESERVATION_STATUSES:
            kind = (
                InconsistencyKind.PAID_PAYMENT_ON_CANCELLED_RESERVATION
                if reservation_status == RESERVATION_CANCELLED_STATUS
                else InconsistencyKind.PAID_PAYMENT_ON_PENDING_RESERVATION
            )
            raise self._inconsistent(kind)

    def _inconsistent(self, kind: InconsistencyKind) -> PaymentStateInconsistentError:
        return PaymentStateInconsistentError(kind, self.reservation_id, self.id)

    def refund(
        self, penalty_amount: int, reason: str, now: datetime | None = None
    ) -> Refund:
        """PAID -> REFUNDED. 환불(COMPLETED) 객체를 만든다. 부분 환불은 없다(D-5)."""
        self.ensure_refundable()
        if (
            not isinstance(penalty_amount, int)
            or isinstance(penalty_amount, bool)
            or not 0 <= penalty_amount <= self.amount
        ):
            raise ValueError("위약금은 0원 이상, 결제 금액 이하여야 합니다.")
        completed_at = now or datetime.now(UTC)
        # Refund 생성자가 사유(공백·200자)를 검증한다. 실패하면 결제 상태는 바뀌지 않는다.
        refund = Refund(
            payment_id=self.id,
            refund_amount=self.amount - penalty_amount,
            penalty_amount=penalty_amount,
            reason=reason,
            status=RefundStatus.COMPLETED,
            created_at=completed_at,
            completed_at=completed_at,
        )
        self.status = PaymentStatus.REFUNDED
        return refund
