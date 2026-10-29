from uuid import UUID

from payments.application.ports import (
    CurrentUser,
    PaymentRepository,
    ReservationGateway,
    UserRole,
)
from payments.domain.payment import Payment
from payments.domain.refund import Refund


# 결제 가능한 예약 상태 (예약 생성 직후 상태)
RESERVATION_PENDING_PAYMENT = "PENDING_PAYMENT"


# 서비스 계층 예외 (router에서 HTTP 상태 코드로 변환)
class PaymentError(Exception):
    pass


class NotFoundError(PaymentError):
    pass


class ForbiddenError(PaymentError):
    pass


class ConflictError(PaymentError):
    pass


class PaymentService:
    def __init__(self, repository: PaymentRepository, reservations: ReservationGateway):
        self.repository = repository
        self.reservations = reservations

    # 모의 결제 실행: 금액은 클라이언트가 아니라 서버(예약 정보)에서 계산
    async def pay(self, user: CurrentUser, reservation_id: UUID) -> Payment:
        if user.role != UserRole.CUSTOMER:
            raise ForbiddenError("고객만 결제할 수 있습니다.")

        reservation = await self.reservations.get(reservation_id)
        if reservation is None:
            raise NotFoundError("예약을 찾을 수 없습니다.")
        if reservation.user_id != user.id:
            raise ForbiddenError("본인 예약만 결제할 수 있습니다.")
        if reservation.status != RESERVATION_PENDING_PAYMENT:
            raise ConflictError("결제 대기 상태의 예약만 결제할 수 있습니다.")
        if await self.repository.get_payment_by_reservation(reservation_id) is not None:
            raise ConflictError("이미 결제된 예약입니다.")

        payment = Payment.pay_mock(
            reservation_id=reservation.id,
            user_id=user.id,
            amount=reservation.total_price,
        )
        await self.repository.add_payment(payment)
        await self.reservations.mark_paid(reservation.id)
        return payment

    # 결제 상태 조회: 본인 또는 관리자
    async def get_payment(self, user: CurrentUser, payment_id: UUID) -> Payment:
        payment = await self.repository.get_payment(payment_id)
        if payment is None:
            raise NotFoundError("결제 내역을 찾을 수 없습니다.")
        if user.role != UserRole.ADMIN and payment.user_id != user.id:
            raise ForbiddenError("결제 내역을 조회할 권한이 없습니다.")
        return payment

    # 환불·위약금 내역 조회: 본인, 해당 매장주, 관리자
    async def get_refund(self, user: CurrentUser, refund_id: UUID) -> Refund:
        refund = await self.repository.get_refund(refund_id)
        if refund is None:
            raise NotFoundError("환불 내역을 찾을 수 없습니다.")

        payment = await self.repository.get_payment(refund.payment_id)
        if user.role == UserRole.ADMIN or (payment and payment.user_id == user.id):
            return refund

        if user.role == UserRole.OWNER and payment is not None:
            reservation = await self.reservations.get(payment.reservation_id)
            if reservation and reservation.store_owner_id == user.id:
                return refund

        raise ForbiddenError("환불 내역을 조회할 권한이 없습니다.")

    # 환불 처리: 예약 취소 API(reservations 모듈)에서 호출하는 용도
    # 위약금(penalty_amount)은 취소 시점에 따라 예약 쪽에서 계산해서 넘겨줌
    async def refund(self, payment_id: UUID, penalty_amount: int, reason: str) -> Refund:
        payment = await self.repository.get_payment(payment_id)
        if payment is None:
            raise NotFoundError("결제 내역을 찾을 수 없습니다.")

        try:
            refund = Refund.refund_mock(payment, penalty_amount, reason)
        except ValueError as error:
            raise ConflictError(str(error)) from error

        await self.repository.add_refund(refund, payment)
        return refund
