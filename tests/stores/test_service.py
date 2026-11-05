import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

import pytest

from stores.application.query_service import StoreQueryService
from stores.application.service import StoresApplicationService
from stores.domain.exceptions import (
    AddressNotFoundError,
    GeocodingUnavailableError,
    NotStoreOwnerError,
    StoreAlreadyClosedError,
    StoreAlreadyExistsError,
    StoreDuplicatedError,
    StoreHasOpenOffersError,
    StoreHasReservedReservationsError,
    StoreNotFoundError,
    StoreSuspendedError,
)
from stores.domain.repository import StoreRepository
from stores.domain.service import Clock
from stores.domain.store import Store
from tests.fakes import DEFAULT_COORDINATES, FakeGeocoder

pytestmark = pytest.mark.anyio

FIXED = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeSession:
    def __init__(self, events=None):
        self.commits = 0
        self.events = events if events is not None else []

    async def commit(self):
        self.commits += 1
        self.events.append("commit")


class FakeClock(Clock):
    def __init__(self, events=None):
        self.events = events if events is not None else []

    def now(self):
        self.events.append("clock.now")
        return FIXED


class FakeStoreRepository(StoreRepository):
    def __init__(self, race_on_save=False, events=None):
        self.items: dict[uuid.UUID, Store] = {}
        self.race_on_save = race_on_save  # True 또는 던질 예외 클래스
        self.saved = 0
        self.events = events if events is not None else []
        self.lookups = 0

    async def find_by_id(self, store_id, for_update=False):
        return self.items.get(store_id)

    async def find_by_ids(self, store_ids: Sequence[uuid.UUID]):
        return [self.items[i] for i in dict.fromkeys(store_ids) if i in self.items]

    async def find_by_owner_id(self, owner_id, for_update=False):
        self.lookups += 1
        self.events.append("find_by_owner_id")
        return next((s for s in self.items.values() if s.owner_id == owner_id), None)

    async def exists_by_name_and_address(self, name, pickup_address):
        self.lookups += 1
        self.events.append("exists_by_name_and_address")
        return any(s.name == name and s.pickup_address == pickup_address for s in self.items.values())

    async def save(self, store):
        if self.race_on_save:
            raise (StoreAlreadyExistsError if self.race_on_save is True else self.race_on_save)()
        self.events.append("save")
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


def build(repo=None, open_offers=None, pickup_pending=None, geocoder=None, events=None):
    events = events if events is not None else []
    session = FakeSession(events)
    repo = repo or FakeStoreRepository(events=events)
    service = StoresApplicationService(
        session=session,
        stores=repo,
        clock=FakeClock(events),
        open_offers=open_offers or FakeOpenOffers(),
        pickup_pending=pickup_pending or FakePickupPending(),
        geocoder=geocoder or FakeGeocoder(events=events),
    )
    return service, session, repo


def build_query(repo=None):
    repo = repo or FakeStoreRepository()
    return StoreQueryService(stores=repo), repo


async def _seed(service, owner=None):
    owner = owner or uuid.uuid4()
    store = await service.open_store(owner, "상호", f"주소 {owner}")
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
    geocoder = FakeGeocoder()
    service, session, repo = build(geocoder=geocoder)
    owner = uuid.uuid4()
    store = await service.open_store(owner, "  상호  ", "  서울시   강남구 ")
    assert store.id is not None and store.owner_id == owner
    assert store.name == "상호" and store.pickup_address == "서울시 강남구"
    assert store.approval_at == FIXED and store.closed_at is None
    assert (store.latitude, store.longitude) == (
        DEFAULT_COORDINATES.latitude,
        DEFAULT_COORDINATES.longitude,
    )
    assert geocoder.calls == ["서울시 강남구"]  # 정규화된 주소로 정확히 1회
    assert session.commits == 1 and repo.saved == 1


async def test_open_store_call_order():
    events: list[str] = []
    service, _, _ = build(events=events)
    await service.open_store(uuid.uuid4(), "상호", "주소")
    assert events == [
        "find_by_owner_id",
        "exists_by_name_and_address",
        "geocode",
        "clock.now",
        "save",
        "commit",
    ]


async def test_open_store_duplicate_owner_skips_geocoder():
    geocoder = FakeGeocoder()
    service, session, _ = build(geocoder=geocoder)
    owner = uuid.uuid4()
    await service.open_store(owner, "상호", "주소")
    with pytest.raises(StoreAlreadyExistsError, match="이미 개설된 상점이 있습니다."):
        await service.open_store(owner, "상호", "다른주소")
    assert session.commits == 1 and len(geocoder.calls) == 1


