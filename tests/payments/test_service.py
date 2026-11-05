import uuid
from datetime import datetime

import pytest

from payments.application.service import PaymentApplicationService
from payments.domain.exceptions import (
    PaymentAccessDeniedError,
    PaymentAlreadyExistsError,
    PaymentAlreadyRefundedError,
    PaymentFailedError,
    PaymentNotFoundError,
    PaymentNotRefundableError,
    RefundAccessDeniedError,
    RefundNotFoundError,
    ReservationNotFoundError,
    ReservationNotPayableError,
)
from payments.domain.payment import PaymentStatus
from payments.domain.refund import RefundStatus
from payments.infrastructure.mock_gateway import MockPaymentGateway
from payments.domain.rules import RESERVATION_PAID_STATUS, RESERVATION_PAYABLE_STATUS
from tests.payments.fakes import (
    FailingGateway,
    FakeGateway,
    FakePaymentRepository,
    FakeRefundRepository,
    FakeReservationPort,
    FixedClock,
    FakeSession,
)

pytestmark = pytest.mark.anyio

USER = uuid.uuid4()
OTHER = uuid.uuid4()


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Env:
    def __init__(self, gateway=None, policy=None):
        self.db = FakeSession()
        self.payments = FakePaymentRepository()
        self.refunds = FakeRefundRepository()
        self.reservations = FakeReservationPort()
        self.gateway = gateway or FakeGateway()
        self.clock = FixedClock()
        extra = {} if policy is None else {"policy": policy}
        self.service = PaymentApplicationService(
            self.db,
            reservations=self.reservations,
            payments=self.payments,
            refunds=self.refunds,
            gateway=self.gateway,
            clock=self.clock,
            **extra,
        )


@pytest.fixture
def env():
    return Env()


# ---------- 결제 ----------
async def test_pay_success(env):
    rid = env.reservations.add(USER, total_price=15000)

    payment = await env.service.pay(USER, rid)

    assert payment.status == PaymentStatus.PAID
    assert payment.amount == 15000  # 금액은 서버가 예약에서 계산
    assert payment.paid_at is not None and payment.provider_payment_id == "fake_pg_1"
    assert payment.id in env.payments.items
    assert env.db.commits == 1 and env.db.rollbacks == 0
    assert env.reservations.mark_paid_calls == [(rid, False)]  # commit=False
    assert env.reservations.items[rid].status == RESERVATION_PAID_STATUS
    assert (rid, True) in env.reservations.get_calls  # 예약 행 잠금 요청


async def test_pay_with_default_mock_gateway_and_zero_penalty_policy():
    # 모의 게이트웨이(항상 성공)를 주입하고 정책을 생략하면 기본 0원 정책이 쓰인다.
    db, payments, reservations = FakeSession(), FakePaymentRepository(), FakeReservationPort()
    service = PaymentApplicationService(
        db,
        reservations=reservations,
        payments=payments,
        refunds=FakeRefundRepository(),
        gateway=MockPaymentGateway(),
        clock=FixedClock(),
    )
    rid = reservations.add(USER)
    payment = await service.pay(USER, rid)
    assert payment.provider_payment_id.startswith("mock_")
    refund = await service.refund(USER, payment.id, "단순 변심")
    assert refund.penalty_amount == 0 and refund.refund_amount == payment.amount


async def test_pay_zero_amount_allowed(env):
    rid = env.reservations.add(USER, total_price=0)
    assert (await env.service.pay(USER, rid)).amount == 0


async def test_pay_other_users_reservation_is_403(env):
    rid = env.reservations.add(OTHER)
    with pytest.raises(PaymentAccessDeniedError):
        await env.service.pay(USER, rid)
    assert env.db.commits == 0 and env.payments.items == {}


async def test_pay_missing_reservation_is_404(env):
    with pytest.raises(ReservationNotFoundError):
        await env.service.pay(USER, uuid.uuid4())


async def test_pay_twice_is_409(env):
    rid = env.reservations.add(USER)
    await env.service.pay(USER, rid)
    with pytest.raises(PaymentAlreadyExistsError):
        await env.service.pay(USER, rid)
    assert env.db.commits == 1


async def test_duplicate_check_comes_before_state_check(env):
    # 결제 후 예약 상태는 PAYABLE이 아니다. 그래도 400이 아니라 409여야 한다.
    rid = env.reservations.add(USER)
    await env.service.pay(USER, rid)
    assert env.reservations.items[rid].status != RESERVATION_PAYABLE_STATUS
    with pytest.raises(PaymentAlreadyExistsError):
        await env.service.pay(USER, rid)


async def test_ownership_check_comes_before_duplicate_check(env):
    rid = env.reservations.add(USER)
    await env.service.pay(USER, rid)
    with pytest.raises(PaymentAccessDeniedError):
        await env.service.pay(OTHER, rid)


