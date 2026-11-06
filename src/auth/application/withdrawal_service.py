import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from auth.application.ports import (
    WithdrawalOfferPort,
    WithdrawalReservationPort,
    WithdrawalStorePort,
)
from auth.application.service import AuthApplicationService
from auth.domain.service import Clock
from auth.domain.user import SELF_WITHDRAWAL_REASON


@dataclass(frozen=True)
class WithdrawalResult:
    id: uuid.UUID
    status: str
    deleted_at: datetime | None
    cancelled_reservation_count: int


class AccountWithdrawalService:
    """자진 탈퇴 조정. AuthApplicationService 밖에 두어 auth가 다른 모듈을 알지 않게 한다 (R12).

    순서: 예약 취소(환불 -> 포인트 복구)가 회원 탈퇴 처리(포인트 소멸)보다 먼저다.
    잠금 순서: offers -> reservations -> payments -> refunds -> users.
    """

    def __init__(
        self,
        session: AsyncSession,
        accounts: AuthApplicationService,
        stores: WithdrawalStorePort,
        offers: WithdrawalOfferPort,
        reservations: WithdrawalReservationPort,
        clock: Clock,
    ):
        self.session = session
        self.accounts = accounts
        self.stores = stores
        self.offers = offers
        self.reservations = reservations
        self.clock = clock

    async def withdraw_self(self, user_id: uuid.UUID, password: str) -> WithdrawalResult:
        now = self.clock.now()
        user = await self.accounts.check_self_withdrawable(user_id, password)  # ① 읽기
        store = await self.stores.lock_store_of_owner(user_id) if user.is_owner else None  # ②
        open_store = store is not None and not store.is_closed
        reserved = False
        if open_store:
            await self.offers.end_all_sales_of_store(store.id, now=now, commit=False)  # ③
            # 타 고객 RESERVED 확인은 본인 예약 취소보다 먼저(잠금 순서). 본인 예약은 제외한다.
            reserved = await self.reservations.has_reserved_for_store(  # ④
                store.id, excluding_user_id=user_id
            )
        cancelled = await self.reservations.cancel_active_for_user(  # ⑤ 환불·포인트 복구
            user_id, reason=SELF_WITHDRAWAL_REASON
        )
        if open_store:
            await self.stores.close_store_by_admin(  # ⑥
                store.id,
                SELF_WITHDRAWAL_REASON,
                has_reserved_reservations=reserved,
                now=now,
                commit=False,
            )
        done = await self.accounts.withdraw_user(  # ⑦ 포인트 소멸
            user_id, SELF_WITHDRAWAL_REASON, now=now, commit=False
        )
        await self.session.commit()  # ⑧ 한 번 (R5, R13)
        return WithdrawalResult(
            id=done.id,
            status=done.status.value,
            deleted_at=done.deleted_at,
            cancelled_reservation_count=cancelled,
        )
