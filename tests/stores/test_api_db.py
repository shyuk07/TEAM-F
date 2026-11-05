import uuid
from datetime import datetime

import httpx
import pytest
from sqlalchemy import text

from auth.infrastructure import models as auth_models  # noqa: F401
from database import get_db
from main import app
from stores.domain.exceptions import StoreAlreadyExistsError
from stores.domain.store import Store
from stores.infrastructure import models as stores_models  # noqa: F401
from stores.infrastructure.repositories import SqlAlchemyStoreRepository
from tests.fakes import DEFAULT_COORDINATES as COORDS
from tests.helpers import approve_owner, bearer, login, signup, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]


async def owner_token(c, email="owner@test.com"):
    return await token_for(c, email, "OWNER")


async def test_open_store_ok(client):
    token = await owner_token(client)
    r = await client.post(
        "/v1/stores", json={"pickup_address": "서울특별시 강남구 테헤란로 123"}, headers=bearer(token)
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {
        "id", "owner_id", "name", "pickup_address", "latitude", "longitude",
        "created_at", "approval_at", "closed_at",
    }
    assert body["name"] == "홍길동"
    assert body["pickup_address"] == "서울특별시 강남구 테헤란로 123"
    assert isinstance(body["latitude"], float) and isinstance(body["longitude"], float)
    assert (body["latitude"], body["longitude"]) == (37.4979, 127.0276)  # FakeGeocoder 기본값
    assert client.geocoder.calls == ["서울특별시 강남구 테헤란로 123"]
    assert body["closed_at"] is None
    uuid.UUID(body["id"]), uuid.UUID(body["owner_id"])
    assert datetime.fromisoformat(body["created_at"]).tzinfo is not None
    assert datetime.fromisoformat(body["approval_at"]).tzinfo is not None


async def test_open_store_unauthorized(client):
    r = await client.post("/v1/stores", json={"pickup_address": "주소"})
    assert r.status_code == 401 and r.json()["success"] is False
    assert r.headers["www-authenticate"] == "Bearer"


async def test_open_store_customer_forbidden(client):
    token = await token_for(client, "c@test.com", "CUSTOMER")
    r = await client.post("/v1/stores", json={"pickup_address": "주소"}, headers=bearer(token))
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"
    assert r.json()["success"] is False


async def test_open_store_second_is_400(client):
    token = await owner_token(client)
    await client.post("/v1/stores", json={"pickup_address": "주소1"}, headers=bearer(token))
    r = await client.post("/v1/stores", json={"pickup_address": "주소2"}, headers=bearer(token))
    assert r.status_code == 400
    assert r.json() == {
        "success": False,
        "error_code": "STORE_ALREADY_EXISTS",
        "message": "이미 개설된 상점이 있습니다.",
    }
    assert client.geocoder.calls == ["주소1"]  # 두 번째 호출은 지오코더에 닿지 않는다


async def test_open_store_blank_address(client):
    token = await owner_token(client)
    r = await client.post("/v1/stores", json={"pickup_address": "   "}, headers=bearer(token))
    assert r.status_code == 400
    assert r.json()["message"] == "주소를 입력해 주세요."


async def test_open_store_validation(client):
    token = await owner_token(client)
    for payload in [{}, {"pickup_address": "a" * 501}]:
        r = await client.post("/v1/stores", json=payload, headers=bearer(token))
        assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


async def test_open_store_owner_without_name(client):
    # 가입은 이름이 필수가 되었으므로, 이름 없는 기존 회원은 가입 뒤 DB에서 이름을 지워 만든다.
    await signup(client, "n@test.com", "OWNER")
    async with client.session_factory() as s:
        await s.execute(text("UPDATE users SET name = NULL WHERE email = 'n@test.com'"))
        await s.commit()
    await approve_owner(client, "n@test.com")
    token = (await login(client, "n@test.com")).json()["access_token"]
    r = await client.post("/v1/stores", json={"pickup_address": "주소"}, headers=bearer(token))
    assert r.status_code == 400
    assert r.json()["message"] == "상점명은 1자 이상 150자 이하여야 합니다."


async def _owner_id(client, email):
    await signup(client, email, "OWNER")
    async with client.session_factory() as s:
        from sqlalchemy import select
        from auth.infrastructure.models import UserModel

        return (await s.execute(select(UserModel.id).where(UserModel.email == email))).scalar_one()


async def test_repository_roundtrip(client):
    from datetime import timezone

    owner = await _owner_id(client, "r@test.com")
    async with client.session_factory() as s:
        repo = SqlAlchemyStoreRepository(s)
        now = datetime.now(timezone.utc)
        saved = await repo.save(Store.open(owner, "상호", "주소", now, COORDS))
        await s.commit()
        assert saved.id is not None and saved.created_at.tzinfo is not None
    async with client.session_factory() as s:
        repo = SqlAlchemyStoreRepository(s)
        found = await repo.find_by_id(saved.id)
        assert found.name == "상호"
        assert (found.latitude, found.longitude) == (COORDS.latitude, COORDS.longitude)
        assert found.approval_at == now and found.approval_at.tzinfo is not None
        assert (await repo.find_by_owner_id(owner)).id == saved.id
        assert await repo.find_by_id(uuid.uuid4()) is None
        found.close(datetime.now(timezone.utc))
        await repo.save(found)
        await s.commit()
    async with client.session_factory() as s:
        assert (await SqlAlchemyStoreRepository(s).find_by_id(saved.id, for_update=True)).is_closed


async def test_repository_unique_owner_converted(client):
    owner = await _owner_id(client, "u@test.com")
    async with client.session_factory() as s:
        repo = SqlAlchemyStoreRepository(s)
        await repo.save(Store(owner_id=owner, name="A", pickup_address="a"))
        with pytest.raises(StoreAlreadyExistsError):
            await repo.save(Store(owner_id=owner, name="B", pickup_address="b"))


async def test_repository_fk_violation_not_converted(client):
    from sqlalchemy.exc import IntegrityError

    async with client.session_factory() as s:
        repo = SqlAlchemyStoreRepository(s)
        with pytest.raises(IntegrityError):
            await repo.save(Store(owner_id=uuid.uuid4(), name="A", pickup_address="a"))


async def test_repository_find_by_ids(client):
    o1 = await _owner_id(client, "a@test.com")
    o2 = await _owner_id(client, "b@test.com")
    async with client.session_factory() as s:
        repo = SqlAlchemyStoreRepository(s)
        a = await repo.save(Store(owner_id=o1, name="A", pickup_address="a"))
        b = await repo.save(Store(owner_id=o2, name="B", pickup_address="b"))
        assert await repo.find_by_ids([]) == []
        got = await repo.find_by_ids([a.id, b.id, a.id, uuid.uuid4()])
        assert sorted(x.id for x in got) == sorted([a.id, b.id])
        assert [x.id for x in got] == sorted(x.id for x in got)


# ── POST /v1/stores/{store_id}/close ──
import asyncio  # noqa: E402
from datetime import timedelta, timezone  # noqa: E402

from sqlalchemy import text  # noqa: E402

from catalog.infrastructure import models as catalog_models  # noqa: E402,F401
from container import create_pickup_pending_port  # noqa: E402
from tests.catalog.test_api_db import make_offer, make_product, offer_body, owner_with_store  # noqa: E402
from tests.catalog.test_admin_api_db import suspend_offer_row, suspend_store_row  # noqa: E402

_H = timedelta(hours=1)


def _fail(r, status, code, message):
    assert r.status_code == status, r.text
    assert r.json() == {"success": False, "error_code": code, "message": message}


async def _close(c, token, store_id):
    return await c.post(f"/v1/stores/{store_id}/close", headers=bearer(token) if token else {})


async def _closed_at_in_db(c, store_id):
    async with c.session_factory() as s:
        return (
            await s.execute(
                text("SELECT closed_at FROM stores WHERE id=:i"), {"i": uuid.UUID(store_id)}
            )
        ).scalar_one()


async def test_close_store_ok(client):
    token, sid = await owner_with_store(client)
    r = await _close(client, token, sid)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"id", "name", "closed_at"}
    assert body["id"] == sid and body["name"] == "홍길동"
    assert datetime.fromisoformat(body["closed_at"]).tzinfo is not None
    assert await _closed_at_in_db(client, sid) is not None


