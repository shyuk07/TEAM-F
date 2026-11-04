import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.ports import RefundPort, StockPort
from reservations.application.views import Page, RefundTarget
from reservations.domain import rules
from reservations.domain.exceptions import ReservationNotFoundError
from reservations.domain.offer_ref import OfferRef
from reservations.domain.pickup_reservation import PickupReservation, ReservationStatus
from reservations.domain.repository import ReservationRepository
from reservations.domain.service import Clock, PickupCodeGenerator


class ReservationApplicationService:
    """엔드포인트 유스케이스와 commit 담당 (D-5)."""

    def __init__(
        self,
        session: AsyncSession,
        lifecycle: ReservationLifecycleService,
        reservations: ReservationRepository,
        stock: StockPort,
        refunds: RefundPort,
        clock: Clock,
        code_generator: PickupCodeGenerator,
    ):
        self.session = session
        self.lifecycle = lifecycle
        self.reservations = reservations
        self.stock = stock
        self.refunds = refunds
        self.clock = clock
        self.code_generator = code_generator

    async def create_reservation(
        self, user_id: uuid.UUID, offer_id: uuid.UUID, quantity: int
    ) -> PickupReservation:
        now = self.clock.now()
        terms = await self.stock.reserve(offer_id, quantity, user_id=user_id, now=now)
        offer = OfferRef.from_info(terms)
        offer.ensure_reservable_by(user_id)
        reservation = PickupReservation.create(
            user_id, offer, quantity, self.code_generator.generate(), now
        )
        await self.reservations.save(reservation)
        await self.session.commit()
        return reservation

    async def list_my_reservations(
        self, user_id: uuid.UUID, status: ReservationStatus | None, page: int, size: int
    ) -> Page[PickupReservation]:
        items, total = await self.reservations.find_by_user(
            user_id, status=status, page=page, size=size
        )
        return Page(items=items, total=total, page=page, size=size)

    async def cancel_reservation(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> PickupReservation:
        view = await self.lifecycle.get_snapshot(reservation_id)
        if view is None:
            raise ReservationNotFoundError()
        view.reservation.ensure_owned_by(user_id, "본인 예약만 취소할 수 있습니다.")  # 잠금보다 먼저
        was_paid = view.reservation.is_paid
        target = RefundTarget(
            reservation_id=reservation_id,
            user_id=view.reservation.user_id,
            total_price=view.reservation.total_price,
            pickup_start=view.offer.pickup_start,
            status=str(ReservationStatus.RESERVED),
        )
        reservation = await self.lifecycle.cancel(
            reservation_id,
            reason=rules.CUSTOMER_CANCEL_REASON,
            actor_user_id=user_id,
            commit=False,
        )
        if was_paid:
            await self.refunds.refund_for_cancelled_reservation(
                target, reason=rules.CUSTOMER_CANCEL_REASON, waive_penalty=False
            )
        await self.session.commit()
        return reservation

    async def complete_pickup(
        self, owner_id: uuid.UUID, reservation_id: uuid.UUID, pickup_code: str
    ) -> PickupReservation:
        view = await self.lifecycle.get_snapshot(reservation_id)
        if view is None:
            raise ReservationNotFoundError()
        view.offer.ensure_owned_by(owner_id)
        reservation = await self.reservations.find_by_id(reservation_id, for_update=True)
        if reservation is None:
            raise ReservationNotFoundError()
        now = self.clock.now()
        view.offer.ensure_pickup_time(now)
        reservation.pick_up(pickup_code, now)
        await self.reservations.save(reservation)
        await self.session.commit()
        return reservation

    async def cancel_all_for_offer(self, offer_id: uuid.UUID, *, reason: str) -> int:
        """catalog ReservationCancelPort용. commit하지 않는다 (R13)."""
        cancelled = await self.lifecycle.cancel_all_for_offer(offer_id, reason=reason)
        for item in cancelled:
            if item.refund_target is not None:
                await self.refunds.refund_for_cancelled_reservation(
                    item.refund_target, reason=reason, waive_penalty=True
                )
        return len(cancelled)
