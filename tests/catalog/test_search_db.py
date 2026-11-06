import uuid
from datetime import datetime, timedelta, timezone

import pytest

from catalog.domain.discount_offer import OfferStatus
from catalog.domain.search import OfferSort
from catalog.infrastructure.models import DiscountOfferModel, ProductModel
from catalog.infrastructure.repositories import (
    SqlAlchemyDiscountOfferRepository,
    SqlAlchemyProductRepository,
)
from stores.infrastructure.models import StoreModel
from tests.catalog.test_api_db import (
    make_offer,
    make_product,
    owner_with_store,
    set_product_inactive,
)

pytestmark = [pytest.mark.db, pytest.mark.anyio]

LAT, LNG = 37.4979, 127.0276  # FakeGeocoder 기본 좌표
H = timedelta(hours=1)


async def set_store(c, store_id, **cols):
    async with c.session_factory() as s:
        m = await s.get(StoreModel, uuid.UUID(store_id))
        for k, v in cols.items():
            setattr(m, k, v)
        await s.commit()


async def set_offer(c, offer_id, **cols):
    async with c.session_factory() as s:
        m = await s.get(DiscountOfferModel, uuid.UUID(offer_id))
        for k, v in cols.items():
            setattr(m, k, v)
        await s.commit()


# ── #3 상품 검색 ──
async def test_search_products_public_shape_and_grouping(client):
    token, sid = await owner_with_store(client)
    p1 = await make_product(client, token, sid, name="모둠 식빵")
    p2 = await make_product(client, token, sid, name="식빵 샌드")
    await make_product(client, token, sid, name="우유")
    await make_offer(client, token, p1["id"])
    r = await client.get("/v1/products", params={"keyword": "식빵"})  # 인증 헤더 없음
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"items", "page", "size", "total"}
    assert body["total"] == 1 and body["page"] == 1 and body["size"] == 20
    item = body["items"][0]
    assert set(item) == {"store", "distance", "unit", "products"}
    assert set(item["store"]) == {"id", "name", "pickup_address", "latitude", "longitude"}
    assert item["distance"] is None and item["unit"] == "km"
    assert [p["id"] for p in item["products"]] == sorted(
        [p1["id"], p2["id"]], key=lambda i: ("모둠 식빵" if i == p1["id"] else "식빵 샌드", i)
    )
    assert set(item["products"][0]) == {
        "id", "store_id", "name", "category", "description", "original_price",
        "is_active", "product_image", "has_active_offer",
    }
    flags = {p["id"]: p["has_active_offer"] for p in item["products"]}
    assert flags == {p1["id"]: True, p2["id"]: False}


async def test_search_products_exposure_filters(client):
    t1, s1 = await owner_with_store(client, "a@t.com")
    t2, s2 = await owner_with_store(client, "b@t.com")
    t3, s3 = await owner_with_store(client, "c@t.com")
    for t, s in [(t1, s1), (t2, s2), (t3, s3)]:
        await make_product(client, t, s, name="빵")
    hidden = await make_product(client, t1, s1, name="빵숨김")
    await set_product_inactive(client, hidden["id"])
    await set_store(client, s2, closed_at=datetime.now(timezone.utc))
    await set_store(client, s3, suspended_at=datetime.now(timezone.utc), suspended_reason="r")
    r = await client.get("/v1/products", params={"keyword": "빵"})
    body = r.json()
    assert body["total"] == 1 and body["items"][0]["store"]["id"] == s1
    assert [p["name"] for p in body["items"][0]["products"]] == ["빵"]


