"""취소 주체 컬럼(설계 16.3) 왕복·CHECK 제약. 실제 PostgreSQL 필요 (db 마커)."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from reservations.domain.cancel_actor import CancelActor
from reservations.domain.offer_ref import OfferRef
from reservations.domain.pickup_reservation import PickupReservation
from reservations.domain.pickup_reservation import ReservationStatus as S
from reservations.infrastructure.repositories import SqlAlchemyReservationRepository
from tests.helpers import token_for
from tests.reservations.test_api_db import H, seed, seed_offer

pytestmark = [pytest.mark.db, pytest.mark.anyio]


async def _new_reservation(session, c, offer_id):
    now = datetime.now(timezone.utc)
    ref = OfferRef.from_info(
        SimpleNamespace(
            offer_id=uuid.UUID(offer_id), owner_id=uuid.uuid4(), store_name="마감 베이커리",
            product_name="샌드위치", pickup_address="서울", sale_price=3000,
            pickup_start=now + H, pickup_end=now + 3 * H,
        )
    )
    return PickupReservation.create(uuid.UUID(await _user_id(session)), ref, 1, "AB3DE9", now)


async def _user_id(session):
    return str((await session.execute(text("SELECT id FROM users LIMIT 1"))).scalar_one())


@pytest.mark.parametrize("actor", list(CancelActor))
async def test_save_and_find_roundtrip_keeps_cancelled_by(client, actor):
    _, offer_id, _ = await seed_offer(client)
    await token_for(client, "me@test.com")
    async with client.session_factory() as session:
        repo = SqlAlchemyReservationRepository(session)
        r = await _new_reservation(session, client, offer_id)
        await repo.save(r)
        r.cancel(datetime.now(timezone.utc), actor)
        await repo.save(r)
        await session.commit()
    async with client.session_factory() as session:
        found = await SqlAlchemyReservationRepository(session).find_by_id(r.id)
    assert found.status == S.CANCELLED and found.cancelled_by is actor


async def test_legacy_cancelled_row_with_null_actor_is_readable(client):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)
    async with client.session_factory() as session:
        await session.execute(
            text("UPDATE pickup_reservations SET status='CANCELLED', cancelled_at=now() WHERE id=:i"),
            {"i": uuid.UUID(rid)},
        )
        await session.commit()
    async with client.session_factory() as session:
        found = await SqlAlchemyReservationRepository(session).find_by_id(uuid.UUID(rid))
    assert found.is_cancelled and found.cancelled_by is None


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE pickup_reservations SET status='CANCELLED', cancelled_at=now(), cancelled_by='ADMIN' WHERE id=:i",
        "UPDATE pickup_reservations SET cancelled_by='CUSTOMER' WHERE id=:i",  # status가 CANCELLED가 아님
    ],
)
async def test_check_constraints_reject_invalid_rows(client, sql):
    _, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id)
    async with client.session_factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text(sql), {"i": uuid.UUID(rid)})
