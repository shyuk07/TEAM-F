from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# 결제/환불 상태는 domain 계층에 정의된 것을 그대로 사용
from payments.domain.payment import PaymentStatus
from payments.domain.refund import RefundStatus


# 결제 요청
class PaymentCreate(BaseModel):
    reservation_id: UUID


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
    reason: str = Field(min_length=1, max_length=200)


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
