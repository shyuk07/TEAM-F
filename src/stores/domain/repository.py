import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence

from stores.domain.store import Store


class StoreRepository(ABC):
    @abstractmethod
    async def find_by_id(self, store_id: uuid.UUID, for_update: bool = False) -> Store | None: ...

    @abstractmethod
    async def find_by_ids(self, store_ids: Sequence[uuid.UUID]) -> list[Store]: ...

    @abstractmethod
    async def find_by_owner_id(self, owner_id: uuid.UUID) -> Store | None: ...

    @abstractmethod
    async def save(self, store: Store) -> Store: ...
