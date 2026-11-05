"""관리자 정지 관련 DB 테스트: S11 컬럼, 상태 SQL 조건(C6), 잠금 조회, 가시성 API (admin.md D17~D22, C7, C8)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from auth.infrastructure import models as auth_models  # noqa: F401
from catalog.application.service import CatalogApplicationService
from catalog.domain.discount_offer import OPEN_OFFER_STATUSES, DiscountOffer, OfferStatus
from catalog.domain.exceptions import OfferAlreadySuspendedError
from catalog.domain.product import Product
from catalog.infrastructure import models as catalog_models
from catalog.infrastructure.repositories import (
    SqlAlchemyDiscountOfferRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyStockLogRepository,
)
from stores.infrastructure import models as stores_models
from tests.catalog.test_api_db import err, iso, make_offer, make_product, owner_with_store, offer_body
from tests.helpers import bearer, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]

H = timedelta(hours=1)


async def suspend_store_row(c, store_id):
    async with c.session_factory() as s:
        sm = await s.get(stores_models.StoreModel, uuid.UUID(store_id))
        sm.suspended_at = datetime.now(timezone.utc)
        sm.suspended_reason = "정책 위반"
        await s.commit()


async def suspend_offer_row(c, offer_id, reason="위생 문제"):
    async with c.session_factory() as s:
        repo = SqlAlchemyDiscountOfferRepository(s)
        o = await repo.find_by_id(uuid.UUID(offer_id))
        o.suspend(reason, datetime.now(timezone.utc))
        await repo.save(o)
        await s.commit()


# ── 모델 왕복 / CHECK ──
async def test_offer_suspension_columns_roundtrip(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    when = datetime.now(timezone.utc)
    async with client.session_factory() as s:
        repo = SqlAlchemyDiscountOfferRepository(s)
        offer = await repo.find_by_id(uuid.UUID(o["id"]))
        assert offer.suspended_at is None and offer.suspended_reason is None
        offer.suspend("  위생 문제 ", when)
        await repo.save(offer)
        await s.commit()
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
        assert m.status == "SUSPENDED" and m.is_active is True
        assert m.suspended_reason == "위생 문제" and m.suspended_at == when
        assert m.suspended_at.tzinfo is not None
        back = await SqlAlchemyDiscountOfferRepository(s).find_by_id(uuid.UUID(o["id"]))
        assert back.is_suspended and back.suspended_at == when and back.suspended_reason == "위생 문제"
        assert back.status == OfferStatus.SUSPENDED
        with pytest.raises(OfferAlreadySuspendedError):
            back.suspend("again", when)


async def test_offer_status_check_allows_suspended_rejects_bogus(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    async with client.session_factory() as s:
        await s.execute(
            text("UPDATE discount_offers SET status='SUSPENDED' WHERE id=:i"), {"i": uuid.UUID(o["id"])}
        )
        await s.commit()
    async with client.session_factory() as s:
        with pytest.raises(IntegrityError):
            await s.execute(
                text("UPDATE discount_offers SET status='BOGUS' WHERE id=:i"), {"i": uuid.UUID(o["id"])}
            )
        await s.rollback()


# ── 상태 SQL 조건 == effective_status (C6, CI-5) ──
async def test_status_clause_matches_effective_status_with_suspended(client):
    token, store_id = await owner_with_store(client)
    now = datetime.now(timezone.utc)
    sid = uuid.UUID(store_id)
    specs = {
        "on_sale": dict(start=-H, end=H, stock=3),
        "sold_out": dict(start=-H, end=H, stock=0),
        "scheduled": dict(start=H, end=2 * H, stock=3),
        "expired": dict(start=-3 * H, end=-H, stock=3),
        "inactive": dict(start=-H, end=H, stock=3, active=False),
        "susp_on_sale": dict(start=-H, end=H, stock=3, susp=True),
        "susp_sold_out": dict(start=-H, end=H, stock=0, susp=True),
        "susp_scheduled": dict(start=H, end=2 * H, stock=3, susp=True),
        "susp_expired": dict(start=-3 * H, end=-H, stock=3, susp=True),
        "susp_then_ended": dict(start=-H, end=H, stock=3, susp=True, active=False),
    }
    async with client.session_factory() as s:
        prod = await SqlAlchemyProductRepository(s).save(Product.register(sid, "p", 10000))
        offers = SqlAlchemyDiscountOfferRepository(s)
        saved = {}
        for key, sp in specs.items():
            susp = sp.get("susp", False)
            end = now + sp["end"]
            o = DiscountOffer(
                product_id=prod.id, sale_price=100, initial_stock=3, remaining_stock=sp["stock"],
                sales_start=now + sp["start"], sales_end=end, pickup_start=end, pickup_end=end + H,
                status=OfferStatus.SUSPENDED if susp else OfferStatus.ON_SALE,
                is_active=sp.get("active", True),
                suspended_reason="x" if susp else None, suspended_at=now - H if susp else None,
            )
            saved[key] = await offers.save(o)
        await s.commit()
    async with client.session_factory() as s:
        offers = SqlAlchemyDiscountOfferRepository(s)
        for status in OfferStatus:
            rows, total = await offers.find_by_store(sid, statuses=[status], now=now, page=1, size=100)
            expected = {o.id for o in saved.values() if o.effective_status(now) == status}
            assert {o.id for o, _ in rows} == expected and total == len(expected), status
        assert {k for k, o in saved.items() if o.effective_status(now) == OfferStatus.SUSPENDED} == {
            "susp_on_sale", "susp_sold_out", "susp_scheduled", "susp_expired",
        }
        rows, _ = await offers.find_by_store(sid, statuses=OPEN_OFFER_STATUSES, now=now, page=1, size=100)
        assert {o.id for o, _ in rows} == {saved[k].id for k in ("on_sale", "sold_out", "scheduled")}
        # 정지된 할인은 진행 중으로 센다 (D22)
        assert await offers.exists_open_by_store(sid, now)
        open_ids = {o.id for o in await offers.find_open_by_store_for_update(sid, now)}
        assert open_ids == {
            saved[k].id
            for k in ("on_sale", "sold_out", "scheduled", "susp_on_sale", "susp_sold_out", "susp_scheduled")
        }


# ── 잠금 조회 ──
async def test_find_all_and_open_by_store_for_update_ordering_and_scope(client):
    token, store_id = await owner_with_store(client)
    other_token, other_store = await owner_with_store(client, "o2@test.com")
    for name in ("c", "a", "b"):
        p = await make_product(client, token, store_id, name=name)
        await make_offer(client, token, p["id"])
    op = await make_product(client, other_token, other_store, name="other")
    await make_offer(client, other_token, op["id"])
    now = datetime.now(timezone.utc)
    async with client.session_factory() as s:
        products = SqlAlchemyProductRepository(s)
        offers = SqlAlchemyDiscountOfferRepository(s)
        prods = await products.find_all_by_store_for_update(uuid.UUID(store_id))
        assert len(prods) == 3 and [p.id for p in prods] == sorted(p.id for p in prods)
        assert {p.store_id for p in prods} == {uuid.UUID(store_id)}
        found = await offers.find_open_by_store_for_update(uuid.UUID(store_id), now)
        assert len(found) == 3 and [o.id for o in found] == sorted(o.id for o in found)
        assert {o.product_id for o in found} == {p.id for p in prods}
        assert await offers.find_open_by_store_for_update(uuid.uuid4(), now) == []
        assert await products.find_all_by_store_for_update(uuid.uuid4()) == []
        # 마감 이후 시각에는 진행 중인 할인이 없다
        assert await offers.find_open_by_store_for_update(uuid.UUID(store_id), now + 10 * H) == []
        # 비활성 할인은 제외
        found[0].end_sale(now)
        await offers.save(found[0])
        again = await offers.find_open_by_store_for_update(uuid.UUID(store_id), now)
        assert len(again) == 2 and found[0].id not in {o.id for o in again}


# ── 서비스(실제 레포) 통합: suspend_offer / end_all_sales_of_store ──
class _Clock:
    def now(self):
        return datetime.now(timezone.utc)


class _Stores:
    async def find_store_by_id(self, store_id):
        return None

    async def find_stores_by_ids(self, ids):
        return []


def _service(s):
    return CatalogApplicationService(
        session=s, stores=_Stores(), products=SqlAlchemyProductRepository(s),
        offers=SqlAlchemyDiscountOfferRepository(s), stock_logs=SqlAlchemyStockLogRepository(s),
        clock=_Clock(), reservations=None, reservation_cancel=None,
    )


async def test_service_suspend_offer_commit_and_rollback(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    now = datetime.now(timezone.utc)
    async with client.session_factory() as s:
        result = await _service(s).suspend_offer(uuid.UUID(o["id"]), "위생 문제", now=now, commit=False)
        assert result.status == OfferStatus.SUSPENDED and result.store_id == uuid.UUID(store_id)
        assert result.title == "샌드위치"
        await s.rollback()  # commit=False 후 롤백하면 반영되지 않는다
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
        assert m.suspended_at is None and m.status == "ON_SALE"
    async with client.session_factory() as s:
        await _service(s).suspend_offer(uuid.UUID(o["id"]), "위생 문제", now=now)
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(o["id"]))
        assert m.suspended_at == now and m.status == "SUSPENDED" and m.is_active is True


async def test_service_end_all_sales_of_store(client):
    token, store_id = await owner_with_store(client)
    ids = []
    for name in ("a", "b"):
        p = await make_product(client, token, store_id, name=name)
        ids.append((await make_offer(client, token, p["id"]))["id"])
    await suspend_offer_row(client, ids[1])
    now = datetime.now(timezone.utc)
    async with client.session_factory() as s:
        assert await _service(s).end_all_sales_of_store(uuid.UUID(store_id), now=now) == 2
    async with client.session_factory() as s:
        for i in ids:
            m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(i))
            assert m.is_active is False and m.status == "CLOSED" and m.remaining_stock == 10
        sus = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(ids[1]))
        assert sus.suspended_reason == "위생 문제" and sus.suspended_at is not None  # 이력 유지
        logs = (await s.execute(select(catalog_models.StockLogModel))).scalars().all()
        assert len(logs) == 2  # 최초 입고 2건만, 종료로 stock_log 추가 없음
    async with client.session_factory() as s:
        assert await _service(s).end_all_sales_of_store(uuid.UUID(store_id), now=now) == 0


# ── API: 정지된 할인 가시성 (D20, C7) ──
async def test_offer_detail_suspended_offer_visibility(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    await suspend_offer_row(client, o["id"])
    url = f"/v1/offers/{o['id']}"
    r = await client.get(url)
    assert r.status_code == 404 and r.json() == err(404, "NOT_FOUND", "할인 판매를 찾을 수 없습니다.")
    other = await token_for(client, "c@test.com", "CUSTOMER")
    r = await client.get(url, headers=bearer(other))
    assert r.status_code == 404
    r = await client.get(url, headers=bearer(token))
    assert r.status_code == 200 and r.json()["offer"]["status"] == "SUSPENDED"
    assert r.json()["offer"]["is_active"] is True


async def test_offer_detail_invalid_token_is_401(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    r = await client.get(f"/v1/offers/{o['id']}", headers={"Authorization": "Bearer bogus"})
    assert r.status_code == 401


async def test_store_offer_list_hides_suspended_offer_and_rejects_status_filter(client):
    token, store_id = await owner_with_store(client)
    p1 = await make_product(client, token, store_id, name="a")
    p2 = await make_product(client, token, store_id, name="b")
    keep = await make_offer(client, token, p1["id"])
    gone = await make_offer(client, token, p2["id"])
    await suspend_offer_row(client, gone["id"])
    url = f"/v1/stores/{store_id}/offers"
    ids = lambda r: {i["id"] for i in r.json()["items"]}  # noqa: E731
    assert ids(await client.get(url)) == {keep["id"]}
    r = await client.get(url, headers=bearer(token))  # 소유자도 기본 목록에서는 제외 (D20)
    assert ids(r) == {keep["id"]}
    for status in ("CLOSED", "ON_SALE", "SOLD_OUT", "SCHEDULED"):
        assert gone["id"] not in ids(await client.get(url, params={"status": status}))
    r = await client.get(url, params={"status": "SUSPENDED"})
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


# ── API: 정지된 상점 (D17, C8) ──
async def test_suspended_store_hidden_from_non_owner_but_visible_to_owner(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    await suspend_store_row(client, store_id)
    not_found = err(404, "NOT_FOUND", "상점을 찾을 수 없습니다.")
    cust = await token_for(client, "c@test.com", "CUSTOMER")
    for headers in ({}, bearer(cust)):
        r = await client.get(f"/v1/stores/{store_id}/products", headers=headers)
        assert r.status_code == 404 and r.json() == not_found
        r = await client.get(f"/v1/stores/{store_id}/offers", headers=headers)
        assert r.status_code == 404 and r.json() == not_found
        r = await client.get(f"/v1/products/{p['id']}", headers=headers)
        assert r.status_code == 404 and r.json() == not_found
        r = await client.get(f"/v1/offers/{o['id']}", headers=headers)
        assert r.status_code == 404
        assert r.json() == err(404, "NOT_FOUND", "할인 판매를 찾을 수 없습니다.")
    r = await client.get(f"/v1/stores/{store_id}/products", headers=bearer(token))
    assert r.status_code == 200 and r.json()["total"] == 1
    assert (await client.get(f"/v1/stores/{store_id}/offers", headers=bearer(token))).status_code == 200
    assert (await client.get(f"/v1/products/{p['id']}", headers=bearer(token))).status_code == 200
    r = await client.get(f"/v1/offers/{o['id']}", headers=bearer(token))
    assert r.status_code == 200 and r.json()["offer"]["status"] == "ON_SALE"


async def test_suspended_store_blocks_product_and_offer_registration(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    old = await make_offer(client, token, p["id"])
    p2 = await make_product(client, token, store_id, name="b")
    await suspend_store_row(client, store_id)
    expect = err(400, "STORE_SUSPENDED", "관리자에 의해 정지된 상점입니다.")
    r = await client.post(
        f"/v1/stores/{store_id}/products", json={"name": "x", "original_price": 1}, headers=bearer(token)
    )
    assert r.status_code == 400 and r.json() == expect
    r = await client.post(f"/v1/products/{p2['id']}/offers", json=offer_body(), headers=bearer(token))
    assert r.status_code == 400 and r.json() == expect
    r = await client.post(f"/v1/offers/{old['id']}/relist", json=offer_body(), headers=bearer(token))
    assert r.status_code == 400 and r.json() == expect


# ── API: 정지된 할인에 대한 상점주 조작 (D20) ──
async def test_owner_operations_on_suspended_offer_return_offer_suspended(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"])
    await suspend_offer_row(client, o["id"])
    expect = err(400, "OFFER_SUSPENDED", "관리자에 의해 정지된 상품입니다.")
    h = bearer(token)
    oid = o["id"]
    for r in (
        await client.patch(f"/v1/offers/{oid}", json={"is_active": False}, headers=h),
        await client.patch(f"/v1/offers/{oid}", json={"is_active": True}, headers=h),
        await client.patch(f"/v1/offers/{oid}", json={"sale_price": 2000}, headers=h),
        await client.post(f"/v1/offers/{oid}/deactivate", json={"reason": "x"}, headers=h),
        await client.post(f"/v1/offers/{oid}/relist", json=offer_body(), headers=h),
        await client.post(f"/v1/offers/{oid}/stock-adjustments", json={"amount": 1}, headers=h),
    ):
        assert r.status_code == 400 and r.json() == expect, r.text
    async with client.session_factory() as s:
        m = await s.get(catalog_models.DiscountOfferModel, uuid.UUID(oid))
        assert m.is_active and m.status == "SUSPENDED" and m.remaining_stock == 10
        logs = (await s.execute(select(catalog_models.StockLogModel))).scalars().all()
        assert len(logs) == 1
    # 같은 상품에 새 할인 등록 불가: 정지된 할인도 진행 중 (D22)
    r = await client.post(f"/v1/products/{p['id']}/offers", json=offer_body(), headers=h)
    assert r.status_code == 400 and r.json()["error_code"] == "OFFER_ALREADY_OPEN"


async def test_invalid_offer_response_status_includes_suspended_for_owner_detail(client):
    token, store_id = await owner_with_store(client)
    p = await make_product(client, token, store_id)
    o = await make_offer(client, token, p["id"], sales_start=iso(datetime.now(timezone.utc) + H // 2))
    await suspend_offer_row(client, o["id"])
    r = await client.get(f"/v1/offers/{o['id']}", headers=bearer(token))
    assert r.status_code == 200 and r.json()["offer"]["status"] == "SUSPENDED"
