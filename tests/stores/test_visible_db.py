import uuid
from datetime import datetime, timezone

import pytest

from auth.infrastructure import models as auth_models  # noqa: F401
from auth.infrastructure.models import UserModel
from stores.domain.store import Store, StoreStatus
from stores.infrastructure import models as stores_models  # noqa: F401
from stores.infrastructure.models import StoreModel
from stores.infrastructure.repositories import SqlAlchemyStoreRepository

pytestmark = [pytest.mark.db, pytest.mark.anyio]

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
LAT, LNG = 37.5665, 126.9780  # 서울시청


async def _user(s, n):
    u = UserModel(
        email=f"o{n}@t.com", password_hash="x", role="OWNER", name=f"o{n}", phone="010",
        users_point=0, status="APPROVED",
    )
    s.add(u)
    await s.flush()
    return u.id


async def _store(s, n, name, lat=LAT, lng=LNG, **kw):
    kw.setdefault("approval_at", NOW)
    m = StoreModel(
        owner_id=await _user(s, n), name=name, pickup_address=f"addr{n}",
        latitude=lat, longitude=lng, **kw,
    )
    s.add(m)
    await s.flush()
    return m.id


async def _seed_all(s):
    ids = {}
    ids["near"] = await _store(s, 1, "near", LAT + 0.01, LNG)  # ~1.11km
    ids["far"] = await _store(s, 2, "far", LAT + 0.05, LNG)  # ~5.56km
    ids["exact"] = await _store(s, 3, "exact")  # 0km
    ids["nocoord"] = await _store(s, 4, "nocoord", None, None)
    ids["closed"] = await _store(s, 5, "closed", closed_at=NOW)
    ids["susp"] = await _store(s, 6, "susp", suspended_at=NOW, suspended_reason="r")
    ids["unapproved"] = await _store(s, 7, "unapproved", approval_at=None)
    await s.commit()
    return ids


async def test_located_filters_orders_and_computes_distance(session_factory):
    async with session_factory() as s:
        ids = await _seed_all(s)
        repo = SqlAlchemyStoreRepository(s)
        rows = await repo.find_visible_near(latitude=LAT, longitude=LNG, radius_km=3.0)
        assert [st.id for st, _ in rows] == [ids["exact"], ids["near"]]
        assert rows[0][1] == pytest.approx(0.0, abs=1e-6)
        assert rows[1][1] == pytest.approx(1.1119, abs=0.01)
        wide = await repo.find_visible_near(latitude=LAT, longitude=LNG, radius_km=20.0)
        assert [st.id for st, _ in wide] == [ids["exact"], ids["near"], ids["far"]]


async def test_radius_boundary_inclusive(session_factory):
    async with session_factory() as s:
        ids = await _seed_all(s)
        repo = SqlAlchemyStoreRepository(s)
        d = (await repo.find_visible_near(latitude=LAT, longitude=LNG, radius_km=3.0))[1][1]
        inc = await repo.find_visible_near(latitude=LAT, longitude=LNG, radius_km=d)
        assert ids["near"] in [st.id for st, _ in inc]
        exc = await repo.find_visible_near(latitude=LAT, longitude=LNG, radius_km=d - 1e-6)
        assert ids["near"] not in [st.id for st, _ in exc]


async def test_distance_ties_broken_by_id(session_factory):
    async with session_factory() as s:
        a = await _store(s, 1, "a")
        b = await _store(s, 2, "b")
        await s.commit()
        rows = await SqlAlchemyStoreRepository(s).find_visible_near(
            latitude=LAT, longitude=LNG, radius_km=1.0
        )
        assert [st.id for st, _ in rows] == sorted([a, b])


async def test_unlocated_includes_coordless_sorted_by_name_id(session_factory):
    async with session_factory() as s:
        ids = await _seed_all(s)
        dup1 = await _store(s, 8, "near", LAT, LNG)
        await s.commit()
        rows = await SqlAlchemyStoreRepository(s).find_visible_near(
            latitude=None, longitude=None, radius_km=1.0  # radius 무시
        )
        assert all(d is None for _, d in rows)
        got = [(st.name, st.id) for st, _ in rows]
        assert got == sorted(got)
        assert {st.id for st, _ in rows} == {
            ids["near"], ids["far"], ids["exact"], ids["nocoord"], dup1
        }
        assert [n for n, _ in got] == ["exact", "far", "near", "near", "nocoord"]


async def test_one_sided_location_is_value_error(session_factory):
    async with session_factory() as s:
        repo = SqlAlchemyStoreRepository(s)
        with pytest.raises(ValueError):
            await repo.find_visible_near(latitude=LAT, longitude=None, radius_km=3.0)
        with pytest.raises(ValueError):
            await repo.find_visible_near(latitude=None, longitude=LNG, radius_km=3.0)


async def test_sql_visibility_matches_domain(session_factory):
    async with session_factory() as s:
        await _seed_all(s)
        repo = SqlAlchemyStoreRepository(s)
        visible = {st.id for st, _ in await repo.find_visible_near(
            latitude=None, longitude=None, radius_km=None)}
        all_models = (await s.execute(__import__("sqlalchemy").select(StoreModel))).scalars().all()
        assert len(all_models) == 7
        for m in all_models:
            store = SqlAlchemyStoreRepository._to_domain(m)
            expected = store.is_approved and store.status == StoreStatus.ACTIVE
            assert store.is_publicly_visible is expected
            assert (m.id in visible) is expected
