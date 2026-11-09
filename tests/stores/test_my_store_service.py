"""StoreQueryService.get_store_of_owner (stores.md 17.3, T12). DB 불필요."""

import uuid
from datetime import datetime, timezone

import pytest

from stores.application.query_service import StoreQueryService
from stores.domain.exceptions import StoreNotFoundError
from stores.domain.repository import StoreRepository
from stores.domain.store import Store

pytestmark = pytest.mark.anyio

NOW = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeRepo(StoreRepository):
    def __init__(self, stores=()):
        self.items = list(stores)
        self.owner_calls: list[tuple[uuid.UUID, bool]] = []

    async def find_by_id(self, store_id, for_update=False): ...

    async def find_by_ids(self, store_ids): ...

    async def find_by_owner_id(self, owner_id, for_update=False):
        self.owner_calls.append((owner_id, for_update))
        return next((s for s in self.items if s.owner_id == owner_id), None)

    async def exists_by_name_and_address(self, name, pickup_address): ...

    async def find_visible_near(self, *, latitude, longitude, radius_km): ...

    async def save(self, store): ...


async def test_returns_same_store_and_does_not_lock():
    owner = uuid.uuid4()
    store = Store(owner_id=owner, name="상호", pickup_address="주소", approval_at=NOW)
    repo = FakeRepo([store, Store(owner_id=uuid.uuid4(), name="다른", pickup_address="다른주소")])
    result = await StoreQueryService(repo).get_store_of_owner(owner)
    assert result is store
    assert repo.owner_calls == [(owner, False)]


async def test_closed_and_suspended_stores_are_returned():
    owner = uuid.uuid4()
    store = Store(
        owner_id=owner, name="상호", pickup_address="주소", approval_at=NOW, closed_at=NOW,
        suspended_reason="x", suspended_at=NOW,
    )
    assert await StoreQueryService(FakeRepo([store])).get_store_of_owner(owner) is store


async def test_missing_store_raises_store_not_found():
    repo = FakeRepo()
    owner = uuid.uuid4()
    with pytest.raises(StoreNotFoundError) as e:
        await StoreQueryService(repo).get_store_of_owner(owner)
    assert str(e.value) == "상점을 찾을 수 없습니다."
    assert repo.owner_calls == [(owner, False)]


def test_query_service_has_no_commit():
    assert not hasattr(StoreQueryService(FakeRepo()), "commit")
