import uuid
from datetime import UTC, datetime
from enum import StrEnum

from payments.domain.exceptions import (
    InvalidPaymentTransitionError,
    PaymentAlreadyRefundedError,
    PaymentNotRefundableError,
    ReservationNotPayableError,
)
from payments.domain.refund import Refund, RefundStatus


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
    ):
        # 0원 결제도 허용한다(D-19).
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError("결제 금액은 0원 이상의 정수여야 합니다.")
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
    ) -> "Payment":
        """READY 결제를 만든다. 금액은 예약 총액을 그대로 쓴다. (포인트 사용은 D-10 미정이라 제외)"""
        if (
            not isinstance(total_price, int)
            or isinstance(total_price, bool)
            or total_price < 0
        ):
            raise ReservationNotPayableError()
        return cls(
            reservation_id=reservation_id,
            user_id=user_id,
            amount=total_price,
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

    def ensure_refundable(self) -> None:
        """409(이미 환불) -> 400(환불 불가 상태) 순서로 검사한다."""
        if self.status == PaymentStatus.REFUNDED:
            raise PaymentAlreadyRefundedError()
        if self.status != PaymentStatus.PAID:
            raise PaymentNotRefundableError()

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
