import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from auth.infrastructure import models as auth_models  # noqa: F401
from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.product import Product
from catalog.infrastructure import models as catalog_models
from catalog.infrastructure.repositories import (
    SqlAlchemyDiscountOfferRepository,
    SqlAlchemyProductRepository,
)
from stores.infrastructure import models as stores_models  # noqa: F401
from tests.helpers import bearer, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]

H = timedelta(hours=1)


def iso(dt):
    return dt.isoformat()


def offer_body(**kw):
    now = datetime.now(timezone.utc)
    body = {
        "sale_price": 3000,
        "initial_stock": 10,
        "sales_end": iso(now + 2 * H),
        "pickup_start": iso(now + H),
        "pickup_end": iso(now + 3 * H),
    }
    body.update(kw)
    return body


async def owner_with_store(c, email="owner@test.com"):
    token = await token_for(c, email, "OWNER")
    r = await c.post("/v1/stores", json={"pickup_address": "서울 강남구"}, headers=bearer(token))
    assert r.status_code == 201, r.text
    return token, r.json()["id"]


async def make_product(c, token, store_id, **kw):
    body = {"name": "샌드위치", "original_price": 6000, "category": "베이커리"}
    body.update(kw)
    r = await c.post(f"/v1/stores/{store_id}/products", json=body, headers=bearer(token))
    assert r.status_code == 201, r.text
    return r.json()


async def make_offer(c, token, product_id, **kw):
    r = await c.post(f"/v1/products/{product_id}/offers", json=offer_body(**kw), headers=bearer(token))
    assert r.status_code == 201, r.text
    return r.json()


def err(code, error_code, message):
    return {"success": False, "error_code": error_code, "message": message}


