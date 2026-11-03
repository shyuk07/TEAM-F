import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

import pytest

from stores.application.service import StoresApplicationService
from stores.domain.exceptions import StoreAlreadyExistsError
from stores.domain.repository import StoreRepository
from stores.domain.service import Clock
from stores.domain.store import Store

pytestmark = pytest.mark.anyio

FIXED = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeSession:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


class FakeClock(Clock):
    def now(self):
        return FIXED


class FakeStoreRepository(StoreRepository):
    def __init__(self, race_on_save=False):
        self.items: dict[uuid.UUID, Store] = {}
        self.race_on_save = race_on_save
        self.saved = 0

    async def find_by_id(self, store_id, for_update=False):
        return self.items.get(store_id)

    async def find_by_ids(self, store_ids: Sequence[uuid.UUID]):
        return [self.items[i] for i in dict.fromkeys(store_ids) if i in self.items]

    async def find_by_owner_id(self, owner_id):
        return next((s for s in self.items.values() if s.owner_id == owner_id), None)

    async def save(self, store):
        if self.race_on_save:
            raise StoreAlreadyExistsError()
        if store.id is None:
            store.id = uuid.uuid4()
            store.created_at = FIXED
        self.items[store.id] = store
        self.saved += 1
        return store


def build(repo=None):
    session = FakeSession()
    repo = repo or FakeStoreRepository()
    return StoresApplicationService(session=session, stores=repo, clock=FakeClock()), session, repo


async def test_find_store_by_id_none():
    service, session, _ = build()
    assert await service.find_store_by_id(uuid.uuid4()) is None
    assert session.commits == 0


async def test_find_store_by_id_found():
    service, _, repo = build()
    store = await service.open_store(uuid.uuid4(), "상호", "주소")
    assert await service.find_store_by_id(store.id) is store


async def test_find_stores_by_ids():
    service, session, _ = build()
    a = await service.open_store(uuid.uuid4(), "A", "주소")
    b = await service.open_store(uuid.uuid4(), "B", "주소")
    assert await service.find_stores_by_ids([]) == []
    result = await service.find_stores_by_ids([a.id, uuid.uuid4(), b.id, a.id])
    assert result == [a, b]


async def test_open_store_ok():
    service, session, repo = build()
    owner = uuid.uuid4()
    store = await service.open_store(owner, "상호", " 서울시 ")
    assert store.id is not None and store.owner_id == owner
    assert store.name == "상호" and store.pickup_address == "서울시"
    assert store.approval_at == FIXED and store.closed_at is None
    assert store.latitude is None and store.longitude is None
    assert session.commits == 1


async def test_open_store_duplicate_owner():
    service, session, _ = build()
    owner = uuid.uuid4()
    await service.open_store(owner, "상호", "주소")
    with pytest.raises(StoreAlreadyExistsError, match="이미 개설된 상점이 있습니다."):
        await service.open_store(owner, "상호", "다른주소")
    assert session.commits == 1


@pytest.mark.parametrize("name", [None, "", "  "])
async def test_open_store_no_name(name):
    service, session, repo = build()
    with pytest.raises(ValueError, match="상점명은 1자 이상 150자 이하여야 합니다."):
        await service.open_store(uuid.uuid4(), name, "주소")
    assert session.commits == 0 and repo.saved == 0


async def test_open_store_empty_address():
    service, session, _ = build()
    with pytest.raises(ValueError, match="주소를 입력해 주세요."):
        await service.open_store(uuid.uuid4(), "상호", " ")
    assert session.commits == 0


async def test_open_store_race_no_commit():
    service, session, _ = build(FakeStoreRepository(race_on_save=True))
    with pytest.raises(StoreAlreadyExistsError):
        await service.open_store(uuid.uuid4(), "상호", "주소")
    assert session.commits == 0
