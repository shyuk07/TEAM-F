import uuid
from dataclasses import dataclass

from catalog.domain.discount_offer import CancelPolicy, DiscountOffer, OfferStatus
from catalog.domain.product import Product


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
class OfferDetailView:
    view: OfferView
    description: str | None
    product_image: list[str]
    pickup_address: str
    latitude: float | None
    longitude: float | None
    notice: str
    cancel_policy: CancelPolicy
