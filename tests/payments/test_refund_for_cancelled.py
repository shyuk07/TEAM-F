"""PaymentApplicationService.refund_for_cancelled_reservation (예약 취소가 부르는 환불) 테스트. DB 없음."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from payments.domain.exceptions import (
    PaymentAlreadyExistsError,
    PaymentAlreadyRefundedError,
    PaymentNotFoundError,
    PaymentStateInconsistentError,
    ReservationNotFoundError,
)
from payments.domain.payment import Payment, PaymentStatus
from payments.domain.refund import Refund
from payments.infrastructure.repositories import SqlAlchemyPaymentRepository, SqlAlchemyRefundRepository
from tests.payments.test_service import USER, Env, paid

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class HalfPolicy:
    def penalty(self, paid_amount, pickup_start, now):
        return paid_amount // 2


async def call(env, payment, **kwargs):
    args = dict(reservation_status="RESERVED", pickup_start=NOW + timedelta(hours=1), reason="고객 요청 취소")
    args.update(kwargs)
    return await env.service.refund_for_cancelled_reservation(payment.reservation_id, **args)


async def test_refund_without_commit_and_full_amount():
    env = Env()
    payment = await paid(env)
    commits = env.db.commits

    refund = await call(env, payment)

    assert env.db.commits == commits and env.db.rollbacks == 0  # commit하지 않는다 (R13)
    assert (refund.refund_amount, refund.penalty_amount) == (payment.amount, 0)  # RD-3: 위약금 0원
    assert env.payments.items[payment.id].status == PaymentStatus.REFUNDED
    assert env.refunds.items[refund.id] is refund
    assert env.reservations.cancel_calls == []  # 예약 취소는 호출한 쪽(예약 서비스)이 한다


async def test_policy_penalty_applies_unless_waived():
    env = Env(policy=HalfPolicy())
    payment = await paid(env)
    refund = await call(env, payment)
    assert (refund.refund_amount, refund.penalty_amount) == (payment.amount // 2, payment.amount // 2)

    env2 = Env(policy=HalfPolicy())
    payment2 = await paid(env2)
    refund2 = await call(env2, payment2, waive_penalty=True)
    assert (refund2.refund_amount, refund2.penalty_amount) == (payment2.amount, 0)


async def test_no_payment_is_inconsistent():
    env = Env()
    with pytest.raises(PaymentStateInconsistentError) as e:
        await env.service.refund_for_cancelled_reservation(
            uuid.uuid4(), reservation_status="RESERVED", pickup_start=None, reason="x"
        )
    assert e.value.error_code == "DATA_INCONSISTENT"
    assert env.refunds.items == {} and env.db.commits == 0


async def test_already_refunded_payment_is_inconsistent():
    env = Env()
    payment = await paid(env)
    await call(env, payment)
    with pytest.raises(PaymentStateInconsistentError):
        await call(env, payment)
    assert len(env.refunds.items) == 1


async def test_existing_refund_row_is_inconsistent():
    env = Env()
    payment = await paid(env)
    await env.refunds.save(Refund(payment.id, payment.amount, 0, "x", completed_at=NOW))
    with pytest.raises(PaymentStateInconsistentError):
        await call(env, payment)
    assert env.payments.items[payment.id].status == PaymentStatus.PAID  # 결제 상태 불변
    assert len(env.refunds.items) == 1


async def test_non_refundable_reservation_status_is_inconsistent():
    env = Env()
    payment = await paid(env)
    with pytest.raises(PaymentStateInconsistentError):
        await call(env, payment, reservation_status="PENDING_PAYMENT")
    assert env.refunds.items == {}


async def test_unpaid_payment_is_inconsistent():
    env = Env()
    payment = Payment.request(uuid.uuid4(), USER, 1000, NOW)  # READY
    await env.payments.save(payment)
    with pytest.raises(PaymentStateInconsistentError):
        await call(env, payment)


# ── 환불 API: 예약 취소 실패 시 롤백 ──
async def test_refund_api_rolls_back_when_cancel_for_refund_fails():
    env = Env()
    payment = await paid(env)
    env.reservations.raise_on_cancel = RuntimeError("취소 실패")
    commits = env.db.commits

    with pytest.raises(RuntimeError):
        await env.service.refund(USER, payment.id, "사유")

    assert env.db.commits == commits and env.db.rollbacks == 1  # 환불 저장분은 롤백 대상


async def test_refund_api_cancels_with_commit_false_and_reason():
    env = Env()
    payment = await paid(env)
    await env.service.refund(USER, payment.id, "사유")
    assert env.reservations.cancel_calls == [(payment.reservation_id, "사유", False)]


# ── 레포지토리: IntegrityError를 UNIQUE와 FK로 구분 (RC-28) ──
class FlushFails:
    def __init__(self, sqlstate, via_cause=False):
        driver = Exception("driver")
        driver.sqlstate = sqlstate
        if via_cause:  # 래퍼에는 코드가 없고 원본(__cause__)에만 있는 경우
            wrapper = Exception("wrapped")
            wrapper.__cause__ = driver
            driver = wrapper
        self.error = IntegrityError("INSERT", {}, driver)
        self.added = []

    def add(self, model):
        self.added.append(model)

    async def flush(self):
        raise self.error


def new_payment():
    payment = Payment.request(uuid.uuid4(), USER, 1000, NOW)
    payment.approve("pg", NOW)
    return payment


@pytest.mark.parametrize("via_cause", [False, True])
async def test_payment_save_unique_violation_is_409(via_cause):
    with pytest.raises(PaymentAlreadyExistsError):
        await SqlAlchemyPaymentRepository(FlushFails("23505", via_cause)).save(new_payment())


@pytest.mark.parametrize("via_cause", [False, True])
async def test_payment_save_fk_violation_is_not_found(via_cause):
    with pytest.raises(ReservationNotFoundError):
        await SqlAlchemyPaymentRepository(FlushFails("23503", via_cause)).save(new_payment())


async def test_payment_save_other_integrity_error_is_not_hidden():
    with pytest.raises(IntegrityError):
        await SqlAlchemyPaymentRepository(FlushFails("23502")).save(new_payment())  # NOT NULL 위반


async def test_refund_save_distinguishes_unique_and_fk():
    refund = Refund(uuid.uuid4(), 1000, 0, "x", completed_at=NOW)
    with pytest.raises(PaymentAlreadyRefundedError):
        await SqlAlchemyRefundRepository(FlushFails("23505")).save(refund)
    with pytest.raises(PaymentNotFoundError):
        await SqlAlchemyRefundRepository(FlushFails("23503")).save(refund)
    with pytest.raises(IntegrityError):
        await SqlAlchemyRefundRepository(FlushFails("23502")).save(refund)


def test_payment_model_has_reservation_fk():
    from payments.infrastructure.models import PaymentModel

    fks = {fk.target_fullname for fk in PaymentModel.__table__.c.reservation_id.foreign_keys}
    assert fks == {"pickup_reservations.id"}  # RD-33
