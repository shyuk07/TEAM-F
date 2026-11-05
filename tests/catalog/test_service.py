import uuid
from datetime import datetime, timedelta, timezone

import pytest

from catalog.application.service import CatalogApplicationService
from catalog.domain.discount_offer import OPEN_OFFER_STATUSES, DiscountOffer, OfferStatus
from catalog.domain.exceptions import (
    NotStoreOwnerError,
    OfferAlreadyActiveError,
    OfferClosedError,
    OfferEndedError,
    OfferHasReservationsError,
    OfferNotFoundError,
    OpenOfferExistsError,
    PickedUpReservationExistsError,
    ProductAlreadyInactiveError,
    ProductHasOpenOfferError,
    ProductInactiveError,
    ProductNotFoundError,
    StoreClosedError,
    StoreNotApprovedError,
    StoreNotFoundError,
)
from catalog.domain.product import Product
from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository
from catalog.domain.repository.product_repository import ProductRepository
from catalog.domain.repository.stock_log_repository import StockLogRepository
from catalog.domain.service import Clock

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
H = timedelta(hours=1)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeSession:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


class FakeClock(Clock):
    def now(self):
        return NOW


class FakeStoreInfo:
    def __init__(self, owner_id, approval_at=NOW, closed_at=None, suspended_at=None):
        self.id = uuid.uuid4()
        self.owner_id = owner_id
        self.name = "상점A"
        self.pickup_address = "서울"
        self.latitude = 37.5
        self.longitude = 127.0
        self.approval_at = approval_at
        self.closed_at = closed_at
        self.suspended_at = suspended_at


class FakeStores:
    def __init__(self):
        self.items = {}

    def add(self, info):
        self.items[info.id] = info
        return info

    async def find_store_by_id(self, store_id):
        return self.items.get(store_id)

    async def find_stores_by_ids(self, ids):
        return [self.items[i] for i in ids if i in self.items]


class FakeProducts(ProductRepository):
    def __init__(self, events=None):
        self.items = {}
        self.locked = []
        self.events = events if events is not None else []

    async def find_by_id(self, product_id, for_update=False):
        if for_update:
            self.locked.append(product_id)
            self.events.append("product_lock")
        return self.items.get(product_id)

    async def find_by_store(self, store_id, *, category, is_active, page, size):
        rows = [
            p for p in self.items.values()
            if p.store_id == store_id and p.is_active == is_active
            and (category is None or p.category == category)
        ]
        return rows[(page - 1) * size : page * size], len(rows)

    async def find_all_by_store_for_update(self, store_id):
        self.events.append("products_lock_all")
        return sorted(
            (p for p in self.items.values() if p.store_id == store_id), key=lambda p: p.id
        )

    async def save(self, product):
        if product.id is None:
            product.id = uuid.uuid4()
        self.items[product.id] = product
        return product


class FakeOffers(DiscountOfferRepository):
    def __init__(self):
        self.items = {}
        self.events = []
        self.last_statuses = None
        self.products = None

    async def find_by_id(self, offer_id, for_update=False):
        if for_update:
            self.events.append("offer_lock")
        return self.items.get(offer_id)

    async def find_with_product(self, offer_id):
        offer = self.items.get(offer_id)
        if offer is None or self.products is None:
            return None
        product = self.products.items.get(offer.product_id)
        return (offer, product) if product else None

    async def find_open_by_product(self, product_id, now):
        return next(
            (o for o in self.items.values() if o.product_id == product_id and o.is_open(now)), None
        )

    async def exists_open_by_store(self, store_id, now):
        return any(o.is_open(now) for o in self.items.values())

    async def find_open_by_store_for_update(self, store_id, now):
        self.events.append("offers_lock_open")
        pids = {p.id for p in self.products.items.values() if p.store_id == store_id}
        return sorted(
            (o for o in self.items.values() if o.product_id in pids and o.is_open(now)),
            key=lambda o: o.id,
        )

    async def find_by_store(self, store_id, *, statuses, now, page, size):
        self.last_statuses = tuple(statuses)
        return [], 0

    async def save(self, offer):
        if offer.id is None:
            offer.id = uuid.uuid4()
        self.items[offer.id] = offer
        return offer


