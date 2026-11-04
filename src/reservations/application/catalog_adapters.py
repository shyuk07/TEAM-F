"""catalog 포트(ReservationLookupPort, ReservationCancelPort)를 구조적으로 만족하는 어댑터 (R11).

catalog의 포트를 import하지 않는다. container 연결은 catalog 담당자의 변경(C-2)으로 남아 있다.
"""

import uuid

from reservations.application.service import ReservationApplicationService
from reservations.domain.repository import ReservationRepository


class OfferReservationLookup:
    def __init__(self, reservations: ReservationRepository):
        self.reservations = reservations

    async def has_reservations_for_offer(self, offer_id: uuid.UUID) -> bool:
        return await self.reservations.exists_by_offer(offer_id)


class OfferReservationCanceller:
    def __init__(self, service: ReservationApplicationService):
        self.service = service

    async def cancel_all_for_offer(self, offer_id: uuid.UUID, *, reason: str) -> int:
        return await self.service.cancel_all_for_offer(offer_id, reason=reason)
