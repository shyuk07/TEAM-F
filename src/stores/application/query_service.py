import uuid
from dataclasses import dataclass
from collections.abc import Sequence

from stores.domain.exceptions import StoreNotFoundError
from stores.domain.repository import StoreRepository
from stores.domain.store import Store


@dataclass(frozen=True)
class StoreWithDistance:
    store: Store
    distance_km: float | None  # 위치 미지정이면 None


class StoreQueryService:
    """읽기 전용 조회. catalog·reservations의 StorePort를 만족한다. 커밋하지 않는다."""

    def __init__(self, stores: StoreRepository):
        self.stores = stores

    async def find_store_by_id(self, store_id: uuid.UUID) -> Store | None:
        return await self.stores.find_by_id(store_id)

    async def get_store_of_owner(self, owner_id: uuid.UUID) -> Store:
        """상점주 본인의 상점. 없으면 StoreNotFoundError. 폐점·정지 상점도 돌려준다 (D59)."""
        store = await self.stores.find_by_owner_id(owner_id)
        if store is None:
            raise StoreNotFoundError()
        return store

    async def find_stores_by_ids(self, ids: Sequence[uuid.UUID]) -> list[Store]:
        return await self.stores.find_by_ids(ids)

    async def find_visible_stores(
        self,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
        radius_km: float | None = None,
    ) -> list[StoreWithDistance]:
        rows = await self.stores.find_visible_near(
            latitude=latitude, longitude=longitude, radius_km=radius_km
        )
        return [StoreWithDistance(store=s, distance_km=d) for s, d in rows]