class FakeReservations:
    def __init__(self):
        self.has = False

    async def has_reservations_for_offer(self, offer_id):
        return self.has


class FakeReservationCancel:
    def __init__(self, events=None):
        self.calls = []
        self.count = 0
        self.error = None
        self.events = events if events is not None else []

    async def cancel_all_for_offer(self, offer_id, *, reason):
        self.events.append("port")
        self.calls.append((offer_id, reason))
        if self.error is not None:
            raise self.error
        return self.count


class FakeStockLogs(StockLogRepository):
    def __init__(self):
        self.items = []

    async def add(self, log):
        log.id = uuid.uuid4()
        self.items.append(log)
        return log


class Ctx:
    def __init__(self):
        self.session = FakeSession()
        self.stores = FakeStores()
        self.products = FakeProducts()
        self.offers = FakeOffers()
        self.offers.events = self.products.events
        self.offers.products = self.products
        self.reservations = FakeReservations()
        self.cancel = FakeReservationCancel(self.products.events)
        self.logs = FakeStockLogs()
        self.service = CatalogApplicationService(
            session=self.session, stores=self.stores, products=self.products,
            offers=self.offers, stock_logs=self.logs, clock=FakeClock(),
            reservations=self.reservations, reservation_cancel=self.cancel,
        )
        self.owner = uuid.uuid4()
        self.store = self.stores.add(FakeStoreInfo(self.owner))

    async def product(self, **kw):
        p = Product.register(self.store.id, kw.pop("name", "샌드위치"), kw.pop("price", 6000), **kw)
        return await self.products.save(p)

    def offer_data(self, **kw):
        d = dict(
            sale_price=3000, initial_stock=10, sales_start=None,
            sales_end=NOW + 2 * H, pickup_start=NOW + H, pickup_end=NOW + 3 * H,
        )
        d.update(kw)
        return d


@pytest.fixture
def ctx():
    return Ctx()


# ── #1 ──
async def test_create_product(ctx):
    p = await ctx.service.create_product(ctx.owner, ctx.store.id, {"name": "빵", "original_price": 1000})
    assert p.id is not None and p.is_active and ctx.session.commits == 1


async def test_create_product_errors(ctx):
    with pytest.raises(StoreNotFoundError):
        await ctx.service.create_product(ctx.owner, uuid.uuid4(), {"name": "x", "original_price": 1})
    with pytest.raises(NotStoreOwnerError, match="본인 상점에만 상품을 등록할 수 있습니다."):
        await ctx.service.create_product(uuid.uuid4(), ctx.store.id, {"name": "x", "original_price": 1})
    with pytest.raises(ValueError, match="정상 가격은 0보다 커야 합니다."):
        await ctx.service.create_product(ctx.owner, ctx.store.id, {"name": "x", "original_price": 0})
    ctx.store.approval_at = None
    with pytest.raises(StoreNotApprovedError):
        await ctx.service.create_product(ctx.owner, ctx.store.id, {"name": "x", "original_price": 1})
    ctx.store.approval_at = NOW
    ctx.store.closed_at = NOW
    with pytest.raises(StoreClosedError):
        await ctx.service.create_product(ctx.owner, ctx.store.id, {"name": "x", "original_price": 1})
    assert ctx.session.commits == 0 and not ctx.products.items


# ── #5 ──
async def test_update_product(ctx):
    p = await ctx.product()
    out = await ctx.service.update_product(ctx.owner, p.id, {"name": "새"})
    assert out.name == "새" and ctx.session.commits == 1 and p.id in ctx.products.locked


