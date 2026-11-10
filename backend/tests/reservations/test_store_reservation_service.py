"""StoreReservationListService 단위 테스트 (DB 없음)."""

import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest

from reservations.application.store_reservation_service import StoreReservationListService
from reservations.domain.exceptions import NotStoreReservationOwnerError, StoreNotFoundError
from reservations.domain.pickup_reservation import PickupReservation, ReservationStatus
from tests.reservations.fakes import NOW, FakeRepo, Log

pytestmark = pytest.mark.anyio

OWNER = uuid.uuid4()
STORE = uuid.uuid4()


class Stores:
    def __init__(self, store):
        self.store = store

    async def find_store_by_id(self, store_id):
        return self.store if store_id == STORE else None


class StoreOffers:
    def __init__(self, offer_ids):
        self.offer_ids = offer_ids
        self.calls = []

    async def list_offer_ids_of_store(self, store_id, *, for_update=False):
        self.calls.append(for_update)
        return self.offer_ids


def make(offer_id, minutes, status=ReservationStatus.PENDING_PAYMENT):
    r = PickupReservation(
        user_id=uuid.uuid4(), offer_id=offer_id, quantity=1, unit_price=1000, total_price=1000,
        pickup_code="A12345", store_name="매장", pickup_address="주소", product_name="빵",
        created_at=NOW + timedelta(minutes=minutes), id=uuid.uuid4(),
    )
    r.status = status
    return r


def service(store, offer_ids, rows=()):
    repo = FakeRepo(Log())
    for r in rows:
        repo.items[r.id] = r
    offers = StoreOffers(offer_ids)
    return StoreReservationListService(repo, Stores(store), offers), offers


async def test_lists_only_store_offers_newest_first_without_lock():
    mine, other = uuid.uuid4(), uuid.uuid4()
    a, b, c = make(mine, 1), make(mine, 2), make(other, 3)
    svc, offers = service(SimpleNamespace(owner_id=OWNER), [mine], [a, b, c])
    page = await svc.list_store_reservations(OWNER, STORE, None, 1, 20)
    assert [r.id for r in page.items] == [b.id, a.id] and page.total == 2
    assert offers.calls == [False]  # 조회는 할인을 잠그지 않는다


async def test_status_filter_and_paging():
    offer = uuid.uuid4()
    rows = [make(offer, i, ReservationStatus.CANCELLED if i % 2 else ReservationStatus.RESERVED) for i in range(5)]
    svc, _ = service(SimpleNamespace(owner_id=OWNER), [offer], rows)
    page = await svc.list_store_reservations(OWNER, STORE, ReservationStatus.CANCELLED, 1, 1)
    assert page.total == 2 and len(page.items) == 1 and page.items[0].status == ReservationStatus.CANCELLED


async def test_store_without_offers_is_empty():
    svc, _ = service(SimpleNamespace(owner_id=OWNER), [])
    page = await svc.list_store_reservations(OWNER, STORE, None, 1, 20)
    assert page.items == [] and page.total == 0


async def test_unknown_store_and_other_owner():
    svc, _ = service(SimpleNamespace(owner_id=OWNER), [])
    with pytest.raises(StoreNotFoundError):
        await svc.list_store_reservations(OWNER, uuid.uuid4(), None, 1, 20)
    with pytest.raises(NotStoreReservationOwnerError):
        await svc.list_store_reservations(uuid.uuid4(), STORE, None, 1, 20)
