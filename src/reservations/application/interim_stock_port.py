"""임시 재고 포트 (D-25). catalog의 재고 기능(C-1)이 머지되면 CatalogStockService로 교체한다."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from catalog.application.ports import StorePort
from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository
from catalog.domain.repository.product_repository import ProductRepository
from reservations.domain.exceptions import (
    OfferNotFoundError,
    OfferNotReservableError,
    OutOfStockError,
)


@dataclass(frozen=True)
class OfferTerms:
    offer_id: uuid.UUID
    owner_id: uuid.UUID
    store_name: str
    product_name: str
    pickup_address: str
    sale_price: int
    pickup_start: datetime
    pickup_end: datetime


class ReadOnlyOfferStockPort:
    """읽기 전용 임시 구현.

    한계: 재고를 차감하지 않고, 행을 잠그지 않으며, stock_log를 쓰지 않는다.
    release는 아무것도 하지 않고 False를 돌려준다. 실서버에서 예약이 재고를 줄이지 않는다
    (오버셀 가능, 취소해도 복구 없음).
    """

    def __init__(self, offers: DiscountOfferRepository, products: ProductRepository, stores: StorePort):
        self.offers = offers
        self.products = products
        self.stores = stores

    async def _load(self, offer_id: uuid.UUID) -> tuple[DiscountOffer, OfferTerms]:
        offer = await self.offers.find_by_id(offer_id)
        if offer is None:
            raise OfferNotFoundError()
        product = await self.products.find_by_id(offer.product_id)
        if product is None:
            raise OfferNotFoundError()
        store = await self.stores.find_store_by_id(product.store_id)
        if store is None:
            raise OfferNotFoundError()
        terms = OfferTerms(
            offer_id=offer_id,
            owner_id=store.owner_id,
            store_name=store.name,
            product_name=product.name,
            pickup_address=store.pickup_address,
            sale_price=offer.sale_price,
            pickup_start=offer.pickup_start,
            pickup_end=offer.pickup_end,
        )
        return offer, terms

    async def get_terms(self, offer_id: uuid.UUID, *, for_update: bool = False) -> OfferTerms:
        _, terms = await self._load(offer_id)
        return terms

    async def reserve(
        self, offer_id: uuid.UUID, quantity: int, *, user_id: uuid.UUID, now: datetime
    ) -> OfferTerms:
        offer, terms = await self._load(offer_id)
        if offer.effective_status(now) != OfferStatus.ON_SALE:
            raise OfferNotReservableError()
        if quantity > offer.remaining_stock:
            raise OutOfStockError()
        return terms

    async def release(
        self, offer_id: uuid.UUID, quantity: int, *, user_id: uuid.UUID, reason: str
    ) -> bool:
        return False
