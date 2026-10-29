from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from payments.domain.payment import Payment


# 환불 상태
class RefundStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# 환불 도메인 객체
@dataclass
class Refund:
    payment_id: UUID
    refund_amount: int
    penalty_amount: int
    reason: str
    status: RefundStatus = RefundStatus.PENDING
    completed_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    # 모의 환불: 결제 금액에서 위약금을 뺀 만큼 바로 환불 완료 처리
    @classmethod
    def refund_mock(cls, payment: Payment, penalty_amount: int, reason: str) -> "Refund":
        if not payment.is_refundable():
            raise ValueError("결제 완료 상태에서만 환불할 수 있습니다.")
        if not 0 <= penalty_amount <= payment.amount:
            raise ValueError("위약금은 0원 이상, 결제 금액 이하여야 합니다.")

        payment.mark_refunded()

        return cls(
            payment_id=payment.id,
            refund_amount=payment.amount - penalty_amount,
            penalty_amount=penalty_amount,
            reason=reason,
            status=RefundStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )
