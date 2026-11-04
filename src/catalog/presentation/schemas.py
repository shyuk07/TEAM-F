import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from catalog.application.views import DeactivateOfferResult, OfferDetailView, OfferView, StockAdjustResult
from catalog.domain.discount_offer import OfferStatus


class ProductCreateRequest(BaseModel):
    # 값 검증과 에러 메시지는 도메인(Product)이 한다 (명세의 400 메시지 유지)
    name: str = Field(..., description="상품명 (1~200자)")
    category: str | None = Field(None, description="카테고리 (최대 80자)")
    description: str | None = Field(None, description="설명")
    original_price: int = Field(..., description="정상 가격 (0보다 큼)")
    product_image: list[str] | None = Field(None, description="이미지 URL (최대 10개)")


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(None, description="상품명 (1~200자)")
    category: str | None = Field(None, description="카테고리 (최대 80자)")
    description: str | None = Field(None, description="설명")
    original_price: int | None = Field(None, description="정상 가격 (0보다 큼)")
    product_image: list[str] | None = Field(None, description="이미지 URL (최대 10개)")


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="상품 ID")
    store_id: uuid.UUID = Field(..., description="상점 ID")
    name: str = Field(..., description="상품명")
    category: str | None = Field(None, description="카테고리")
    description: str | None = Field(None, description="설명")
    original_price: int = Field(..., description="정상 가격")
    is_active: bool = Field(..., description="노출 여부")
    product_image: list[str] = Field(..., description="이미지 URL 목록")


class ProductDetailResponse(ProductResponse):
    store_name: str = Field(..., description="상점명")
    pickup_address: str = Field(..., description="픽업 주소")


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    page: int
    size: int
    total: int


class OfferCreateRequest(BaseModel):
    sale_price: int = Field(..., description="할인 가격")
    initial_stock: int = Field(..., description="최초 수량 (1~9999)")
    sales_start: datetime | None = Field(None, description="판매 시작 (기본: 현재 시각)")
    sales_end: datetime = Field(..., description="판매 마감")
    pickup_start: datetime = Field(..., description="픽업 시작")
    pickup_end: datetime = Field(..., description="픽업 마감")

    @field_validator("sales_start", "sales_end", "pickup_start", "pickup_end")
    @classmethod
    def _require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("시간대 정보가 필요합니다.")
        return value


class OfferUpdateRequest(BaseModel):
    sale_price: int | None = Field(None, description="할인 가격")
    initial_stock: int | None = Field(None, description="최초 수량 (1~9999)")
    sales_start: datetime | None = None
    sales_end: datetime | None = None
    pickup_start: datetime | None = None
    pickup_end: datetime | None = None
    is_active: bool | None = Field(
        None, description="false=판매 중단, true=재개 (다른 항목과 함께 보낼 수 없음)"
    )

    @field_validator("sales_start", "sales_end", "pickup_start", "pickup_end")
    @classmethod
    def _require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("시간대 정보가 필요합니다.")
        return value

    @model_validator(mode="after")
    def _check_sent_fields(self) -> "OfferUpdateRequest":
        sent = self.model_fields_set
        for name in sent:
            if getattr(self, name) is None:
                raise ValueError(f"{name}은(는) null일 수 없습니다.")
        if "is_active" in sent and len(sent) > 1:
            raise ValueError("is_active는 다른 항목과 함께 보낼 수 없습니다.")
        return self


