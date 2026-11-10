import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class ReservationCreateRequest(BaseModel):
    offer_id: uuid.UUID = Field(..., description="예약할 할인 상품 ID")
    quantity: StrictInt = Field(..., ge=1, description="예약 수량 (1~5, 상한은 도메인 규칙 R-REQ1에서 검사)")


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
    cancelled_by: str | None = Field(
        None, description="취소 주체: CUSTOMER / STORE / SYSTEM. 취소되지 않았거나 주체를 모르면 null"
    )


class ReservationListResponse(BaseModel):
    reservations: list[ReservationListItem]
    # 제안 필드 (Q-9, D-18): 명세 확정 전
    page: int
    size: int
    total: int


class StoreReservationListItem(BaseModel):
    """상점주용 예약 목록 항목. 고객 정보와 픽업 코드는 넣지 않는다 (R-REQ25)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_name: str
    quantity: int
    total_price: int = Field(..., description="예약 금액")
    status: str = Field(..., description="PENDING_PAYMENT / RESERVED / PICKED_UP / CANCELLED")
    created_at: datetime = Field(..., description="예약 시각")


class StoreReservationListResponse(BaseModel):
    reservations: list[StoreReservationListItem]
    page: int
    size: int
    total: int


class ReservationCancelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    cancelled_at: datetime
    cancelled_by: str | None = Field(None, description="취소 주체: CUSTOMER / STORE / SYSTEM")


class PickupRequest(BaseModel):
    pickup_code: str = Field(..., min_length=1, max_length=20, description="예약 확인용 예약번호")


class PickupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pickup_code: str
    status: str
    picked_up_at: datetime