# ── #1 상품 등록 ──
async def test_create_product_ok(client):
    token, store_id = await owner_with_store(client)
    r = await client.post(
        f"/v1/stores/{store_id}/products",
        json={"name": "샌드위치", "category": "베이커리", "description": "햄치즈",
              "original_price": 6000, "product_image": ["https://e.com/a.jpg"]},
        headers=bearer(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["store_id"] == store_id and body["is_active"] is True
    assert body["product_image"] == ["https://e.com/a.jpg"] and body["original_price"] == 6000
    uuid.UUID(body["id"])


async def test_create_product_errors(client):
    token, store_id = await owner_with_store(client)
    url = f"/v1/stores/{store_id}/products"
    r = await client.post(url, json={"name": "a", "original_price": 0}, headers=bearer(token))
    assert r.status_code == 400
    assert r.json() == err(400, "VALIDATION_ERROR", "정상 가격은 0보다 커야 합니다.")
    r = await client.post(url, json={"name": "a", "original_price": 1})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    cust = await token_for(client, "c@test.com", "CUSTOMER")
    r = await client.post(url, json={"name": "a", "original_price": 1}, headers=bearer(cust))
    assert r.status_code == 403
    other, _ = await owner_with_store(client, "o2@test.com")
    r = await client.post(url, json={"name": "a", "original_price": 1}, headers=bearer(other))
    assert r.status_code == 403
    assert r.json() == err(403, "FORBIDDEN", "본인 상점에만 상품을 등록할 수 있습니다.")
    r = await client.post(
        f"/v1/stores/{uuid.uuid4()}/products", json={"name": "a", "original_price": 1},
        headers=bearer(token),
    )
    assert r.status_code == 404 and r.json() == err(404, "NOT_FOUND", "상점을 찾을 수 없습니다.")
    r = await client.post(url, json={"original_price": 1}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


async def test_create_product_closed_store(client):
    token, store_id = await owner_with_store(client)
    async with client.session_factory() as s:
        from stores.infrastructure.models import StoreModel

        (await s.get(StoreModel, uuid.UUID(store_id))).closed_at = datetime.now(timezone.utc)
        await s.commit()
    r = await client.post(
        f"/v1/stores/{store_id}/products", json={"name": "a", "original_price": 1},
        headers=bearer(token),
    )
    assert r.status_code == 400 and r.json()["error_code"] == "STORE_CLOSED"


# ── #2 상품 목록 ──
async def test_list_products(client):
    token, store_id = await owner_with_store(client)
    await make_product(client, token, store_id, name="b", category="x")
    await make_product(client, token, store_id, name="a", category="y")
    hidden = await make_product(client, token, store_id, name="c", category="x")
    await client.post(f"/v1/products/{hidden['id']}/deactivate", headers=bearer(token))
    r = await client.get(f"/v1/stores/{store_id}/products")
    body = r.json()
    assert r.status_code == 200 and body["total"] == 2 and body["page"] == 1 and body["size"] == 20
    assert [i["name"] for i in body["items"]] == ["a", "b"]
    r = await client.get(f"/v1/stores/{store_id}/products", params={"category": "x"})
    assert [i["name"] for i in r.json()["items"]] == ["b"]
    r = await client.get(f"/v1/stores/{store_id}/products", params={"page": 2, "size": 1})
    assert [i["name"] for i in r.json()["items"]] == ["b"] and r.json()["total"] == 2


async def test_list_products_inactive_rules(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    await client.post(f"/v1/products/{p['id']}/deactivate", headers=bearer(token))
    url = f"/v1/stores/{store_id}/products"
    r = await client.get(url, params={"is_active": "false"})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    other = await token_for(client, "x@test.com", "CUSTOMER")
    r = await client.get(url, params={"is_active": "false"}, headers=bearer(other))
    assert r.status_code == 403
    assert r.json()["message"] == "본인 상점의 비활성 상품만 조회할 수 있습니다."
    r = await client.get(url, params={"is_active": "false"}, headers=bearer(token))
    assert r.status_code == 200 and r.json()["total"] == 1


async def test_list_products_errors(client):
    r = await client.get(f"/v1/stores/{uuid.uuid4()}/products")
    assert r.status_code == 404
    _, store_id = await owner_with_store(client)
    for params in [{"page": 0}, {"size": 0}, {"size": 101}]:
        r = await client.get(f"/v1/stores/{store_id}/products", params=params)
        assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    r = await client.get(
        f"/v1/stores/{store_id}/products", headers={"Authorization": "Bearer bad.token"}
    )
    assert r.status_code == 401


# ── #4 상품 상세 ──
async def test_get_product(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    r = await client.get(f"/v1/products/{p['id']}")
    assert r.status_code == 200
    assert r.json()["store_name"] == "홍길동" and r.json()["pickup_address"] == "서울 강남구"
    assert r.json()["id"] == p["id"]
    await client.post(f"/v1/products/{p['id']}/deactivate", headers=bearer(token))
    r = await client.get(f"/v1/products/{p['id']}")
    assert r.status_code == 404 and r.json() == err(404, "NOT_FOUND", "상품을 찾을 수 없습니다.")
    assert (await client.get(f"/v1/products/{p['id']}", headers=bearer(token))).status_code == 200
    assert (await client.get(f"/v1/products/{uuid.uuid4()}")).status_code == 404
    assert (await client.get("/v1/products/not-a-uuid")).status_code == 400


# ── #5 상품 수정 ──
async def test_update_product(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id, description="d")
    url = f"/v1/products/{p['id']}"
    r = await client.patch(url, json={"original_price": 6500, "description": None}, headers=bearer(token))
    assert r.status_code == 200, r.text
    assert r.json()["original_price"] == 6500 and r.json()["description"] is None
    assert r.json()["name"] == "샌드위치"
    r = await client.patch(url, json={}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["message"] == "수정할 항목이 없습니다."
    r = await client.patch(url, json={"name": None}, headers=bearer(token))
    assert r.status_code == 400
    assert (await client.patch(url, json={"name": "a"})).status_code == 401
    other, _ = await owner_with_store(client, "o2@test.com")
    r = await client.patch(url, json={"name": "a"}, headers=bearer(other))
    assert r.status_code == 403 and r.json()["message"] == "본인 상점의 상품만 수정할 수 있습니다."
    r = await client.patch(f"/v1/products/{uuid.uuid4()}", json={"name": "a"}, headers=bearer(token))
    assert r.status_code == 404


async def test_update_price_blocked_by_open_offer(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    await make_offer(client, token, p["id"], sale_price=3000)
    r = await client.patch(
        f"/v1/products/{p['id']}", json={"original_price": 3000}, headers=bearer(token)
    )
    assert r.status_code == 400
    assert r.json()["message"] == "정상 가격은 진행 중인 할인 가격보다 커야 합니다."
    r = await client.patch(
        f"/v1/products/{p['id']}", json={"original_price": 3001}, headers=bearer(token)
    )
    assert r.status_code == 200


# ── #6 노출 중단 ──
async def test_deactivate(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    url = f"/v1/products/{p['id']}/deactivate"
    r = await client.post(url, headers=bearer(token))
    assert r.status_code == 200 and r.json()["is_active"] is False
    r = await client.post(url, headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "PRODUCT_ALREADY_INACTIVE"
    assert (await client.post(url)).status_code == 401
    other, _ = await owner_with_store(client, "o2@test.com")
    r = await client.post(url, headers=bearer(other))
    assert r.status_code == 403
    assert (await client.post(f"/v1/products/{uuid.uuid4()}/deactivate", headers=bearer(token))).status_code == 404


async def test_deactivate_blocked_by_open_offer(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    await make_offer(client, token, p["id"])
    r = await client.post(f"/v1/products/{p['id']}/deactivate", headers=bearer(token))
    assert r.status_code == 400
    assert r.json() == err(400, "PRODUCT_HAS_OPEN_OFFER", "진행 중인 할인 판매가 있어 비활성화할 수 없습니다.")


# ── #7 할인 등록 ──
async def test_register_offer_ok_and_stock_log(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    assert o["product_id"] == p["id"] and o["store_id"] == store_id
    assert o["store_name"] == "홍길동" and o["product_name"] == "샌드위치"
    assert o["original_price"] == 6000 and o["sale_price"] == 3000 and o["discount_rate"] == 50
    assert o["initial_stock"] == o["remaining_stock"] == 10 and o["is_sold_out"] is False
    assert o["status"] == "ON_SALE" and o["is_active"] is True
    assert datetime.fromisoformat(o["sales_end"]).tzinfo is not None
    async with client.session_factory() as s:
        logs = (await s.execute(select(catalog_models.StockLogModel))).scalars().all()
    assert len(logs) == 1 and logs[0].amount == 10 and logs[0].reason == "최초 입고"
    assert str(logs[0].offer_id) == o["id"]


async def test_register_offer_scheduled(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(
        client, token, p["id"], sales_start=iso(datetime.now(timezone.utc) + H // 2)
    )
    assert o["status"] == "SCHEDULED"


async def test_register_offer_errors(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    url = f"/v1/products/{p['id']}/offers"
    r = await client.post(url, json=offer_body(sale_price=6000), headers=bearer(token))
    assert r.status_code == 400
    assert r.json()["message"] == "할인 가격은 정상 가격보다 낮아야 합니다."
    now = datetime.now(timezone.utc)
    r = await client.post(
        url, json=offer_body(sales_start=iso(now + 3 * H)), headers=bearer(token)
    )
    assert r.json()["message"] == "판매 마감 시간은 판매 시작 시간 이후여야 합니다."
    r = await client.post(url, json=offer_body(pickup_end=iso(now + H)), headers=bearer(token))
    assert r.json()["message"] == "픽업 마감 시간은 판매 마감 시간 이후여야 합니다."
    for bad in [{"initial_stock": 0}, {"initial_stock": 10000}, {"sales_end": "2030-01-01T00:00:00"}]:
        r = await client.post(url, json=offer_body(**bad), headers=bearer(token))
        assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR", bad
    assert (await client.post(url, json=offer_body())).status_code == 401
    other, _ = await owner_with_store(client, "o2@test.com")
    r = await client.post(url, json=offer_body(), headers=bearer(other))
    assert r.status_code == 403
    assert r.json()["message"] == "본인 상점의 상품만 할인 등록할 수 있습니다."
    r = await client.post(f"/v1/products/{uuid.uuid4()}/offers", json=offer_body(), headers=bearer(token))
    assert r.status_code == 404
    await make_offer(client, token, p["id"])
    r = await client.post(url, json=offer_body(), headers=bearer(token))
    assert r.status_code == 400
    assert r.json() == err(400, "OFFER_ALREADY_OPEN", "이미 진행 중인 할인 판매가 있습니다.")


async def test_register_offer_inactive_product(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    await client.post(f"/v1/products/{p['id']}/deactivate", headers=bearer(token))
    r = await client.post(f"/v1/products/{p['id']}/offers", json=offer_body(), headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "PRODUCT_INACTIVE"
    assert r.json()["message"] == "비활성화된 상품은 할인 등록할 수 없습니다."


async def test_concurrent_offer_registration_only_one(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    url = f"/v1/products/{p['id']}/offers"
    results = await asyncio.gather(
        *[client.post(url, json=offer_body(), headers=bearer(token)) for _ in range(4)]
    )
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 400, 400, 400], [r.text for r in results]


# ── #9 상점 할인 목록 ──
async def test_list_store_offers(client):
    token, store_id = await owner_with_store(client)
    p1 = await make_product(client, token, store_id, name="a")
    p2 = await make_product(client, token, store_id, name="b")
    now = datetime.now(timezone.utc)
    o1 = await make_offer(client, token, p1["id"], sales_end=iso(now + 5 * H), pickup_end=iso(now + 6 * H))
    o2 = await make_offer(client, token, p2["id"])
    sched = await make_product(client, token, store_id, name="s")
    await make_offer(client, token, sched["id"], sales_start=iso(now + H // 2))
    r = await client.get(f"/v1/stores/{store_id}/offers")
    body = r.json()
    assert r.status_code == 200 and body["total"] == 2
    assert [i["id"] for i in body["items"]] == [o2["id"], o1["id"]]  # sales_end 오름차순
    assert body["items"][0]["product_name"] == "b" and body["items"][0]["store_name"] == "홍길동"
    r = await client.get(f"/v1/stores/{store_id}/offers", params={"status": "SCHEDULED"})
    assert r.json()["total"] == 1
    r = await client.get(f"/v1/stores/{store_id}/offers", params={"status": "CLOSED"})
    assert r.json()["total"] == 0
    r = await client.get(f"/v1/stores/{store_id}/offers", params={"page": 2, "size": 1})
    assert [i["id"] for i in r.json()["items"]] == [o1["id"]]


async def test_list_store_offers_errors(client):
    assert (await client.get(f"/v1/stores/{uuid.uuid4()}/offers")).status_code == 404
    _, store_id = await owner_with_store(client)
    r = await client.get(f"/v1/stores/{store_id}/offers", params={"status": "BOGUS"})
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


# ── #13 재등록 ──
async def test_relist(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    old = await make_offer(client, token, p["id"])
    r = await client.post(
        f"/v1/offers/{old['id']}/relist",
        json=offer_body(sale_price=2500, initial_stock=5),
        headers=bearer(token),
    )
    assert r.status_code == 201, r.text
    new = r.json()
    assert new["id"] != old["id"] and new["sale_price"] == 2500 and new["initial_stock"] == 5
    assert new["status"] == "ON_SALE"
    async with client.session_factory() as s:
        old_model = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(old["id"]))
        assert old_model.is_active is False and old_model.status == "CLOSED"
        assert old_model.remaining_stock == 10  # 기존 건 재고 유지
        logs = (await s.execute(select(catalog_models.StockLogModel))).scalars().all()
        assert len(logs) == 2
    r = await client.post(f"/v1/offers/{old['id']}/relist", json=offer_body(), headers=bearer(token))
    assert r.status_code == 400
    assert r.json() == err(400, "OFFER_CLOSED", "이미 중단된 할인은 재등록할 수 없습니다.")


async def test_relist_price_error_keeps_old_open(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    old = await make_offer(client, token, p["id"])
    r = await client.post(
        f"/v1/offers/{old['id']}/relist", json=offer_body(sale_price=6000), headers=bearer(token)
    )
    assert r.status_code == 400
    assert r.json()["message"] == "할인 가격은 정상 가격보다 낮아야 합니다."
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(old["id"]))
        assert m.is_active is True and m.status == "ON_SALE"
        assert len((await s.execute(select(catalog_models.DiscountOfferModel))).scalars().all()) == 1


async def test_relist_auth_errors(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    old = await make_offer(client, token, p["id"])
    url = f"/v1/offers/{old['id']}/relist"
    assert (await client.post(url, json=offer_body())).status_code == 401
    other, _ = await owner_with_store(client, "o2@test.com")
    r = await client.post(url, json=offer_body(), headers=bearer(other))
    assert r.status_code == 403 and r.json()["message"] == "본인 상점의 할인만 재등록할 수 있습니다."
    r = await client.post(f"/v1/offers/{uuid.uuid4()}/relist", json=offer_body(), headers=bearer(token))
    assert r.status_code == 404 and r.json()["message"] == "할인 판매를 찾을 수 없습니다."


# ── #14 재고 조정 ──
async def test_adjust_stock(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"], initial_stock=3)
    url = f"/v1/offers/{o['id']}/stock-adjustments"
    r = await client.post(url, json={"amount": -3, "reason": "포장 파손"}, headers=bearer(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["offer_id"] == o["id"] and body["initial_stock"] == 3 and body["remaining_stock"] == 0
    assert body["is_sold_out"] is True and body["status"] == "SOLD_OUT"
    uuid.UUID(body["log_id"])
    r = await client.post(url, json={"amount": 2}, headers=bearer(token))
    body = r.json()
    assert body["initial_stock"] == 5 and body["remaining_stock"] == 2
    assert body["status"] == "ON_SALE" and body["is_sold_out"] is False
    async with client.session_factory() as s:
        logs = (
            await s.execute(select(catalog_models.StockLogModel).order_by(catalog_models.StockLogModel.created_at))
        ).scalars().all()
    assert sorted(l.amount for l in logs) == [-3, 2, 3]
    assert {l.reason for l in logs} == {"최초 입고", "포장 파손", None}


async def test_adjust_stock_errors(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    url = f"/v1/offers/{o['id']}/stock-adjustments"
    r = await client.post(url, json={"amount": -11}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "INSUFFICIENT_STOCK"
    r = await client.post(url, json={"amount": 0}, headers=bearer(token))
    assert r.status_code == 400
    r = await client.post(url, json={"amount": 9990}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["message"] == "최초 수량은 9999개를 넘을 수 없습니다."
    r = await client.post(url, json={"amount": 1, "reason": "a" * 201}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    assert (await client.post(url, json={"amount": 1})).status_code == 401
    other, _ = await owner_with_store(client, "o2@test.com")
    r = await client.post(url, json={"amount": 1}, headers=bearer(other))
    assert r.status_code == 403 and r.json()["message"] == "본인 상점의 재고만 조정할 수 있습니다."
    r = await client.post(f"/v1/offers/{uuid.uuid4()}/stock-adjustments", json={"amount": 1}, headers=bearer(token))
    assert r.status_code == 404
    await client.post(f"/v1/offers/{o['id']}/relist", json=offer_body(), headers=bearer(token))
    r = await client.post(url, json={"amount": 1}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_CLOSED"


async def test_concurrent_adjustments_serialize(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"], initial_stock=5)
    url = f"/v1/offers/{o['id']}/stock-adjustments"
    results = await asyncio.gather(
        *[client.post(url, json={"amount": -2}, headers=bearer(token)) for _ in range(4)]
    )
    codes = sorted(r.status_code for r in results)
    assert codes == [200, 200, 400, 400], [r.text for r in results]
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
        assert m.remaining_stock == 1


# ── 레포지토리: 상태 SQL 조건과 도메인 effective_status 일치 ──
async def test_status_clause_matches_effective_status(client):
    token, store_id = await owner_with_store(client)
    now = datetime.now(timezone.utc)
    sid = uuid.UUID(store_id)
    async with client.session_factory() as s:
        products = SqlAlchemyProductRepository(s)
        offers = SqlAlchemyDiscountOfferRepository(s)
        prod = await products.save(Product.register(sid, "p", 10000))
        specs = {
            "on_sale": dict(sales_start=now - H, sales_end=now + H, stock=3, active=True),
            "sold_out": dict(sales_start=now - H, sales_end=now + H, stock=0, active=True),
            "scheduled": dict(sales_start=now + H, sales_end=now + 2 * H, stock=3, active=True),
            "scheduled_zero": dict(sales_start=now + H, sales_end=now + 2 * H, stock=0, active=True),
            "expired": dict(sales_start=now - 3 * H, sales_end=now - H, stock=3, active=True),
            "inactive": dict(sales_start=now - H, sales_end=now + H, stock=3, active=False),
        }
        saved = []
        for key, sp in specs.items():
            o = DiscountOffer(
                product_id=prod.id, sale_price=100, initial_stock=3, remaining_stock=sp["stock"],
                sales_start=sp["sales_start"], sales_end=sp["sales_end"],
                pickup_start=sp["sales_end"], pickup_end=sp["sales_end"] + H,
                status=OfferStatus.ON_SALE, is_active=sp["active"],
            )
            saved.append(await offers.save(o))
        await s.commit()
    async with client.session_factory() as s:
        offers = SqlAlchemyDiscountOfferRepository(s)
        for status in OfferStatus:
            rows, total = await offers.find_by_store(sid, status=status, now=now, page=1, size=100)
            expected = {o.id for o in saved if o.effective_status(now) == status}
            assert {o.id for o, _ in rows} == expected and total == len(expected), status
        assert await offers.exists_open_by_store(sid, now)
        assert await offers.exists_open_by_store(uuid.uuid4(), now) is False
        assert (await offers.find_open_by_product(prod.id, now)) is not None
        assert await offers.exists_open_by_store(sid, now + 10 * H) is False
