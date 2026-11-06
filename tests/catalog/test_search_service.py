import uuid

import pytest

from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.product import Product
from catalog.domain.search import OfferSort
from tests.catalog.test_service import H, NOW, Ctx, FakeStoreInfo, FakeVisible, anyio_backend  # noqa: F401

pytestmark = pytest.mark.anyio


@pytest.fixture
def ctx():
    return Ctx()


def _store(ctx, name):
    info = ctx.stores.add(FakeStoreInfo(uuid.uuid4()))
    info.name = name
    return info


async def test_search_products_empty_visible_skips_repos(ctx):
    r = await ctx.service.search_products(
        keyword=None, category=None, lat=None, lng=None, radius_km=None, page=1, size=20
    )
    assert (r.items, r.total) == ([], 0)
    assert ctx.products.search_calls == [] and ctx.session.commits == 0


async def test_search_products_groups_by_store_in_stores_order_and_rounds(ctx):
    a, b = _store(ctx, "A"), _store(ctx, "B")
    ctx.stores.visible = [FakeVisible(b, 1.23456), FakeVisible(a, 2.0)]
    pa = await ctx.products.save(Product.register(a.id, "빵", 1000))
    pb1 = await ctx.products.save(Product.register(b.id, "케이크", 1000))
    pb2 = await ctx.products.save(Product.register(b.id, "과자", 1000))
    r = await ctx.service.search_products(
        keyword="  ", category="x", lat=37.0, lng=127.0, radius_km=None, page=1, size=20
    )
    assert ctx.stores.visible_calls == [(37.0, 127.0, 3.0)]  # 기본 반경 채움
    assert [h.store.id for h in r.items] == [b.id, a.id]  # stores가 준 순서
    assert r.items[0].distance_km == 1.23
    assert [sp.product.id for sp in r.items[0].products] == [pb2.id, pb1.id]  # name 순
    assert [sp.product.id for sp in r.items[1].products] == [pa.id]
    assert r.total == 2 and ctx.session.commits == 0
    kinds = [c[0] for c in ctx.products.search_calls]
    assert kinds == ["search_store_ids", "find_matching_in_stores"]
    assert ctx.products.search_calls[0][1] == [b.id, a.id]
    assert ctx.products.search_calls[0][2] is None  # 공백 키워드는 미지정


async def test_search_products_no_location_passes_none(ctx):
    a = _store(ctx, "A")
    ctx.stores.visible = [FakeVisible(a, None)]
    await ctx.products.save(Product.register(a.id, "빵", 1000))
    r = await ctx.service.search_products(
        keyword=None, category=None, lat=None, lng=None, radius_km=5, page=1, size=20
    )
    assert ctx.stores.visible_calls == [(None, None, None)]
    assert r.items[0].distance_km is None


async def test_search_products_empty_page_skips_second_query(ctx):
    a = _store(ctx, "A")
    ctx.stores.visible = [FakeVisible(a)]
    ctx.products.page_ids = []
    r = await ctx.service.search_products(
        keyword=None, category=None, lat=None, lng=None, radius_km=None, page=1, size=20
    )
    assert r.items == []
    assert [c[0] for c in ctx.products.search_calls] == ["search_store_ids"]


async def test_search_products_validation_errors(ctx):
    with pytest.raises(ValueError, match="lat과 lng는 함께 입력해야 합니다."):
        await ctx.service.search_products(
            keyword=None, category=None, lat=1.0, lng=None, radius_km=None, page=1, size=20
        )
    with pytest.raises(ValueError, match="검색어는 100자 이하여야 합니다."):
        await ctx.service.search_products(
            keyword="a" * 101, category=None, lat=None, lng=None, radius_km=None, page=1, size=20
        )
    assert ctx.stores.visible_calls == []


def _kw(**o):
    d = dict(lat=None, lng=None, radius_km=None, category=None, keyword=None,
             status=OfferStatus.ON_SALE, sort=OfferSort.SALES_END, page=1, size=20)
    d.update(o)
    return d


async def test_nearby_offers_empty_visible(ctx):
    r = await ctx.service.list_nearby_offers(**_kw())
    assert (r.items, r.total) == ([], 0)
    assert ctx.offers.search_calls == [] and ctx.session.commits == 0


async def test_nearby_offers_maps_store_name_distance_and_order(ctx):
    a = _store(ctx, "가게A")
    ctx.stores.visible = [FakeVisible(a, 0.456)]
    p = await ctx.products.save(Product.register(a.id, "빵", 1000))
    o = DiscountOffer(
        product_id=p.id, sale_price=500, initial_stock=5, sales_start=NOW - H,
        sales_end=NOW + H, pickup_start=NOW, pickup_end=NOW + 2 * H,
    )
    o.id = uuid.uuid4()
    ctx.offers.search_rows = [(o, p)]
    r = await ctx.service.list_nearby_offers(**_kw(lat=37.0, lng=127.0, sort=OfferSort.DISTANCE, keyword=" 빵 "))
    item = r.items[0]
    assert item.view.store_name == "가게A" and item.distance_km == 0.46
    assert item.view.status == OfferStatus.ON_SALE and item.view.discount_rate == 50
    call = ctx.offers.search_calls[0]
    assert call["store_ids"] == [a.id] and call["keyword"] == "빵" and call["sort"] == OfferSort.DISTANCE
    assert ctx.stores.visible_calls == [(37.0, 127.0, 3.0)] and ctx.session.commits == 0


async def test_nearby_offers_validation_order(ctx):
    with pytest.raises(ValueError, match="lat과 lng는 함께 입력해야 합니다."):
        await ctx.service.list_nearby_offers(**_kw(lat=1.0, sort=OfferSort.DISTANCE))
    with pytest.raises(ValueError, match="distance 정렬은 위치 정보가 필요합니다."):
        await ctx.service.list_nearby_offers(**_kw(sort=OfferSort.DISTANCE))
    assert ctx.stores.visible_calls == []
