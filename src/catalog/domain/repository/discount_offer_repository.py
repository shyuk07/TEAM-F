import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.product import Product


class DiscountOfferRepository(ABC):
    @abstractmethod
    async def find_by_id(self, offer_id: uuid.UUID, for_update: bool = False) -> DiscountOffer | None: ...

    @abstractmethod
    async def find_with_product(self, offer_id: uuid.UUID) -> tuple[DiscountOffer, Product] | None: ...

    @abstractmethod
    async def find_open_by_product(
        self, product_id: uuid.UUID, now: datetime
    ) -> DiscountOffer | None: ...

    @abstractmethod
    async def exists_open_by_store(self, store_id: uuid.UUID, now: datetime) -> bool: ...

    @abstractmethod
    async def find_open_by_store_for_update(
        self, store_id: uuid.UUID, now: datetime
    ) -> list[DiscountOffer]:
        """상점의 진행 중(is_active 이고 마감 전, 정지 포함) 할인을 id 오름차순으로 FOR UPDATE 조회."""

    @abstractmethod
    async def find_ids_by_store(
        self, store_id: uuid.UUID, *, for_update: bool = False
    ) -> list[uuid.UUID]:
        """상점의 모든 할인 ID(상태 무관)를 id 오름차순으로 조회한다. for_update면 할인 행을 잠근다."""

    @abstractmethod
    async def find_by_store(
        self,
        store_id: uuid.UUID,
        *,
        statuses: Sequence[OfferStatus],
        now: datetime,
        page: int,
        size: int,
    ) -> tuple[list[tuple[DiscountOffer, Product]], int]: ...

    @abstractmethod
    async def save(self, offer: DiscountOffer) -> DiscountOffer: ...
