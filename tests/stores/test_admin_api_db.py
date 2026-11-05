from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from auth.infrastructure import models as auth_models  # noqa: F401
from auth.infrastructure.models import UserModel
from stores.domain.store import Store
from stores.infrastructure import models as stores_models  # noqa: F401
from stores.infrastructure.repositories import SqlAlchemyStoreRepository
from tests.helpers import bearer, login, signup

pytestmark = [pytest.mark.db, pytest.mark.anyio]

NOW = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)


async def test_open_store_pending_owner_forbidden(client):
    await signup(client, "pend@test.com", "OWNER")
    token = (await login(client, "pend@test.com")).json()["access_token"]
    r = await client.post("/v1/stores", json={"pickup_address": "주소"}, headers=bearer(token))
    assert r.status_code == 403
    body = r.json()
    assert body["success"] is False and body["error_code"] == "FORBIDDEN"
    assert body["message"] == "승인 대기 중인 상점주 계정입니다."


async def test_repository_suspend_and_close_roundtrip(client):
    await signup(client, "adm@test.com", "OWNER")
    async with client.session_factory() as s:
        owner = (
            await s.execute(select(UserModel.id).where(UserModel.email == "adm@test.com"))
        ).scalar_one()
    async with client.session_factory() as session:
        repo = SqlAlchemyStoreRepository(session)
        saved = await repo.save(Store.open(owner, "상호", "주소", NOW))
        saved.suspend("위반", NOW)
        await repo.save(saved)
        await session.commit()
    async with client.session_factory() as session:
        repo = SqlAlchemyStoreRepository(session)
        loaded = await repo.find_by_owner_id(owner, for_update=True)
        assert loaded.status == "SUSPENDED" and loaded.suspended_reason == "위반"
        assert loaded.suspended_at == NOW and loaded.suspended_at.tzinfo is not None
        loaded.force_close("폐점", NOW, False)
        await repo.save(loaded)
        await session.commit()
    async with client.session_factory() as session:
        again = await SqlAlchemyStoreRepository(session).find_by_id(saved.id, for_update=True)
        assert again.status == "CLOSED" and again.closed_reason == "폐점"
        assert again.closed_at == NOW and again.suspended_at == NOW


@pytest.mark.parametrize("lookup", ["id", "owner"])
async def test_for_update_refreshes_stale_identity_map(client, lookup):
    from stores.domain.exceptions import StoreAlreadySuspendedError
    from stores.infrastructure.models import StoreModel

    email = f"stale-{lookup}@test.com"
    await signup(client, email, "OWNER")
    async with client.session_factory() as s:
        owner = (await s.execute(select(UserModel.id).where(UserModel.email == email))).scalar_one()
    async with client.session_factory() as s:
        store = await SqlAlchemyStoreRepository(s).save(Store.open(owner, "상호", "주소", NOW))
        await s.commit()
    async with client.session_factory() as a:
        repo_a = SqlAlchemyStoreRepository(a)
        held = await a.get(StoreModel, store.id)  # identity map에 유지
        assert held.suspended_at is None
        async with client.session_factory() as b:
            repo_b = SqlAlchemyStoreRepository(b)
            other = await repo_b.find_by_id(store.id, for_update=True)
            other.suspend("위반", NOW)
            await repo_b.save(other)
            await b.commit()
        if lookup == "id":
            fresh = await repo_a.find_by_id(store.id, for_update=True)
        else:
            fresh = await repo_a.find_by_owner_id(owner, for_update=True)
        with pytest.raises(StoreAlreadySuspendedError):
            fresh.suspend("again", NOW)
