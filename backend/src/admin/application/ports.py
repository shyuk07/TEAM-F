"""admin이 다른 컨텍스트에 요구하는 포트 (쓰는 쪽이 정의, D30, R11).

각 모듈의 application 서비스가 구조적으로 만족한다. admin은 그 모듈들을 import하지 않는다.
"""

import uuid
from datetime import datetime
from typing import Protocol


# ── 결과 Protocol: 필요한 속성만 선언한다 ──
class AccountInfo(Protocol):
    id: uuid.UUID
    role: str
    status: str
    is_owner: bool


class UserAdminInfo(Protocol):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    status: str
    approved_at: datetime | None
    rejected_reason: str | None
    rejected_at: datetime | None
    suspended_reason: str | None
    suspended_at: datetime | None
    suspended_until: datetime | None
    deleted_at: datetime | None


class PointLogInfo(Protocol):
    id: uuid.UUID | None
    user_id: uuid.UUID
    amount: int
    point_type: str
    reason: str | None
    balance_after: int | None
    created_by: uuid.UUID | None
    created_at: datetime | None


class PointHistoryInfo(Protocol):
    user_id: uuid.UUID
    balance: int
    history: list[PointLogInfo]
    page: int
    size: int
    total: int


class UserListItemInfo(Protocol):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    status: str  # 실효 상태 (D55)
    created_at: datetime


class UserPageInfo(Protocol):
    items: list[UserListItemInfo]
    page: int
    size: int
    total: int


class StoreAdminInfo(Protocol):
    id: uuid.UUID | None
    owner_id: uuid.UUID
    name: str
    status: str
    suspended_reason: str | None
    suspended_at: datetime | None
    closed_reason: str | None
    closed_at: datetime | None
    is_closed: bool


class OfferAdminInfo(Protocol):
    id: uuid.UUID
    store_id: uuid.UUID
    title: str
    status: str
    suspended_reason: str
    suspended_at: datetime


# ── 포트 ──
class AccountAdminPort(Protocol):
    async def get_account(self, user_id: uuid.UUID) -> AccountInfo: ...

    async def approve_owner(
        self, user_id: uuid.UUID, *, now: datetime, commit: bool = True
    ) -> UserAdminInfo: ...

    async def reject_owner(
        self, user_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> UserAdminInfo: ...

    async def suspend_user(
        self,
        user_id: uuid.UUID,
        reason: str,
        suspended_until: datetime | None,
        *,
        now: datetime,
        commit: bool = True,
    ) -> UserAdminInfo: ...

    async def check_withdrawable(self, user_id: uuid.UUID, reason: str) -> None: ...

    async def withdraw_user(
        self, user_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> UserAdminInfo: ...

    async def grant_points(
        self,
        user_id: uuid.UUID,
        amount: int,
        reason: str,
        admin_id: uuid.UUID,
        *,
        now: datetime,
        commit: bool = True,
    ) -> PointLogInfo: ...

    async def list_points(self, user_id: uuid.UUID, page: int, size: int) -> PointHistoryInfo: ...

    async def list_users(
        self,
        *,
        role: str | None = None,
        status: str | None = None,
        email: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> UserPageInfo: ...


class StoreAdminPort(Protocol):
    async def lock_store(self, store_id: uuid.UUID) -> StoreAdminInfo: ...

    async def lock_store_of_owner(self, owner_id: uuid.UUID) -> StoreAdminInfo | None: ...

    async def suspend_store(
        self, store_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> StoreAdminInfo: ...

    async def suspend_stores_of_owner(
        self, owner_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> StoreAdminInfo | None: ...

    async def check_force_closable(self, store_id: uuid.UUID, reason: str) -> None: ...

    async def close_store_by_admin(
        self,
        store_id: uuid.UUID,
        reason: str,
        *,
        has_reserved_reservations: bool,
        now: datetime,
        commit: bool = True,
    ) -> StoreAdminInfo: ...


class OfferAdminPort(Protocol):
    async def suspend_offer(
        self, offer_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> OfferAdminInfo: ...

    async def end_all_sales_of_store(
        self, store_id: uuid.UUID, *, now: datetime, commit: bool = True
    ) -> int: ...


class ReservationAdminPort(Protocol):
    """reservations 어댑터(ReservationAdminAdapter)가 만족한다. 두 메서드 모두 절대 commit하지 않는다 (R13).

    불일치(500)는 admin.domain.exceptions.ReservationDataInconsistentError로 낸다.
    """

    # 결제 대기·RESERVED 예약을 취소(재고 복구, RESERVED는 위약금 없는 전액 환불)한다. 취소 수를 돌려준다.
    async def cancel_active_for_user(self, user_id: uuid.UUID, *, reason: str) -> int: ...

    # 매장에 RESERVED 예약이 있는지. excluding_user_id의 예약은 제외한다. offer 행을 잠근다.
    async def has_reserved_for_store(
        self, store_id: uuid.UUID, *, excluding_user_id: uuid.UUID | None = None
    ) -> bool: ...
