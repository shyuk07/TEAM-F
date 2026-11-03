"""catalog가 stores에 요구하는 읽기 포트. stores를 import하지 않고 구조적으로 맞춘다 (R11)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol


class StoreInfo(Protocol):
    id: uuid.UUID | None
    owner_id: uuid.UUID
    name: str
    pickup_address: str
    approval_at: datetime | None
    closed_at: datetime | None


class StorePort(Protocol):
    async def find_store_by_id(self, store_id: uuid.UUID) -> StoreInfo | None: ...

    async def find_stores_by_ids(self, ids: Sequence[uuid.UUID]) -> list[StoreInfo]: ...
