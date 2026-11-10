"""StockPort의 실제 구현: catalog의 도메인·추상 레포지토리만 사용한다 (R11). commit하지 않는다 (R13).

catalog 서비스(CatalogApplicationService)는 받지 않는다(순환 의존 방지, R12).
잠금은 할인(discount_offers) 행만 건다. 상품 행은 잠그지 않는다.
catalog 예외는 여기서 reservations 예외로 번역한다(RD-34). 로그는 남기지 않는다(요청을 끝내는 서비스가 1건 기록).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from catalog.application.ports import StorePort
from catalog.domain.discount_offer import DiscountOffer
from catalog.domain.exceptions import (
    OfferNotReservableError as CatalogOfferNotReservableError,
)
from catalog.domain.exceptions import (
    OfferOutOfStockError as CatalogOfferOutOfStockError,
)
from catalog.domain.exceptions import StockRestoreExceedsInitialError
from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository
from catalog.domain.repository.product_repository import ProductRepository
from catalog.domain.repository.stock_log_repository import StockLogRepository
from catalog.domain.stock_log import StockLog
from reservations.domain.exceptions import (
    DataInconsistentError,
    InconsistencyDetail,
    OfferNotFoundError,
    OfferNotReservableError,
    OutOfStockError,
)

STOCK_RESTORE_OVER_LIMIT = "STOCK_RESTORE_OVER_LIMIT"


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
    cancellable_until: datetime  # Catalog 취소 정책(D55, C14)으로 계산한 고객 취소·환불 마감 시각


class CatalogStockAdapter:
    def __init__(
        self,
        offers: DiscountOfferRepository,
        products: ProductRepository,
        stores: StorePort,
        stock_logs: StockLogRepository,
    ):
        self.offers = offers
        self.products = products
        self.stores = stores
        self.stock_logs = stock_logs

    async def _load(self, offer_id: uuid.UUID, *, for_update: bool) -> tuple[DiscountOffer, OfferTerms]:
        offer = await self.offers.find_by_id(offer_id, for_update=for_update)  # 할인 행만 잠근다
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
            # 별도 상수를 두지 않고 Catalog 정책을 그대로 쓴다(C14): pickup_start - CANCEL_LEAD_TIME
            cancellable_until=offer.cancel_policy().cancellable_until,
        )
        return offer, terms

    async def get_terms(self, offer_id: uuid.UUID, *, for_update: bool = False) -> OfferTerms:
        _, terms = await self._load(offer_id, for_update=for_update)
        return terms

    async def reserve(
        self, offer_id: uuid.UUID, quantity: int, *, user_id: uuid.UUID, now: datetime
    ) -> OfferTerms:
        offer, terms = await self._load(offer_id, for_update=True)
        try:
            offer.deduct_stock(quantity, now)
        except CatalogOfferNotReservableError as error:
            raise OfferNotReservableError() from error  # 품절·판매 전·종료·중단 모두 OFFER_NOT_RESERVABLE
        except CatalogOfferOutOfStockError as error:
            raise OutOfStockError() from error
        await self.offers.save(offer)
        await self.stock_logs.add(StockLog.reservation_deduction(offer_id, user_id, quantity))
        return terms

    async def release(
        self, offer_id: uuid.UUID, quantity: int, *, user_id: uuid.UUID, reason: str, now: datetime
    ) -> bool:
        """재고를 되돌린다. 닫힌(중단) 할인이면 아무것도 하지 않고 False(D40). reason은 로그에 쓰지 않는다(고정 문구)."""
        offer, _ = await self._load(offer_id, for_update=True)
        try:
            restored = offer.restore_stock(quantity, now)
        except StockRestoreExceedsInitialError as error:
            raise DataInconsistentError(
                [InconsistencyDetail(reservation_id=None, kind=STOCK_RESTORE_OVER_LIMIT)]
            ) from error
        if not restored:
            return False
        await self.offers.save(offer)
        await self.stock_logs.add(StockLog.reservation_cancel_restore(offer_id, user_id, quantity))
        return True
