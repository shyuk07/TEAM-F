"""payments 테스트용 fake 모음 (DB 없이 서비스·API 테스트)."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from payments.domain.exceptions import PaymentAlreadyExistsError, PaymentAlreadyRefundedError
from payments.domain.gateway_result import GatewayResult
from payments.domain.repository.payment_repository import PaymentRepository
from payments.domain.repository.refund_repository import RefundRepository
from payments.domain.reservation_snapshot import ReservationSnapshot
from payments.domain.rules import RESERVATION_PAID_STATUS, RESERVATION_PAYABLE_STATUS
from payments.domain.service import Clock, PaymentGateway


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class FakeAuth:
    """AuthApplicationService 대역. 호출 (이름, user_id, amount, commit)을 순서대로 기록한다."""

    POINT_USE_UNIT = 100

    def __init__(self, balance: int = 100000):
        self.balance = balance
        self.calls: list[tuple[str, uuid.UUID, int, bool]] = []
        self.raise_on: dict[str, Exception] = {}

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]

    async def use_points(self, user_id, amount, *, commit=True):
        self.calls.append(("use_points", user_id, amount, commit))
        if "use_points" in self.raise_on:
            raise self.raise_on["use_points"]
        if amount <= 0 or amount % self.POINT_USE_UNIT or amount > self.balance:
            raise ValueError("포인트를 사용할 수 없습니다.")
        self.balance -= amount

    async def earn_points(self, user_id, amount, *, commit=True):
        self.calls.append(("earn_points", user_id, amount, commit))
        if "earn_points" in self.raise_on:
            raise self.raise_on["earn_points"]
        self.balance += amount

    async def restore_points(self, user_id, amount, *, commit=True):
        self.calls.append(("restore_points", user_id, amount, commit))
        if "restore_points" in self.raise_on:
            raise self.raise_on["restore_points"]
        self.balance += amount

    async def revoke_points(self, user_id, amount, *, commit=True) -> int:
        self.calls.append(("revoke_points", user_id, amount, commit))
        if "revoke_points" in self.raise_on:
            raise self.raise_on["revoke_points"]
        actual = min(self.balance, amount)
        self.balance -= actual
        return actual


class FakePaymentRepository(PaymentRepository):
    """메모리 저장소. 실제 DB처럼 reservation_id UNIQUE를 흉내 낸다."""

    def __init__(self):
        self.items = {}

    async def find_by_id(self, payment_id, for_update=False):
        return self.items.get(payment_id)

    async def find_by_reservation_id(self, reservation_id, for_update=False):
        return next((p for p in self.items.values() if p.reservation_id == reservation_id), None)

    async def save(self, payment):
        if payment.id is None:
            if await self.find_by_reservation_id(payment.reservation_id) is not None:
                raise PaymentAlreadyExistsError()
            payment.id = uuid.uuid4()
        self.items[payment.id] = payment
        return payment


class FakeRefundRepository(RefundRepository):
    """메모리 저장소. 실제 DB처럼 payment_id UNIQUE를 흉내 낸다."""

    def __init__(self):
        self.items = {}

    async def find_by_id(self, refund_id):
        return self.items.get(refund_id)

    async def find_by_payment_id(self, payment_id):
        return next((r for r in self.items.values() if r.payment_id == payment_id), None)

    async def save(self, refund):
        if await self.find_by_payment_id(refund.payment_id) is not None:
            raise PaymentAlreadyRefundedError()
        refund.id = uuid.uuid4()
        self.items[refund.id] = refund
        return refund


class FakeReservationPort:
    def __init__(self):
        self.items: dict[uuid.UUID, ReservationSnapshot] = {}
        self.mark_paid_calls: list[tuple[uuid.UUID, bool]] = []  # (reservation_id, commit)
        self.get_calls: list[tuple[uuid.UUID, bool]] = []  # (reservation_id, for_update)
        self.raise_on_mark_paid: Exception | None = None
        self.cancel_calls: list[tuple[uuid.UUID, str, bool]] = []  # (reservation_id, reason, commit)
        self.raise_on_cancel: Exception | None = None

    def add(
        self,
        user_id: uuid.UUID,
        total_price: int | None = 12000,
        status: str = RESERVATION_PAYABLE_STATUS,
        pickup_start: datetime | None = None,
    ) -> uuid.UUID:
        reservation_id = uuid.uuid4()
        self.items[reservation_id] = ReservationSnapshot(
            id=reservation_id,
            user_id=user_id,
            total_price=total_price,
            status=status,
            pickup_start=pickup_start,
        )
        return reservation_id

    def set_status(self, reservation_id: uuid.UUID, status: str) -> None:
        self.items[reservation_id] = replace(self.items[reservation_id], status=status)

    async def get(self, reservation_id, *, for_update=False):
        self.get_calls.append((reservation_id, for_update))
        return self.items.get(reservation_id)

    async def mark_paid(self, reservation_id, *, commit=False):
        self.mark_paid_calls.append((reservation_id, commit))
        if self.raise_on_mark_paid is not None:
            raise self.raise_on_mark_paid
        self.set_status(reservation_id, RESERVATION_PAID_STATUS)

    async def cancel_for_refund(self, reservation_id, reason, *, commit=False):
        self.cancel_calls.append((reservation_id, reason, commit))
        if self.raise_on_cancel is not None:
            raise self.raise_on_cancel
        self.set_status(reservation_id, "CANCELLED")


class FakeGateway(PaymentGateway):
    def __init__(self):
        self.charged = []

    async def charge(self, payment):
        self.charged.append(payment)
        return GatewayResult(success=True, provider_payment_id="fake_pg_1")


class FailingGateway(PaymentGateway):
    async def charge(self, payment):
        return GatewayResult(success=False, failure_response={"code": "CARD_DECLINED"})


class FixedClock(Clock):
    def __init__(self, now: datetime | None = None):
        self.current = now or datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

