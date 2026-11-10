"""상점주용 예약 목록 조회 (요구조건 reservations R-REQ24·25). 읽기 전용, commit 없음."""

import uuid

from reservations.application.ports import StoreOffersPort, StoreOwnerPort
from reservations.application.views import Page
from reservations.domain.exceptions import NotStoreReservationOwnerError, StoreNotFoundError
from reservations.domain.pickup_reservation import PickupReservation, ReservationStatus
from reservations.domain.repository import ReservationRepository


class StoreReservationListService:
    def __init__(
        self,
        reservations: ReservationRepository,
        stores: StoreOwnerPort,
        store_offers: StoreOffersPort,
    ):
        self.reservations = reservations
        self.stores = stores
        self.store_offers = store_offers

    async def list_store_reservations(
        self,
        owner_id: uuid.UUID,
        store_id: uuid.UUID,
        status: ReservationStatus | None,
        page: int,
        size: int,
    ) -> Page[PickupReservation]:
        store = await self.stores.find_store_by_id(store_id)
        if store is None:
            raise StoreNotFoundError()
        if store.owner_id != owner_id:
            raise NotStoreReservationOwnerError()
        # 판매 중단·마감 할인도 포함한 상점의 모든 할인 (잠그지 않음)
        offer_ids = await self.store_offers.list_offer_ids_of_store(store_id)
        items, total = await self.reservations.find_by_offers(
            offer_ids, status=status, page=page, size=size
        )
        return Page(items=items, total=total, page=page, size=size)