async def test_search_products_location_and_radius(client):
    t1, near = await owner_with_store(client, "n@t.com")
    t2, far = await owner_with_store(client, "f@t.com")
    t3, nocoord = await owner_with_store(client, "x@t.com")
    for t, s in [(t1, near), (t2, far), (t3, nocoord)]:
        await make_product(client, t, s, name="빵")
    await set_store(client, far, latitude=LAT + 0.1)  # 약 11km
    await set_store(client, nocoord, latitude=None, longitude=None)
    r = await client.get("/v1/products", params={"lat": LAT, "lng": LNG})
    ids = [i["store"]["id"] for i in r.json()["items"]]
    assert ids == [near]  # 반경 3km 기본, 좌표 없는 상점 제외
    assert r.json()["items"][0]["distance"] == 0.0
    r = await client.get("/v1/products", params={"lat": LAT, "lng": LNG, "radius_km": 20})
    assert [i["store"]["id"] for i in r.json()["items"]] == [near, far]
    assert r.json()["items"][1]["distance"] == pytest.approx(11.12, abs=0.05)
    r = await client.get("/v1/products")  # 위치 미지정: 전체, distance null
    body = r.json()
    assert body["total"] == 3 and all(i["distance"] is None for i in body["items"])


async def test_search_products_total_counts_stores_and_paginates(client):
    ids = []
    for n in range(3):
        t, s = await owner_with_store(client, f"s{n}@t.com")
        for k in range(3):
            await make_product(client, t, s, name=f"빵{k}")
        ids.append(s)
    r = await client.get("/v1/products", params={"size": 2, "page": 2})
    body = r.json()
    assert body["total"] == 3 and len(body["items"]) == 1
    assert len(body["items"][0]["products"]) == 3


async def test_search_products_errors(client):
    for params, msg in [
        ({"lat": 37.0}, "lat과 lng는 함께 입력해야 합니다."),
        ({"lng": 127.0}, "lat과 lng는 함께 입력해야 합니다."),
    ]:
        r = await client.get("/v1/products", params=params)
        assert r.status_code == 400
        assert r.json() == {"success": False, "error_code": "VALIDATION_ERROR", "message": msg}
    for params in [
        {"lat": 37, "lng": 127, "radius_km": 0.09},
        {"lat": 37, "lng": 127, "radius_km": 20.1},
        {"lat": 91, "lng": 127},
        {"page": 0},
        {"size": 101},
    ]:
        r = await client.get("/v1/products", params=params)
        assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR", params
    r = await client.get("/v1/products", params={"keyword": "없는상품"})
    assert r.status_code == 200 and r.json()["items"] == [] and r.json()["total"] == 0


async def test_search_products_coexists_with_detail(client):
    t, s = await owner_with_store(client)
    p = await make_product(client, t, s)
    assert (await client.get("/v1/products")).status_code == 200
    assert (await client.get(f"/v1/products/{p['id']}")).status_code == 200


async def test_keyword_escape_and_case_insensitive(client):
    t, s = await owner_with_store(client)
    await make_product(client, t, s, name="100% 주스")
    await make_product(client, t, s, name="a_b")
    await make_product(client, t, s, name="axb")
    await make_product(client, t, s, name="Bread", description="back\\slash")
    async def names(kw):
        r = await client.get("/v1/products", params={"keyword": kw})
        return sorted(p["name"] for i in r.json()["items"] for p in i["products"])
    assert await names("100%") == ["100% 주스"]
    assert await names("a_b") == ["a_b"]
    assert await names("BREAD") == ["Bread"]
    assert await names("k\\s") == ["Bread"]


async def test_store_id_array_over_bind_parameter_limit(session_factory):
    async with session_factory() as s:
        ids = [uuid.uuid4() for _ in range(40000)]
        repo = SqlAlchemyProductRepository(s)
        assert await repo.search_store_ids(store_ids=ids, keyword=None, category=None, page=1, size=20) == ([], 0)


