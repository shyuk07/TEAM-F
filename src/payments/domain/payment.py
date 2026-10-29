from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4


# 결제 상태
class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


# 결제 도메인 객체 (DB와 무관한 순수 파이썬 객체)
@dataclass
class Payment:
    reservation_id: UUID
    user_id: UUID
    amount: int
    status: PaymentStatus = PaymentStatus.PENDING
    paid_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    # 모의 결제: 실제 PG 연동 없이 바로 결제 완료 처리
    @classmethod
    def pay_mock(cls, reservation_id: UUID, user_id: UUID, amount: int) -> "Payment":
        if amount < 0:
            raise ValueError("결제 금액은 0원 이상이어야 합니다.")

        return cls(
            reservation_id=reservation_id,
            user_id=user_id,
            amount=amount,
            status=PaymentStatus.PAID,
            paid_at=datetime.now(UTC),
        )

    def is_refundable(self) -> bool:
        return self.status == PaymentStatus.PAID

    def mark_refunded(self) -> None:
        self.status = PaymentStatus.REFUNDED
