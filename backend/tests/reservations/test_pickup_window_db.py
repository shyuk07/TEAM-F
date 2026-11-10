"""픽업 가능 시간 + 실제 PostgreSQL (확정, 사용자 결정 2026-11-10).

픽업 완료는 pickup_start <= 현재 <= pickup_end일 때만 된다(양 끝 포함). 밖이면 400 PICKUP_OUTSIDE_WINDOW이고
예약·결제·재고·재고 기록·포인트는 바뀌지 않는다. 시각은 할인 상품(Catalog)의 픽업 시작·마감을 쓴다.
"""

import uuid
from datetime import timedelta

import pytest

import container
from tests.helpers import bearer, token_for
from tests.payments.test_rd40_db import everything
from tests.reservations.test_api_db import reserve, seed_offer
from tests.reservations.test_stock_db import pay, scalar

pytestmark = [pytest.mark.db, pytest.mark.anyio]

TICK = timedelta(microseconds=1)
OUTSIDE = {"success": False, "error_code": "PICKUP_OUTSIDE_WINDOW", "message": "픽업 가능 시간이 아닙니다."}


class AtClock:
    def __init__(self, at):
        self.at = at

    def now(self):
        return self.at


async def paid(c):
    owner, offer_id, _ = await seed_offer(c, stock=5)
    me = await token_for(c, "me@test.com")
    rid = (await reserve(c, me, offer_id, 1)).json()["id"]
    assert (await pay(c, me, rid)).status_code == 201
    code = await scalar(c, "SELECT pickup_code FROM pickup_reservations WHERE id = :i", i=uuid.UUID(rid))
    start = await scalar(c, "SELECT pickup_start FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id))
    end = await scalar(c, "SELECT pickup_end FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id))
    return owner, rid, code, start, end


async def pickup(c, owner, rid, code):
    return await c.post(f"/v1/reservations/{rid}/pickup", json={"pickup_code": code}, headers=bearer(owner))


@pytest.mark.parametrize(
    "where,allowed",
    [("start-1us", False), ("start", True), ("end", True), ("end+1us", False)],
)
async def test_pickup_boundaries(client, monkeypatch, where, allowed):
    owner, rid, code, start, end = await paid(client)
    at = {"start-1us": start - TICK, "start": start, "end": end, "end+1us": end + TICK}[where]
    monkeypatch.setattr(container, "_reservations_clock", AtClock(at))
    before = await everything(client)
    r = await pickup(client, owner, rid, code)
    if allowed:
        assert r.status_code == 200 and r.json()["status"] == "PICKED_UP", r.text
        return
    assert r.status_code == 400 and r.json() == OUTSIDE, r.text
    assert await everything(client) == before  # 예약·결제·환불·재고·재고 기록·포인트 그대로


async def test_existing_checks_still_apply_inside_window(client, monkeypatch):
    owner, rid, code, start, _ = await paid(client)
    monkeypatch.setattr(container, "_reservations_clock", AtClock(start + timedelta(minutes=10)))
    other = await token_for(client, "other-owner@test.com", "OWNER")
    assert (await pickup(client, other, rid, code)).status_code == 403  # 해당 매장 상점주만
    cust = await token_for(client, "cust2@test.com")
    assert (await pickup(client, cust, rid, code)).status_code == 403  # 고객 불가
    r = await pickup(client, owner, rid, "Z99999")
    assert r.status_code == 400 and r.json()["error_code"] == "PICKUP_CODE_MISMATCH"
    assert (await pickup(client, owner, rid, code)).status_code == 200
    assert (await pickup(client, owner, rid, code)).status_code == 409  # 이미 픽업 완료


async def test_pending_payment_cannot_be_picked_up_even_inside_window(client, monkeypatch):
    owner, offer_id, _ = await seed_offer(client, stock=5)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 1)).json()["id"]
    code = await scalar(client, "SELECT pickup_code FROM pickup_reservations WHERE id = :i", i=uuid.UUID(rid))
    start = await scalar(client, "SELECT pickup_start FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id))
    monkeypatch.setattr(container, "_reservations_clock", AtClock(start))
    r = await pickup(client, owner, rid, code)
    assert r.status_code == 409 and r.json()["error_code"] == "RESERVATION_NOT_PAID", r.text
