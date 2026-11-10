import uuid
from abc import ABC, abstractmethod
from collections.abc import Collection

from catalog.domain.product_image import ProductImage


class ProductImageRepository(ABC):
    @abstractmethod
    async def add(self, image: ProductImage) -> ProductImage: ...

    @abstractmethod
    async def find_by_id(self, product_id: uuid.UUID, image_id: uuid.UUID) -> ProductImage | None: ...

    @abstractmethod
    async def delete(self, product_id: uuid.UUID, image_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def delete_many(self, product_id: uuid.UUID, image_ids: Collection[uuid.UUID]) -> int: ...
