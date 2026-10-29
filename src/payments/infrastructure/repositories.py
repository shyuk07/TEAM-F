from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.service import ConflictError
from payments.domain.payment import Payment, PaymentStatus
from payments.domain.refund import Refund, RefundStatus
from payments.infrastructure.models import PaymentModel, RefundModel


# DB 모델 <-> 도메인 객체 변환
def _to_payment(row: PaymentModel) -> Payment:
    return Payment(
        id=row.id,
        reservation_id=row.reservation_id,
        user_id=row.user_id,
        amount=row.amount,
        status=PaymentStatus(row.status),
        paid_at=row.paid_at,
    )


def _to_refund(row: RefundModel) -> Refund:
    return Refund(
        id=row.id,
        payment_id=row.payment_id,
        refund_amount=row.refund_amount,
        penalty_amount=row.penalty_amount,
        reason=row.reason,
        status=RefundStatus(row.status),
        completed_at=row.completed_at,
    )


class SqlAlchemyPaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_payment(self, payment_id: UUID) -> Payment | None:
        row = await self.session.get(PaymentModel, payment_id)
        return _to_payment(row) if row else None

    async def get_payment_by_reservation(self, reservation_id: UUID) -> Payment | None:
        result = await self.session.execute(
            select(PaymentModel).where(PaymentModel.reservation_id == reservation_id)
        )
        row = result.scalar_one_or_none()
        return _to_payment(row) if row else None

    async def add_payment(self, payment: Payment) -> None:
        self.session.add(
            PaymentModel(
                id=payment.id,
                reservation_id=payment.reservation_id,
                user_id=payment.user_id,
                amount=payment.amount,
                status=payment.status.value,
                paid_at=payment.paid_at,
            )
        )
        await self._commit("이미 결제된 예약입니다.")

    async def get_refund(self, refund_id: UUID) -> Refund | None:
        row = await self.session.get(RefundModel, refund_id)
        return _to_refund(row) if row else None

    async def add_refund(self, refund: Refund, payment: Payment) -> None:
        payment_row = await self.session.get(PaymentModel, payment.id)
        payment_row.status = payment.status.value

        self.session.add(
            RefundModel(
                id=refund.id,
                payment_id=refund.payment_id,
                refund_amount=refund.refund_amount,
                penalty_amount=refund.penalty_amount,
                reason=refund.reason,
                status=refund.status.value,
                completed_at=refund.completed_at,
            )
        )
        await self._commit("이미 환불된 결제입니다.")

    # 동시에 같은 요청이 들어와 unique 제약에 걸리면 409로 처리
    async def _commit(self, conflict_message: str) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise ConflictError(conflict_message) from error