async def test_update_product_errors(ctx):
    p = await ctx.product()
    with pytest.raises(ProductNotFoundError):
        await ctx.service.update_product(ctx.owner, uuid.uuid4(), {"name": "a"})
    with pytest.raises(NotStoreOwnerError, match="본인 상점의 상품만 수정할 수 있습니다."):
        await ctx.service.update_product(uuid.uuid4(), p.id, {"name": "a"})
    with pytest.raises(ValueError, match="수정할 항목이 없습니다."):
        await ctx.service.update_product(ctx.owner, p.id, {})
    await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    ctx.session.commits = 0
    with pytest.raises(ValueError, match="진행 중인 할인 가격보다 커야"):
        await ctx.service.update_product(ctx.owner, p.id, {"original_price": 3000})
    assert ctx.session.commits == 0


# ── #6 상품 노출 중단 ──
async def test_deactivate(ctx):
    p = await ctx.product()
    out = await ctx.service.deactivate_product(ctx.owner, p.id)
    assert not out.is_active and ctx.session.commits == 1


async def test_deactivate_with_open_offer(ctx):
    p = await ctx.product()
    await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    before = ctx.session.commits
    with pytest.raises(ProductHasOpenOfferError):
        await ctx.service.deactivate_product(ctx.owner, p.id)
    assert p.is_active and ctx.session.commits == before


async def test_deactivate_already_inactive(ctx):
    p = await ctx.product()
    await ctx.service.deactivate_product(ctx.owner, p.id)
    with pytest.raises(ProductAlreadyInactiveError, match="이미 비활성화된 상품입니다."):
        await ctx.service.deactivate_product(ctx.owner, p.id)


async def test_deactivate_forbidden(ctx):
    p = await ctx.product()
    with pytest.raises(NotStoreOwnerError, match="본인 상점의 상품만 변경할 수 있습니다."):
        await ctx.service.deactivate_product(uuid.uuid4(), p.id)


# ── #12 할인 판매 중단 (16.5) ──
async def _deactivate(ctx, offer_id, reason="재료 소진", cancel=False, user=None):
    return await ctx.service.deactivate_offer(user or ctx.owner, offer_id, reason, cancel)


async def test_deactivate_offer_without_cancel(ctx):
    p, o = await _open_offer(ctx)
    n_logs = len(ctx.logs.items)
    result = await _deactivate(ctx, o.id)
    assert not o.is_active and o.status == OfferStatus.CLOSED
    assert result.view.offer is o and result.view.status == OfferStatus.CLOSED
    assert p.is_active  # 상품 불변
    assert o.remaining_stock == 10 and len(ctx.logs.items) == n_logs  # D40
    assert ctx.cancel.calls == [] and result.cancelled_reservation_count == 0
    assert ctx.session.commits == 1


async def test_deactivate_offer_with_cancel(ctx):
    p, o = await _open_offer(ctx)
    ctx.cancel.count = 3
    result = await _deactivate(ctx, o.id, reason="사고", cancel=True)
    assert ctx.cancel.calls == [(o.id, "사고")]
    assert result.cancelled_reservation_count == 3 and ctx.session.commits == 1
    assert not o.is_active


async def test_deactivate_offer_port_error_propagates_without_commit(ctx):
    p, o = await _open_offer(ctx)
    ctx.cancel.error = PickedUpReservationExistsError()
    with pytest.raises(PickedUpReservationExistsError):
        await _deactivate(ctx, o.id, cancel=True)
    assert ctx.session.commits == 0  # 원자성: commit되지 않아 세션 종료 시 롤백


async def test_deactivate_offer_already_closed_skips_port(ctx):
    p, o = await _open_offer(ctx)
    await _deactivate(ctx, o.id)
    ctx.session.commits = 0
    with pytest.raises(OfferClosedError, match="이미 중단된 할인입니다."):
        await _deactivate(ctx, o.id, cancel=True)
    assert ctx.cancel.calls == [] and ctx.session.commits == 0


async def test_deactivate_offer_already_closed_by_other_owner_is_forbidden(ctx):
    p, o = await _open_offer(ctx)
    await _deactivate(ctx, o.id)
    ctx.session.commits = 0
    # 소유권 검사가 상태 검사(400)보다 먼저다
    with pytest.raises(NotStoreOwnerError):
        await _deactivate(ctx, o.id, cancel=True, user=uuid.uuid4())
    assert ctx.cancel.calls == [] and ctx.session.commits == 0


