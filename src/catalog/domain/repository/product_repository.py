import uuid
from abc import ABC, abstractmethod

from catalog.domain.product import Product


class ProductRepository(ABC):
    @abstractmethod
    async def find_by_id(self, product_id: uuid.UUID, for_update: bool = False) -> Product | None: ...

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