async def test_close_store_unauthorized(client):
    r = await _close(client, None, str(uuid.uuid4()))
    assert r.status_code == 401 and r.json()["success"] is False
    assert r.headers["www-authenticate"] == "Bearer"


async def test_close_store_customer_forbidden(client):
    token = await token_for(client, "c@test.com", "CUSTOMER")
    r = await _close(client, token, uuid.uuid4())
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN"


async def test_close_store_pending_owner_forbidden(client):
    await signup(client, "p@test.com", "OWNER")
    token = (await login(client, "p@test.com")).json()["access_token"]
    r = await _close(client, token, uuid.uuid4())
    _fail(r, 403, "FORBIDDEN", "승인 대기 중인 상점주 계정입니다.")


async def test_close_store_suspended_owner_account_forbidden(client):
    token, sid = await owner_with_store(client)
    async with client.session_factory() as s:
        await s.execute(
            text(
                "UPDATE users SET status='SUSPENDED', suspended_reason='x', "
                "suspended_at=now() WHERE email='owner@test.com'"
            )
        )
        await s.commit()
    r = await _close(client, token, sid)
    _fail(r, 403, "FORBIDDEN", "정지된 계정입니다.")
    assert await _closed_at_in_db(client, sid) is None


async def test_close_store_not_owner(client):
    _, sid = await owner_with_store(client)
    other = await token_for(client, "other@test.com", "OWNER")
    r = await _close(client, other, sid)
    _fail(r, 403, "FORBIDDEN", "본인 상점만 폐점할 수 있습니다.")
    assert await _closed_at_in_db(client, sid) is None