async def test_deactivate_offer_after_sales_end_allowed(ctx):
    p, o = await _open_offer(ctx)
    o.sales_end = NOW - H  # 마감 지난 활성 할인 (Q24 A)
    assert o.is_active
    result = await _deactivate(ctx, o.id, cancel=True)
    assert not o.is_active and result.view.status == OfferStatus.CLOSED
    assert ctx.session.commits == 1


async def test_deactivate_offer_lock_order(ctx):
    p, o = await _open_offer(ctx)
    await _deactivate(ctx, o.id, cancel=True)
    assert ctx.products.events == ["product_lock", "offer_lock", "port"]


async def test_deactivate_offer_not_found_and_forbidden(ctx):
    p, o = await _open_offer(ctx)
    with pytest.raises(OfferNotFoundError, match="할인 판매를 찾을 수 없습니다."):
        await _deactivate(ctx, uuid.uuid4(), cancel=True)
    with pytest.raises(NotStoreOwnerError, match="본인 상점의 할인만 중단할 수 있습니다."):
        await _deactivate(ctx, o.id, cancel=True, user=uuid.uuid4())
    assert ctx.session.commits == 0 and ctx.cancel.calls == [] and o.is_active


async def test_deactivate_offer_allowed_for_closed_store(ctx):
    p, o = await _open_offer(ctx)
    ctx.store.closed_at = NOW
    result = await _deactivate(ctx, o.id)
    assert not o.is_active and result.cancelled_reservation_count == 0


# ── #7 ──
async def test_register_offer(ctx):
    p = await ctx.product()
    view = await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    assert view.status == OfferStatus.ON_SALE and view.discount_rate == 50
    assert view.store_name == "상점A" and not view.is_sold_out
    assert ctx.session.commits == 1
    (log,) = ctx.logs.items
    assert log.amount == 10 and log.reason == "최초 입고" and log.user_id == ctx.owner
    assert log.offer_id == view.offer.id


async def test_register_offer_errors(ctx):
    p = await ctx.product()
    with pytest.raises(ProductNotFoundError):
        await ctx.service.register_offer(ctx.owner, uuid.uuid4(), ctx.offer_data())
    with pytest.raises(NotStoreOwnerError, match="본인 상점의 상품만 할인 등록할 수 있습니다."):
        await ctx.service.register_offer(uuid.uuid4(), p.id, ctx.offer_data())
    with pytest.raises(ValueError, match="할인 가격은 정상 가격보다 낮아야 합니다."):
        await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data(sale_price=6000))
    await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    with pytest.raises(OpenOfferExistsError, match="이미 진행 중인 할인 판매가 있습니다."):
        await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    assert ctx.session.commits == 1 and len(ctx.logs.items) == 1


async def test_register_offer_inactive_product_and_closed_store(ctx):
    p = await ctx.product()
    p.is_active = False
    with pytest.raises(ProductInactiveError):
        await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    ctx.store.closed_at = NOW
    with pytest.raises(StoreClosedError):
        await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())


async def test_register_offer_scheduled(ctx):
    p = await ctx.product()
    view = await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data(sales_start=NOW + H // 2))
    assert view.status == OfferStatus.SCHEDULED


# ── #13 ──
async def test_relist(ctx):
    p = await ctx.product()
    old = (await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())).offer
    ctx.session.commits = 0
    view = await ctx.service.relist_offer(ctx.owner, old.id, ctx.offer_data(sale_price=2500, initial_stock=5))
    assert not old.is_active and old.status == OfferStatus.CLOSED
    assert view.offer.id != old.id and view.offer.sale_price == 2500
    assert ctx.session.commits == 1  # 한 트랜잭션
    assert ctx.logs.items[-1].offer_id == view.offer.id and ctx.logs.items[-1].amount == 5


