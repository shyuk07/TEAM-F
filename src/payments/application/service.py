from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.ports import ReservationPort
from payments.domain.cancellation_policy import CancellationPolicy
from payments.domain.exceptions import (
    PaymentAlreadyExistsError,
    PaymentAlreadyRefundedError,
    PaymentFailedError,
    PaymentNotFoundError,
    RefundNotFoundError,
    ReservationNotFoundError,
)
from payments.domain.payment import Payment
from payments.domain.refund import Refund
from payments.domain.rules import DEFAULT_CANCELLATION_POLICY
from payments.domain.repository.payment_repository import PaymentRepository
from payments.domain.repository.refund_repository import RefundRepository
from payments.domain.service import Clock, PaymentGateway


class PaymentApplicationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        reservations: ReservationPort,
        payments: PaymentRepository,
        refunds: RefundRepository,
        gateway: PaymentGateway,
        clock: Clock,
        policy: CancellationPolicy = DEFAULT_CANCELLATION_POLICY,
    ):
        self.session = session
        self.reservations = reservations
        self.payments = payments
        self.refunds = refunds
        self.gateway = gateway
        self.clock = clock
        self.policy = policy

    # 모의 결제 실행: 금액은 클라이언트가 아니라 서버(예약 정보)에서 계산한다.
    # 검사 순서: 404(예약 없음) -> 403(본인 아님) -> 409(이미 결제) -> 400(결제 불가 상태)
    # 이미 결제된 예약은 상태가 바뀌어 있으므로 중복(409) 검사가 상태(400) 검사보다 먼저여야 한다.
    # TODO(D-10): 포인트 사용·적립(use_point, auth 연동)은 미정이라 구현하지 않았다.
    async def pay(self, user_id: UUID, reservation_id: UUID) -> Payment:
        snapshot = await self.reservations.get(reservation_id, for_update=True)
        if snapshot is None:
            raise ReservationNotFoundError()
        snapshot.ensure_payable_by(user_id)
        if await self.payments.find_by_reservation_id(reservation_id) is not None:
            raise PaymentAlreadyExistsError()
        snapshot.ensure_payable_state()

        payment = Payment.request(reservation_id, user_id, snapshot.total_price, self.clock.now())
        result = await self.gateway.charge(payment)
        if not result.success:
            # 1차: 실패한 결제는 DB에 저장하지 않는다.
            # models.py의 payments.reservation_id가 UNIQUE라서 FAILED를 저장하면
            # 같은 예약을 다시 결제할 수 없게 된다. (실패 기록 저장은 2차 스키마 정렬 때 결정)
            payment.fail(result.failure_response, self.clock.now())
            await self.session.rollback()
            raise PaymentFailedError()
        payment.approve(result.provider_payment_id, self.clock.now())

        try:
            await self.payments.save(payment)  # 동시 결제면 UNIQUE 위반 -> PaymentAlreadyExistsError(409)
            await self.reservations.mark_paid(reservation_id, commit=False)
        except Exception:
            await self.session.rollback()
            raise
        await self.session.commit()  # 한 번만
        return payment

    # 결제 조회: 본인만
    async def get_payment(self, user_id: UUID, payment_id: UUID) -> Payment:
        payment = await self.payments.find_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError()
        snapshot = await self.reservations.get(payment.reservation_id)
        if snapshot is None:
            raise ReservationNotFoundError()
        snapshot.ensure_viewable_by(user_id)
        return payment

    # 환불 조회: 본인만
    async def get_refund(self, user_id: UUID, refund_id: UUID) -> Refund:
        refund = await self.refunds.find_by_id(refund_id)
        if refund is None:
            raise RefundNotFoundError()
        payment = await self.payments.find_by_id(refund.payment_id)
        if payment is None:
            raise PaymentNotFoundError()
        snapshot = await self.reservations.get(payment.reservation_id)
        if snapshot is None:
            raise ReservationNotFoundError()
        snapshot.ensure_refund_viewable_by(user_id)
        return refund

    # 환불 요청. 전액 기준이고 위약금은 정책이 계산한다(현재 0원).
    # 검사 순서: 404(결제 없음) -> 403(본인 아님) -> 409(이미 환불) -> 400(환불 불가)
    # 락 순서: 예약 -> 결제 -> 환불 INSERT (예약 취소와의 교착 방지)
    async def refund(self, user_id: UUID, payment_id: UUID, reason: str) -> Refund:
        payment = await self.payments.find_by_id(payment_id)
        if payment is None:
            raise PaymentNotFoundError()
        snapshot = await self.reservations.get(payment.reservation_id, for_update=True)
        if snapshot is None:
            raise ReservationNotFoundError()
        snapshot.ensure_refundable_by(user_id)

        payment = await self.payments.find_by_id(payment_id, for_update=True)
        if payment is None:
            raise PaymentNotFoundError()
        if await self.refunds.find_by_payment_id(payment_id) is not None:
            raise PaymentAlreadyRefundedError()
        payment.ensure_refundable()  # REFUNDED -> 409, READY/FAILED -> 400
        snapshot.ensure_refundable_state()  # 예약 상태 -> 400 (D-7)

        # 미정(D-2): 위약금 계산 담당. 현재는 payments의 정책이 계산한다(D-1: 0원).
        now = self.clock.now()
        penalty = self.policy.penalty(payment.amount, snapshot.pickup_start, now)
        refund = payment.refund(penalty, reason, now)

        try:
            await self.refunds.save(refund)  # 동시 환불이면 UNIQUE 위반 -> 409
            await self.payments.save(payment)
            # TODO(D-6): 예약 취소·재고 복구(cancel_for_refund)는 처리 순서가 미정이라 호출하지 않는다.
        except Exception:
            await self.session.rollback()
            raise
        await self.session.commit()  # 한 번만
        return refund
