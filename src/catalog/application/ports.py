"""catalog가 stores에 요구하는 읽기 포트. stores를 import하지 않고 구조적으로 맞춘다 (R11)."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol


class StoreInfo(Protocol):
    id: uuid.UUID | None
    owner_id: uuid.UUID
    name: str
    pickup_address: str
    latitude: float | None
    longitude: float | None
    approval_at: datetime | None
    closed_at: datetime | None
    suspended_at: datetime | None


class StorePort(Protocol):
    async def find_store_by_id(self, store_id: uuid.UUID) -> StoreInfo | None: ...

    async def find_stores_by_ids(self, ids: Sequence[uuid.UUID]) -> list[StoreInfo]: ...


class ReservationLookupPort(Protocol):
    """할인에 예약이 있는지 묻는 읽기 포트 (쓰는 쪽인 catalog가 정의, R11)."""

    async def has_reservations_for_offer(self, offer_id: uuid.UUID) -> bool: ...


class ReservationCancelPort(Protocol):
    """할인의 예약을 상점주 사유로 일괄 취소하고 전액 환불을 요청하는 쓰기 포트 (쓰는 쪽인 catalog가 정의, R11).

    - 취소한 예약 수를 돌려준다. 이미 취소된 예약은 세지 않는다.
    - 픽업 완료 예약이 하나라도 있으면 아무것도 취소하기 전에 PickedUpReservationExistsError를 낸다.
    - commit하지 않는다(R5, R13). 같은 요청 세션에서 동작하고 commit은 catalog 서비스가 한다.
    - 재고를 되돌리지 않는다(순환 의존 방지, R12).
    """

    async def cancel_all_for_offer(self, offer_id: uuid.UUID, *, reason: str) -> int: ...