# ── #8 주변 할인 ──
async def test_nearby_offers_basic_and_filters(client):
    t, s = await owner_with_store(client)
    p = await make_product(client, t, s, name="샌드위치")
    o = await make_offer(client, t, p["id"])
    r = await client.get("/v1/offers")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"items", "page", "size", "total"} and body["total"] == 1
    item = body["items"][0]
    assert set(item) == {"offer", "distance", "unit"} and item["distance"] is None
    assert item["unit"] == "km" and item["offer"]["id"] == o["id"]
    assert item["offer"]["status"] == "ON_SALE" and item["offer"]["store_name"]
    # status 필터
    assert (await client.get("/v1/offers", params={"status": "SOLD_OUT"})).json()["total"] == 0
    # 정지 할인·비노출 상품·폐점 상점 제외
    await set_offer(client, o["id"], suspended_at=datetime.now(timezone.utc), suspended_reason="r")
    assert (await client.get("/v1/offers")).json()["total"] == 0
    await set_offer(client, o["id"], suspended_at=None, suspended_reason=None)
    await set_product_inactive(client, p["id"])
    assert (await client.get("/v1/offers")).json()["total"] == 0
    async with client.session_factory() as ss:
        (await ss.get(ProductModel, uuid.UUID(p["id"]))).is_active = True
        await ss.commit()
    await set_store(client, s, closed_at=datetime.now(timezone.utc))
    assert (await client.get("/v1/offers")).json()["total"] == 0


async def test_nearby_offers_location_and_distance_sort(client):
    t1, a = await owner_with_store(client, "a@t.com")
    t2, b = await owner_with_store(client, "b@t.com")
    await set_store(client, b, latitude=LAT + 0.01)  # 약 1.11km
    pa = await make_product(client, t1, a, name="가")
    pb = await make_product(client, t2, b, name="나")
    # a 상점 할인이 마감이 더 늦어도 거리 정렬에서는 a가 먼저
    oa = await make_offer(client, t1, pa["id"], sales_end=(datetime.now(timezone.utc) + 5 * H).isoformat(),
                          pickup_start=(datetime.now(timezone.utc) + 6 * H).isoformat(),
                          pickup_end=(datetime.now(timezone.utc) + 7 * H).isoformat())
    ob = await make_offer(client, t2, pb["id"])
    r = await client.get("/v1/offers", params={"lat": LAT, "lng": LNG, "sort": "distance"})
    assert [i["offer"]["id"] for i in r.json()["items"]] == [oa["id"], ob["id"]]
    assert [i["distance"] for i in r.json()["items"]][0] == 0.0
    r = await client.get("/v1/offers", params={"lat": LAT, "lng": LNG, "radius_km": 0.5})
    assert [i["offer"]["id"] for i in r.json()["items"]] == [oa["id"]]
    r = await client.get("/v1/offers")  # sales_end 기본: 마감 임박순
    assert [i["offer"]["id"] for i in r.json()["items"]] == [ob["id"], oa["id"]]


async def test_nearby_offers_errors_and_coexistence(client):
    r = await client.get("/v1/offers", params={"lat": 37.0})
    assert r.status_code == 400 and r.json()["message"] == "lat과 lng는 함께 입력해야 합니다."
    r = await client.get("/v1/offers", params={"sort": "distance"})
    assert r.status_code == 400
    assert r.json() == {
        "success": False, "error_code": "VALIDATION_ERROR",
        "message": "distance 정렬은 위치 정보가 필요합니다.",
    }
    for params in [{"status": "SUSPENDED"}, {"status": "NOPE"}, {"sort": "nope"},
                   {"lat": 37, "lng": 127, "radius_km": 0.09}, {"lat": 91, "lng": 127}]:
        r = await client.get("/v1/offers", params=params)
        assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR", params
    r = await client.get(f"/v1/offers/{uuid.uuid4()}")
    assert r.status_code == 404  # 상세 EP와 공존


