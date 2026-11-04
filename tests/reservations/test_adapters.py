import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from catalog.domain.discount_offer import DiscountOffer
from reservations.application.catalog_adapters import OfferReservationCanceller, OfferReservationLookup
from reservations.application.interim_stock_port import ReadOnlyOfferStockPort
from reservations.domain.exceptions import OfferNotFoundError, OfferNotReservableError, OutOfStockError
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.reservations.fakes import build, set_status

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
H = timedelta(hours=1)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Offers:
    def __init__(self, offer=None):
        self.offer = offer

    async def find_by_id(self, offer_id, for_update=False):
        return self.offer


class Products:
    def __init__(self, product):
        self.product = product

    async def find_by_id(self, product_id, for_update=False):
        return self.product


class Stores:
    def __init__(self, store):
        self.store = store

    async def find_store_by_id(self, store_id):
        return self.store


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
    return (
        ReadOnlyOfferStockPort(
            Offers(o if offer else None), Products(p if product else None), Stores(s if store else None)
        ),
        o,
        owner,
    )


async def test_interim_get_terms_and_reserve_do_not_change_stock():
    stock, offer, owner = port()
    terms = await stock.get_terms(offer.id, for_update=True)
    assert (terms.sale_price, terms.owner_id, terms.store_name, terms.product_name) == (
        3000, owner, "마감 베이커리", "샌드위치",
    )
    t2 = await stock.reserve(offer.id, 2, user_id=uuid.uuid4(), now=NOW)
    assert t2.offer_id == offer.id and offer.remaining_stock == 3  # 차감 없음 (임시)
    assert await stock.release(offer.id, 2, user_id=uuid.uuid4(), reason="x") is False


async def test_interim_reserve_checks():
    stock, offer, _ = port()
    with pytest.raises(OutOfStockError):
        await stock.reserve(offer.id, 4, user_id=uuid.uuid4(), now=NOW)
    with pytest.raises(OfferNotReservableError):
        await stock.reserve(offer.id, 1, user_id=uuid.uuid4(), now=NOW + 2 * H)  # 판매 종료
    closed, off2, _ = port(is_active=False)
    with pytest.raises(OfferNotReservableError):
        await closed.reserve(off2.id, 1, user_id=uuid.uuid4(), now=NOW)
    sold, off3, _ = port(initial_stock=1, remaining_stock=0)
    with pytest.raises(OfferNotReservableError):
        await sold.reserve(off3.id, 1, user_id=uuid.uuid4(), now=NOW)


@pytest.mark.parametrize("missing", ["offer", "product", "store"])
async def test_interim_missing_is_not_found(missing):
    stock, offer, _ = port(**{missing: False})
    with pytest.raises(OfferNotFoundError):
        await stock.get_terms(uuid.uuid4())


async def test_lookup_adapter():
    service, _, _, repo, stock, *_ = build()
    lookup = OfferReservationLookup(repo)
    assert await lookup.has_reservations_for_offer(stock.offer_id) is False
    await service.create_reservation(uuid.uuid4(), stock.offer_id, 1)
    assert await lookup.has_reservations_for_offer(stock.offer_id) is True


async def test_canceller_adapter_delegates_without_commit():
    service, _, session, repo, stock, refunds, *_ = build()
    r, _ = await service.create_reservation(uuid.uuid4(), stock.offer_id, 1), None
    set_status(r, S.RESERVED)
    session.commits = 0
    n = await OfferReservationCanceller(service).cancel_all_for_offer(stock.offer_id, reason="중단")
    assert n == 1 and session.commits == 0 and len(refunds.calls) == 1
