import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from stores.domain.exceptions import StoreAlreadyExistsError
from stores.domain.repository import StoreRepository
from stores.domain.service import Clock
from stores.domain.store import Store


class StoresApplicationService:
    def __init__(self, session: AsyncSession, stores: StoreRepository, clock: Clock):
        self.session = session
        self.stores = stores
        self.clock = clock

    async def find_store_by_id(self, store_id: uuid.UUID) -> Store | None:
        return await self.stores.find_by_id(store_id)

    async def find_stores_by_ids(self, ids: Sequence[uuid.UUID]) -> list[Store]:
        return await self.stores.find_by_ids(ids)

    async def open_store(
        self, owner_id: uuid.UUID, owner_name: str | None, pickup_address: str
    ) -> Store:
        if await self.stores.find_by_owner_id(owner_id) is not None:
            raise StoreAlreadyExistsError()
        store = Store.open(
            owner_id=owner_id,
            name=owner_name or "",
            pickup_address=pickup_address,
            now=self.clock.now(),
        )
        await self.stores.save(store)
        await self.session.commit()
        return store
