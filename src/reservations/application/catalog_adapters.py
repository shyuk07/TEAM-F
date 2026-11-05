"""catalog 포트(ReservationLookupPort, ReservationCancelPort)를 구조적으로 만족하는 어댑터 (R11).

catalog의 포트를 import하지 않는다(구조적으로만 만족). 예외 번역을 위해 catalog의 domain 예외만 import한다(R11).
container 연결은 src/container.py에서 한다.
"""

import uuid

from catalog.domain.exceptions import ReservationDataInconsistentError
from reservations.application.service import ReservationApplicationService
from reservations.domain.exceptions import DataInconsistentError
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
        # 불일치(500)면 예약 서비스가 이미 롤백하고 ERROR 로그를 1건 남겼다. 여기서는 catalog 예외로 번역만 한다(로그 없음).
        try:
            return await self.service.cancel_all_for_offer(offer_id, reason=reason)
        except DataInconsistentError as error:
            raise ReservationDataInconsistentError(str(error)) from error
