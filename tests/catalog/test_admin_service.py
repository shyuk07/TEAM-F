"""관리자 연동 서비스 메서드와 정지 가시성 (admin.md 5.2·5.3, D17~D22, D34, C7, C8)."""

import inspect
import uuid
from typing import Protocol

import pytest

from catalog.domain.discount_offer import OfferStatus
from catalog.domain.exceptions import (
    OfferAlreadySuspendedError,
    OfferNotFoundError,
    OfferSalesEndedError,
    OfferSuspendedError,
    OpenOfferExistsError,
    ProductNotFoundError,
    StoreNotFoundError,
    StoreSuspendedError,
)
from catalog.domain.product import Product
from tests.catalog.test_service import H, NOW, Ctx, FakeStoreInfo

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def ctx():
    return Ctx()


async def open_offer(ctx, name="샌드위치", **kw):
    p = await ctx.product(name=name)
    view = await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data(**kw))
    ctx.session.commits = 0
    ctx.products.events.clear()
    return p, view.offer


# ── OfferAdminPort 구조적 일치 (admin.md 5.2) ──
class OfferAdminPort(Protocol):
    async def suspend_offer(self, offer_id, reason, *, now, commit: bool = True): ...

    async def end_all_sales_of_store(self, store_id, *, now, commit: bool = True) -> int: ...


def _shape(fn):
    sig = inspect.signature(fn)
    return [(n, p.kind, p.default) for n, p in sig.parameters.items() if n != "self"]


def test_catalog_service_satisfies_offer_admin_port_signatures(ctx):
    for name in ("suspend_offer", "end_all_sales_of_store"):
        assert _shape(getattr(ctx.service, name)) == _shape(getattr(OfferAdminPort, name)), name
        assert inspect.iscoroutinefunction(getattr(ctx.service, name))


# ── suspend_offer ──
async def test_suspend_offer_ok_commit_true(ctx):
    p, o = await open_offer(ctx)
    result = await ctx.service.suspend_offer(o.id, "  위생 문제 ", now=NOW)
    assert ctx.session.commits == 1
    assert o.is_suspended and o.status == OfferStatus.SUSPENDED and o.is_active
    assert (result.id, result.store_id, result.title) == (o.id, ctx.store.id, "샌드위치")
    assert result.status == OfferStatus.SUSPENDED
    assert (result.suspended_reason, result.suspended_at) == ("위생 문제", NOW)


async def test_suspend_offer_commit_false_does_not_commit(ctx):
    p, o = await open_offer(ctx)
    await ctx.service.suspend_offer(o.id, "x", now=NOW, commit=False)
    assert ctx.session.commits == 0 and o.is_suspended


async def test_suspend_offer_lock_order_product_then_offer(ctx):
    p, o = await open_offer(ctx)
    await ctx.service.suspend_offer(o.id, "x", now=NOW)
    assert ctx.products.events == ["product_lock", "offer_lock"]  # D34


async def test_suspend_offer_errors_do_not_commit(ctx):
    p, o = await open_offer(ctx)
    with pytest.raises(OfferNotFoundError, match="할인 판매를 찾을 수 없습니다."):
        await ctx.service.suspend_offer(uuid.uuid4(), "x", now=NOW)
    with pytest.raises(ValueError, match="정지 사유를 입력해 주세요."):
        await ctx.service.suspend_offer(o.id, " ", now=NOW)
    await ctx.service.suspend_offer(o.id, "x", now=NOW, commit=False)
    with pytest.raises(OfferAlreadySuspendedError):
        await ctx.service.suspend_offer(o.id, "y", now=NOW)
    assert ctx.session.commits == 0
    _, ended = await open_offer(ctx, name="b")
    ended.end_sale(NOW)
    with pytest.raises(OfferSalesEndedError):
        await ctx.service.suspend_offer(ended.id, "x", now=NOW)
    assert ctx.session.commits == 0


