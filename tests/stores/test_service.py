import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

import pytest

from stores.application.query_service import StoreQueryService
from stores.application.service import StoresApplicationService
from stores.domain.exceptions import (
    NotStoreOwnerError,
    StoreAlreadyClosedError,
    StoreAlreadyExistsError,
    StoreHasOpenOffersError,
    StoreHasReservedReservationsError,
    StoreNotFoundError,
    StoreSuspendedError,
)
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

    async def find_by_owner_id(self, owner_id, for_update=False):
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


class FakeOpenOffers:
    def __init__(self, value=False):
        self.value = value
        self.calls = []

    async def has_open_offers_for_store(self, store_id, *, now=None):
        self.calls.append((store_id, now))
        return self.value


class FakePickupPending:
    def __init__(self, value=False):
        self.value = value
        self.calls = []

    async def has_pickup_pending_for_store(self, store_id):
        self.calls.append(store_id)
        return self.value


def build(repo=None, open_offers=None, pickup_pending=None):
    session = FakeSession()
    repo = repo or FakeStoreRepository()
    service = StoresApplicationService(
        session=session,
        stores=repo,
        clock=FakeClock(),
        open_offers=open_offers or FakeOpenOffers(),
        pickup_pending=pickup_pending or FakePickupPending(),
    )
    return service, session, repo


def build_query(repo=None):
    repo = repo or FakeStoreRepository()
    return StoreQueryService(stores=repo), repo


async def _seed(service, owner=None):
    owner = owner or uuid.uuid4()
    store = await service.open_store(owner, "상호", "주소")
    return owner, store


async def test_find_store_by_id_none():
    query, _ = build_query()
    assert await query.find_store_by_id(uuid.uuid4()) is None


async def test_find_store_by_id_found():
    service, _, repo = build()
    store = await service.open_store(uuid.uuid4(), "상호", "주소")
    query, _ = build_query(repo)
    assert await query.find_store_by_id(store.id) is store


async def test_find_stores_by_ids():
    service, session, repo = build()
    a = await service.open_store(uuid.uuid4(), "A", "주소")
    b = await service.open_store(uuid.uuid4(), "B", "주소")
    query, _ = build_query(repo)
    assert await query.find_stores_by_ids([]) == []
    result = await query.find_stores_by_ids([a.id, uuid.uuid4(), b.id, a.id])
    assert result == [a, b]


# ── close_store ──
async def test_close_store_ok():
    offers, pending = FakeOpenOffers(), FakePickupPending()
    service, session, repo = build(open_offers=offers, pickup_pending=pending)
    owner, store = await _seed(service)
    saved_before, commits_before = repo.saved, session.commits
    result = await service.close_store(owner, store.id)
    assert result is store and store.closed_at == FIXED
    assert repo.saved == saved_before + 1
    assert session.commits == commits_before + 1
    assert offers.calls == [(store.id, FIXED)]
    assert pending.calls == [store.id]


async def test_close_store_not_found():
    service, session, repo = build()
    with pytest.raises(StoreNotFoundError):
        await service.close_store(uuid.uuid4(), uuid.uuid4())
    assert session.commits == 0 and repo.saved == 0


async def test_close_store_not_owner_skips_ports():
    offers, pending = FakeOpenOffers(), FakePickupPending()
    service, session, repo = build(open_offers=offers, pickup_pending=pending)
    _, store = await _seed(service)
    commits, saved = session.commits, repo.saved
    with pytest.raises(NotStoreOwnerError, match="본인 상점만 폐점할 수 있습니다."):
        await service.close_store(uuid.uuid4(), store.id)
    assert offers.calls == [] and pending.calls == []
    assert session.commits == commits and repo.saved == saved
    assert store.closed_at is None


async def test_close_store_open_offers():
    offers = FakeOpenOffers(True)
    service, session, repo = build(open_offers=offers)
    owner, store = await _seed(service)
    commits, saved = session.commits, repo.saved
    with pytest.raises(StoreHasOpenOffersError):
        await service.close_store(owner, store.id)
    assert offers.calls == [(store.id, FIXED)]
    assert session.commits == commits and repo.saved == saved
    assert store.closed_at is None


async def test_close_store_pickup_pending():
    service, session, _ = build(pickup_pending=FakePickupPending(True))
    owner, store = await _seed(service)
    commits = session.commits
    with pytest.raises(StoreHasReservedReservationsError, match="픽업 대기 중인 예약"):
        await service.close_store(owner, store.id)
    assert session.commits == commits and store.closed_at is None


async def test_close_store_already_closed():
    service, _, _ = build()
    owner, store = await _seed(service)
    await service.close_store(owner, store.id)
    with pytest.raises(StoreAlreadyClosedError):
        await service.close_store(owner, store.id)


async def test_close_store_suspended_wins_over_open_offers():
    service, session, _ = build(open_offers=FakeOpenOffers(True))
    owner, store = await _seed(service)
    store.suspend("사유", FIXED)
    with pytest.raises(StoreSuspendedError):
        await service.close_store(owner, store.id)
    assert store.closed_at is None


async def test_close_store_commit_false():
    service, session, _ = build()
    owner, store = await _seed(service)
    commits = session.commits
    await service.close_store(owner, store.id, commit=False)
    assert session.commits == commits and store.closed_at == FIXED


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
