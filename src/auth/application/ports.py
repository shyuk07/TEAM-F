"""탈퇴 조정(AccountWithdrawalService)이 다른 컨텍스트에 요구하는 포트 (쓰는 쪽이 정의, R11).

stores·catalog·reservations의 기존 서비스/어댑터가 구조적으로 만족한다. auth는 그 모듈들을 import하지 않는다 (R12).
모든 메서드는 commit=False로 부르며 호출자(AccountWithdrawalService)가 마지막에 한 번 commit한다 (R13).
"""

import uuid
from datetime import datetime
from typing import Protocol


class StoreInfo(Protocol):
    id: uuid.UUID | None
    is_closed: bool


class WithdrawalStorePort(Protocol):
    async def lock_store_of_owner(self, owner_id: uuid.UUID) -> StoreInfo | None: ...

    async def close_store_by_admin(
        self,
        store_id: uuid.UUID,
        reason: str,
        *,
        has_reserved_reservations: bool,
        now: datetime,
        commit: bool = True,
    ) -> StoreInfo: ...


class WithdrawalOfferPort(Protocol):
    async def end_all_sales_of_store(
        self, store_id: uuid.UUID, *, now: datetime, commit: bool = True
    ) -> int: ...


class WithdrawalReservationPort(Protocol):
    """결제 대기·RESERVED 예약을 취소(재고 복구, 환불·포인트 복구)한다. 절대 commit하지 않는다."""

    async def cancel_active_for_user(self, user_id: uuid.UUID, *, reason: str) -> int: ...

    async def has_reserved_for_store(
        self, store_id: uuid.UUID, *, excluding_user_id: uuid.UUID | None = None
    ) -> bool: ...
