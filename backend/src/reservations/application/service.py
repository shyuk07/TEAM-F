import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.ports import RefundPort, StockPort
from reservations.application.views import MyReservationEntry, Page, RefundTarget
from reservations.domain import rules
from reservations.domain.cancel_actor import CancelActor
from reservations.domain.exceptions import (
    DataInconsistentError,
    InconsistencyDetail,
    ReservationNotFoundError,
)
from reservations.domain.offer_ref import OfferRef
from reservations.domain.pickup_reservation import PickupReservation, ReservationStatus
from reservations.domain.repository import ReservationRepository
from reservations.domain.service import Clock, PickupCodeGenerator

logger = logging.getLogger(__name__)


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
        PickupReservation.validate_new_quantity(quantity)  # 잠금·재고 차감 전에 거절(R-REQ1, R-REQ29)
        # 할인 행을 잠그고 차감한다. 같은 할인의 예약 생성은 이 잠금에서 차례로 진행된다.
        terms = await self.stock.reserve(offer_id, quantity, user_id=user_id, now=now)
        offer = OfferRef.from_info(terms)
        offer.ensure_reservable_by(user_id)
        # 잠금 안에서 확인하므로 동시 요청이 함께 통과하지 못한다(R-REQ28, R-REQ29).
        # 거절되면 commit하지 않아 차감·재고 기록도 남지 않는다.
        pending = await self.reservations.find_by_user_and_statuses(
            user_id, [ReservationStatus.PENDING_PAYMENT]
        )
        PickupReservation.ensure_no_pending_for_offer(pending, offer_id)
        reservation = PickupReservation.create(
            user_id, offer, quantity, self.code_generator.generate(), now
        )
        await self.reservations.save(reservation)
        await self.session.commit()
        return reservation

    async def list_my_reservations(
        self, user_id: uuid.UUID, status: ReservationStatus | None, page: int, size: int
    ) -> Page[MyReservationEntry]:
        items, total = await self.reservations.find_by_user(
            user_id, status=status, page=page, size=size
        )
        terms = {}
        for offer_id in dict.fromkeys(r.offer_id for r in items):  # 같은 할인은 한 번만 읽는다(잠금 없음)
            terms[offer_id] = await self.stock.get_terms(offer_id)
        entries = [
            MyReservationEntry(
                reservation=r,
                pickup_start=terms[r.offer_id].pickup_start,
                pickup_end=terms[r.offer_id].pickup_end,
                cancellable_until=terms[r.offer_id].cancellable_until,
            )
            for r in items
        ]
        return Page(items=entries, total=total, page=page, size=size)

    async def get_my_reservation(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> MyReservationEntry:
        """본인 예약 한 건(결제 완료 화면 등). 없으면 404, 남의 예약이면 403. 읽기 전용."""
        view = await self.lifecycle.get_snapshot(reservation_id)
        if view is None:
            raise ReservationNotFoundError()
        view.reservation.ensure_owned_by(user_id, "본인 예약만 조회할 수 있습니다.")
        return MyReservationEntry(
            reservation=view.reservation,
            pickup_start=view.offer.pickup_start,
            pickup_end=view.offer.pickup_end,
            cancellable_until=view.offer.cancellable_until,
        )

    async def cancel_reservation(
        self, user_id: uuid.UUID, reservation_id: uuid.UUID
    ) -> PickupReservation:
        peek = await self.lifecycle.get_snapshot(reservation_id)  # 잠금 없이: 404·403을 잠금보다 먼저
        if peek is None:
            raise ReservationNotFoundError()
        peek.reservation.ensure_owned_by(user_id, "본인 예약만 취소할 수 있습니다.")
        # 잠금 순서(RD-5): 할인 -> 예약. 환불 여부는 잠근 뒤의 상태로 정한다(그 사이 결제될 수 있음).
        view = await self.lifecycle.get_snapshot(reservation_id, for_update=True)
        if view is None:
            raise ReservationNotFoundError()
        was_paid = view.reservation.is_paid
        check_paid_payment = view.reservation.is_pending_payment
        target = RefundTarget(
            reservation_id=reservation_id,
            user_id=view.reservation.user_id,
            total_price=view.reservation.total_price,
            pickup_start=view.offer.pickup_start,
            status=str(ReservationStatus.RESERVED),
            cancellable_until=view.offer.cancellable_until,
        )
        # 데이터 불일치(RD-38·RD-39)는 전부 롤백하고 ERROR 로그를 정확히 1건 남긴다. 기록 지점은 이 서비스 한 곳이다
        # (어댑터는 번역만, 라우터는 응답 변환만 한다).
        try:
            if check_paid_payment:
                await self.refunds.ensure_no_paid_payment(reservation_id)  # 읽기 전용, 쓰기 전에 확인(RD-39)
            if was_paid:
                # 환불(불일치 검사 포함)을 취소·재고 복구보다 먼저 한다(reservations.md 13.6.4).
                # 불일치(500)가 재고 쪽 오류에 가려지지 않고, 재고 복구 전에 중단된다.
                await self.refunds.refund_for_cancelled_reservation(
                    target, reason=rules.CUSTOMER_CANCEL_REASON, waive_penalty=False
                )
            reservation = await self.lifecycle.cancel(
                reservation_id,
                reason=rules.CUSTOMER_CANCEL_REASON,
                actor_user_id=user_id,
                cancelled_by=CancelActor.CUSTOMER,
                commit=False,
            )
        except DataInconsistentError as error:
            await self.session.rollback()
            self._log_inconsistency("cancel", error.details)
            raise
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
        """catalog ReservationCancelPort용. 정상이면 commit하지 않는다 (R13).

        불일치(RD-38·RD-39)가 1건이라도 있으면 끝까지 모은 뒤 전체 롤백하고 DataInconsistentError(불일치 목록)를 낸다.
        ERROR 로그는 요청당 1건(불일치 예약 ID 전부 포함)이다. PICKED_UP 검사는 기존대로 먼저 한다.
        """
        cancelled = await self.lifecycle.cancel_all_for_offer(offer_id, reason=reason)
        inconsistent: list[InconsistencyDetail] = []
        for item in cancelled:
            try:
                if item.refund_target is not None:
                    await self.refunds.refund_for_cancelled_reservation(
                        item.refund_target, reason=reason, waive_penalty=True
                    )
                elif item.check_paid_payment:
                    await self.refunds.ensure_no_paid_payment(item.reservation.id)  # type: ignore[arg-type]
            except DataInconsistentError as error:
                inconsistent.extend(
                    error.details or (InconsistencyDetail(item.reservation.id, "UNKNOWN"),)
                )
        if inconsistent:
            await self.session.rollback()
            self._log_inconsistency("cancel_all_for_offer", inconsistent)
            raise DataInconsistentError(inconsistent)
        return len(cancelled)

    async def cancel_all_for_user(self, user_id: uuid.UUID, *, reason: str) -> int:
        """admin·탈퇴 흐름용(D-31). 정상이면 commit하지 않는다 (R13).

        PENDING_PAYMENT·RESERVED를 취소하고 재고를 복구한다. RESERVED는 위약금 없이 전액 환불한다.
        불일치(재고 복구·RD-38·RD-39)가 있으면 전체 롤백하고 ERROR 로그 1건을 남긴 뒤 DataInconsistentError를 낸다(D-37).
        """
        try:
            cancelled = await self.lifecycle.cancel_all_for_user(user_id, reason=reason)
        except DataInconsistentError as error:
            await self.session.rollback()
            self._log_inconsistency("cancel_all_for_user", error.details)
            raise
        inconsistent: list[InconsistencyDetail] = []
        for item in cancelled:
            try:
                if item.refund_target is not None:
                    await self.refunds.refund_for_cancelled_reservation(
                        item.refund_target, reason=reason, waive_penalty=True
                    )
                elif item.check_paid_payment:
                    await self.refunds.ensure_no_paid_payment(item.reservation.id)  # type: ignore[arg-type]
            except DataInconsistentError as error:
                inconsistent.extend(
                    error.details or (InconsistencyDetail(item.reservation.id, "UNKNOWN"),)
                )
        if inconsistent:
            await self.session.rollback()
            self._log_inconsistency("cancel_all_for_user", inconsistent)
            raise DataInconsistentError(inconsistent)
        return len(cancelled)

    @staticmethod
    def _log_inconsistency(flow: str, details: tuple[InconsistencyDetail, ...] | list[InconsistencyDetail]) -> None:
        """요청당 ERROR 로그 1건. 예약·결제 ID와 불일치 종류만 남긴다(개인정보 금지)."""
        logger.error(
            "DATA_INCONSISTENT flow=%s count=%d details=[%s]",
            flow,
            len(details),
            "; ".join(
                f"reservation_id={d.reservation_id} payment_id={d.payment_id} kind={d.kind}" for d in details
            ),
        )
