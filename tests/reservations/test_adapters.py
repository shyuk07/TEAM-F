"""실제 재고 어댑터(CatalogStockAdapter)와 catalog 포트 어댑터 테스트. DB 없음: catalog 레포는 메모리 fake."""

import inspect
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.exceptions import ReservationDataInconsistentError
from reservations.application import catalog_stock_adapter as stock_adapter_module
from reservations.application.catalog_adapters import OfferReservationCanceller, OfferReservationLookup
from reservations.application.catalog_stock_adapter import CatalogStockAdapter
from reservations.domain.exceptions import (
    DataInconsistentError,
    OfferNotFoundError,
    OfferNotReservableError,
    OutOfStockError,
    ReservationConflictError,
)
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.reservations.fakes import Log, build, set_status

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
H = timedelta(hours=1)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Offers:
    def __init__(self, offer=None, log: Log | None = None):
        self.offer = offer
        self.log = log or Log()
        self.saved = 0

    async def find_by_id(self, offer_id, for_update=False):
        self.log.events.append("offer_lock" if for_update else "offer_read")
        return self.offer

    async def save(self, offer):
        self.saved += 1
        self.log.events.append("offer_save")
        self.offer = offer
        return offer


class Products:
    def __init__(self, product):
        self.product = product
        self.locked = False

    async def find_by_id(self, product_id, for_update=False):
        self.locked = self.locked or for_update
        return self.product


class Stores:
    def __init__(self, store):
        self.store = store

    async def find_store_by_id(self, store_id):
        return self.store


class StockLogs:
    def __init__(self, log: Log):
        self.logs = []
        self.log = log

    async def add(self, entry):
        self.log.events.append("stock_log")
        self.logs.append(entry)
        return entry


def port(offer=True, product=True, store=True, **offer_kw):
    pid, sid, owner = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    kw = dict(
        product_id=pid, sale_price=3000, initial_stock=3, sales_start=NOW - H, sales_end=NOW + H,
        pickup_start=NOW + H, pickup_end=NOW + 3 * H, id=uuid.uuid4(),
    )
    kw.update(offer_kw)
    o = DiscountOffer(**kw)
    p = SimpleNamespace(name="샌드위치", store_id=sid)
    s = SimpleNamespace(owner_id=owner, name="마감 베이커리", pickup_address="서울")
    offers = Offers(o if offer else None)
    adapter = CatalogStockAdapter(
        offers=offers,
        products=Products(p if product else None),
        stores=Stores(s if store else None),
        stock_logs=StockLogs(offers.log),
    )
    return adapter, o, owner


async def test_get_terms_locks_offer_only_when_requested():
    stock, offer, owner = port()
    terms = await stock.get_terms(offer.id, for_update=True)
    assert (terms.sale_price, terms.owner_id, terms.store_name, terms.product_name) == (
        3000, owner, "마감 베이커리", "샌드위치",
    )
    assert stock.offers.log.events == ["offer_lock"]
    await stock.get_terms(offer.id)
    assert stock.offers.log.events == ["offer_lock", "offer_read"]
    assert stock.products.locked is False  # 상품 행은 잠그지 않는다


async def test_reserve_locks_offer_deducts_saves_and_logs_negative_amount():
    stock, offer, _ = port()
    user = uuid.uuid4()
    terms = await stock.reserve(offer.id, 2, user_id=user, now=NOW)
    assert terms.offer_id == offer.id
    assert offer.remaining_stock == 1 and offer.initial_stock == 3  # initial_stock 불변
    assert stock.offers.log.events == ["offer_lock", "offer_save", "stock_log"]  # 잠금 -> 저장 -> 로그
    [entry] = stock.stock_logs.logs
    assert (entry.offer_id, entry.user_id, entry.amount, entry.reason) == (offer.id, user, -2, "예약 생성")


async def test_reserve_last_unit_makes_sold_out():
    stock, offer, _ = port(initial_stock=1)
    await stock.reserve(offer.id, 1, user_id=uuid.uuid4(), now=NOW)
    assert offer.remaining_stock == 0 and offer.status == OfferStatus.SOLD_OUT


async def test_reserve_checks_translate_to_409_and_write_nothing():
    stock, offer, _ = port()
    with pytest.raises(OutOfStockError):
        await stock.reserve(offer.id, 4, user_id=uuid.uuid4(), now=NOW)
    with pytest.raises(OfferNotReservableError):
        await stock.reserve(offer.id, 1, user_id=uuid.uuid4(), now=NOW + 2 * H)  # 판매 종료
    with pytest.raises(OfferNotReservableError):
        await stock.reserve(offer.id, 1, user_id=uuid.uuid4(), now=NOW - 2 * H)  # 판매 전
    closed, off2, _ = port(is_active=False)
    with pytest.raises(OfferNotReservableError):
        await closed.reserve(off2.id, 1, user_id=uuid.uuid4(), now=NOW)
    sold, off3, _ = port(initial_stock=1, remaining_stock=0)
    with pytest.raises(OfferNotReservableError):  # 품절은 OUT_OF_STOCK이 아니라 OFFER_NOT_RESERVABLE
        await sold.reserve(off3.id, 1, user_id=uuid.uuid4(), now=NOW)
    for s in (stock, closed, sold):
        assert s.offers.saved == 0 and s.stock_logs.logs == []
    assert offer.remaining_stock == 3


