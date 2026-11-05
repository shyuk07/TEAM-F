import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from stores.application.ports import OpenOffersPort, PickupPendingPort
from stores.domain.exceptions import StoreNotFoundError
from stores.domain.repository import StoreRepository
from stores.domain.service import Clock, Geocoder
from stores.domain.store import Store


class StoresApplicationService:
    def __init__(
        self,
        session: AsyncSession,
        stores: StoreRepository,
        clock: Clock,
        open_offers: OpenOffersPort,
        pickup_pending: PickupPendingPort,
        geocoder: Geocoder,
    ):
        self.geocoder = geocoder
        self.session = session
        self.stores = stores
        self.clock = clock
        self.open_offers = open_offers
        self.pickup_pending = pickup_pending

    async def close_store(
        self, owner_id: uuid.UUID, store_id: uuid.UUID, *, commit: bool = True
    ) -> Store:
        now = self.clock.now()
        store = await self._locked_store(store_id)
        store.ensure_owned_by(owner_id, "본인 상점만 폐점할 수 있습니다.")
        has_open = await self.open_offers.has_open_offers_for_store(store_id, now=now)
        pending = await self.pickup_pending.has_pickup_pending_for_store(store_id)
        store.close(now, has_open_offers=has_open, has_pickup_pending=pending)
        await self.stores.save(store)
        await self._finish(commit)
        return store

    async def open_store(
        self, owner_id: uuid.UUID, owner_name: str | None, pickup_address: str
    ) -> Store:
        # 검증 -> 중복 확인 -> 지오코딩(외부 호출, 행 잠금 없음) -> 쓰기 (stores.md 14.4, D31·D40)
        address = Store.normalize_address(pickup_address)
        name = Store.normalize_name(owner_name)
        has_store = await self.stores.find_by_owner_id(owner_id) is not None
        duplicate = await self.stores.exists_by_name_and_address(name, address)
        Store.ensure_can_open(owner_already_has_store=has_store, duplicate_exists=duplicate)
        coordinates = await self.geocoder.geocode(address)
        store = Store.open(
            owner_id=owner_id,
            name=name,
            pickup_address=address,
            now=self.clock.now(),
            coordinates=coordinates,
        )
        await self.stores.save(store)
        await self.session.commit()
        return store

    async def _finish(self, commit: bool) -> None:
        if commit:
            await self.session.commit()

    async def _locked_store(self, store_id: uuid.UUID) -> Store:
        store = await self.stores.find_by_id(store_id, for_update=True)
        if store is None:
            raise StoreNotFoundError()
        return store

    async def lock_store(self, store_id: uuid.UUID) -> Store:
        return await self._locked_store(store_id)

    async def lock_store_of_owner(self, owner_id: uuid.UUID) -> Store | None:
        return await self.stores.find_by_owner_id(owner_id, for_update=True)

    async def suspend_store(
        self, store_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> Store:
        store = await self._locked_store(store_id)
        store.suspend(reason, now)
        await self.stores.save(store)
        await self._finish(commit)
        return store

    async def suspend_stores_of_owner(
        self, owner_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> Store | None:
        store = await self.stores.find_by_owner_id(owner_id, for_update=True)
        if store is None:
            return None
        if store.suspend_if_active(reason, now):
            await self.stores.save(store)
        await self._finish(commit)
        return store

    async def check_force_closable(self, store_id: uuid.UUID, reason: str) -> None:
        store = await self._locked_store(store_id)
        store.ensure_force_closable(reason)

    async def close_store_by_admin(
        self,
        store_id: uuid.UUID,
        reason: str,
        *,
        has_reserved_reservations: bool,
        now: datetime,
        commit: bool = True,
    ) -> Store:
        store = await self._locked_store(store_id)
        store.force_close(reason, now, has_reserved_reservations)
        await self.stores.save(store)
        await self._finish(commit)
        return store
