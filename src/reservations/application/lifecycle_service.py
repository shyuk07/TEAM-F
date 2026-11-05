import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from reservations.application.ports import StockPort
from reservations.application.views import CancelledReservation, RefundTarget, ReservationView
from reservations.domain.exceptions import (
    PickedUpReservationExistsError,
    ReservationNotFoundError,
    StockRestoreNotConnectedError,
)
from reservations.domain.offer_ref import OfferRef
from reservations.domain.pickup_reservation import PickupReservation, ReservationStatus
from reservations.domain.repository import ReservationRepository
from reservations.domain.service import Clock


class ReservationLifecycleService:
    """예약 상태 전이와 재고 복구. 결제를 모른다 (D-5). 잠금 순서 offer -> reservation (D-6)."""

    def __init__(
        self,
        session: AsyncSession,
        reservations: ReservationRepository,
        stock: StockPort,
        clock: Clock,
    ):
        self.session = session
        self.reservations = reservations
        self.stock = stock
        self.clock = clock

    async def _load_locked(self, reservation_id: uuid.UUID) -> ReservationView | None:
        peek = await self.reservations.find_by_id(reservation_id)
        if peek is None:
            return None
        terms = await self.stock.get_terms(peek.offer_id, for_update=True)
        reservation = await self.reservations.find_by_id(reservation_id, for_update=True)
        if reservation is None:
            return None
        return ReservationView(reservation, OfferRef.from_info(terms))

    async def _release_stock(self, reservation: PickupReservation, *, was_paid: bool, user_id: uuid.UUID, reason: str) -> None:
        """재고를 되돌린다. 결제된(RESERVED) 예약인데 되돌리지 못하면 503으로 중단한다(호출자가 commit 전이라 전부 롤백).

        미결제(PENDING_PAYMENT) 예약은 임시 포트가 False를 줘도 통과한다.
        TODO: catalog 재고 서비스가 연결돼 release가 True를 주면 이 가드는 자연히 통과한다.
        """
        restored = await self.stock.release(
            reservation.offer_id, reservation.quantity, user_id=user_id, reason=reason
        )
        if was_paid and not restored:
            raise StockRestoreNotConnectedError()

    async def get_snapshot(
        self, reservation_id: uuid.UUID, *, for_update: bool = False
    ) -> ReservationView | None:
        if for_update:
            return await self._load_locked(reservation_id)
        reservation = await self.reservations.find_by_id(reservation_id)
        if reservation is None:
            return None
        terms = await self.stock.get_terms(reservation.offer_id)
        return ReservationView(reservation, OfferRef.from_info(terms))

    async def mark_paid(self, reservation_id: uuid.UUID, *, commit: bool = False) -> PickupReservation:
        view = await self._load_locked(reservation_id)
        if view is None:
            raise ReservationNotFoundError()
        view.reservation.mark_paid()
        await self.reservations.save(view.reservation)
        if commit:
            await self.session.commit()
        return view.reservation

    async def cancel(
        self,
        reservation_id: uuid.UUID,
        *,
        reason: str,
        actor_user_id: uuid.UUID,
        commit: bool = False,
    ) -> PickupReservation:
        view = await self._load_locked(reservation_id)
        if view is None:
            raise ReservationNotFoundError()
        reservation = view.reservation
        was_paid = reservation.is_paid
        reservation.cancel(self.clock.now())  # 상태 검사가 재고 복구보다 먼저 (이중 복구 방지)
        await self._release_stock(reservation, was_paid=was_paid, user_id=actor_user_id, reason=reason)
        await self.reservations.save(reservation)
        if commit:
            await self.session.commit()
        return reservation

    async def cancel_for_refund(
        self, reservation_id: uuid.UUID, reason: str, *, commit: bool = False
    ) -> None:
        view = await self._load_locked(reservation_id)
        if view is None:
            raise ReservationNotFoundError()
        reservation = view.reservation
        if reservation.is_cancelled:
            return  # 멱등: 재고·환불을 다시 건드리지 않는다
        was_paid = reservation.is_paid
        reservation.cancel(self.clock.now())
        await self._release_stock(reservation, was_paid=was_paid, user_id=reservation.user_id, reason=reason)
        await self.reservations.save(reservation)
        if commit:
            await self.session.commit()

    async def cancel_all_for_offer(self, offer_id: uuid.UUID, *, reason: str) -> list[CancelledReservation]:
        """재고는 복구하지 않는다 (D40). commit하지 않는다."""
        terms = await self.stock.get_terms(offer_id, for_update=True)  # offer 먼저
        reservations = await self.reservations.find_by_offer(offer_id, for_update=True)
        if any(r.is_picked_up for r in reservations):
            raise PickedUpReservationExistsError()  # 아무것도 바꾸기 전에 중단
        cancelled: list[CancelledReservation] = []
        now = self.clock.now()
        for reservation in reservations:
            if not reservation.holds_stock:
                continue
            target = None
            check_paid_payment = reservation.is_pending_payment  # 취소하기 전 상태로 판단
            if reservation.is_paid:
                target = RefundTarget(
                    reservation_id=reservation.id,  # type: ignore[arg-type]
                    user_id=reservation.user_id,
                    total_price=reservation.total_price,
                    pickup_start=terms.pickup_start,
                    status=str(ReservationStatus.RESERVED),
                )
            reservation.cancel(now)
            await self.reservations.save(reservation)
            cancelled.append(CancelledReservation(reservation, target, check_paid_payment))
        return cancelled