async def test_relist_failure_does_not_close_old(ctx):
    p = await ctx.product()
    old = (await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())).offer
    ctx.session.commits = 0
    with pytest.raises(ValueError, match="할인 가격은 정상 가격보다 낮아야 합니다."):
        await ctx.service.relist_offer(ctx.owner, old.id, ctx.offer_data(sale_price=6000))
    assert old.is_active and ctx.session.commits == 0 and len(ctx.logs.items) == 1


async def test_relist_errors(ctx):
    p = await ctx.product()
    old = (await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())).offer
    with pytest.raises(OfferNotFoundError):
        await ctx.service.relist_offer(ctx.owner, uuid.uuid4(), ctx.offer_data())
    with pytest.raises(NotStoreOwnerError, match="본인 상점의 할인만 재등록할 수 있습니다."):
        await ctx.service.relist_offer(uuid.uuid4(), old.id, ctx.offer_data())
    await ctx.service.relist_offer(ctx.owner, old.id, ctx.offer_data())
    with pytest.raises(OfferClosedError, match="이미 중단된 할인은 재등록할 수 없습니다."):
        await ctx.service.relist_offer(ctx.owner, old.id, ctx.offer_data())


# ── #14 ──
async def test_adjust_stock(ctx):
    p = await ctx.product()
    offer = (await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data(initial_stock=3))).offer
    ctx.session.commits = 0
    res = await ctx.service.adjust_stock(ctx.owner, offer.id, -3, "파손")
    assert res.status == OfferStatus.SOLD_OUT and offer.remaining_stock == 0
    assert ctx.session.commits == 1
    log = ctx.logs.items[-1]
    assert log.amount == -3 and log.reason == "파손" and log.id == res.log_id
    res = await ctx.service.adjust_stock(ctx.owner, offer.id, 2, None)
    assert res.status == OfferStatus.ON_SALE and offer.initial_stock == 5
    assert ctx.logs.items[-1].amount == 2


async def test_adjust_stock_errors(ctx):
    p = await ctx.product()
    offer = (await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())).offer
    with pytest.raises(OfferNotFoundError):
        await ctx.service.adjust_stock(ctx.owner, uuid.uuid4(), 1, None)
    with pytest.raises(NotStoreOwnerError, match="본인 상점의 재고만 조정할 수 있습니다."):
        await ctx.service.adjust_stock(uuid.uuid4(), offer.id, 1, None)
    ctx.session.commits = 0
    with pytest.raises(ValueError):
        await ctx.service.adjust_stock(ctx.owner, offer.id, 0, None)
    with pytest.raises(ValueError):
        await ctx.service.adjust_stock(ctx.owner, offer.id, -11, None)
    assert ctx.session.commits == 0 and offer.remaining_stock == 10 and len(ctx.logs.items) == 1


# ── 읽기 ──
async def test_list_products_active_public(ctx):
    await ctx.product(name="a")
    inactive = await ctx.product(name="b")
    inactive.is_active = False
    page = await ctx.service.list_products(None, ctx.store.id, None, True, 1, 20)
    assert [p.name for p in page.items] == ["a"] and page.total == 1
    assert ctx.session.commits == 0  # 읽기는 commit하지 않음


async def test_list_products_inactive_owner_only(ctx):
    p = await ctx.product()
    p.is_active = False
    for viewer in (None, uuid.uuid4()):
        with pytest.raises(NotStoreOwnerError, match="본인 상점의 비활성 상품만 조회할 수 있습니다."):
            await ctx.service.list_products(viewer, ctx.store.id, None, False, 1, 20)
    page = await ctx.service.list_products(ctx.owner, ctx.store.id, None, False, 1, 20)
    assert page.total == 1
    with pytest.raises(StoreNotFoundError):
        await ctx.service.list_products(None, uuid.uuid4(), None, True, 1, 20)


