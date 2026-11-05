"""결제용 ReservationPort 어댑터와 예약용 RefundPort 어댑터 계약 테스트. DB 없음."""

import uuid

import pytest

from payments.domain.exceptions import (
    PaymentAlreadyRefundedError,
    PaymentNotRefundableError,
    InconsistencyKind,
    PaymentStateInconsistentError,
)
from payments.domain.exceptions import StockNotConnectedError as PaymentsStockNotConnected
from payments.domain.reservation_snapshot import ReservationSnapshot
from payments.domain.rules import (
    REFUNDABLE_RESERVATION_STATUSES,
    RESERVATION_PAID_STATUS,
    RESERVATION_PAYABLE_STATUS,
)
from reservations.application.adapters import PaymentRefundAdapter, PaymentReservationAdapter
from reservations.application.views import RefundTarget
from reservations.domain.exceptions import (
    DataInconsistentError,
    RefundConflictError,
    ReservationConflictError,
    ReservationNotFoundError,
    ReservationStateError,
)
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.reservations.fakes import NOW, build, set_status
from tests.reservations.test_stock_guard import NoRestoreStock

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def created(service, stock, status=S.PENDING_PAYMENT):
    r = await service.create_reservation(uuid.uuid4(), stock.offer_id, 2)
    set_status(r, status)
    return r


def test_status_strings_match_payments_constants():
    assert str(S.PENDING_PAYMENT) == RESERVATION_PAYABLE_STATUS
    assert str(S.RESERVED) == RESERVATION_PAID_STATUS
    assert str(S.RESERVED) in REFUNDABLE_RESERVATION_STATUSES  # RefundTarget.status가 환불 가능 상태


async def test_get_returns_payments_snapshot_with_pickup_start_from_offer():
    service, lifecycle, _, _, stock, *_ = build()
    r = await created(service, stock)
    adapter = PaymentReservationAdapter(lifecycle)
    snapshot = await adapter.get(r.id)
    assert isinstance(snapshot, ReservationSnapshot)
    assert (snapshot.id, snapshot.user_id, snapshot.total_price) == (r.id, r.user_id, r.total_price)
    assert snapshot.status == RESERVATION_PAYABLE_STATUS
    assert snapshot.pickup_start == stock._terms(stock.offer_id).pickup_start
    set_status(r, S.RESERVED)
    assert (await adapter.get(r.id)).status == RESERVATION_PAID_STATUS


async def test_get_missing_is_none_and_for_update_locks_offer_then_reservation():
    service, lifecycle, _, _, stock, _, log, _ = build()
    adapter = PaymentReservationAdapter(lifecycle)
    assert await adapter.get(uuid.uuid4()) is None
    r = await created(service, stock)
    log.events.clear()
    await adapter.get(r.id, for_update=True)
    assert log.events == ["res_read", "offer_lock", "res_lock"]  # 할인 -> 예약 (RD-5)


async def test_mark_paid_does_not_commit_unless_asked():
    service, lifecycle, session, _, stock, *_ = build()
    r = await created(service, stock)
    session.commits = 0
    adapter = PaymentReservationAdapter(lifecycle)
    await adapter.mark_paid(r.id)
    assert r.status == S.RESERVED and session.commits == 0
    with pytest.raises(ReservationStateError):  # 이미 결제됨 -> 예약 예외 그대로(공용 409 핸들러)
        await adapter.mark_paid(r.id)
    with pytest.raises(ReservationNotFoundError):
        await adapter.mark_paid(uuid.uuid4())


async def test_cancel_for_refund_no_commit_and_restores_stock():
    service, lifecycle, session, _, stock, *_ = build()
    r = await created(service, stock, S.RESERVED)
    session.commits = 0
    await PaymentReservationAdapter(lifecycle).cancel_for_refund(r.id, "환불")
    assert r.status == S.CANCELLED and session.commits == 0
    assert stock.released and stock.released[0][3] == "환불"


