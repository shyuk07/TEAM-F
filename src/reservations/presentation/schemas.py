import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReservationCreateRequest(BaseModel):
    offer_id: uuid.UUID = Field(..., description="예약할 할인 상품 ID")
    quantity: int = Field(..., ge=1, description="예약 수량")


class ReservationCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    offer_id: uuid.UUID
    quantity: int
    unit_price: int = Field(..., description="예약 당시 개당 가격")
    total_price: int = Field(..., description="총 결제 예정 금액")
    status: str = Field(..., description="PENDING_PAYMENT / RESERVED / PICKED_UP / CANCELLED")
    created_at: datetime
    store_name: str
    product_name: str


class ReservationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offer_id: uuid.UUID
    store_name: str
    product_name: str
    quantity: int
    total_price: int
    status: str
    created_at: datetime
    # 제안 필드 (Q-4, D-19): 명세 확정 전
    pickup_code: str
    pickup_address: str


class ReservationListResponse(BaseModel):
    reservations: list[ReservationListItem]
    # 제안 필드 (Q-9, D-18): 명세 확정 전
    page: int
    size: int
    total: int


class ReservationCancelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    cancelled_at: datetime


class PickupRequest(BaseModel):
    pickup_code: str = Field(..., min_length=1, max_length=20, description="예약 확인용 예약번호")


class PickupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pickup_code: str
    status: str
    picked_up_at: datetime