@pytest.mark.parametrize("status", ["CANCELLED", "PICKED_UP", RESERVATION_PAID_STATUS])
async def test_pay_not_payable_state_is_400(env, status):
    rid = env.reservations.add(USER, status=status)
    with pytest.raises(ReservationNotPayableError):
        await env.service.pay(USER, rid)
    assert env.db.commits == 0 and env.payments.items == {}


async def test_pay_gateway_failure_is_not_saved_and_400():
    env = Env(gateway=FailingGateway())
    rid = env.reservations.add(USER)

    with pytest.raises(PaymentFailedError):
        await env.service.pay(USER, rid)

    assert env.payments.items == {}  # 저장 안 함
    assert env.db.commits == 0 and env.db.rollbacks == 1
    assert env.reservations.mark_paid_calls == []
    assert env.reservations.items[rid].status == RESERVATION_PAYABLE_STATUS


async def test_pay_can_retry_after_gateway_failure():
    env = Env(gateway=FailingGateway())
    rid = env.reservations.add(USER)
    with pytest.raises(PaymentFailedError):
        await env.service.pay(USER, rid)
    env.service.gateway = FakeGateway()
    assert (await env.service.pay(USER, rid)).status == PaymentStatus.PAID


async def test_pay_mark_paid_error_means_no_commit(env):
    rid = env.reservations.add(USER)
    env.reservations.raise_on_mark_paid = RuntimeError("예약 상태 변경 실패")

    with pytest.raises(RuntimeError):
        await env.service.pay(USER, rid)

    assert env.db.commits == 0
    assert env.db.rollbacks == 1


async def test_pay_race_conflict_rolls_back(env):
    # 사전 중복 검사를 통과한 뒤 다른 요청이 먼저 저장해 UNIQUE에 걸리는 상황
    class StaleCheck:
        """사전 조회는 None, save는 실제 UNIQUE 검사 (동시 결제 흉내)"""

        def __init__(self, real):
            self.real = real

        async def find_by_reservation_id(self, reservation_id, for_update=False):
            return None

        async def save(self, payment):
            return await self.real.save(payment)

    rid = env.reservations.add(USER)
    first = await env.service.pay(USER, rid)  # 다른 요청이 먼저 저장
    env.reservations.set_status(rid, RESERVATION_PAYABLE_STATUS)
    env.service.payments = StaleCheck(env.payments)
    commits_before, rollbacks_before = env.db.commits, env.db.rollbacks

    with pytest.raises(PaymentAlreadyExistsError):
        await env.service.pay(USER, rid)

    assert env.db.commits == commits_before
    assert env.db.rollbacks == rollbacks_before + 1
    assert list(env.payments.items) == [first.id]


# ---------- 결제 조회 ----------
async def test_get_payment_owner_only(env):
    payment = await env.service.pay(USER, env.reservations.add(USER))

    assert (await env.service.get_payment(USER, payment.id)).id == payment.id
    with pytest.raises(PaymentAccessDeniedError):
        await env.service.get_payment(OTHER, payment.id)
    with pytest.raises(PaymentNotFoundError):
        await env.service.get_payment(USER, uuid.uuid4())
    assert env.db.commits == 1  # 조회는 commit하지 않는다


# ---------- 환불 ----------
async def paid(env, total_price=12000, pickup_start: datetime | None = None):
    rid = env.reservations.add(USER, total_price=total_price, pickup_start=pickup_start)
    return await env.service.pay(USER, rid)


async def test_refund_success_with_zero_penalty(env):
    payment = await paid(env, 12000)
    commits_before = env.db.commits

    refund = await env.service.refund(USER, payment.id, "단순 변심")

    assert refund.penalty_amount == 0  # D-1: 위약금 0원
    assert refund.refund_amount == 12000
    assert refund.status == RefundStatus.COMPLETED
    assert refund.reason == "단순 변심" and refund.id in env.refunds.items
    assert payment.status == PaymentStatus.REFUNDED
    assert env.db.commits == commits_before + 1


async def test_refund_uses_injected_policy():
    class Fixed2000:
        def penalty(self, paid_amount, pickup_start, now):
            return 2000

    env = Env(policy=Fixed2000())
    payment = await paid(env, 12000)
    refund = await env.service.refund(USER, payment.id, "사유")
    assert (refund.refund_amount, refund.penalty_amount) == (10000, 2000)


async def test_refund_policy_out_of_range_is_value_error():
    class TooBig:
        def penalty(self, paid_amount, pickup_start, now):
            return paid_amount + 1

    env = Env(policy=TooBig())
    payment = await paid(env)
    commits_before = env.db.commits
    with pytest.raises(ValueError):
        await env.service.refund(USER, payment.id, "사유")
    assert env.db.commits == commits_before and env.refunds.items == {}