# ── end_all_sales_of_store ──
async def test_end_all_sales_ends_open_offers_and_counts(ctx):
    _, a = await open_offer(ctx, name="a")
    _, b = await open_offer(ctx, name="b")
    _, paused = await open_offer(ctx, name="c")
    paused.pause(NOW)
    _, sus = await open_offer(ctx, name="d")
    sus.suspend("x", NOW)
    _, expired = await open_offer(ctx, name="e")
    expired.sales_end = NOW - H  # 마감 경과(이미 진행 중 아님)
    logs = len(ctx.logs.items)
    n = await ctx.service.end_all_sales_of_store(ctx.store.id, now=NOW)
    assert n == 3 and ctx.session.commits == 1
    for o in (a, b, sus):
        assert not o.is_active and o.status == OfferStatus.CLOSED
    assert sus.suspended_reason == "x"  # 정지 이력 유지
    assert (a.remaining_stock, b.remaining_stock) == (10, 10) and len(ctx.logs.items) == logs  # D18
    assert expired.is_active  # 진행 중이 아닌 것은 건드리지 않음


async def test_end_all_sales_is_idempotent_and_zero_when_none(ctx):
    assert await ctx.service.end_all_sales_of_store(ctx.store.id, now=NOW) == 0
    await open_offer(ctx)
    assert await ctx.service.end_all_sales_of_store(ctx.store.id, now=NOW, commit=False) == 1
    assert await ctx.service.end_all_sales_of_store(ctx.store.id, now=NOW, commit=False) == 0
    assert ctx.session.commits == 0


async def test_end_all_sales_commit_flag_and_lock_order(ctx):
    await open_offer(ctx)
    await ctx.service.end_all_sales_of_store(ctx.store.id, now=NOW, commit=False)
    assert ctx.session.commits == 0
    assert ctx.products.events == ["products_lock_all", "offers_lock_open"]  # 상품 -> 할인 (D34)


async def test_end_all_sales_only_target_store(ctx):
    _, mine = await open_offer(ctx)
    other_store = ctx.stores.add(FakeStoreInfo(uuid.uuid4()))
    other_product = await ctx.products.save(Product.register(other_store.id, "남의 빵", 5000))
    other = (
        await ctx.service.register_offer(
            other_store.owner_id, other_product.id, ctx.offer_data(sale_price=2000)
        )
    ).offer
    assert await ctx.service.end_all_sales_of_store(ctx.store.id, now=NOW) == 1
    assert not mine.is_active and other.is_active


# ── 소유자 조작 차단 (D20) ──
async def test_owner_operations_blocked_on_suspended_offer(ctx):
    p, o = await open_offer(ctx)
    await ctx.service.suspend_offer(o.id, "x", now=NOW, commit=False)
    ops = [
        lambda: ctx.service.update_offer(ctx.owner, o.id, {"is_active": False}),
        lambda: ctx.service.update_offer(ctx.owner, o.id, {"is_active": True}),
        lambda: ctx.service.update_offer(ctx.owner, o.id, {"sale_price": 2000}),
        lambda: ctx.service.deactivate_offer(ctx.owner, o.id, "사유", False),
        lambda: ctx.service.adjust_stock(ctx.owner, o.id, 1, None),
        lambda: ctx.service.relist_offer(ctx.owner, o.id, ctx.offer_data()),
    ]
    logs = len(ctx.logs.items)
    for op in ops:
        with pytest.raises(OfferSuspendedError):
            await op()
    assert ctx.session.commits == 0 and len(ctx.logs.items) == logs
    assert o.is_active and o.is_suspended and o.remaining_stock == 10


async def test_suspended_offer_still_blocks_new_offer_on_same_product(ctx):  # D22
    p, o = await open_offer(ctx)
    o.suspend("x", NOW)
    with pytest.raises(OpenOfferExistsError):
        await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())
    assert await ctx.service.has_open_offers_for_store(ctx.store.id)


