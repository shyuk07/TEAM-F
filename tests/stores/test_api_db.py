import uuid
from datetime import datetime

import httpx
import pytest

from auth.infrastructure import models as auth_models  # noqa: F401
from database import get_db
from main import app
from stores.domain.exceptions import StoreAlreadyExistsError
from stores.domain.store import Store
from stores.infrastructure import models as stores_models  # noqa: F401
from stores.infrastructure.repositories import SqlAlchemyStoreRepository
from tests.helpers import bearer, login, signup, token_for

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
    assert body["name"] == "홍길동"
    assert body["pickup_address"] == "서울특별시 강남구 테헤란로 123"
    assert body["latitude"] is None and body["longitude"] is None
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
    await client.post(
        "/v1/auth/signup",
        json={"email": "n@test.com", "password": "password123", "role": "OWNER"},
    )
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
        saved = await repo.save(Store.open(owner, "상호", "주소", now))
        await s.commit()
        assert saved.id is not None and saved.created_at.tzinfo is not None
    async with client.session_factory() as s:
        repo = SqlAlchemyStoreRepository(s)
        found = await repo.find_by_id(saved.id)
        assert found.name == "상호" and found.latitude is None
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
