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
    r = await c.post(
        "/v1/stores",
        json={"pickup_address": f"서울 강남구 {email}"},  # STORE_DUPLICATED 방지: 주소를 이메일로 구분
        headers=bearer(token),
    )
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


async def set_product_inactive(c, product_id):
    """비활성 상품 준비: 이 EP는 상품을 비활성화하지 않으므로 DB를 직접 고친다."""
    async with c.session_factory() as s:
        pm = await s.get(catalog_models.ProductModel, uuid.UUID(product_id))
        pm.is_active = False
        await s.commit()


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
    await set_product_inactive(client, hidden["id"])
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
    await set_product_inactive(client, p["id"])
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
    assert r.json()["store_name"] == "홍길동" and r.json()["pickup_address"] == "서울 강남구 owner@test.com"
    assert r.json()["id"] == p["id"]
    await set_product_inactive(client, p["id"])
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


# ── #6 상품 노출 중단 ──
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


# ── #12 할인 판매 중단 (16.7) ──
NOT_FOUND_MSG = "할인 판매를 찾을 수 없습니다."
OFFER_KEYS = {
    "id", "product_id", "store_id", "store_name", "product_name", "original_price",
    "sale_price", "discount_rate", "initial_stock", "remaining_stock", "is_sold_out",
    "sales_start", "sales_end", "pickup_start", "pickup_end", "status", "is_active",
}


def deact_url(offer_id):
    return f"/v1/offers/{offer_id}/deactivate"


async def test_deactivate_offer_ok(client):
    token, store_id, p, o = await _setup_offer(client)
    h = bearer(token)
    r = await client.post(
        deact_url(o["id"]), json={"reason": "재료 소진", "cancel_reservations": False}, headers=h
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"offer", "cancelled_reservation_count"}
    assert set(body["offer"]) == OFFER_KEYS
    assert body["offer"]["id"] == o["id"]
    assert body["offer"]["status"] == "CLOSED" and body["offer"]["is_active"] is False
    assert body["cancelled_reservation_count"] == 0
    # 기본 상점 할인 목록에서 사라지고 CLOSED 목록에 나타남
    r = await client.get(f"/v1/stores/{store_id}/offers", headers=h)
    assert r.json()["total"] == 0
    r = await client.get(f"/v1/stores/{store_id}/offers", params={"status": "CLOSED"}, headers=h)
    assert [i["id"] for i in r.json()["items"]] == [o["id"]]
    # 상품은 그대로 활성
    r = await client.get(f"/v1/products/{p['id']}")
    assert r.status_code == 200 and r.json()["is_active"] is True
    # DB: 상품 불변, reason 컬럼 없음(저장 안 함)
    async with client.session_factory() as s:
        pm = await s.get(catalog_models.ProductModel, uuid.UUID(p["id"]))
        om = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
    assert pm.is_active is True and om.is_active is False and om.status == "CLOSED"
    assert om.remaining_stock == 10
    assert "reason" not in catalog_models.DiscountOfferModel.__table__.columns


async def test_deactivate_offer_cancel_true_and_default(client):
    token, _, p, o = await _setup_offer(client)
    h = bearer(token)
    r = await client.post(
        deact_url(o["id"]), json={"reason": "사고", "cancel_reservations": True}, headers=h
    )
    assert r.status_code == 200 and r.json()["cancelled_reservation_count"] == 0  # 취소할 예약이 없으면 0건
    assert r.json()["offer"]["status"] == "CLOSED"
    # 생략하면 기본 false
    p2 = await make_product(client, token, p["store_id"], name="b")
    o2 = await make_offer(client, token, p2["id"])
    r = await client.post(deact_url(o2["id"]), json={"reason": "x"}, headers=h)
    assert r.status_code == 200 and r.json()["cancelled_reservation_count"] == 0


