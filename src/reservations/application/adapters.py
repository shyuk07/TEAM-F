"""결제 모듈과 예약 모듈을 잇는 어댑터. commit하지 않는다 (R13). 연결은 container에서만 한다 (R9).

R11/R2 판단:
- payments의 application 서비스·domain 타입(ReservationSnapshot, 예외)만 import한다.
  payments의 ORM 모델·레포지토리 구현체·infrastructure는 쓰지 않는다. layer-check도 application -> 다른 모듈 domain/application을 허용한다.
- 결제 서비스가 snapshot의 검증 메서드(ensure_payable_by 등)를 부르므로 구조적(duck typing)으로만은 맞출 수 없어
  payments의 ReservationSnapshot 값 객체를 그대로 만들어 돌려준다. payments는 reservations를 import하지 않으므로 순환이 없다 (R12).
"""

import uuid

from payments.application.service import PaymentApplicationService
from payments.domain.exceptions import (
    PaymentConflictError,
    PaymentStateInconsistentError,
)
from payments.domain.exceptions import StockNotConnectedError as PaymentsStockNotConnectedError
from payments.domain.reservation_snapshot import ReservationSnapshot
from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.views import RefundTarget
from reservations.domain.exceptions import (
    DataInconsistentError,
    RefundConflictError,
    StockNotConnectedError,
)


class PaymentReservationAdapter:
    """payments.application.ports.ReservationPort를 구조적으로 만족한다 (예약 -> 결제 방향)."""

    def __init__(self, lifecycle: ReservationLifecycleService):
        self.lifecycle = lifecycle

    async def get(
        self, reservation_id: uuid.UUID, *, for_update: bool = False
    ) -> ReservationSnapshot | None:
        view = await self.lifecycle.get_snapshot(reservation_id, for_update=for_update)
        if view is None:
            return None
        reservation = view.reservation
        return ReservationSnapshot(
            id=reservation_id,
            user_id=reservation.user_id,
            total_price=reservation.total_price,
            status=str(reservation.status),
            pickup_start=view.offer.pickup_start,  # 픽업 시작은 할인(offer) 정보에서
        )

    async def mark_paid(self, reservation_id: uuid.UUID, *, commit: bool = False) -> None:
        await self.lifecycle.mark_paid(reservation_id, commit=commit)

    async def cancel_for_refund(
        self, reservation_id: uuid.UUID, reason: str, *, commit: bool = False
    ) -> None:
        try:
            await self.lifecycle.cancel_for_refund(reservation_id, reason, commit=commit)
        except StockNotConnectedError as error:  # RD-34: 결제 쪽 라우터가 503으로 바꿀 수 있게 번역
            raise PaymentsStockNotConnectedError(str(error)) from error


class PaymentRefundAdapter:
    """reservations.application.ports.RefundPort를 구조적으로 만족한다 (결제 -> 예약 방향)."""

    def __init__(self, payments: PaymentApplicationService):
        self.payments = payments

    async def refund_for_cancelled_reservation(
        self, target: RefundTarget, *, reason: str, waive_penalty: bool = False
    ) -> None:
        try:
            await self.payments.refund_for_cancelled_reservation(
                target.reservation_id,
                reservation_status=target.status,
                pickup_start=target.pickup_start,
                reason=reason,
                waive_penalty=waive_penalty,
            )
        except PaymentStateInconsistentError as error:  # RD-34: 결제 예외 -> 예약 예외
            raise DataInconsistentError() from error
        except PaymentConflictError as error:
            raise RefundConflictError() from error