async def test_close_store_not_found(client):
    token = await owner_token(client)
    r = await _close(client, token, uuid.uuid4())
    _fail(r, 404, "NOT_FOUND", "상점을 찾을 수 없습니다.")


async def test_close_store_bad_uuid(client):
    token = await owner_token(client)
    r = await client.post("/v1/stores/not-a-uuid/close", headers=bearer(token))
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


async def test_close_store_already_closed(client):
    token, sid = await owner_with_store(client)
    assert (await _close(client, token, sid)).status_code == 200
    r = await _close(client, token, sid)
    _fail(r, 400, "STORE_ALREADY_CLOSED", "이미 폐점된 상점입니다.")


async def test_close_store_suspended_store(client):
    token, sid = await owner_with_store(client)
    await suspend_store_row(client, sid)
    r = await _close(client, token, sid)
    _fail(r, 400, "STORE_SUSPENDED", "관리자에 의해 정지된 상점입니다.")
    assert await _closed_at_in_db(client, sid) is None


_OPEN_MSG = "진행 중이거나 예정된 할인 판매가 있어 폐점할 수 없습니다."


async def test_close_store_blocked_by_open_offer(client):
    token, sid = await owner_with_store(client)
    p = await make_product(client, token, sid)
    await make_offer(client, token, p["id"])
    r = await _close(client, token, sid)
    _fail(r, 400, "STORE_HAS_OPEN_OFFERS", _OPEN_MSG)
    assert await _closed_at_in_db(client, sid) is None