async def test_get_product(ctx):
    p = await ctx.product()
    view = await ctx.service.get_product(None, p.id)
    assert view.store_name == "상점A" and view.pickup_address == "서울"
    p.is_active = False
    with pytest.raises(ProductNotFoundError):
        await ctx.service.get_product(None, p.id)
    with pytest.raises(ProductNotFoundError):
        await ctx.service.get_product(uuid.uuid4(), p.id)
    assert (await ctx.service.get_product(ctx.owner, p.id)).product is p
    with pytest.raises(ProductNotFoundError):
        await ctx.service.get_product(None, uuid.uuid4())


async def test_has_open_offers_for_store(ctx):
    p = await ctx.product()
    assert not await ctx.service.has_open_offers_for_store(ctx.store.id)
    await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    assert await ctx.service.has_open_offers_for_store(ctx.store.id)
    assert not await ctx.service.has_open_offers_for_store(ctx.store.id, now=NOW + 5 * H)


# ── #9 목록 기본 상태 (D25) ──
async def test_list_offers_default_statuses(ctx):
    await ctx.service.list_offers_by_store(None, ctx.store.id, None, 1, 20)
    assert ctx.offers.last_statuses == OPEN_OFFER_STATUSES
    await ctx.service.list_offers_by_store(None, ctx.store.id, [], 1, 20)
    assert ctx.offers.last_statuses == OPEN_OFFER_STATUSES


async def test_list_offers_dedup_and_explicit(ctx):
    S = OfferStatus
    await ctx.service.list_offers_by_store(None, ctx.store.id, [S.CLOSED, S.ON_SALE, S.CLOSED], 1, 20)
    assert ctx.offers.last_statuses == (S.CLOSED, S.ON_SALE)
    await ctx.service.list_offers_by_store(None, ctx.store.id, [S.ON_SALE], 1, 20)
    assert ctx.offers.last_statuses == (S.ON_SALE,)
    with pytest.raises(StoreNotFoundError):
        await ctx.service.list_offers_by_store(None, uuid.uuid4(), None, 1, 20)


# ── #11 할인 수정 (D26~D30) ──
async def _open_offer(ctx, **kw):
    p = await ctx.product()
    view = await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data(**kw))
    ctx.session.commits = 0
    ctx.products.events.clear()
    return p, view.offer


async def test_update_offer_fields(ctx):
    p, o = await _open_offer(ctx)
    view = await ctx.service.update_offer(ctx.owner, o.id, {"sale_price": 2000, "initial_stock": 15})
    assert o.sale_price == 2000 and o.remaining_stock == 15 and view.status == OfferStatus.ON_SALE
    assert ctx.session.commits == 1
    assert ctx.logs.items[-1].amount == 5 and ctx.logs.items[-1].reason == "할인 수정"
    assert ctx.products.events[:2] == ["product_lock", "offer_lock"]  # 잠금 순서


async def test_update_offer_no_stock_log_when_stock_unchanged(ctx):
    p, o = await _open_offer(ctx)
    n = len(ctx.logs.items)
    await ctx.service.update_offer(ctx.owner, o.id, {"sale_price": 2500})
    assert len(ctx.logs.items) == n and ctx.session.commits == 1


async def test_update_offer_errors(ctx):
    p, o = await _open_offer(ctx)
    with pytest.raises(OfferNotFoundError):
        await ctx.service.update_offer(ctx.owner, uuid.uuid4(), {"sale_price": 1})
    with pytest.raises(NotStoreOwnerError, match="본인 상점의 할인만 수정할 수 있습니다."):
        await ctx.service.update_offer(uuid.uuid4(), o.id, {"sale_price": 1})
    ctx.reservations.has = True
    with pytest.raises(OfferHasReservationsError):
        await ctx.service.update_offer(ctx.owner, o.id, {"sale_price": 2000})
    ctx.reservations.has = False
    with pytest.raises(ValueError, match="정상 가격보다 낮아야"):
        await ctx.service.update_offer(ctx.owner, o.id, {"sale_price": 6000})
    with pytest.raises(ValueError, match="수정할 항목이 없습니다."):
        await ctx.service.update_offer(ctx.owner, o.id, {})
    with pytest.raises(ValueError, match="null"):
        await ctx.service.update_offer(ctx.owner, o.id, {"is_active": None})
    assert ctx.session.commits == 0 and o.sale_price == 3000


