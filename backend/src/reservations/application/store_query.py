import uuid

from reservations.application.ports import StoreOffersPort
from reservations.domain.pickup_reservation import ReservationStatus
from reservations.domain.repository import ReservationRepository
from reservations.domain.service import Clock


class StoreReservationQuery:
    """매장 단위 예약 확인(읽기 전용, commit 없음). stores PickupPendingPort와 admin 매장 확인을 구조적으로 만족한다 (D-34)."""

    def __init__(
        self, reservations: ReservationRepository, store_offers: StoreOffersPort, clock: Clock | None = None
    ):
        self.reservations = reservations
        self.store_offers = store_offers
        self.clock = clock  # container가 주입한다. 없으면 미수령 판단을 할 수 없어 아래에서 막는다(fail-closed)

    async def has_reserved_for_store(
        self, store_id: uuid.UUID, *, excluding_user_id: uuid.UUID | None = None
    ) -> bool:
        # offer 행을 id 오름차순으로 잠가 확인 후 폐점까지 RESERVED가 생기거나 사라지지 못하게 한다 (D-35, D-6)
        # 미수령(픽업 마감 지남) 예약은 '픽업 대기'로 세지 않는다: 폐점·상점주 탈퇴를 막지 않는다(사용자 결정 2026-11-10, A안)
        offer_ids = await self.store_offers.list_offer_ids_of_store(store_id, for_update=True)
        with_reserved = await self.reservations.find_offer_ids_with_status(
            offer_ids, ReservationStatus.RESERVED, excluding_user_id=excluding_user_id
        )
        if not with_reserved:
            return False
        if self.clock is None:
            raise RuntimeError("StoreReservationQuery에 시계가 주입되지 않았습니다.")
        now = self.clock.now()
        pickup_ends = await self.store_offers.get_pickup_ends(sorted(with_reserved))
        # 픽업 마감을 알 수 없는 할인은 안전하게 픽업 대기로 본다(fail-closed)
        return any(offer_id not in pickup_ends or now <= pickup_ends[offer_id] for offer_id in with_reserved)

    async def has_pickup_pending_for_store(self, store_id: uuid.UUID) -> bool:
        return await self.has_reserved_for_store(store_id)
