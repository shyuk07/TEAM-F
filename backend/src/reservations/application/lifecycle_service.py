import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from reservations.application.ports import StockPort
from reservations.application.views import CancelledReservation, RefundTarget, ReservationView
from reservations.domain import rules
from reservations.domain.cancel_actor import CancelActor
from reservations.domain.exceptions import (
    DataInconsistentError,
    InconsistencyDetail,
    PickedUpReservationExistsError,
    ReservationNotFoundError,
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

    async def _release_stock(
        self, reservation: PickupReservation, *, user_id: uuid.UUID, reason: str
    ) -> None:
        """재고를 되돌린다. 닫힌 할인이면 포트가 False를 주며 정상 경로다(D40). 상한 초과는 DataInconsistentError(500)."""
        try:
            await self.stock.release(
                reservation.offer_id,
                reservation.quantity,
                user_id=user_id,
                reason=reason,
                now=self.clock.now(),
            )
        except DataInconsistentError as error:
            # 포트는 예약 ID를 모른다. 로그에 남도록 이 예약의 ID를 채워 다시 낸다.
            raise DataInconsistentError(
                [
                    InconsistencyDetail(d.reservation_id or reservation.id, d.kind, d.payment_id)
                    for d in error.details
                ]
            ) from error

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
        cancelled_by: CancelActor,
        commit: bool = False,
    ) -> PickupReservation:
        view = await self._load_locked(reservation_id)
        if view is None:
            raise ReservationNotFoundError()
        reservation = view.reservation
        reservation.cancel(self.clock.now(), cancelled_by)  # 상태 검사가 재고 복구보다 먼저 (이중 복구 방지)
        await self._release_stock(reservation, user_id=actor_user_id, reason=reason)
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
        reservation.cancel(self.clock.now(), rules.REFUND_REQUEST_CANCEL_ACTOR)
        await self._release_stock(reservation, user_id=reservation.user_id, reason=reason)
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
            if reservation.is_no_show(terms.pickup_end, now):
                continue  # 미수령: 취소·환불하지 않고 RESERVED로 남긴다(A안). 바뀌는 것이 없어 불일치 검사 대상도 아니다
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
            reservation.cancel(now, rules.OFFER_CLOSE_CANCEL_ACTOR)
            await self.reservations.save(reservation)
            cancelled.append(CancelledReservation(reservation, target, check_paid_payment))
        return cancelled

    async def cancel_all_for_user(self, user_id: uuid.UUID, *, reason: str) -> list[CancelledReservation]:
        """회원의 PENDING_PAYMENT·RESERVED를 취소하고 재고를 복구한다. PICKED_UP·CANCELLED는 건드리지 않는다. commit하지 않는다.

        잠금 순서: offer(id 오름차순) -> reservation(offer_id, id 오름차순) (D-6).
        """
        active = [ReservationStatus.PENDING_PAYMENT, ReservationStatus.RESERVED]
        peek = await self.reservations.find_by_user_and_statuses(user_id, active)
        if not peek:
            return []
        terms_by_offer = {}
        for offer_id in sorted({r.offer_id for r in peek}):
            terms_by_offer[offer_id] = await self.stock.get_terms(offer_id, for_update=True)
        # offer를 모두 잠근 뒤 정본 목록을 다시 읽는다(그 사이 취소·결제된 예약 반영, 멱등)
        reservations = await self.reservations.find_by_user_and_statuses(user_id, active, for_update=True)
        cancelled: list[CancelledReservation] = []
        now = self.clock.now()
        for reservation in reservations:
            if not reservation.holds_stock:
                continue
            terms = terms_by_offer.get(reservation.offer_id)
            if terms is None:  # 재조회에서 새로 나타난 offer(드문 경우): 잠그고 추가
                terms = await self.stock.get_terms(reservation.offer_id, for_update=True)
                terms_by_offer[reservation.offer_id] = terms
            if reservation.is_no_show(terms.pickup_end, now):
                continue  # 미수령: 환불·재고 복구 없이 RESERVED로 남긴다(A안)
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
            reservation.cancel(now, rules.WITHDRAWAL_CANCEL_ACTOR)
            await self._release_stock(reservation, user_id=reservation.user_id, reason=reason)
            await self.reservations.save(reservation)
            cancelled.append(CancelledReservation(reservation, target, check_paid_payment))
        return cancelled
