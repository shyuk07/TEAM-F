import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.ports import ReservationPort
from payments.domain.cancellation_policy import CancellationPolicy
from payments.domain.exceptions import (
    InconsistencyKind,
    PaymentAlreadyExistsError,
    PaymentAlreadyRefundedError,
    PaymentFailedError,
    PaymentNotFoundError,
    PaymentStateInconsistentError,
    RefundNotFoundError,
    ReservationNotFoundError,
)
from payments.domain.payment import Payment
from payments.domain.refund import Refund
from payments.domain.rules import (
    DEFAULT_CANCELLATION_POLICY,
    RESERVATION_PAYABLE_STATUS,
)
from payments.domain.repository.payment_repository import PaymentRepository
from payments.domain.repository.refund_repository import RefundRepository
from payments.domain.service import Clock, PaymentGateway

logger = logging.getLogger(__name__)


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
    # 검사 순서: 404(예약 없음) -> 403(본인 아님) -> 500(데이터 불일치) -> 409(이미 결제) -> 400(결제 불가 상태)
    # 500: 예약이 CANCELLED/PENDING_PAYMENT인데 PAID 결제가 이미 있음(RD-38). 정상 중복 결제(예약 RESERVED)는 409.
    # 이미 결제된 예약은 상태가 바뀌어 있으므로 중복(409) 검사가 상태(400) 검사보다 먼저여야 한다.
    # TODO(D-10): 포인트 사용·적립(use_point, auth 연동)은 미정이라 구현하지 않았다.
    async def pay(self, user_id: UUID, reservation_id: UUID) -> Payment:
        snapshot = await self.reservations.get(reservation_id, for_update=True)
        if snapshot is None:
            raise ReservationNotFoundError()
        snapshot.ensure_payable_by(user_id)
        existing = await self.payments.find_by_reservation_id(reservation_id)
        if existing is not None:
            await self._ensure_consistent(existing, snapshot.status, flow="pay")
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
    # 검사 순서: 404(결제 없음) -> 403(본인 아님) -> 500(데이터 불일치) -> 409(이미 환불) -> 400(환불 불가)
    # 500: 예약이 CANCELLED/PENDING_PAYMENT인데 결제가 PAID(RD-38). 정상 중복 환불(결제 REFUNDED)은 409.
    # 락 순서(RD-5): (상품 ->) 할인 -> 예약 -> 결제 -> 환불 INSERT. 결제를 먼저 잠그지 않는다.
    #   결제는 잠금 없이 읽어 예약 ID만 얻고, 예약(할인->예약) 잠금 뒤에 결제를 잠근다.
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
        await self._ensure_consistent(payment, snapshot.status, flow="refund")
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
            # RD-2: 환불 API도 예약 취소 + 재고 복구까지. 재고 복구가 안 되면 503으로 중단되고 위 저장은 롤백된다.
            await self.reservations.cancel_for_refund(payment.reservation_id, reason, commit=False)
        except Exception:
            await self.session.rollback()
            raise
        await self.session.commit()  # 한 번만
        return refund

    # 예약 취소가 부르는 환불. commit하지 않는다(R13): 호출한 예약 서비스가 마지막에 한 번 commit한다.
    # 예약은 이미 결제 완료(RESERVED)였으므로 결제 PAID가 정확히 1건 있고 환불이 없어야 한다.
    # 아니면 환불을 만들지 않고 PaymentStateInconsistentError(500)로 중단한다(RD-38 ①②③).
    # 로그·롤백은 여기서 하지 않는다. 요청을 끝내는 예약 서비스가 한 번만 기록하고 롤백한다(중복 로그 방지).
    # 위약금은 정책이 계산한다(RD-3: 현재 0원). waive_penalty=True(판매자 중단 등)면 항상 0원.
    # 락 순서: 호출자가 이미 할인 -> 예약을 잠갔고, 여기서 결제 -> 환불 순으로 잠근다.
    async def refund_for_cancelled_reservation(
        self,
        reservation_id: UUID,
        *,
        reservation_status: str,
        pickup_start: datetime | None,
        reason: str,
        waive_penalty: bool = False,
    ) -> Refund:
        payment = await self.payments.find_by_reservation_id(reservation_id, for_update=True)
        if payment is None or payment.id is None:
            raise PaymentStateInconsistentError(InconsistencyKind.PAYMENT_MISSING, reservation_id)
        has_refund = await self.refunds.find_by_payment_id(payment.id) is not None
        payment.ensure_cancel_refundable(reservation_status, has_refund)  # 불일치면 500 예외

        now = self.clock.now()
        penalty = 0 if waive_penalty else self.policy.penalty(payment.amount, pickup_start, now)
        refund = payment.refund(penalty, reason, now)
        await self.refunds.save(refund)
        await self.payments.save(payment)
        return refund

    # 예약 취소(직전 PENDING_PAYMENT)가 부르는 읽기 전용 확인(RD-39). 쓰기·commit·잠금 없음.
    # 결제가 없거나 PAID가 아니면 통과(RD-40 미정이라 REFUNDED도 막지 않음). PAID면 불일치 예외(500).
    async def ensure_no_paid_payment_for_reservation(self, reservation_id: UUID) -> None:
        payment = await self.payments.find_by_reservation_id(reservation_id)
        if payment is None:
            return
        payment.ensure_consistent_with_reservation(RESERVATION_PAYABLE_STATUS)

    # pay()/refund()가 요청을 끝내기 전에 부르는 반대 방향 불일치 검사. 이 지점이 이 요청의 유일한 ERROR 로그 지점이다.
    async def _ensure_consistent(self, payment: Payment, reservation_status: str, *, flow: str) -> None:
        try:
            payment.ensure_consistent_with_reservation(reservation_status)
        except PaymentStateInconsistentError as error:
            await self.session.rollback()
            logger.error(
                "DATA_INCONSISTENT flow=%s kind=%s reservation_id=%s payment_id=%s",
                flow,
                error.kind,
                error.reservation_id,
                error.payment_id,
            )
            raise
