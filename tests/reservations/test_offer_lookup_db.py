"""catalog 할인 수정 가드용 예약 존재 판정 + 실제 PostgreSQL (catalog REQ-17, catalog D81, reservations D-39).

취소되지 않은 예약(PENDING_PAYMENT·RESERVED·PICKED_UP)이 한 건이라도 있으면 할인 판매 조건 수정을 막고,
예약이 없거나 모두 취소됐으면 수정할 수 있다. 실제 레포지토리와 할인 수정 API(PATCH /v1/offers/{id}) 양쪽으로 확인한다.
"""

import uuid

import pytest
from sqlalchemy import text

from reservations.infrastructure.repositories import SqlAlchemyReservationRepository
from tests.helpers import bearer, token_for
from tests.payments.test_inconsistency_db import set_reservation_status
from tests.reservations.test_api_db import seed, seed_offer
from tests.reservations.test_stock_db import scalar

pytestmark = [pytest.mark.db, pytest.mark.anyio]

HAS_RES = {
    "success": False,
    "error_code": "OFFER_HAS_RESERVATIONS",
    "message": "예약이 있는 할인은 수정할 수 없습니다. 재등록을 이용하세요.",
}


async def exists(c, offer_id):
    async with c.session_factory() as s:
        return await SqlAlchemyReservationRepository(s).exists_non_cancelled_by_offer(uuid.UUID(offer_id))


async def edit(c, owner, offer_id, price=2500):
    return await c.patch(f"/v1/offers/{offer_id}", json={"sale_price": price}, headers=bearer(owner))


async def price_of(c, offer_id):
    return await scalar(c, "SELECT sale_price FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id))


async def test_no_reservation_allows_edit(client):
    owner, offer_id, _ = await seed_offer(client)
    assert await exists(client, offer_id) is False
    r = await edit(client, owner, offer_id)
    assert r.status_code == 200, r.text
    assert await price_of(client, offer_id) == 2500


async def test_all_cancelled_allows_edit(client):
    owner, offer_id, _ = await seed_offer(client)
    a = await token_for(client, "a@test.com")
    b = await token_for(client, "b@test.com")
    for token in (a, b):
        rid, _ = await seed(client, token, offer_id, 1)
        await set_reservation_status(client, rid, "CANCELLED")
    assert await exists(client, offer_id) is False
    r = await edit(client, owner, offer_id)
    assert r.status_code == 200, r.text
    assert await price_of(client, offer_id) == 2500


@pytest.mark.parametrize("status", ["PENDING_PAYMENT", "RESERVED", "PICKED_UP"])
async def test_non_cancelled_reservation_blocks_edit(client, status):
    owner, offer_id, _ = await seed_offer(client)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id, 1, paid=status in ("RESERVED", "PICKED_UP"))
    if status == "PICKED_UP":
        async with client.session_factory() as s:
            await s.execute(
                text("UPDATE pickup_reservations SET status = 'PICKED_UP', picked_up_at = now() WHERE id = :i"),
                {"i": uuid.UUID(rid)},
            )
            await s.commit()
    assert await scalar(client, "SELECT status FROM pickup_reservations WHERE id = :i", i=uuid.UUID(rid)) == status
    assert await exists(client, offer_id) is True
    r = await edit(client, owner, offer_id)
    assert r.status_code == 400 and r.json() == HAS_RES, r.text
    assert await price_of(client, offer_id) == 3000  # 바뀌지 않음


async def test_one_live_among_cancelled_still_blocks(client):
    owner, offer_id, _ = await seed_offer(client)
    a = await token_for(client, "a@test.com")
    b = await token_for(client, "b@test.com")
    cancelled, _ = await seed(client, a, offer_id, 1)
    await set_reservation_status(client, cancelled, "CANCELLED")
    await seed(client, b, offer_id, 1)  # 결제 대기 1건 남음
    assert await exists(client, offer_id) is True
    assert (await edit(client, owner, offer_id)).status_code == 400


async def test_other_offer_reservation_does_not_block(client):
    owner, offer_id, _ = await seed_offer(client)
    _, other_offer, _ = await seed_offer(client, email="owner2@test.com")
    me = await token_for(client, "me@test.com")
    await seed(client, me, other_offer, 1)
    assert await exists(client, offer_id) is False
    assert (await edit(client, owner, offer_id)).status_code == 200