async def test_cancel_for_refund_translates_stock_error_to_payments_exception():
    service, lifecycle, session, repo, stock, _, log, owner = build()
    r = await created(service, stock, S.RESERVED)
    lifecycle.stock = NoRestoreStock(log, owner)
    lifecycle.stock.offer_id = stock.offer_id
    session.commits = 0
    with pytest.raises(PaymentsStockNotConnected) as e:
        await PaymentReservationAdapter(lifecycle).cancel_for_refund(r.id, "환불")
    assert e.value.error_code == "STOCK_NOT_CONNECTED"
    assert "결제된 예약의 취소·환불" in str(e.value)
    assert session.commits == 0  # 어댑터는 commit하지 않는다


class FakePayments:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    async def refund_for_cancelled_reservation(self, reservation_id, **kwargs):
        self.calls.append((reservation_id, kwargs))
        if self.error:
            raise self.error

    async def ensure_no_paid_payment_for_reservation(self, reservation_id):
        self.calls.append((reservation_id, "ensure_no_paid_payment"))
        if self.error:
            raise self.error


def target():
    return RefundTarget(
        reservation_id=uuid.uuid4(), user_id=uuid.uuid4(), total_price=6000,
        pickup_start=NOW, status=str(S.RESERVED),
    )


async def test_refund_adapter_passes_arguments():
    payments = FakePayments()
    t = target()
    await PaymentRefundAdapter(payments).refund_for_cancelled_reservation(
        t, reason="중단", waive_penalty=True
    )
    assert payments.calls == [
        (
            t.reservation_id,
            dict(reservation_status="RESERVED", pickup_start=NOW, reason="중단", waive_penalty=True),
        )
    ]


async def test_refund_adapter_translates_inconsistency_without_logging(caplog):
    t = target()
    payment_id = uuid.uuid4()
    adapter = PaymentRefundAdapter(
        FakePayments(
            PaymentStateInconsistentError(InconsistencyKind.PAYMENT_MISSING, t.reservation_id, payment_id)
        )
    )
    with caplog.at_level("DEBUG"):
        with pytest.raises(DataInconsistentError) as e:
            await adapter.refund_for_cancelled_reservation(t, reason="x")
    assert e.value.error_code == "DATA_INCONSISTENT"
    assert not isinstance(e.value, ReservationConflictError)  # 409로 잡히지 않는다
    (detail,) = e.value.details
    assert (detail.reservation_id, detail.payment_id, detail.kind) == (
        t.reservation_id, payment_id, "PAYMENT_MISSING",
    )
    assert caplog.records == []  # 어댑터는 로그를 남기지 않는다(중복 방지)


async def test_ensure_no_paid_payment_adapter_passes_and_translates(caplog):
    rid = uuid.uuid4()
    ok = FakePayments()
    await PaymentRefundAdapter(ok).ensure_no_paid_payment(rid)
    assert ok.calls == [(rid, "ensure_no_paid_payment")]

    paid_error = PaymentStateInconsistentError(InconsistencyKind.PAID_PAYMENT_ON_PENDING_RESERVATION, rid)
    with caplog.at_level("DEBUG"):
        with pytest.raises(DataInconsistentError) as e:
            await PaymentRefundAdapter(FakePayments(paid_error)).ensure_no_paid_payment(rid)
    assert e.value.reservation_ids == (rid,) and e.value.details[0].kind == str(paid_error.kind)
    assert caplog.records == []


async def test_refund_adapter_translates_other_conflicts():
    adapter = PaymentRefundAdapter(FakePayments(PaymentAlreadyRefundedError()))
    with pytest.raises(RefundConflictError):
        await adapter.refund_for_cancelled_reservation(target(), reason="x")


async def test_refund_adapter_lets_validation_errors_through():
    adapter = PaymentRefundAdapter(FakePayments(PaymentNotRefundableError()))
    with pytest.raises(PaymentNotRefundableError):  # ValueError 계열은 공용 400 핸들러가 처리
        await adapter.refund_for_cancelled_reservation(target(), reason="x")