async def test_deactivate_offer_already_closed_400(client):
    token, _, p, o = await _setup_offer(client)
    h = bearer(token)
    body = {"reason": "x", "cancel_reservations": True}
    assert (await client.post(deact_url(o["id"]), json=body, headers=h)).status_code == 200
    r = await client.post(deact_url(o["id"]), json=body, headers=h)
    assert r.status_code == 400 and r.json() == err(400, "OFFER_CLOSED", "이미 중단된 할인입니다.")
    # PATCH로 중단한 할인도 같다
    p2 = await make_product(client, token, p["store_id"], name="b")
    o2 = await make_offer(client, token, p2["id"])
    await client.patch(f"/v1/offers/{o2['id']}", json={"is_active": False}, headers=h)
    r = await client.post(deact_url(o2["id"]), json=body, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_CLOSED"


async def test_deactivate_offer_after_sales_end_allowed(client):
    token, _, p, o = await _setup_offer(client)
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
        m.sales_start = datetime.now(timezone.utc) - 3 * H
        m.sales_end = datetime.now(timezone.utc) - H
        m.pickup_start = m.sales_end
        m.pickup_end = m.sales_end + 2 * H
        await s.commit()
    r = await client.post(deact_url(o["id"]), json={"reason": "x"}, headers=bearer(token))
    assert r.status_code == 200, r.text  # 마감 지난 활성 할인도 중단 (Q24 A)
    assert r.json()["offer"]["is_active"] is False and r.json()["offer"]["status"] == "CLOSED"


async def test_deactivate_offer_after_close_flows(client):
    token, store_id, p, o = await _setup_offer(client)
    h = bearer(token)
    r = await client.post(deact_url(o["id"]), json={"reason": "x"}, headers=h)
    assert r.status_code == 200
    # #13 재등록, #14 재고 조정은 종료된 할인이라 400 OFFER_CLOSED
    r = await client.post(f"/v1/offers/{o['id']}/relist", json=offer_body(), headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_CLOSED"
    r = await client.post(
        f"/v1/offers/{o['id']}/stock-adjustments", json={"amount": 1}, headers=h
    )
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_CLOSED"
    # 마감 전이므로 PATCH 재개 가능 (Q19)
    r = await client.patch(f"/v1/offers/{o['id']}", json={"is_active": True}, headers=h)
    assert r.status_code == 200 and r.json()["is_active"] is True
    # 다시 중단 후 같은 상품에 신규 할인 등록 가능 (진행 중 없음)
    assert (await client.post(deact_url(o["id"]), json={"reason": "x"}, headers=h)).status_code == 200
    r = await client.post(f"/v1/products/{p['id']}/offers", json=offer_body(), headers=h)
    assert r.status_code == 201


async def test_deactivate_offer_validation_400(client):
    token, _, p, o = await _setup_offer(client)
    h = bearer(token)
    url = deact_url(o["id"])
    bad_bodies = [
        {}, {"reason": ""}, {"reason": "   "}, {"reason": "a" * 201},
        {"reason": "x", "cancel_reservations": "maybe"},
    ]
    for body in bad_bodies:
        r = await client.post(url, json=body, headers=h)
        assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR", body
        assert r.json()["success"] is False
    r = await client.post(url, headers=h)  # 본문 없음
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    r = await client.post(deact_url("not-a-uuid"), json={"reason": "x"}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    # 검증 실패는 할인을 바꾸지 않는다
    async with client.session_factory() as s:
        assert (await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))).is_active
    r = await client.post(url, json={"reason": "a" * 200}, headers=h)  # 정확히 200자는 성공
    assert r.status_code == 200


async def test_deactivate_offer_auth_errors(client):
    token, _, p, o = await _setup_offer(client)
    url = deact_url(o["id"])
    body = {"reason": "x"}
    r = await client.post(url, json=body)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    cust = await token_for(client, "c@test.com", "CUSTOMER")
    assert (await client.post(url, json=body, headers=bearer(cust))).status_code == 403
    other, _ = await owner_with_store(client, "o2@test.com")
    r = await client.post(url, json=body, headers=bearer(other))
    assert r.status_code == 403
    assert r.json() == err(403, "FORBIDDEN", "본인 상점의 할인만 중단할 수 있습니다.")
    r = await client.post(deact_url(uuid.uuid4()), json=body, headers=bearer(token))
    assert r.status_code == 404 and r.json() == err(404, "NOT_FOUND", NOT_FOUND_MSG)
    # 실패한 요청은 할인을 바꾸지 않는다
    async with client.session_factory() as s:
        assert (await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))).is_active