# ── 정지된 상점: 등록 가드 ──
async def test_suspended_store_blocks_registration(ctx):
    p = await ctx.product()
    old = (await ctx.service.register_offer(ctx.owner, p.id, ctx.offer_data())).offer
    ctx.session.commits = 0
    ctx.store.suspended_at = NOW
    with pytest.raises(StoreSuspendedError) as e:
        await ctx.service.create_product(ctx.owner, ctx.store.id, {"name": "x", "original_price": 1})
    assert e.value.error_code == "STORE_SUSPENDED"
    p2 = await ctx.product(name="b")
    with pytest.raises(StoreSuspendedError):
        await ctx.service.register_offer(ctx.owner, p2.id, ctx.offer_data())
    with pytest.raises(StoreSuspendedError):
        await ctx.service.relist_offer(ctx.owner, old.id, ctx.offer_data())
    assert ctx.session.commits == 0 and old.is_active


# ── 정지된 상점: 가시성 (C8) ──
async def test_suspended_store_hidden_from_non_owner_reads(ctx):
    p = await ctx.product()
    ctx.store.suspended_at = NOW
    for viewer in (None, uuid.uuid4()):
        with pytest.raises(StoreNotFoundError):
            await ctx.service.list_products(viewer, ctx.store.id, None, True, 1, 20)
        with pytest.raises(StoreNotFoundError):
            await ctx.service.get_product(viewer, p.id)
        with pytest.raises(StoreNotFoundError):
            await ctx.service.list_offers_by_store(viewer, ctx.store.id, None, 1, 20)
    page = await ctx.service.list_products(ctx.owner, ctx.store.id, None, True, 1, 20)
    assert page.total == 1
    assert (await ctx.service.get_product(ctx.owner, p.id)).product is p
    await ctx.service.list_offers_by_store(ctx.owner, ctx.store.id, None, 1, 20)
    assert ctx.session.commits == 0


async def test_suspended_store_visibility_check_precedes_inactive_check(ctx):
    await ctx.product()
    ctx.store.suspended_at = NOW
    with pytest.raises(StoreNotFoundError):  # 403이 아니라 404
        await ctx.service.list_products(uuid.uuid4(), ctx.store.id, None, False, 1, 20)


async def test_unsuspended_store_still_public(ctx):
    p = await ctx.product()
    assert (await ctx.service.list_products(None, ctx.store.id, None, True, 1, 20)).total == 1
    await ctx.service.get_product(None, p.id)
    await ctx.service.list_offers_by_store(None, ctx.store.id, None, 1, 20)


# ── 할인 상세 (C7) ──
async def test_offer_detail_suspended_offer_hidden_from_non_owner(ctx):
    p, o = await open_offer(ctx)
    o.suspend("x", NOW)
    for viewer in (None, uuid.uuid4()):
        with pytest.raises(OfferNotFoundError, match="할인 판매를 찾을 수 없습니다."):
            await ctx.service.get_offer_detail(viewer, o.id)
    d = await ctx.service.get_offer_detail(ctx.owner, o.id)
    assert d.view.status == OfferStatus.SUSPENDED and d.view.offer is o
    assert ctx.session.commits == 0


async def test_offer_detail_suspended_store_hides_offers_from_non_owner(ctx):
    p, o = await open_offer(ctx)
    ctx.store.suspended_at = NOW
    for viewer in (None, uuid.uuid4()):
        with pytest.raises(OfferNotFoundError, match="할인 판매를 찾을 수 없습니다."):
            await ctx.service.get_offer_detail(viewer, o.id)
    d = await ctx.service.get_offer_detail(ctx.owner, o.id)
    assert d.view.offer is o


async def test_offer_detail_ended_suspended_offer_is_public_closed(ctx):
    p, o = await open_offer(ctx)
    o.suspend("x", NOW)
    o.end_sale(NOW)
    d = await ctx.service.get_offer_detail(None, o.id)
    assert d.view.status == OfferStatus.CLOSED


async def test_offer_detail_public_when_not_suspended(ctx):
    p, o = await open_offer(ctx)
    assert (await ctx.service.get_offer_detail(None, o.id)).view.status == OfferStatus.ON_SALE
    with pytest.raises(OfferNotFoundError):
        await ctx.service.get_offer_detail(None, uuid.uuid4())
    with pytest.raises(ProductNotFoundError):
        await ctx.service.get_product(None, uuid.uuid4())
