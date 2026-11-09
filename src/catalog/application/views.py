import uuid
from dataclasses import dataclass
from datetime import datetime

from catalog.application.ports import StoreInfo
from catalog.domain.discount_offer import CancelPolicy, DiscountOffer, OfferStatus
from catalog.domain.product import Product
from catalog.domain.product_image import ProductImage


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    page: int
    size: int
    total: int


@dataclass(frozen=True)
class ProductDetailView:
    product: Product
    store_name: str
    pickup_address: str


@dataclass(frozen=True)
class OfferView:
    offer: DiscountOffer
    product: Product
    store_name: str
    status: OfferStatus
    discount_rate: int
    is_sold_out: bool


@dataclass(frozen=True)
class StockAdjustResult:
    offer: DiscountOffer
    status: OfferStatus
    log_id: uuid.UUID


@dataclass(frozen=True)
class DeactivateOfferResult:
    view: OfferView
    cancelled_reservation_count: int


@dataclass(frozen=True)
class OfferSuspensionView:
    """suspend_offer 결과. admin.md 6.2 EP 7 응답 필드(id, store_id, title, status, suspended_*)와 같은 평평한 속성."""

    id: uuid.UUID
    store_id: uuid.UUID
    title: str  # 상품명
    status: OfferStatus
    suspended_reason: str
    suspended_at: datetime


@dataclass(frozen=True)
class OfferDetailView:
    view: OfferView
    description: str | None
    product_image: list[str]
    pickup_address: str
    latitude: float | None
    longitude: float | None
    notice: str
    cancel_policy: CancelPolicy


@dataclass(frozen=True)
class SearchedProduct:
    product: Product
    has_active_offer: bool


@dataclass(frozen=True)
class StoreSearchHit:
    store: StoreInfo
    distance_km: float | None
    products: list[SearchedProduct]


@dataclass(frozen=True)
class NearbyOfferView:
    view: OfferView
    distance_km: float | None


@dataclass(frozen=True)
class ProductImageUploadResult:
    image: ProductImage
    product: Product