async def test_update_offer_pause_and_resume(ctx):
    p, o = await _open_offer(ctx)
    view = await ctx.service.update_offer(ctx.owner, o.id, {"is_active": False})
    assert not o.is_active and view.status == OfferStatus.CLOSED and ctx.session.commits == 1
    with pytest.raises(OfferClosedError):
        await ctx.service.update_offer(ctx.owner, o.id, {"is_active": False})
    with pytest.raises(OfferClosedError, match="종료된 할인은 수정할 수 없습니다."):
        await ctx.service.update_offer(ctx.owner, o.id, {"sale_price": 2000})
    view = await ctx.service.update_offer(ctx.owner, o.id, {"is_active": True})
    assert o.is_active and view.status == OfferStatus.ON_SALE
    with pytest.raises(OfferAlreadyActiveError):
        await ctx.service.update_offer(ctx.owner, o.id, {"is_active": True})


async def test_resume_blocked_by_other_open_offer_and_closed_store(ctx):
    p, o = await _open_offer(ctx)
    await ctx.service.update_offer(ctx.owner, o.id, {"is_active": False})
    await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    with pytest.raises(OpenOfferExistsError):
        await ctx.service.update_offer(ctx.owner, o.id, {"is_active": True})
    ctx.store.closed_at = NOW
    with pytest.raises(StoreClosedError, match="폐점된 상점에서는 할인을 재개할 수 없습니다."):
        await ctx.service.update_offer(ctx.owner, o.id, {"is_active": True})


async def test_resume_inactive_product(ctx):
    p, o = await _open_offer(ctx)
    await ctx.service.update_offer(ctx.owner, o.id, {"is_active": False})
    p.is_active = False
    with pytest.raises(ProductInactiveError, match="비활성화된 상품의 할인은 재개할 수 없습니다."):
        await ctx.service.update_offer(ctx.owner, o.id, {"is_active": True})


# ── #10 할인 상세 ──
async def test_offer_detail_ok_and_no_commit():
    from catalog.domain.discount_offer import CANCEL_POLICY_DESCRIPTION, OFFER_NOTICE

    c = Ctx()
    p = await c.product(description="식빵", product_image=["https://e.com/a.jpg"])
    o = await c.service.register_offer(c.owner, p.id, c.offer_data())
    commits = c.session.commits
    c.products.locked.clear()
    d = await c.service.get_offer_detail(None, o.offer.id)
    assert c.session.commits == commits and not c.products.locked
    assert d.view.offer.id == o.offer.id
    assert d.description == "식빵" and d.product_image == ["https://e.com/a.jpg"]
    assert (d.pickup_address, d.latitude, d.longitude) == ("서울", 37.5, 127.0)
    assert d.notice == OFFER_NOTICE
    assert d.cancel_policy.cancellable_until == o.offer.pickup_start - H
    assert d.cancel_policy.description == CANCEL_POLICY_DESCRIPTION


async def test_offer_detail_not_found_and_store_missing():
    c = Ctx()
    with pytest.raises(OfferNotFoundError):
        await c.service.get_offer_detail(None, uuid.uuid4())
    p = await c.product()
    o = await c.service.register_offer(c.owner, p.id, c.offer_data())
    c.stores.items.clear()
    with pytest.raises(OfferNotFoundError, match="할인 판매를 찾을 수 없습니다."):
        await c.service.get_offer_detail(None, o.offer.id)


async def test_offer_detail_visible_when_closed_product_inactive_store_closed_no_coords():
    c = Ctx()
    p = await c.product()
    o = await c.service.register_offer(c.owner, p.id, c.offer_data())
    o.offer.close(NOW)
    p.is_active = False
    c.store.closed_at = NOW
    c.store.latitude = None
    c.store.longitude = None
    d = await c.service.get_offer_detail(None, o.offer.id)
    assert d.view.status == OfferStatus.CLOSED and d.view.offer.is_active is False
    assert d.latitude is None and d.longitude is None and d.description is None
