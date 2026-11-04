import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from payments.domain.exceptions import (
    PaymentAlreadyExistsError,
    PaymentAlreadyRefundedError,
    PaymentNotFoundError,
)
from payments.domain.payment import Payment, PaymentStatus
from payments.domain.refund import Refund, RefundStatus
from payments.domain.repository.payment_repository import PaymentRepository
from payments.domain.repository.refund_repository import RefundRepository
from payments.infrastructure.models import PaymentModel, RefundModel

# 레포지토리는 flush까지만 하고 commit/rollback은 서비스가 한다.
# 현재 models.py에 없는 도메인 필드는 저장하지 못한다(조회하면 None):
#   Payment: provider_payment_id, created_at, failed_at, failed_response
#   Refund:  created_at
# (models.py/schema 정렬은 2차)


class SqlAlchemyPaymentRepository(PaymentRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(
        self, payment_id: uuid.UUID, for_update: bool = False
    ) -> Payment | None:
        stmt = select(PaymentModel).where(PaymentModel.id == payment_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_by_reservation_id(
        self, reservation_id: uuid.UUID, for_update: bool = False
    ) -> Payment | None:
        # 현재 models.py의 reservation_id가 UNIQUE라서 상태와 상관없이 예약당 결제는 1건이다.
        stmt = select(PaymentModel).where(PaymentModel.reservation_id == reservation_id)
        if for_update:
            stmt = stmt.with_for_update()
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def save(self, payment: Payment) -> Payment:
        if payment.id is None:
            model = PaymentModel(
                id=uuid.uuid4(),
                reservation_id=payment.reservation_id,
                user_id=payment.user_id,
                amount=payment.amount,
                status=str(payment.status),
                paid_at=payment.paid_at,
            )
            self.db.add(model)
            try:
                await self.db.flush()
            except IntegrityError as error:
                # 동시 결제로 reservation_id UNIQUE에 걸린 경우(DB 레벨 최종 방어)
                raise PaymentAlreadyExistsError() from error
            payment.id = model.id
        else:
            model = await self.db.get(PaymentModel, payment.id)
            if model is None:
                raise PaymentNotFoundError("저장할 결제 정보를 찾을 수 없습니다.")
            model.status = str(payment.status)
            model.paid_at = payment.paid_at
            await self.db.flush()
        return payment

    @staticmethod
    def _to_domain(model: PaymentModel) -> Payment:
        return Payment(
            id=model.id,
            reservation_id=model.reservation_id,
            user_id=model.user_id,
            amount=model.amount,
            status=PaymentStatus(model.status),
            paid_at=model.paid_at,
        )


class SqlAlchemyRefundRepository(RefundRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, refund_id: uuid.UUID) -> Refund | None:
        model = await self.db.get(RefundModel, refund_id)
        return self._to_domain(model) if model else None

    async def find_by_payment_id(self, payment_id: uuid.UUID) -> Refund | None:
        stmt = select(RefundModel).where(RefundModel.payment_id == payment_id)
        model = (await self.db.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def save(self, refund: Refund) -> Refund:
        # 환불은 변경 불가 이력이라 INSERT만 한다.
        model = RefundModel(
            id=uuid.uuid4(),
            payment_id=refund.payment_id,
            refund_amount=refund.refund_amount,
            penalty_amount=refund.penalty_amount,
            reason=refund.reason,
            status=str(refund.status),
            completed_at=refund.completed_at,
        )
        self.db.add(model)
        try:
            await self.db.flush()
        except IntegrityError as error:
            # 동시 환불로 payment_id UNIQUE에 걸린 경우(DB 레벨 최종 방어)
            raise PaymentAlreadyRefundedError() from error
        refund.id = model.id
        return refund

    @staticmethod
    def _to_domain(model: RefundModel) -> Refund:
        return Refund(
            id=model.id,
            payment_id=model.payment_id,
            refund_amount=model.refund_amount,
            penalty_amount=model.penalty_amount,
            reason=model.reason,
            status=RefundStatus(model.status),
            completed_at=model.completed_at,
        )
