import uuid
from datetime import datetime, timedelta, timezone

import pytest

from catalog.application.service import CatalogApplicationService
from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.exceptions import (
    NotStoreOwnerError,
    OfferClosedError,
    OfferNotFoundError,
    OpenOfferExistsError,
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
    def __init__(self, owner_id, approval_at=NOW, closed_at=None):
        self.id = uuid.uuid4()
        self.owner_id = owner_id
        self.name = "상점A"
        self.pickup_address = "서울"
        self.approval_at = approval_at
        self.closed_at = closed_at


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
    def __init__(self):
        self.items = {}
        self.locked = []

    async def find_by_id(self, product_id, for_update=False):
        if for_update:
            self.locked.append(product_id)
        return self.items.get(product_id)

    async def find_by_store(self, store_id, *, category, is_active, page, size):
        rows = [
            p for p in self.items.values()
            if p.store_id == store_id and p.is_active == is_active
            and (category is None or p.category == category)
        ]
        return rows[(page - 1) * size : page * size], len(rows)

    async def save(self, product):
        if product.id is None:
            product.id = uuid.uuid4()
        self.items[product.id] = product
        return product


class FakeOffers(DiscountOfferRepository):
    def __init__(self):
        self.items = {}

    async def find_by_id(self, offer_id, for_update=False):
        return self.items.get(offer_id)

    async def find_open_by_product(self, product_id, now):
        return next(
            (o for o in self.items.values() if o.product_id == product_id and o.is_open(now)), None
        )

    async def exists_open_by_store(self, store_id, now):
        return any(o.is_open(now) for o in self.items.values())

    async def find_by_store(self, store_id, *, status, now, page, size):
        raise NotImplementedError

    async def save(self, offer):
        if offer.id is None:
            offer.id = uuid.uuid4()
        self.items[offer.id] = offer
        return offer


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
        self.logs = FakeStockLogs()
        self.service = CatalogApplicationService(
            session=self.session, stores=self.stores, products=self.products,
            offers=self.offers, stock_logs=self.logs, clock=FakeClock(),
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


# ── #6 ──
async def test_deactivate(ctx):
    p = await ctx.product()
    out = await ctx.service.deactivate_product(ctx.owner, p.id)
    assert not out.is_active and ctx.session.commits == 1


async def test_deactivate_with_open_offer(ctx):
    p = await ctx.product()
    await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    with pytest.raises(ProductHasOpenOfferError):
        await ctx.service.deactivate_product(ctx.owner, p.id)
    assert p.is_active


async def test_deactivate_forbidden(ctx):
    p = await ctx.product()
    with pytest.raises(NotStoreOwnerError, match="본인 상점의 상품만 변경할 수 있습니다."):
        await ctx.service.deactivate_product(uuid.uuid4(), p.id)


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
    await ctx.service.deactivate_product(ctx.owner, p.id)
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
    await ctx.service.deactivate_product(ctx.owner, inactive.id)
    page = await ctx.service.list_products(None, ctx.store.id, None, True, 1, 20)
    assert [p.name for p in page.items] == ["a"] and page.total == 1
    assert ctx.session.commits == 1  # 읽기는 commit하지 않음 (deactivate의 1회만)


async def test_list_products_inactive_owner_only(ctx):
    p = await ctx.product()
    await ctx.service.deactivate_product(ctx.owner, p.id)
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
    await ctx.service.deactivate_product(ctx.owner, p.id)
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
