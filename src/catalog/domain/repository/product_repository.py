import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from catalog.domain.product import Product


class ProductRepository(ABC):
    @abstractmethod
    async def find_by_id(self, product_id: uuid.UUID, for_update: bool = False) -> Product | None: ...

    @abstractmethod
    async def find_all_by_store_for_update(self, store_id: uuid.UUID) -> list[Product]:
        """상점의 모든 상품을 id 오름차순으로 FOR UPDATE 조회 (잠금 순서: product -> offer)."""

    @abstractmethod
    async def find_by_store(
        self,
        store_id: uuid.UUID,
        *,
        category: str | None,
        is_active: bool,
        page: int,
        size: int,
    ) -> tuple[list[Product], int]: ...

    @abstractmethod
    async def save(self, product: Product) -> Product: ...

    @abstractmethod
    async def search_store_ids(
        self,
        *,
        store_ids: Sequence[uuid.UUID],
        keyword: str | None,
        category: str | None,
        page: int,
        size: int,
    ) -> tuple[list[uuid.UUID], int]:
        """조건에 맞는 노출 상품을 1개 이상 가진 상점 id를 store_ids 순서대로 페이지 단위로, 상점 수 total과 함께 돌려준다."""

    @abstractmethod
    async def find_matching_in_stores(
        self,
        *,
        store_ids: Sequence[uuid.UUID],
        keyword: str | None,
        category: str | None,
        now: datetime,
    ) -> list[tuple[Product, bool]]:
        """상점들의 조건 일치 노출 상품과 has_active_offer. 상품명, id 순."""
