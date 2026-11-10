from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# 결제/환불 상태는 domain 계층에 정의된 것을 그대로 사용
from payments.domain.payment import PaymentStatus
from payments.domain.refund import RefundStatus
from payments.domain.rules import REFUND_REASON_RAW_MAX_LENGTH


# 결제 요청
class PaymentCreate(BaseModel):
    reservation_id: UUID
    use_point: int = Field(0, ge=0, description="사용할 포인트(100P 단위, 선택)")


# 결제 응답
class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reservation_id: UUID
    amount: int = Field(ge=0)
    status: PaymentStatus
    paid_at: datetime | None = None


# 환불 요청
class RefundCreate(BaseModel):
    # 원문 길이는 남용 방지 상한만 둔다. 앞뒤 공백을 뺀 1~200자 판정은 도메인(Refund)이 한다(REQ-34).
    reason: str = Field(min_length=1, max_length=REFUND_REASON_RAW_MAX_LENGTH)


# 환불 요청 응답 (completed_at·reason 없음, D-13)
class RefundCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    refund_amount: int = Field(ge=0)
    penalty_amount: int = Field(ge=0)
    status: RefundStatus


# 환불 조회 응답 (reason 없음)
class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    refund_amount: int = Field(ge=0)
    penalty_amount: int = Field(ge=0)
    status: RefundStatus
    completed_at: datetime | None = None