async def test_offer_sorts_price_and_discount_rate_match_domain(session_factory, client):
    t, s = await owner_with_store(client)
    specs = [(2_100_000_000, 1_000_000_000), (10000, 9000), (6000, 3000), (7, 3)]
    made = []
    for k, (orig, sale) in enumerate(specs):
        p = await make_product(client, t, s, name=f"p{k}", original_price=orig)
        o = await make_offer(client, t, p["id"], sale_price=sale)
        made.append((o["id"], orig, sale))
    now = datetime.now(timezone.utc)  # 할인 sales_start(생성 시각) 이후
    async with session_factory() as ss:
        repo = SqlAlchemyDiscountOfferRepository(ss)
        store_ids = [uuid.UUID(s)]
        common = dict(store_ids=store_ids, status=OfferStatus.ON_SALE, keyword=None, category=None,
                      now=now, page=1, size=20)
        rows, total = await repo.search_in_stores(sort=OfferSort.DISCOUNT_RATE, **common)
        assert total == 4
        expected = sorted(made, key=lambda m: -((m[1] - m[2]) * 100 // m[1]))
        got = [str(o.id) for o, _ in rows]
        rates = [(o.discount_rate(p.original_price)) for o, p in rows]
        assert rates == sorted(rates, reverse=True)
        assert got[0] in {m[0] for m in expected if (m[1] - m[2]) * 100 // m[1] == rates[0]}
        rows, _ = await repo.search_in_stores(sort=OfferSort.PRICE, **common)
        prices = [o.sale_price for o, _ in rows]
        assert prices == sorted(prices)


# ── has_active_offer 경계 (D64·D70) ──
async def test_has_active_offer_by_offer_state(client):
    t, s = await owner_with_store(client)
    now = datetime.now(timezone.utc)
    cases = {}  # 이름 -> (할인 컬럼 변경, 기대 has_active_offer)
    cases["정지"] = ({"suspended_at": now, "suspended_reason": "r"}, False)
    cases["중단"] = ({"is_active": False}, False)
    cases["마감경과"] = ({"sales_end": now - H, "sales_start": now - 2 * H}, False)
    cases["품절"] = ({"remaining_stock": 0}, True)
    cases["예정"] = ({"sales_start": now + H}, True)
    cases["판매중"] = ({}, True)
    for name, (cols, _) in cases.items():
        p = await make_product(client, t, s, name=name)
        o = await make_offer(client, t, p["id"])
        if cols:
            await set_offer(client, o["id"], **cols)
    r = await client.get("/v1/products", params={"size": 100})
    flags = {p["name"]: p["has_active_offer"] for i in r.json()["items"] for p in i["products"]}
    assert flags == {name: expected for name, (_, expected) in cases.items()}


# ── 페이지네이션 순서 ──
async def _named_stores(client, names):
    out = {}
    for n, name in enumerate(names):
        t, s = await owner_with_store(client, f"pg{n}@t.com")
        await make_product(client, t, s, name="빵")
        await set_store(client, s, name=name)
        out[name] = s
    return out


async def test_pagination_order_by_store_name_without_location(client):
    st = await _named_stores(client, ["다", "가", "라", "나"])
    order = [st[n] for n in ["가", "나", "다", "라"]]
    r1 = (await client.get("/v1/products", params={"size": 2, "page": 1})).json()
    r2 = (await client.get("/v1/products", params={"size": 2, "page": 2})).json()
    assert r1["total"] == r2["total"] == 4
    assert [i["store"]["id"] for i in r1["items"]] == order[:2]
    assert [i["store"]["id"] for i in r2["items"]] == order[2:]


async def test_pagination_order_by_distance_with_location(client):
    st = await _named_stores(client, ["a", "b", "c"])
    # 이름 순서와 거리 순서를 다르게: c가 가장 가깝고 a가 가장 멀다
    await set_store(client, st["c"], latitude=LAT)
    await set_store(client, st["b"], latitude=LAT + 0.01)
    await set_store(client, st["a"], latitude=LAT + 0.02)
    order = [st["c"], st["b"], st["a"]]
    params = {"lat": LAT, "lng": LNG, "size": 2}
    r1 = (await client.get("/v1/products", params={**params, "page": 1})).json()
    r2 = (await client.get("/v1/products", params={**params, "page": 2})).json()
    r3 = (await client.get("/v1/products", params={**params, "page": 3})).json()
    assert r1["total"] == r2["total"] == r3["total"] == 3
    assert [i["store"]["id"] for i in r1["items"]] == order[:2]
    assert [i["store"]["id"] for i in r2["items"]] == order[2:]
    assert r1["items"][0]["distance"] <= r1["items"][1]["distance"] <= r2["items"][0]["distance"]
    assert r3["items"] == []
