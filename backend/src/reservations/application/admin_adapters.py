"""admin ReservationAdminPort를 구조적으로 만족하는 어댑터 (R11). admin 포트는 import하지 않고 admin 도메인 예외만 쓴다."""

import uuid

from admin.domain.exceptions import ReservationDataInconsistentError
from reservations.application.service import ReservationApplicationService
from reservations.application.store_query import StoreReservationQuery
from reservations.domain.exceptions import DataInconsistentError


class ReservationAdminAdapter:
    def __init__(self, service: ReservationApplicationService, query: StoreReservationQuery):
        self.service = service
        self.query = query

    async def cancel_active_for_user(self, user_id: uuid.UUID, *, reason: str) -> int:
        # 불일치면 예약 서비스가 이미 롤백하고 ERROR 로그를 1건 남겼다. 여기서는 번역만 한다(로그 없음).
        try:
            return await self.service.cancel_all_for_user(user_id, reason=reason)
        except DataInconsistentError as error:
            raise ReservationDataInconsistentError(str(error)) from error

    async def has_reserved_for_store(
        self, store_id: uuid.UUID, *, excluding_user_id: uuid.UUID | None = None
    ) -> bool:
        return await self.query.has_reserved_for_store(store_id, excluding_user_id=excluding_user_id)
