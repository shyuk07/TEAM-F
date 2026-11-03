import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.product import Product


class DiscountOfferRepository(ABC):
    @abstractmethod
    async def find_by_id(self, offer_id: uuid.UUID, for_update: bool = False) -> DiscountOffer | None: ...

    @abstractmethod
    async def find_open_by_product(
        self, product_id: uuid.UUID, now: datetime
    ) -> DiscountOffer | None: ...

    @abstractmethod
    async def exists_open_by_store(self, store_id: uuid.UUID, now: datetime) -> bool: ...

    @abstractmethod
    async def find_by_store(
        self,
        store_id: uuid.UUID,
        *,
        status: OfferStatus,
        now: datetime,
        page: int,
        size: int,
    ) -> tuple[list[tuple[DiscountOffer, Product]], int]: ...

    @abstractmethod
    async def save(self, offer: DiscountOffer) -> DiscountOffer: ...