async def test_refund_does_not_change_reservation(env):
    # TODO(D-6): 예약 취소 연동은 아직 없다. 서비스는 예약 상태를 바꾸지 않는다.
    payment = await paid(env)
    await env.service.refund(USER, payment.id, "사유")
    assert env.reservations.items[payment.reservation_id].status == RESERVATION_PAID_STATUS
    assert len(env.reservations.mark_paid_calls) == 1  # 결제 때의 1회뿐


async def test_refund_twice_is_409(env):
    payment = await paid(env)
    await env.service.refund(USER, payment.id, "사유")
    commits_before = env.db.commits
    with pytest.raises(PaymentAlreadyRefundedError):
        await env.service.refund(USER, payment.id, "사유")
    assert env.db.commits == commits_before


async def test_refund_409_beats_reservation_state_400(env):
    # 환불 뒤 예약이 취소 상태가 되어도 이미 환불된 결제는 400이 아닌 409
    payment = await paid(env)
    await env.service.refund(USER, payment.id, "사유")
    env.reservations.set_status(payment.reservation_id, "CANCELLED")
    with pytest.raises(PaymentAlreadyRefundedError):
        await env.service.refund(USER, payment.id, "사유")


async def test_refund_by_other_user_is_403(env):
    payment = await paid(env)
    commits_before = env.db.commits
    with pytest.raises(RefundAccessDeniedError):
        await env.service.refund(OTHER, payment.id, "사유")
    assert payment.status == PaymentStatus.PAID and env.db.commits == commits_before


async def test_refund_403_beats_409(env):
    payment = await paid(env)
    await env.service.refund(USER, payment.id, "사유")
    with pytest.raises(RefundAccessDeniedError):
        await env.service.refund(OTHER, payment.id, "사유")


async def test_refund_missing_payment_is_404(env):
    with pytest.raises(PaymentNotFoundError):
        await env.service.refund(USER, uuid.uuid4(), "사유")


@pytest.mark.parametrize("status", ["CANCELLED", "PICKED_UP", RESERVATION_PAYABLE_STATUS])
async def test_refund_not_refundable_reservation_state_is_400(env, status):
    payment = await paid(env)
    env.reservations.set_status(payment.reservation_id, status)
    commits_before = env.db.commits
    with pytest.raises(PaymentNotRefundableError):
        await env.service.refund(USER, payment.id, "사유")
    assert payment.status == PaymentStatus.PAID  # 상태가 바뀌지 않음
    assert env.db.commits == commits_before and env.refunds.items == {}


async def test_refund_not_paid_payment_is_400(env):
    # READY 결제는 정상 흐름에서 저장되지 않지만 도메인 규칙은 서비스에서도 막는다.
    from payments.domain.payment import Payment

    rid = env.reservations.add(USER, status=RESERVATION_PAID_STATUS)
    ready = await env.payments.save(Payment(rid, USER, 12000))
    with pytest.raises(PaymentNotRefundableError):
        await env.service.refund(USER, ready.id, "사유")


async def test_refund_blank_reason_is_value_error(env):
    payment = await paid(env)
    with pytest.raises(ValueError):
        await env.service.refund(USER, payment.id, "  ")
    assert payment.status == PaymentStatus.PAID


async def test_refund_race_conflict_rolls_back(env):
    payment = await paid(env)
    await env.service.refund(USER, payment.id, "사유")

    class StaleRefunds:
        """사전 조회는 None, save는 실제 UNIQUE 검사 (동시 환불 흉내)"""

        def __init__(self, real):
            self.real = real

        async def find_by_payment_id(self, payment_id):
            return None

        async def save(self, refund):
            return await self.real.save(refund)

    env.payments.items[payment.id].status = PaymentStatus.PAID  # 사전 검사를 통과시키기 위해
    env.service.refunds = StaleRefunds(env.refunds)
    commits_before, rollbacks_before = env.db.commits, env.db.rollbacks
    with pytest.raises(PaymentAlreadyRefundedError):
        await env.service.refund(USER, payment.id, "사유")
    assert env.db.commits == commits_before
    assert env.db.rollbacks == rollbacks_before + 1


# ---------- 환불 조회 ----------
async def test_get_refund_owner_only(env):
    payment = await paid(env)
    refund = await env.service.refund(USER, payment.id, "사유")

    assert (await env.service.get_refund(USER, refund.id)).id == refund.id
    with pytest.raises(RefundAccessDeniedError):
        await env.service.get_refund(OTHER, refund.id)
    with pytest.raises(RefundNotFoundError):
        await env.service.get_refund(USER, uuid.uuid4())


async def test_pay_and_refund_use_injected_clock(env):
    rid = env.reservations.add(USER)
    payment = await env.service.pay(USER, rid)
    assert payment.paid_at == env.clock.current
    refund = await env.service.refund(USER, payment.id, "단순 변심")
    assert refund.completed_at == env.clock.current


def test_service_constructor_requires_all_args():
    with pytest.raises(TypeError):
        PaymentApplicationService(FakeSession(), reservations=FakeReservationPort())  # type: ignore[call-arg]
