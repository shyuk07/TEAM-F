import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from catalog.application.views import OfferView, StockAdjustResult
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
    initial_stock: int = Field(..., ge=1, le=9999, description="최초 수량 (1~9999)")
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
