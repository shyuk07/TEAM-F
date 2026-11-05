import uuid
from collections.abc import Sequence

from stores.domain.repository import StoreRepository
from stores.domain.store import Store


class StoreQueryService:
    """읽기 전용 조회. catalog·reservations의 StorePort를 만족한다. 커밋하지 않는다."""

    def __init__(self, stores: StoreRepository):
        self.stores = stores

    async def find_store_by_id(self, store_id: uuid.UUID) -> Store | None:
        return await self.stores.find_by_id(store_id)

    async def find_stores_by_ids(self, ids: Sequence[uuid.UUID]) -> list[Store]:
        return await self.stores.find_by_ids(ids)
