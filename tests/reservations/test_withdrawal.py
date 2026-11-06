"""회원별 일괄 취소·매장별 예약 확인 (reservations.md 15절). fake 주입, DB 없음."""

import logging
import uuid

import pytest

from admin.domain.exceptions import ReservationDataInconsistentError
from reservations.application.admin_adapters import ReservationAdminAdapter
from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.service import ReservationApplicationService
from reservations.application.store_adapters import CatalogStoreOffersAdapter
from reservations.application.store_query import StoreReservationQuery
from reservations.domain import rules
from reservations.domain.exceptions import DataInconsistentError
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.reservations.fakes import (
    NOW,
    FakeClock,
    FakeCodes,
    FakeRefunds,
    FakeRepo,
    FakeSession,
    Log,
    Terms,
    set_status,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class MultiStock:
    """offer 여러 개를 가진 재고 fake. 잠금·복구 호출 순서를 기록한다."""

    def __init__(self, log: Log, offer_ids):
        self.log = log
        self.offer_ids = list(offer_ids)
        self.locked: list[uuid.UUID] = []
        self.released: list[tuple] = []
        self.restore_result = True
        self.over_limit = False

    async def get_terms(self, offer_id, *, for_update=False):
        if for_update:
            self.locked.append(offer_id)
            self.log.events.append("offer_lock")
        return Terms(offer_id=offer_id, owner_id=uuid.uuid4())

    async def release(self, offer_id, quantity, *, user_id, reason, now):
        self.log.events.append("release")
        if self.over_limit:
            from reservations.domain.exceptions import InconsistencyDetail

            raise DataInconsistentError([InconsistencyDetail(None, "STOCK_RESTORE_OVER_LIMIT")])
        if not self.restore_result:
            return False
        self.released.append((offer_id, quantity, user_id, reason))
        return True


def make_env(offer_count=2):
    from reservations.domain.offer_ref import OfferRef

    log = Log()
    offers = sorted(uuid.uuid4() for _ in range(offer_count))
    session, repo, stock, refunds = FakeSession(log), FakeRepo(log), MultiStock(log, offers), FakeRefunds(log)
    lifecycle = ReservationLifecycleService(session=session, reservations=repo, stock=stock, clock=FakeClock())
    service = ReservationApplicationService(
        session=session, lifecycle=lifecycle, reservations=repo, stock=stock,
        refunds=refunds, clock=FakeClock(), code_generator=FakeCodes(),
    )

    def add(user_id, offer_id, status=S.PENDING_PAYMENT, qty=1):
        terms = Terms(offer_id=offer_id, owner_id=uuid.uuid4())
        from reservations.domain.pickup_reservation import PickupReservation

        r = PickupReservation.create(user_id, OfferRef.from_info(terms), qty, "A12345", NOW)
        r.id = uuid.uuid4()
        if status != S.PENDING_PAYMENT:
            if status == S.RESERVED:
                r.mark_paid()
            elif status == S.PICKED_UP:
                r.mark_paid()
                set_status(r, S.PICKED_UP)
            else:
                set_status(r, status)
        repo.items[r.id] = r
        return r

    return service, lifecycle, session, repo, stock, refunds, log, offers, add


# ── lifecycle.cancel_all_for_user ──
async def test_cancel_all_for_user_cancels_pending_and_reserved_skips_others():
    service, lifecycle, session, repo, stock, refunds, log, offers, add = make_env()
    user = uuid.uuid4()
    p1, p2 = add(user, offers[0]), add(user, offers[1], qty=2)
    r1 = add(user, offers[0], S.RESERVED)
    picked, done = add(user, offers[0], S.PICKED_UP), add(user, offers[1], S.CANCELLED)
    other = add(uuid.uuid4(), offers[0])
    result = await lifecycle.cancel_all_for_user(user, reason="회원 탈퇴")
    assert len(result) == 3
    assert {p1.status, p2.status, r1.status} == {S.CANCELLED}
    assert picked.status == S.PICKED_UP and done.status == S.CANCELLED  # 기록 유지
    assert other.status == S.PENDING_PAYMENT  # 다른 회원은 건드리지 않음
    assert len(stock.released) == 3 and sorted(q for _, q, _, _ in stock.released) == [1, 1, 2]
    targets = [c.refund_target for c in result if c.refund_target]
    assert [t.reservation_id for t in targets] == [r1.id] and targets[0].status == "RESERVED"
    assert sorted(c.check_paid_payment for c in result) == [False, True, True]
    assert session.commits == 0


async def test_cancel_all_for_user_locks_offers_ascending_once_before_reservations():
    service, lifecycle, session, repo, stock, refunds, log, offers, add = make_env(3)
    user = uuid.uuid4()
    for o in (offers[2], offers[0], offers[2], offers[1], offers[0]):
        add(user, o)
    await lifecycle.cancel_all_for_user(user, reason="x")
    assert stock.locked == offers  # 오름차순, 중복 1회
    events = log.events
    assert events.index("res_lock_user") > max(i for i, e in enumerate(events) if e == "offer_lock")


async def test_cancel_all_for_user_rereads_after_locking_and_skips_changed():
    service, lifecycle, session, repo, stock, refunds, log, offers, add = make_env(1)
    user = uuid.uuid4()
    a, b = add(user, offers[0]), add(user, offers[0])
    original = stock.get_terms

    async def get_terms(offer_id, *, for_update=False):
        set_status(a, S.CANCELLED)  # 잠금 대기 중 고객이 직접 취소
        return await original(offer_id, for_update=for_update)

    stock.get_terms = get_terms
    result = await lifecycle.cancel_all_for_user(user, reason="x")
    assert [c.reservation.id for c in result] == [b.id]
    assert len(stock.released) == 1


async def test_cancel_all_for_user_empty_returns_empty_without_locks():
    service, lifecycle, session, repo, stock, refunds, log, offers, add = make_env(1)
    user = uuid.uuid4()
    add(user, offers[0], S.PICKED_UP)  # 활성 없음: PickedUpReservationExistsError도 없다
    assert await lifecycle.cancel_all_for_user(user, reason="x") == []
    assert stock.locked == [] and stock.released == []


async def test_cancel_all_for_user_proceeds_when_offer_closed():
    service, lifecycle, session, repo, stock, refunds, log, offers, add = make_env(1)
    stock.restore_result = False  # 닫힌 할인: 복구 안 함(D40)
    user = uuid.uuid4()
    a = add(user, offers[0])
    assert len(await lifecycle.cancel_all_for_user(user, reason="x")) == 1
    assert a.status == S.CANCELLED


# ── service.cancel_all_for_user ──
async def test_service_cancel_all_for_user_refunds_reserved_with_waived_penalty_no_commit(caplog):
    service, lifecycle, session, repo, stock, refunds, log, offers, add = make_env()
    user = uuid.uuid4()
    p, r = add(user, offers[0]), add(user, offers[1], S.RESERVED)
    add(user, offers[1], S.PICKED_UP)
    n = await service.cancel_all_for_user(user, reason=rules.WITHDRAWAL_CANCEL_REASON)
    assert n == 2 and session.commits == 0 and session.rollbacks == 0
    (target, reason, waive), = refunds.calls
    assert target.reservation_id == r.id and waive is True and reason == "회원 탈퇴"
    assert refunds.checks == [p.id]  # PENDING은 PAID 결제 확인만


async def test_service_cancel_all_for_user_refund_inconsistency_rolls_back_and_logs_once(caplog):
    service, lifecycle, session, repo, stock, refunds, log, offers, add = make_env()
    user = uuid.uuid4()
    r1, r2 = add(user, offers[0], S.RESERVED), add(user, offers[1], S.RESERVED)
    p = add(user, offers[1])
    refunds.inconsistent = {r1.id, r2.id}
    refunds.paid_pending = {p.id}
    with caplog.at_level(logging.ERROR):
        with pytest.raises(DataInconsistentError) as exc:
            await service.cancel_all_for_user(user, reason="x")
    assert set(exc.value.reservation_ids) == {r1.id, r2.id, p.id}
    assert session.rollbacks == 1 and session.commits == 0
    logs = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(logs) == 1 and "cancel_all_for_user" in logs[0].getMessage()


async def test_service_cancel_all_for_user_stock_inconsistency_rolls_back_and_logs_once(caplog):
    service, lifecycle, session, repo, stock, refunds, log, offers, add = make_env(1)
    stock.over_limit = True
    user = uuid.uuid4()
    add(user, offers[0])
    with caplog.at_level(logging.ERROR):
        with pytest.raises(DataInconsistentError):
            await service.cancel_all_for_user(user, reason="x")
    assert session.rollbacks == 1 and session.commits == 0
    assert len([r for r in caplog.records if r.levelno == logging.ERROR]) == 1
    assert refunds.calls == []


async def test_service_cancel_all_for_user_zero_when_nothing_active():
    service, lifecycle, session, repo, stock, refunds, log, offers, add = make_env(1)
    assert await service.cancel_all_for_user(uuid.uuid4(), reason="x") == 0
    assert session.commits == 0


# ── StoreReservationQuery ──
class FakeStoreOffers:
    def __init__(self, ids):
        self.ids = ids
        self.calls = []

    async def list_offer_ids_of_store(self, store_id, *, for_update=False):
        self.calls.append((store_id, for_update))
        return self.ids


def make_query(offer_ids):
    log = Log()
    repo, store_offers = FakeRepo(log), FakeStoreOffers(offer_ids)
    return StoreReservationQuery(repo, store_offers), repo, store_offers, log


def put(repo, user_id, offer_id, status):
    from reservations.domain.offer_ref import OfferRef
    from reservations.domain.pickup_reservation import PickupReservation

    r = PickupReservation.create(user_id, OfferRef.from_info(Terms(offer_id, uuid.uuid4())), 1, "A12345", NOW)
    r.id = uuid.uuid4()
    if status == S.RESERVED:
        r.mark_paid()
    elif status != S.PENDING_PAYMENT:
        if status == S.PICKED_UP:
            r.mark_paid()
        set_status(r, status)
    repo.items[r.id] = r


async def test_store_query_true_only_for_reserved():
    offer = uuid.uuid4()
    for status, expected in [
        (S.RESERVED, True), (S.PENDING_PAYMENT, False), (S.PICKED_UP, False), (S.CANCELLED, False),
    ]:
        query, repo, _, _ = make_query([offer])
        put(repo, uuid.uuid4(), offer, status)
        assert await query.has_reserved_for_store(uuid.uuid4()) is expected
        assert await query.has_pickup_pending_for_store(uuid.uuid4()) is expected


async def test_store_query_ignores_other_stores_offers():
    query, repo, _, _ = make_query([uuid.uuid4()])
    put(repo, uuid.uuid4(), uuid.uuid4(), S.RESERVED)  # 다른 매장의 offer
    assert await query.has_reserved_for_store(uuid.uuid4()) is False


async def test_store_query_without_offers_skips_reservation_lookup():
    query, repo, store_offers, log = make_query([])
    assert await query.has_reserved_for_store(uuid.uuid4()) is False
    assert store_offers.calls[0][1] is True


async def test_store_query_locks_offers_for_update():
    store = uuid.uuid4()
    query, repo, store_offers, _ = make_query([uuid.uuid4()])
    await query.has_reserved_for_store(store)
    assert store_offers.calls == [(store, True)]


async def test_store_query_excludes_given_user():
    offer, user = uuid.uuid4(), uuid.uuid4()
    query, repo, _, _ = make_query([offer])
    put(repo, user, offer, S.RESERVED)
    assert await query.has_reserved_for_store(uuid.uuid4()) is True
    assert await query.has_reserved_for_store(uuid.uuid4(), excluding_user_id=user) is False
    put(repo, uuid.uuid4(), offer, S.RESERVED)
    assert await query.has_reserved_for_store(uuid.uuid4(), excluding_user_id=user) is True


# ── 어댑터 ──
async def test_catalog_store_offers_adapter_delegates():
    class Offers:
        async def find_ids_by_store(self, store_id, *, for_update=False):
            return [store_id, for_update]

    store = uuid.uuid4()
    assert await CatalogStoreOffersAdapter(Offers()).list_offer_ids_of_store(store, for_update=True) == [
        store, True,
    ]


async def test_admin_adapter_delegates_and_translates_inconsistency(caplog):
    class Service:
        def __init__(self, error=None):
            self.error, self.calls = error, []

        async def cancel_all_for_user(self, user_id, *, reason):
            self.calls.append((user_id, reason))
            if self.error:
                raise self.error
            return 4

    query, repo, _, _ = make_query([])
    user = uuid.uuid4()
    service = Service()
    adapter = ReservationAdminAdapter(service, query)
    assert await adapter.cancel_active_for_user(user, reason="약관 위반") == 4
    assert service.calls == [(user, "약관 위반")]
    assert await adapter.has_reserved_for_store(uuid.uuid4(), excluding_user_id=user) is False

    bad = ReservationAdminAdapter(Service(DataInconsistentError()), query)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ReservationDataInconsistentError) as exc:
            await bad.cancel_active_for_user(user, reason="x")
    assert exc.value.error_code == "DATA_INCONSISTENT"
    assert caplog.records == []  # 번역만, 로그 없음
