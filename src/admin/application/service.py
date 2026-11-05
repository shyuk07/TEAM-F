import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from admin.application.ports import (
    AccountAdminPort,
    OfferAdminInfo,
    OfferAdminPort,
    PointHistoryInfo,
    PointLogInfo,
    ReservationAdminPort,
    StoreAdminInfo,
    StoreAdminPort,
    UserAdminInfo,
)
from admin.domain.service import Clock


@dataclass(frozen=True)
class UserWithdrawalResult:
    """EP 4 결과. cancelled_reservation_count는 NoReservationAdmin인 동안 항상 0 (미연계, R16)."""

    id: uuid.UUID
    status: str
    deleted_at: datetime | None
    cancelled_reservation_count: int


class AdminApplicationService:
    """관리자 유스케이스 조합. 규칙은 소유 컨텍스트에 있다. 쓰기는 마지막에 commit 한 번 (R5, R13)."""

    def __init__(
        self,
        session: AsyncSession,
        accounts: AccountAdminPort,
        stores: StoreAdminPort,
        offers: OfferAdminPort,
        reservations: ReservationAdminPort,
        clock: Clock,
    ):
        self.session = session
        self.accounts = accounts
        self.stores = stores
        self.offers = offers
        self.reservations = reservations
        self.clock = clock

    # EP 1
    async def approve_owner(self, owner_id: uuid.UUID) -> UserAdminInfo:
        now = self.clock.now()
        user = await self.accounts.approve_owner(owner_id, now=now, commit=False)
        await self.session.commit()
        return user

    # EP 2
    async def reject_owner(self, owner_id: uuid.UUID, reason: str) -> UserAdminInfo:
        now = self.clock.now()
        user = await self.accounts.reject_owner(owner_id, reason, now=now, commit=False)
        await self.session.commit()
        return user

    # EP 3
    async def suspend_user(
        self, user_id: uuid.UUID, reason: str, suspended_until: datetime | None
    ) -> UserAdminInfo:
        now = self.clock.now()
        account = await self.accounts.get_account(user_id)
        is_owner = account.is_owner
        if is_owner:
            await self.stores.lock_store_of_owner(user_id)  # 상점 먼저 (D34)
        user = await self.accounts.suspend_user(
            user_id, reason, suspended_until, now=now, commit=False
        )
        if is_owner:
            await self.stores.suspend_stores_of_owner(user_id, reason, now=now, commit=False)
        await self.session.commit()
        return user

    # EP 4
    async def withdraw_user(self, user_id: uuid.UUID, reason: str) -> UserWithdrawalResult:
        now = self.clock.now()
        account = await self.accounts.get_account(user_id)
        await self.accounts.check_withdrawable(user_id, reason)
        store = None
        if account.is_owner:
            store = await self.stores.lock_store_of_owner(user_id)
        open_store = store is not None and not store.is_closed
        if open_store:
            await self.offers.end_all_sales_of_store(store.id, now=now, commit=False)
        cancelled = await self.reservations.cancel_reserved_for_user(user_id, reason=reason)
        if open_store:
            reserved = await self.reservations.has_reserved_for_store(store.id)
            await self.stores.close_store_by_admin(
                store.id, reason, has_reserved_reservations=reserved, now=now, commit=False
            )
        user = await self.accounts.withdraw_user(user_id, reason, now=now, commit=False)
        await self.session.commit()
        return UserWithdrawalResult(
            id=user.id,
            status=user.status,
            deleted_at=user.deleted_at,
            cancelled_reservation_count=cancelled,
        )

    # EP 5
    async def suspend_store(self, store_id: uuid.UUID, reason: str) -> StoreAdminInfo:
        now = self.clock.now()
        store = await self.stores.suspend_store(store_id, reason, now=now, commit=False)
        await self.session.commit()
        return store

    # EP 6
    async def close_store(self, store_id: uuid.UUID, reason: str) -> StoreAdminInfo:
        now = self.clock.now()
        await self.stores.check_force_closable(store_id, reason)
        await self.offers.end_all_sales_of_store(store_id, now=now, commit=False)
        reserved = await self.reservations.has_reserved_for_store(store_id)
        store = await self.stores.close_store_by_admin(
            store_id, reason, has_reserved_reservations=reserved, now=now, commit=False
        )
        await self.session.commit()
        return store

    # EP 7
    async def suspend_offer(self, offer_id: uuid.UUID, reason: str) -> OfferAdminInfo:
        now = self.clock.now()
        offer = await self.offers.suspend_offer(offer_id, reason, now=now, commit=False)
        await self.session.commit()
        return offer

    # EP 8 (읽기 전용, commit 없음)
    async def get_user_points(self, user_id: uuid.UUID, page: int, size: int) -> PointHistoryInfo:
        return await self.accounts.list_points(user_id, page, size)

    # EP 9
    async def grant_points(
        self, admin_id: uuid.UUID, user_id: uuid.UUID, amount: int, reason: str
    ) -> PointLogInfo:
        now = self.clock.now()
        log = await self.accounts.grant_points(
            user_id, amount, reason, admin_id, now=now, commit=False
        )
        await self.session.commit()
        return log
