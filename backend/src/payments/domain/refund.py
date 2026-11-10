import uuid
from datetime import datetime
from enum import StrEnum

from payments.domain.rules import REFUND_REASON_MAX_LENGTH


class RefundStatus(StrEnum):
    # D-8: 환불은 모의라서 생성 즉시 완료된다. PENDING/FAILED는 확정 전까지 만들지 않는다.
    COMPLETED = "COMPLETED"


def _ensure_aware(name: str, value: datetime | None) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{name}에는 timezone이 필요합니다.")


class Refund:
    """환불 이력. 생성 즉시 COMPLETED이며 이후 바뀌지 않는다. (부분 환불 없음, D-5)

    환불 금액 + 위약금 == 결제 금액은 Payment.refund()가 보장한다.
    """

    def __init__(
        self,
        payment_id: uuid.UUID,
        refund_amount: int,
        penalty_amount: int,
        reason: str,
        status: RefundStatus = RefundStatus.COMPLETED,
        id: uuid.UUID | None = None,
        created_at: datetime | None = None,
        completed_at: datetime | None = None,
    ):
        for name, value in (("환불 금액", refund_amount), ("위약금", penalty_amount)):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name}은 0원 이상의 정수여야 합니다.")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("환불 사유는 비워 둘 수 없습니다.")
        if len(reason) > REFUND_REASON_MAX_LENGTH:
            raise ValueError(f"환불 사유는 {REFUND_REASON_MAX_LENGTH}자 이하여야 합니다.")
        _ensure_aware("created_at", created_at)
        _ensure_aware("completed_at", completed_at)
        status = RefundStatus(status)
        if status == RefundStatus.COMPLETED and completed_at is None:
            raise ValueError("완료된 환불에는 completed_at이 필요합니다.")

        self.id = id
        self.payment_id = payment_id
        self.refund_amount = refund_amount
        self.penalty_amount = penalty_amount
        self.reason = reason
        self.status = status
        self.created_at = created_at
        self.completed_at = completed_at