class OfferResponse(BaseModel):
    id: uuid.UUID = Field(..., description="할인 ID")
    product_id: uuid.UUID = Field(..., description="상품 ID")
    store_id: uuid.UUID = Field(..., description="상점 ID")
    store_name: str = Field(..., description="상점명")
    product_name: str = Field(..., description="상품명")
    original_price: int = Field(..., description="정상 가격")
    sale_price: int = Field(..., description="할인 가격")
    discount_rate: int = Field(..., description="할인율(%)")
    initial_stock: int = Field(..., description="최초 수량")
    remaining_stock: int = Field(..., description="남은 수량")
    is_sold_out: bool = Field(..., description="품절 여부")
    sales_start: datetime
    sales_end: datetime
    pickup_start: datetime
    pickup_end: datetime
    status: OfferStatus = Field(..., description="SCHEDULED / ON_SALE / SOLD_OUT / CLOSED")
    is_active: bool = Field(..., description="활성 여부")

    @classmethod
    def from_view(cls, view: OfferView) -> "OfferResponse":
        o, p = view.offer, view.product
        return cls(
            id=o.id,
            product_id=o.product_id,
            store_id=p.store_id,
            store_name=view.store_name,
            product_name=p.name,
            original_price=p.original_price,
            sale_price=o.sale_price,
            discount_rate=view.discount_rate,
            initial_stock=o.initial_stock,
            remaining_stock=o.remaining_stock,
            is_sold_out=view.is_sold_out,
            sales_start=o.sales_start,
            sales_end=o.sales_end,
            pickup_start=o.pickup_start,
            pickup_end=o.pickup_end,
            status=view.status,
            is_active=o.is_active,
        )


class OfferListResponse(BaseModel):
    items: list[OfferResponse]
    page: int
    size: int
    total: int


class StockAdjustmentRequest(BaseModel):
    amount: int = Field(..., description="증감 수량 (0 제외, + 입고 / - 차감)")
    reason: str | None = Field(None, max_length=200, description="사유 (최대 200자)")


class StockAdjustmentResponse(BaseModel):
    offer_id: uuid.UUID
    initial_stock: int
    remaining_stock: int
    is_sold_out: bool
    status: OfferStatus
    log_id: uuid.UUID

    @classmethod
    def from_result(cls, result: StockAdjustResult) -> "StockAdjustmentResponse":
        o = result.offer
        return cls(
            offer_id=o.id,
            initial_stock=o.initial_stock,
            remaining_stock=o.remaining_stock,
            is_sold_out=o.is_sold_out,
            status=result.status,
            log_id=result.log_id,
        )


class OfferDeactivateRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=200, description="중단 사유 (1~200자, 저장하지 않음)")
    cancel_reservations: bool = Field(False, description="true이면 기존 예약을 상점주 사유로 취소하고 전액 환불 요청")

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("사유를 입력해 주세요.")
        return value


class OfferDeactivateResponse(BaseModel):
    offer: OfferResponse
    cancelled_reservation_count: int = Field(..., description="취소된 예약 수")

    @classmethod
    def from_result(cls, result: DeactivateOfferResult) -> "OfferDeactivateResponse":
        return cls(
            offer=OfferResponse.from_view(result.view),
            cancelled_reservation_count=result.cancelled_reservation_count,
        )


class CancelPolicyResponse(BaseModel):
    cancellable_until: datetime = Field(..., description="취소 가능 시각")
    description: str = Field(..., description="취소 정책 설명")


class OfferDetailResponse(BaseModel):
    offer: OfferResponse
    description: str | None = Field(None, description="상품 설명")
    product_image: list[str] = Field(..., description="상품 이미지")
    pickup_address: str = Field(..., description="픽업 주소")
    latitude: float | None = Field(None, description="상점 위도")
    longitude: float | None = Field(None, description="상점 경도")
    notice: str = Field(..., description="안내 문구")
    cancel_policy: CancelPolicyResponse

    @classmethod
    def from_view(cls, view: OfferDetailView) -> "OfferDetailResponse":
        return cls(
            offer=OfferResponse.from_view(view.view),
            description=view.description,
            product_image=view.product_image,
            pickup_address=view.pickup_address,
            latitude=view.latitude,
            longitude=view.longitude,
            notice=view.notice,
            cancel_policy=CancelPolicyResponse(
                cancellable_until=view.cancel_policy.cancellable_until,
                description=view.cancel_policy.description,
            ),
        )
