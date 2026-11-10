import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.service import ReservationApplicationService
from reservations.domain.exceptions import (
    DataInconsistentError,
    InconsistencyDetail,
    OfferNotFoundError,
    OutOfStockError,
)
from reservations.domain.pickup_reservation import ReservationStatus
from reservations.domain.repository import ReservationRepository
from reservations.domain.service import Clock, PickupCodeGenerator

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


@dataclass
class Terms:
    offer_id: uuid.UUID
    owner_id: uuid.UUID
    store_name: str = "마감 베이커리"
    product_name: str = "샌드위치"
    pickup_address: str = "서울"
    sale_price: int = 3000
    pickup_start: datetime = NOW + timedelta(hours=1)
    pickup_end: datetime = NOW + timedelta(hours=3)
    cancellable_until: datetime = NOW  # Catalog 정책과 같게 pickup_start - 1시간(경계 포함이라 NOW에 취소 가능)


class Log:
    def __init__(self):
        self.events: list[str] = []


class FakeSession:
    def __init__(self, log: Log):
        self.log = log
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1
        self.log.events.append("commit")

    async def rollback(self):
        self.rollbacks += 1
        self.log.events.append("rollback")


class FakeClock(Clock):
    def now(self):
        return NOW


class FakeCodes(PickupCodeGenerator):
    def generate(self):
        return "A12345"


class FakeRepo(ReservationRepository):
    def __init__(self, log: Log):
        self.log = log
        self.items = {}

    async def find_by_id(self, reservation_id, for_update=False):
        self.log.events.append("res_lock" if for_update else "res_read")
        return self.items.get(reservation_id)

    async def find_by_user(self, user_id, *, status, page, size):
        rows = [r for r in self.items.values() if r.user_id == user_id and (status is None or r.status == status)]
        return rows[(page - 1) * size : page * size], len(rows)

    async def find_by_offer(self, offer_id, *, for_update=False):
        self.log.events.append("res_lock_all" if for_update else "res_read_all")
        return sorted((r for r in self.items.values() if r.offer_id == offer_id), key=lambda r: str(r.id))

    async def exists_by_offer(self, offer_id):
        return any(r.offer_id == offer_id for r in self.items.values())

    async def exists_non_cancelled_by_offer(self, offer_id):
        return any(r.offer_id == offer_id and r.status != ReservationStatus.CANCELLED for r in self.items.values())

    async def find_by_user_and_statuses(self, user_id, statuses, *, for_update=False):
        self.log.events.append("res_lock_user" if for_update else "res_read_user")
        rows = [r for r in self.items.values() if r.user_id == user_id and r.status in statuses]
        return sorted(rows, key=lambda r: (str(r.offer_id), str(r.id)))

    async def find_by_offers(self, offer_ids, *, status, page, size):
        rows = [r for r in self.items.values() if r.offer_id in offer_ids and (status is None or r.status == status)]
        rows.sort(key=lambda r: (r.created_at, str(r.id)), reverse=True)
        return rows[(page - 1) * size : page * size], len(rows)

    async def find_offer_ids_with_status(self, offer_ids, status, *, excluding_user_id=None):
        return {
            r.offer_id for r in self.items.values()
            if r.offer_id in offer_ids and r.status == status and r.user_id != excluding_user_id
        }

    async def exists_by_offers_and_status(self, offer_ids, status, *, excluding_user_id=None):
        self.log.events.append("res_exists")
        return any(
            r.offer_id in offer_ids and r.status == status and r.user_id != excluding_user_id
            for r in self.items.values()
        )

    async def save(self, reservation):
        if reservation.id is None:
            reservation.id = uuid.uuid4()
        self.items[reservation.id] = reservation
        self.log.events.append("save")
        return reservation


class FakeStock:
    def __init__(self, log: Log, owner_id: uuid.UUID, stock: int = 5):
        self.log = log
        self.owner_id = owner_id
        self.stock = stock
        self.offer_id = uuid.uuid4()
        self.released: list[tuple] = []
        self.restore_result = True  # False면 닫힌 할인처럼 복구하지 않고 False(D40)
        self.over_limit = False  # True면 복구 상한 초과(데이터 이상)

    def _terms(self, offer_id):
        if offer_id != self.offer_id:
            raise OfferNotFoundError()
        return Terms(offer_id=offer_id, owner_id=self.owner_id)

    async def get_terms(self, offer_id, *, for_update=False):
        self.log.events.append("offer_lock" if for_update else "offer_read")
        return self._terms(offer_id)

    async def reserve(self, offer_id, quantity, *, user_id, now):
        self.log.events.append("reserve")
        terms = self._terms(offer_id)
        if quantity > self.stock:
            raise OutOfStockError()
        self.stock -= quantity
        return terms

    async def release(self, offer_id, quantity, *, user_id, reason, now):
        self.log.events.append("release")
        if self.over_limit:
            raise DataInconsistentError([InconsistencyDetail(None, "STOCK_RESTORE_OVER_LIMIT")])
        if not self.restore_result:
            return False
        self.stock += quantity
        self.released.append((offer_id, quantity, user_id, reason))
        return True


class FakeRefunds:
    def __init__(self, log: Log):
        self.log = log
        self.calls: list[tuple] = []
        self.checks: list[uuid.UUID] = []  # ensure_no_paid_payment 호출 기록 (읽기 전용이라 events에는 남기지 않는다)
        self.fail = False
        self.inconsistent: set[uuid.UUID] = set()  # 환불 시 불일치로 거절할 예약 ID (RESERVED 취소)
        self.paid_pending: set[uuid.UUID] = set()  # PENDING_PAYMENT인데 PAID 결제가 있는 예약 ID

    @staticmethod
    def _error(reservation_id, kind):
        return DataInconsistentError(
            [InconsistencyDetail(reservation_id, kind, payment_id=uuid.uuid4())]
        )

    async def refund_for_cancelled_reservation(self, target, *, reason, waive_penalty=False):
        self.log.events.append("refund")
        if self.fail:
            raise RuntimeError("환불 실패")
        if target.reservation_id in self.inconsistent:
            raise self._error(target.reservation_id, "PAYMENT_ALREADY_REFUNDED")
        self.calls.append((target, reason, waive_penalty))

    async def ensure_no_paid_payment(self, reservation_id):
        self.checks.append(reservation_id)
        if reservation_id in self.paid_pending:
            raise self._error(reservation_id, "PAID_PAYMENT_ON_PENDING_RESERVATION")


def build():
    log = Log()
    owner_id = uuid.uuid4()
    session, repo, stock = FakeSession(log), FakeRepo(log), FakeStock(log, owner_id)
    refunds = FakeRefunds(log)
    lifecycle = ReservationLifecycleService(session=session, reservations=repo, stock=stock, clock=FakeClock())
    service = ReservationApplicationService(
        session=session, lifecycle=lifecycle, reservations=repo, stock=stock,
        refunds=refunds, clock=FakeClock(), code_generator=FakeCodes(),
    )
    return service, lifecycle, session, repo, stock, refunds, log, owner_id


def set_status(reservation, status):
    reservation.status = status
    if status == ReservationStatus.CANCELLED:
        reservation.cancelled_at = NOW
    if status == ReservationStatus.PICKED_UP:
        reservation.picked_up_at = NOW