async def test_close_store_blocked_by_scheduled_offer(client):
    token, sid = await owner_with_store(client)
    p = await make_product(client, token, sid)
    now = datetime.now(timezone.utc)
    await make_offer(
        client, token, p["id"],
        sales_start=(now + _H).isoformat(), sales_end=(now + 2 * _H).isoformat(),
        pickup_start=(now + 2 * _H).isoformat(), pickup_end=(now + 3 * _H).isoformat(),
    )
    r = await _close(client, token, sid)
    _fail(r, 400, "STORE_HAS_OPEN_OFFERS", _OPEN_MSG)


async def test_close_store_suspended_offer_still_blocks(client):
    token, sid = await owner_with_store(client)
    p = await make_product(client, token, sid)
    o = await make_offer(client, token, p["id"])
    await suspend_offer_row(client, o["id"])
    r = await _close(client, token, sid)
    _fail(r, 400, "STORE_HAS_OPEN_OFFERS", _OPEN_MSG)
    assert await _closed_at_in_db(client, sid) is None


async def test_close_store_inactive_and_expired_offers_pass(client):
    token, sid = await owner_with_store(client)
    p = await make_product(client, token, sid)
    p2 = await make_product(client, token, sid, name="두번째")
    inactive = await make_offer(client, token, p["id"])
    expired = await make_offer(client, token, p2["id"])
    async with client.session_factory() as s:
        await s.execute(
            text("UPDATE discount_offers SET is_active=false WHERE id=:i"),
            {"i": uuid.UUID(inactive["id"])},
        )
        past = datetime.now(timezone.utc) - _H
        await s.execute(
            text("UPDATE discount_offers SET sales_start=:a, sales_end=:b WHERE id=:i"),
            {"a": past - _H, "b": past, "i": uuid.UUID(expired["id"])},
        )
        await s.commit()
    r = await _close(client, token, sid)
    assert r.status_code == 200, r.text


async def test_close_store_then_cannot_register_products_or_offers(client):
    token, sid = await owner_with_store(client)
    p = await make_product(client, token, sid)
    o = await make_offer(client, token, p["id"])
    async with client.session_factory() as s:
        await s.execute(
            text("UPDATE discount_offers SET is_active=false WHERE id=:i"), {"i": uuid.UUID(o["id"])}
        )
        await s.commit()
    assert (await _close(client, token, sid)).status_code == 200
    r = await client.post(
        f"/v1/stores/{sid}/products",
        json={"name": "x", "original_price": 1000, "category": "c"},
        headers=bearer(token),
    )
    assert r.status_code == 400, r.text
    r = await client.post(
        f"/v1/products/{p['id']}/offers", json=offer_body(), headers=bearer(token)
    )
    assert r.status_code == 400, r.text


async def test_close_store_pickup_pending_override(client):
    class AlwaysPending:
        async def has_pickup_pending_for_store(self, store_id):
            return True

    token, sid = await owner_with_store(client)
    original = app.dependency_overrides[create_pickup_pending_port]  # wire_dependencies가 넣은 실제 연결
    app.dependency_overrides[create_pickup_pending_port] = lambda: AlwaysPending()
    try:
        r = await _close(client, token, sid)
    finally:
        app.dependency_overrides[create_pickup_pending_port] = original
    _fail(r, 400, "STORE_HAS_RESERVED_RESERVATIONS", "픽업 대기 중인 예약이 있어 폐점할 수 없습니다.")
    assert await _closed_at_in_db(client, sid) is None


async def test_close_store_concurrent_double_close(client):
    # 잔여 경합(C12: 폐점 확인 직후 신규 할인 등록)은 catalog 후속 작업이라 테스트하지 않는다.
    token, sid = await owner_with_store(client)
    rs = await asyncio.gather(_close(client, token, sid), _close(client, token, sid))
    assert sorted(r.status_code for r in rs) == [200, 400], [r.text for r in rs]
    bad = next(r for r in rs if r.status_code == 400)
    assert bad.json()["error_code"] == "STORE_ALREADY_CLOSED"
    assert await _closed_at_in_db(client, sid) is not None