async def test_release_restores_saves_and_logs_positive_amount():
    stock, offer, _ = port(initial_stock=3, remaining_stock=1)
    user = uuid.uuid4()
    assert await stock.release(offer.id, 2, user_id=user, reason="사용자가 쓴 사유", now=NOW) is True
    assert offer.remaining_stock == 3
    assert stock.offers.log.events == ["offer_lock", "offer_save", "stock_log"]
    [entry] = stock.stock_logs.logs
    assert (entry.amount, entry.user_id, entry.reason) == (2, user, "예약 취소 복구")  # 고정 문구


async def test_release_sold_out_becomes_on_sale_again():
    stock, offer, _ = port(initial_stock=1, remaining_stock=0, status=OfferStatus.SOLD_OUT)
    assert await stock.release(offer.id, 1, user_id=uuid.uuid4(), reason="x", now=NOW) is True
    assert offer.remaining_stock == 1 and offer.status == OfferStatus.ON_SALE


async def test_release_on_closed_offer_returns_false_and_changes_nothing():
    stock, offer, _ = port(initial_stock=3, remaining_stock=1, is_active=False)
    assert await stock.release(offer.id, 1, user_id=uuid.uuid4(), reason="x", now=NOW) is False
    assert offer.remaining_stock == 1
    assert stock.offers.saved == 0 and stock.stock_logs.logs == []


async def test_release_over_limit_is_translated_to_data_inconsistent():
    stock, offer, _ = port(initial_stock=3, remaining_stock=3)  # 차감 없이 복구 -> 상한 초과
    with pytest.raises(DataInconsistentError) as e:
        await stock.release(offer.id, 1, user_id=uuid.uuid4(), reason="x", now=NOW)
    assert [d.kind for d in e.value.details] == ["STOCK_RESTORE_OVER_LIMIT"]
    assert offer.remaining_stock == 3 and stock.offers.saved == 0 and stock.stock_logs.logs == []


@pytest.mark.parametrize("missing", ["offer", "product", "store"])
async def test_missing_is_not_found(missing):
    stock, offer, _ = port(**{missing: False})
    with pytest.raises(OfferNotFoundError):
        await stock.get_terms(uuid.uuid4())


def test_adapter_does_not_commit_or_take_catalog_service():
    source = inspect.getsource(stock_adapter_module)
    assert ".commit(" not in source  # R5·R13
    assert "catalog.application.service" not in source  # R12: catalog 서비스에 의존하지 않는다


async def test_lookup_adapter():
    service, _, _, repo, stock, *_ = build()
    lookup = OfferReservationLookup(repo)
    assert await lookup.has_reservations_for_offer(stock.offer_id) is False
    await service.create_reservation(uuid.uuid4(), stock.offer_id, 1)
    assert await lookup.has_reservations_for_offer(stock.offer_id) is True


@pytest.mark.parametrize(
    "statuses,expected",
    [
        ([], False),  # 예약 없음
        (["CANCELLED", "CANCELLED"], False),  # 모두 취소 (REQ-17: 수정 가능)
        (["PENDING_PAYMENT"], True),
        (["RESERVED"], True),
        (["PICKED_UP"], True),
        (["CANCELLED", "RESERVED"], True),  # 취소 + 살아 있는 예약 1건
    ],
)
async def test_lookup_adapter_counts_only_non_cancelled(statuses, expected):
    """catalog 할인 수정 가드(REQ-17, D81·D-39): 취소되지 않은 예약만 센다. 레포지토리는 exists_non_cancelled_by_offer만 쓴다."""
    service, _, _, repo, stock, *_ = build()
    for status in statuses:
        r = await service.create_reservation(uuid.uuid4(), stock.offer_id, 1)
        set_status(r, S(status))
    calls = []
    original = repo.exists_by_offer

    async def spy(offer_id):
        calls.append(offer_id)
        return await original(offer_id)

    repo.exists_by_offer = spy
    lookup = OfferReservationLookup(repo)
    assert await lookup.has_reservations_for_offer(stock.offer_id) is expected
    assert calls == []  # 상태 무관 조회(exists_by_offer)는 쓰지 않는다


async def test_canceller_adapter_delegates_without_commit():
    service, _, session, repo, stock, refunds, *_ = build()
    r = await service.create_reservation(uuid.uuid4(), stock.offer_id, 1)
    set_status(r, S.RESERVED)
    session.commits = 0
    n = await OfferReservationCanceller(service).cancel_all_for_offer(stock.offer_id, reason="중단")
    assert n == 1 and session.commits == 0 and len(refunds.calls) == 1


async def test_canceller_translates_data_inconsistent_without_extra_log(caplog):
    service, _, session, repo, stock, refunds, *_ = build()
    r = await service.create_reservation(uuid.uuid4(), stock.offer_id, 1)
    set_status(r, S.RESERVED)
    refunds.inconsistent.add(r.id)
    session.commits = session.rollbacks = 0
    with caplog.at_level("DEBUG"):
        with pytest.raises(ReservationDataInconsistentError) as e:
            await OfferReservationCanceller(service).cancel_all_for_offer(stock.offer_id, reason="중단")
    assert e.value.error_code == "DATA_INCONSISTENT"
    assert str(r.id) not in str(e.value)
    assert session.commits == 0 and session.rollbacks == 1  # 예약 서비스가 롤백
    assert len([x for x in caplog.records if x.levelno >= 40]) == 1  # 로그는 예약 서비스의 1건뿐


def test_catalog_inconsistent_error_is_not_any_handled_family():
    error = ReservationDataInconsistentError()
    for family in (ReservationConflictError, ValueError, PermissionError, LookupError, RuntimeError):
        assert not isinstance(error, family)