async def test_open_store_duplicate_owner_with_closed_store_skips_geocoder():
    geocoder = FakeGeocoder()
    service, session, _ = build(geocoder=geocoder)
    owner, store = await _seed(service)
    await service.close_store(owner, store.id)
    commits, calls = session.commits, len(geocoder.calls)
    with pytest.raises(StoreAlreadyExistsError):
        await service.open_store(owner, "상호", "새주소")
    assert session.commits == commits and len(geocoder.calls) == calls


@pytest.mark.parametrize("name", [None, "", "  "])
async def test_open_store_no_name(name):
    geocoder = FakeGeocoder()
    service, session, repo = build(geocoder=geocoder)
    with pytest.raises(ValueError, match="상점명은 1자 이상 150자 이하여야 합니다."):
        await service.open_store(uuid.uuid4(), name, "주소")
    assert session.commits == 0 and repo.saved == 0 and geocoder.calls == []


@pytest.mark.parametrize("address", ["", " ", "　"])
async def test_open_store_empty_address_skips_everything(address):
    geocoder = FakeGeocoder()
    service, session, repo = build(geocoder=geocoder)
    with pytest.raises(ValueError, match="주소를 입력해 주세요."):
        await service.open_store(uuid.uuid4(), "상호", address)
    assert session.commits == 0 and repo.lookups == 0 and geocoder.calls == []


async def test_open_store_address_too_long():
    geocoder = FakeGeocoder()
    service, _, repo = build(geocoder=geocoder)
    with pytest.raises(ValueError, match="픽업 주소는 500자 이하여야 합니다."):
        await service.open_store(uuid.uuid4(), "상호", "가" * 501)
    assert geocoder.calls == [] and repo.lookups == 0


async def test_open_store_duplicate_name_and_address_other_owner():
    geocoder = FakeGeocoder()
    service, session, repo = build(geocoder=geocoder)
    await service.open_store(uuid.uuid4(), "상호", "서울 강남구")
    commits, calls = session.commits, len(geocoder.calls)
    with pytest.raises(StoreDuplicatedError, match="동일한 상점명과 주소의 상점이 이미 존재합니다."):
        await service.open_store(uuid.uuid4(), "상호", "서울 강남구")
    assert session.commits == commits and len(geocoder.calls) == calls and repo.saved == 1


async def test_open_store_duplicate_detected_after_normalization():
    import unicodedata

    service, _, _ = build()
    await service.open_store(uuid.uuid4(), "서울 카페", "서울 강남구 1")
    nfd = unicodedata.normalize("NFD", "서울")
    with pytest.raises(StoreDuplicatedError):
        await service.open_store(uuid.uuid4(), f" {nfd}   카페 ", f"{nfd}  강남구   1")


async def test_open_store_duplicate_against_closed_store():
    service, _, _ = build()
    owner = uuid.uuid4()
    store = await service.open_store(owner, "상호", "주소")
    await service.close_store(owner, store.id)
    with pytest.raises(StoreDuplicatedError):
        await service.open_store(uuid.uuid4(), "상호", "주소")


async def test_open_store_already_exists_wins_over_duplicate():
    service, _, _ = build()
    owner = uuid.uuid4()
    await service.open_store(owner, "상호", "주소")
    with pytest.raises(StoreAlreadyExistsError):  # 같은 상점주가 같은 이름·주소: 둘 다 해당
        await service.open_store(owner, "상호", "주소")


async def test_open_store_address_not_found():
    geocoder = FakeGeocoder(results={"없는주소": AddressNotFoundError()})
    service, session, repo = build(geocoder=geocoder)
    with pytest.raises(AddressNotFoundError, match="주소를 찾을 수 없습니다."):
        await service.open_store(uuid.uuid4(), "상호", "없는주소")
    assert session.commits == 0 and repo.saved == 0 and geocoder.calls == ["없는주소"]


async def test_open_store_geocoder_unavailable():
    geocoder = FakeGeocoder(results={"주소": GeocodingUnavailableError()})
    service, session, repo = build(geocoder=geocoder)
    with pytest.raises(GeocodingUnavailableError):
        await service.open_store(uuid.uuid4(), "상호", "주소")
    assert session.commits == 0 and repo.saved == 0


@pytest.mark.parametrize("error", [True, StoreDuplicatedError])
async def test_open_store_race_no_commit(error):
    service, session, _ = build(FakeStoreRepository(race_on_save=error))
    with pytest.raises((StoreAlreadyExistsError, StoreDuplicatedError)):
        await service.open_store(uuid.uuid4(), "상호", "주소")
    assert session.commits == 0


def test_service_requires_geocoder():
    with pytest.raises(TypeError):
        StoresApplicationService(
            session=FakeSession(),
            stores=FakeStoreRepository(),
            clock=FakeClock(),
            open_offers=FakeOpenOffers(),
            pickup_pending=FakePickupPending(),
        )
