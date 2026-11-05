import uuid

from reservations.application.ports import StoreOffersPort
from reservations.domain.pickup_reservation import ReservationStatus
from reservations.domain.repository import ReservationRepository


class StoreReservationQuery:
    """매장 단위 예약 확인(읽기 전용, commit 없음). stores PickupPendingPort와 admin 매장 확인을 구조적으로 만족한다 (D-34)."""

    def __init__(self, reservations: ReservationRepository, store_offers: StoreOffersPort):
        self.reservations = reservations
        self.store_offers = store_offers

    async def has_reserved_for_store(
        self, store_id: uuid.UUID, *, excluding_user_id: uuid.UUID | None = None
    ) -> bool:
        # offer 행을 id 오름차순으로 잠가 확인 후 폐점까지 RESERVED가 생기거나 사라지지 못하게 한다 (D-35, D-6)
        offer_ids = await self.store_offers.list_offer_ids_of_store(store_id, for_update=True)
        return await self.reservations.exists_by_offers_and_status(
            offer_ids, ReservationStatus.RESERVED, excluding_user_id=excluding_user_id
        )

    async def has_pickup_pending_for_store(self, store_id: uuid.UUID) -> bool:
        return await self.has_reserved_for_store(store_id)
