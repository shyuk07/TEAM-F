"""관리자용 stores application 메서드 (docs/design/admin.md 5.3)."""

import uuid

import pytest

from stores.domain.exceptions import StoreHasReservedReservationsError, StoreNotFoundError
from stores.domain.store import Store
from tests.fakes import DEFAULT_COORDINATES as COORDS
from tests.stores.test_service import FIXED, FakeStoreRepository, build

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _seed(repo: FakeStoreRepository) -> Store:
    s = Store.open(uuid.uuid4(), "상호", "주소", FIXED, COORDS)
    s.id = uuid.uuid4()
    repo.items[s.id] = s
    return s


async def test_suspend_store_commit_flag():
    service, session, repo = build()
    s = _seed(repo)
    r = await service.suspend_store(s.id, "사유", now=FIXED, commit=False)
    assert r.suspended_at == FIXED and session.commits == 0 and repo.saved == 1
    s2 = _seed(repo)
    await service.suspend_store(s2.id, "사유", now=FIXED)
    assert session.commits == 1


async def test_suspend_store_not_found():
    service, session, _ = build()
    with pytest.raises(StoreNotFoundError):
        await service.suspend_store(uuid.uuid4(), "x", now=FIXED)
    assert session.commits == 0


async def test_suspend_stores_of_owner_cascade():
    service, session, repo = build()
    s = _seed(repo)
    r = await service.suspend_stores_of_owner(s.owner_id, "x", now=FIXED, commit=False)
    assert r is s and s.suspended_at == FIXED and repo.saved == 1 and session.commits == 0


async def test_suspend_stores_of_owner_skips():
    service, session, repo = build()
    assert await service.suspend_stores_of_owner(uuid.uuid4(), "x", now=FIXED) is None
    s = _seed(repo)
    s.suspend("a", FIXED)
    await service.suspend_stores_of_owner(s.owner_id, "x", now=FIXED, commit=False)
    assert repo.saved == 0 and s.suspended_reason == "a"
    c = _seed(repo)
    c.force_close("y", FIXED, False)
    await service.suspend_stores_of_owner(c.owner_id, "x", now=FIXED, commit=False)
    assert c.suspended_at is None and repo.saved == 0


async def test_suspend_stores_of_owner_skipped_still_commits():
    service, session, repo = build()
    s = _seed(repo)
    s.suspend("a", FIXED)
    await service.suspend_stores_of_owner(s.owner_id, "x", now=FIXED)
    assert repo.saved == 0 and session.commits == 1


async def test_lock_store_and_owner():
    service, _, repo = build()
    s = _seed(repo)
    assert await service.lock_store(s.id) is s
    assert await service.lock_store_of_owner(s.owner_id) is s
    assert await service.lock_store_of_owner(uuid.uuid4()) is None
    with pytest.raises(StoreNotFoundError):
        await service.lock_store(uuid.uuid4())


async def test_check_force_closable_no_side_effect():
    service, session, repo = build()
    s = _seed(repo)
    await service.check_force_closable(s.id, "x")
    assert s.closed_at is None and session.commits == 0 and repo.saved == 0
    with pytest.raises(ValueError, match="폐점 사유를 입력해 주세요."):
        await service.check_force_closable(s.id, " ")
    with pytest.raises(StoreNotFoundError):
        await service.check_force_closable(uuid.uuid4(), "x")


async def test_close_store_by_admin():
    service, session, repo = build()
    s = _seed(repo)
    r = await service.close_store_by_admin(
        s.id, "사유", has_reserved_reservations=False, now=FIXED, commit=False
    )
    assert r.closed_at == FIXED and r.closed_reason == "사유" and session.commits == 0
    s2 = _seed(repo)
    await service.close_store_by_admin(s2.id, "사유", has_reserved_reservations=False, now=FIXED)
    assert session.commits == 1


async def test_close_store_by_admin_reserved_no_save_no_commit():
    service, session, repo = build()
    s = _seed(repo)
    with pytest.raises(StoreHasReservedReservationsError):
        await service.close_store_by_admin(s.id, "x", has_reserved_reservations=True, now=FIXED)
    assert s.closed_at is None and repo.saved == 0 and session.commits == 0
