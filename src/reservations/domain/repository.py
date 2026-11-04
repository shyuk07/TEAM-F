import uuid
from abc import ABC, abstractmethod

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
    async def save(self, reservation: PickupReservation) -> PickupReservation: ...
