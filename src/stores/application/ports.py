import uuid
from datetime import datetime
from typing import Protocol


class OpenOffersPort(Protocol):
    """진행 중이거나 예정된 할인이 있는지 묻는 읽기 포트. catalog 서비스가 구조적으로 만족한다."""

    async def has_open_offers_for_store(
        self, store_id: uuid.UUID, *, now: datetime | None = None
    ) -> bool: ...


class PickupPendingPort(Protocol):
    """픽업 대기 중인 예약이 있는지 묻는 읽기 포트. commit하지 않는다.

    미연계: 구현은 NoPickupPendingReservations(항상 False). reservations 후속에서 교체한다.
    """

    async def has_pickup_pending_for_store(self, store_id: uuid.UUID) -> bool: ...