async def test_deactivate_offer_already_closed_other_owner_403(client):
    token, _, p, o = await _setup_offer(client)
    body = {"reason": "x"}
    assert (await client.post(deact_url(o["id"]), json=body, headers=bearer(token))).status_code == 200
    other, _ = await owner_with_store(client, "o2@test.com")
    r = await client.post(deact_url(o["id"]), json=body, headers=bearer(other))
    assert r.status_code == 403
    assert r.json() == err(403, "FORBIDDEN", "본인 상점의 할인만 중단할 수 있습니다.")


async def test_deactivate_offer_picked_up_reservation_400_keeps_offer(client):
    from catalog.domain.exceptions import PickedUpReservationExistsError
    from container import create_reservation_cancel

    class FakeCancel:
        async def cancel_all_for_offer(self, offer_id, *, reason):
            raise PickedUpReservationExistsError()

    token, _, p, o = await _setup_offer(client)
    from main import app

    previous = app.dependency_overrides.get(create_reservation_cancel)  # wire_dependencies가 넣은 실제 어댑터 매핑
    app.dependency_overrides[create_reservation_cancel] = lambda: FakeCancel()
    try:
        r = await client.post(
            deact_url(o["id"]),
            json={"reason": "사고", "cancel_reservations": True},
            headers=bearer(token),
        )
    finally:
        app.dependency_overrides[create_reservation_cancel] = previous  # 다른 테스트를 위해 되돌린다
    assert r.status_code == 400
    assert r.json()["error_code"] == "PICKED_UP_RESERVATION_EXISTS"
    assert r.json()["success"] is False
    async with client.session_factory() as s:
        om = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
    assert om.is_active is True and om.status == o["status"]


async def test_deactivate_offer_closed_store_allowed(client):
    token, store_id, p, o = await _setup_offer(client)
    async with client.session_factory() as s:
        from stores.infrastructure.models import StoreModel

        (await s.get(StoreModel, uuid.UUID(store_id))).closed_at = datetime.now(timezone.utc)
        await s.commit()
    r = await client.post(deact_url(o["id"]), json={"reason": "x"}, headers=bearer(token))
    assert r.status_code == 200


async def test_deactivate_offer_concurrent_with_adjust(client):
    token, store_id, p, o = await _setup_offer(client)
    h = bearer(token)
    results = await asyncio.gather(
        client.post(deact_url(o["id"]), json={"reason": "x"}, headers=h),
        client.post(f"/v1/offers/{o['id']}/stock-adjustments", json={"amount": -2}, headers=h),
    )
    assert all(r.status_code in (200, 400) for r in results), [r.text for r in results]
    async with client.session_factory() as s:
        offers = (await s.execute(select(catalog_models.DiscountOfferModel))).scalars().all()
        logs = (await s.execute(select(catalog_models.StockLogModel))).scalars().all()
        for m in offers:
            assert sum(lg.amount for lg in logs if lg.offer_id == m.id) == m.remaining_stock


