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
    async def find_by_owner_id(
        self, owner_id: uuid.UUID, for_update: bool = False
    ) -> Store | None: ...

    @abstractmethod
    async def exists_by_name_and_address(self, name: str, pickup_address: str) -> bool:
        """정규화된 값의 정확 일치. 폐점·정지 상점도 포함한다."""

    @abstractmethod
    async def save(self, store: Store) -> Store: ...

    @abstractmethod
    async def find_visible_near(
        self,
        *,
        latitude: float | None,
        longitude: float | None,
        radius_km: float | None,
    ) -> list[tuple[Store, float | None]]:
        """공개 노출 상점과 거리(km). 위치 지정 시 좌표 있는 상점만 반경 이내를 거리순(동률 id),
        미지정 시 전체를 (name, id) 순으로 거리 None과 함께 돌려준다. 한쪽만 지정하면 ValueError."""
