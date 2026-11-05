import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence

from reservations.domain.pickup_reservation import PickupReservation, ReservationStatus


class ReservationRepository(ABC):
    @abstractmethod
    async def find_by_id(
        self, reservation_id: uuid.UUID, for_update: bool = False
    ) -> PickupReservation | None: ...

    @abstractmethod
    async def find_by_user(
        self,
        user_id: uuid.UUID,
        *,
        status: ReservationStatus | None,
        page: int,
        size: int,
    ) -> tuple[list[PickupReservation], int]: ...

    @abstractmethod
    async def find_by_offer(
        self, offer_id: uuid.UUID, *, for_update: bool = False
    ) -> list[PickupReservation]: ...

    @abstractmethod
    async def exists_by_offer(self, offer_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def find_by_user_and_statuses(
        self,
        user_id: uuid.UUID,
        statuses: Sequence[ReservationStatus],
        *,
        for_update: bool = False,
    ) -> list[PickupReservation]:
        """회원의 해당 상태 예약을 (offer_id, id) 오름차순으로 조회한다(잠금 순서 고정)."""

    @abstractmethod
    async def exists_by_offers_and_status(
        self,
        offer_ids: Sequence[uuid.UUID],
        status: ReservationStatus,
        *,
        excluding_user_id: uuid.UUID | None = None,
    ) -> bool:
        """offer_ids 중 하나라도 해당 상태 예약이 있으면 True. 빈 목록이면 False. 행을 잠그지 않는다."""

    @abstractmethod
    async def save(self, reservation: PickupReservation) -> PickupReservation: ...