async def test_deactivate_offer_concurrent_with_relist(client):
    token, store_id, p, o = await _setup_offer(client)
    h = bearer(token)
    results = await asyncio.gather(
        client.post(deact_url(o["id"]), json={"reason": "x"}, headers=h),
        client.post(f"/v1/offers/{o['id']}/relist", json=offer_body(), headers=h),
    )
    assert all(r.status_code in (200, 201, 400) for r in results), [r.text for r in results]
    now = datetime.now(timezone.utc)
    async with client.session_factory() as s:
        offers = (await s.execute(select(catalog_models.DiscountOfferModel).where(
            catalog_models.DiscountOfferModel.product_id == uuid.UUID(p["id"])
        ))).scalars().all()
        assert len([m for m in offers if m.is_active and m.sales_end > now]) <= 1


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
    await set_product_inactive(client, p["id"])
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
    sched_p = await make_product(client, token, store_id, name="s")
    sched = await make_offer(
        client, token, sched_p["id"], sales_start=iso(now + H // 2),
        sales_end=iso(now + 3 * H), pickup_end=iso(now + 4 * H),
    )
    r = await client.get(f"/v1/stores/{store_id}/offers")
    body = r.json()
    assert r.status_code == 200 and body["total"] == 3  # 기본: SCHEDULED + ON_SALE + SOLD_OUT (D25)
    assert [i["id"] for i in body["items"]] == [o2["id"], sched["id"], o1["id"]]  # sales_end 오름차순
    assert body["items"][0]["product_name"] == "b" and body["items"][0]["store_name"] == "홍길동"
    r = await client.get(f"/v1/stores/{store_id}/offers", params={"status": "ON_SALE"})
    assert [i["id"] for i in r.json()["items"]] == [o2["id"], o1["id"]]  # 단일 값 하위 호환
    r = await client.get(f"/v1/stores/{store_id}/offers", params={"status": "SCHEDULED"})
    assert r.json()["total"] == 1
    r = await client.get(f"/v1/stores/{store_id}/offers", params={"status": "CLOSED"})
    assert r.json()["total"] == 0
    r = await client.get(f"/v1/stores/{store_id}/offers", params={"page": 2, "size": 1})
    body = r.json()
    assert [i["id"] for i in body["items"]] == [sched["id"]] and body["total"] == 3


async def test_list_store_offers_default_excludes_closed_and_multi_status(client):
    token, store_id = await owner_with_store(client)
    p1 = await make_product(client, token, store_id, name="a")
    p2 = await make_product(client, token, store_id, name="b")
    p3 = await make_product(client, token, store_id, name="c")
    now = datetime.now(timezone.utc)
    on = await make_offer(client, token, p1["id"])
    sched = await make_offer(client, token, p2["id"], sales_start=iso(now + H // 2))
    closed = await make_offer(client, token, p3["id"])
    r = await client.patch(f"/v1/offers/{closed['id']}", json={"is_active": False}, headers=bearer(token))
    assert r.status_code == 200
    url = f"/v1/stores/{store_id}/offers"
    ids = lambda r: {i["id"] for i in r.json()["items"]}  # noqa: E731
    assert ids(await client.get(url)) == {on["id"], sched["id"]}
    r = await client.get(url, params={"status": "CLOSED"})
    assert ids(r) == {closed["id"]}
    r = await client.get(url, params=[("status", "ON_SALE"), ("status", "CLOSED")])
    assert ids(r) == {on["id"], closed["id"]} and r.json()["total"] == 2


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
            rows, total = await offers.find_by_store(sid, statuses=[status], now=now, page=1, size=100)
            expected = {o.id for o in saved if o.effective_status(now) == status}
            assert {o.id for o, _ in rows} == expected and total == len(expected), status
        multi = [OfferStatus.SCHEDULED, OfferStatus.SOLD_OUT]
        rows, total = await offers.find_by_store(sid, statuses=multi, now=now, page=1, size=100)
        expected = {o.id for o in saved if o.effective_status(now) in multi}
        assert {o.id for o, _ in rows} == expected and total == len(expected)
        assert await offers.exists_open_by_store(sid, now)
        assert await offers.exists_open_by_store(uuid.uuid4(), now) is False
        assert (await offers.find_open_by_product(prod.id, now)) is not None
        assert await offers.exists_open_by_store(sid, now + 10 * H) is False


# ── #11 할인 수정 ──
async def _setup_offer(client, **kw):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"], **kw)
    return token, store_id, p, o


async def test_update_offer_fields(client):
    token, _, p, o = await _setup_offer(client)
    r = await client.patch(
        f"/v1/offers/{o['id']}", json={"sale_price": 2000, "initial_stock": 15}, headers=bearer(token)
    )
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["sale_price"] == 2000 and b["initial_stock"] == 15 and b["remaining_stock"] == 15
    assert b["status"] == "ON_SALE" and b["is_active"] is True and b["discount_rate"] == 66
    # 저장 컬럼 반영 (CI-7) + stock_log
    new_start = datetime.now(timezone.utc) + H // 2
    r = await client.patch(
        f"/v1/offers/{o['id']}",
        json={"sales_start": iso(new_start), "pickup_start": iso(new_start + H)},
        headers=bearer(token),
    )
    assert r.status_code == 200 and r.json()["status"] == "SCHEDULED"
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
        assert m.sale_price == 2000 and m.sales_start == new_start and m.pickup_start == new_start + H
        assert m.initial_stock == 15 and m.remaining_stock == 15
        logs = (
            await s.execute(
                select(catalog_models.StockLogModel).where(
                    catalog_models.StockLogModel.offer_id == m.id
                )
            )
        ).scalars().all()
        assert sorted(x.amount for x in logs) == [5, 10]
        assert sum(x.amount for x in logs) == m.remaining_stock
        assert {x.reason for x in logs} == {"최초 입고", "할인 수정"}


async def test_update_offer_400_cases(client):
    token, _, p, o = await _setup_offer(client)
    url = f"/v1/offers/{o['id']}"
    h = bearer(token)
    r = await client.patch(url, json={}, headers=h)
    assert r.status_code == 400 and r.json() == err(400, "VALIDATION_ERROR", "수정할 항목이 없습니다.")
    r = await client.patch(url, json={"sale_price": 6000}, headers=h)
    assert r.json() == err(400, "VALIDATION_ERROR", "할인 가격은 정상 가격보다 낮아야 합니다.")
    r = await client.patch(url, json={"sale_price": None}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    r = await client.patch(url, json={"is_active": None}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    r = await client.patch(url, json={"is_active": False, "sale_price": 100}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    r = await client.patch(url, json={"initial_stock": 0}, headers=h)
    assert r.status_code == 400
    r = await client.patch(url, json={"sales_end": "2030-01-01T00:00:00"}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    await client.post(
        f"/v1/offers/{o['id']}/stock-adjustments", json={"amount": -4}, headers=h
    )
    r = await client.patch(url, json={"initial_stock": 3}, headers=h)
    assert r.status_code == 400 and "줄어든 수량(4개)" in r.json()["message"]
    now = datetime.now(timezone.utc)
    r = await client.patch(url, json={"sales_end": iso(now + 5 * H)}, headers=h)
    assert r.status_code == 400 and "픽업 마감 시간은 판매 마감 시간 이후" in r.json()["message"]


async def test_update_offer_auth_and_not_found(client):
    token, _, p, o = await _setup_offer(client)
    url = f"/v1/offers/{o['id']}"
    r = await client.patch(url, json={"sale_price": 100})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    cust = await token_for(client, "c@test.com", "CUSTOMER")
    assert (await client.patch(url, json={"sale_price": 100}, headers=bearer(cust))).status_code == 403
    other, _ = await owner_with_store(client, "o2@test.com")
    r = await client.patch(url, json={"sale_price": 100}, headers=bearer(other))
    assert r.status_code == 403
    assert r.json() == err(403, "FORBIDDEN", "본인 상점의 할인만 수정할 수 있습니다.")
    r = await client.patch(f"/v1/offers/{uuid.uuid4()}", json={"sale_price": 100}, headers=bearer(token))
    assert r.status_code == 404 and r.json() == err(404, "NOT_FOUND", "할인 판매를 찾을 수 없습니다.")
    r = await client.patch("/v1/offers/not-a-uuid", json={"sale_price": 100}, headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


async def test_pause_resume_roundtrip_and_guards(client):
    token, store_id, p, o = await _setup_offer(client)
    url = f"/v1/offers/{o['id']}"
    h = bearer(token)
    r = await client.patch(url, json={"is_active": True}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_ALREADY_ACTIVE"
    r = await client.patch(url, json={"is_active": False}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "CLOSED" and r.json()["is_active"] is False
    r = await client.patch(url, json={"is_active": False}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_CLOSED"
    r = await client.patch(url, json={"sale_price": 100}, headers=h)
    assert r.status_code == 400 and r.json() == err(400, "OFFER_CLOSED", "종료된 할인은 수정할 수 없습니다.")
    # 중단 중에 새 할인을 등록하면 재개 불가
    o2 = await make_offer(client, token, p["id"])
    r = await client.patch(url, json={"is_active": True}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_ALREADY_OPEN"
    await client.patch(f"/v1/offers/{o2['id']}", json={"is_active": False}, headers=h)
    r = await client.patch(url, json={"is_active": True}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "ON_SALE" and r.json()["is_active"] is True
    # 재개 후 새 등록은 400
    r = await client.post(f"/v1/products/{p['id']}/offers", json=offer_body(), headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_ALREADY_OPEN"


async def test_resume_product_inactive_store_closed_and_ended(client):
    token, store_id, p, o = await _setup_offer(client)
    url = f"/v1/offers/{o['id']}"
    h = bearer(token)
    await client.patch(url, json={"is_active": False}, headers=h)
    async with client.session_factory() as s:
        pm = await s.get(catalog_models.ProductModel, uuid.UUID(p["id"]))
        pm.is_active = False
        await s.commit()
    r = await client.patch(url, json={"is_active": True}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "PRODUCT_INACTIVE"
    async with client.session_factory() as s:
        pm = await s.get(catalog_models.ProductModel, uuid.UUID(p["id"]))
        pm.is_active = True
        from stores.infrastructure.models import StoreModel

        (await s.get(StoreModel, uuid.UUID(store_id))).closed_at = datetime.now(timezone.utc)
        await s.commit()
    r = await client.patch(url, json={"is_active": True}, headers=h)
    assert r.status_code == 400 and r.json() == err(
        400, "STORE_CLOSED", "폐점된 상점에서는 할인을 재개할 수 없습니다."
    )
    async with client.session_factory() as s:
        from stores.infrastructure.models import StoreModel

        (await s.get(StoreModel, uuid.UUID(store_id))).closed_at = None
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
        m.sales_start = datetime.now(timezone.utc) - 3 * H
        m.sales_end = datetime.now(timezone.utc) - H
        m.pickup_start = m.sales_end
        m.pickup_end = m.sales_end + H
        await s.commit()
    r = await client.patch(url, json={"is_active": True}, headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_ENDED"


async def test_concurrent_update_and_adjust_serialize(client):
    token, _, p, o = await _setup_offer(client, initial_stock=10)
    h = bearer(token)
    results = await asyncio.gather(
        client.patch(f"/v1/offers/{o['id']}", json={"initial_stock": 20}, headers=h),
        client.post(f"/v1/offers/{o['id']}/stock-adjustments", json={"amount": -3}, headers=h),
        client.patch(f"/v1/offers/{o['id']}", json={"sale_price": 2500}, headers=h),
    )
    assert [r.status_code for r in results] == [200, 200, 200], [r.text for r in results]
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
        total = (
            await s.execute(
                select(catalog_models.StockLogModel.amount).where(
                    catalog_models.StockLogModel.offer_id == m.id
                )
            )
        ).scalars().all()
        assert sum(total) == m.remaining_stock and m.sale_price == 2500
        assert m.initial_stock == 20
        assert m.remaining_stock == 17
        assert m.sale_price == 2500
        assert sorted(total) == sorted([10, -3, 10])


async def test_locked_find_by_id_refreshes_identity_map(client):
    """B-1: 잠금 없이 읽은 뒤 다른 세션이 커밋해도 for_update 조회는 최신값을 반영한다."""
    _, _, _, o = await _setup_offer(client, initial_stock=10)
    oid = uuid.UUID(o["id"])
    async with client.session_factory() as a:
        repo_a = SqlAlchemyDiscountOfferRepository(a)
        before = await repo_a.find_by_id(oid)
        assert before.remaining_stock == 10
        # identity map은 약한 참조이므로 모델을 강하게 붙들어 서비스가 쓰는 상황(저장 시 session.get)을 재현
        held = await a.get(catalog_models.DiscountOfferModel, oid)
        assert held.remaining_stock == 10
        async with client.session_factory() as b:
            m = await b.get(catalog_models.DiscountOfferModel, oid)
            m.remaining_stock = 7
            await b.commit()
        locked = await repo_a.find_by_id(oid, for_update=True)
        assert locked.remaining_stock == 7


@pytest.mark.parametrize("stock", [0, 10000])
async def test_update_offer_initial_stock_range_message(client, stock):
    """M-3: 수량 범위 위반은 명세 문구로 400."""
    token, _, _, o = await _setup_offer(client)
    r = await client.patch(f"/v1/offers/{o['id']}", json={"initial_stock": stock}, headers=bearer(token))
    assert r.status_code == 400
    assert r.json()["message"] == "수량은 1개 이상 9999개 이하여야 합니다.", r.text


@pytest.mark.parametrize("stock", [0, 10000])
async def test_create_offer_initial_stock_range_message(client, stock):
    """명세 #7: 수량 범위 위반은 Pydantic 문구가 아닌 명세 문구로 400."""
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    r = await client.post(
        f"/v1/products/{p['id']}/offers", json=offer_body(initial_stock=stock), headers=bearer(token)
    )
    assert r.status_code == 400
    assert r.json()["message"] == "수량은 1개 이상 9999개 이하여야 합니다.", r.text


@pytest.mark.parametrize("stock", [0, 10000])
async def test_relist_initial_stock_range_message(client, stock):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    old = await make_offer(client, token, p["id"])
    r = await client.post(
        f"/v1/offers/{old['id']}/relist", json=offer_body(initial_stock=stock), headers=bearer(token)
    )
    assert r.status_code == 400
    assert r.json()["message"] == "수량은 1개 이상 9999개 이하여야 합니다.", r.text


# ── #10 할인 상세 ──
async def test_offer_detail_public_ok(client):
    from catalog.domain.discount_offer import CANCEL_POLICY_DESCRIPTION, OFFER_NOTICE

    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id, description="햄치즈", product_image=["https://e.com/a.jpg"])
    o = await make_offer(client, token, p["id"])
    r = await client.get(f"/v1/offers/{o['id']}")  # 인증 없음
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {
        "offer", "description", "product_image", "pickup_address",
        "latitude", "longitude", "notice", "cancel_policy",
    }
    assert body["offer"]["id"] == o["id"] and body["offer"] == o
    assert body["description"] == "햄치즈" and body["product_image"] == ["https://e.com/a.jpg"]
    assert body["pickup_address"] == "서울 강남구 owner@test.com"
    # 상점 개설 시 지오코딩된 좌표가 그대로 노출된다 (tests/fakes.py DEFAULT_COORDINATES)
    assert body["latitude"] == 37.4979 and body["longitude"] == 127.0276
    assert body["notice"] == OFFER_NOTICE
    cp = body["cancel_policy"]
    assert cp["description"] == CANCEL_POLICY_DESCRIPTION
    assert datetime.fromisoformat(cp["cancellable_until"]) == datetime.fromisoformat(o["pickup_start"]) - H


async def test_offer_detail_returns_store_coordinates(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    async with client.session_factory() as s:
        sm = await s.get(stores_models.StoreModel, uuid.UUID(store_id))
        sm.latitude = 37.4979
        sm.longitude = 127.0276
        await s.commit()
    r = await client.get(f"/v1/offers/{o['id']}")
    assert r.status_code == 200, r.text
    assert r.json()["latitude"] == 37.4979 and r.json()["longitude"] == 127.0276


async def test_offer_detail_visible_after_deactivate_inactive_product_closed_store(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    r = await client.post(
        f"/v1/offers/{o['id']}/deactivate", json={"reason": "품절"}, headers=bearer(token)
    )
    assert r.status_code == 200, r.text
    await set_product_inactive(client, p["id"])
    async with client.session_factory() as s:
        sm = await s.get(stores_models.StoreModel, uuid.UUID(store_id))
        sm.closed_at = datetime.now(timezone.utc)
        await s.commit()
    r = await client.get(f"/v1/offers/{o['id']}")
    assert r.status_code == 200, r.text
    assert r.json()["offer"]["status"] == "CLOSED" and r.json()["offer"]["is_active"] is False


async def test_offer_detail_not_found_and_invalid_uuid(client):
    r = await client.get(f"/v1/offers/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json() == err(404, "NOT_FOUND", "할인 판매를 찾을 수 없습니다.")
    r = await client.get("/v1/offers/not-a-uuid")
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
