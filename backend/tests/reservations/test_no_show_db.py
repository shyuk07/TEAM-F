"""미수령 예약(A안, 사용자 결정 2026-11-10) + 실제 PostgreSQL.

미수령 = 결제 완료(RESERVED)인데 now > pickup_end. 새 상태는 없고 RESERVED로 남는다.
- 고객 탈퇴(본인·관리자)·판매 중단 일괄 취소: 미수령은 자동 취소·환불·재고 복구하지 않는다(나머지는 기존대로)
- 상점주 폐점·상점주 탈퇴: 미수령은 '픽업 대기 예약'이 아니라 막지 않는다. 픽업 마감 전 예약은 기존대로 막는다
시계는 예약 모듈 시계만 바꾼다(container._reservations_clock). 예약 생성·결제는 실제 시각에 한다.
"""

import uuid
from datetime import timedelta

import pytest

import container
from tests.admin.test_api_db import admin_headers, user_id
from tests.helpers import bearer, token_for
from tests.reservations.test_api_db import reserve, seed_offer
from tests.reservations.test_cancel_deadline_db import make_offer
from tests.reservations.test_stock_db import deactivate, pay, scalar
from tests.reservations.test_withdrawal_db import withdraw

pytestmark = [pytest.mark.db, pytest.mark.anyio]

M = timedelta(minutes=1)


class AtClock:
    def __init__(self, at):
        self.at = at

    def now(self):
        return self.at


async def pickup_end(c, offer_id):
    return await scalar(c, "SELECT pickup_end FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id))


async def paid(c, token, offer_id, qty=1):
    rid = (await reserve(c, token, offer_id, qty)).json()["id"]
    p = await pay(c, token, rid)
    assert p.status_code == 201, p.text
    return rid, p.json()["id"]


async def row(c, rid, pid=None):
    status = await scalar(c, "SELECT status FROM pickup_reservations WHERE id = :i", i=uuid.UUID(rid))
    pay_status = None if pid is None else await scalar(c, "SELECT status FROM payments WHERE id = :i", i=uuid.UUID(pid))
    refunds = 0 if pid is None else await scalar(c, "SELECT count(*) FROM refunds WHERE payment_id = :i", i=uuid.UUID(pid))
    return status, pay_status, refunds


async def stock(c, offer_id):
    return await scalar(c, "SELECT remaining_stock FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id))


@pytest.mark.parametrize("path", ["self", "admin"])
async def test_customer_withdrawal_keeps_no_show_and_cancels_the_rest(client, monkeypatch, path):
    _, over_offer = await make_offer(client, pickup_in=150 * M)  # 픽업 마감 = 생성 시각 + 3시간
    _, live_offer, _ = await seed_offer(client, stock=10, email="owner2@test.com")  # 픽업 마감 = 생성 시각 + 4시간
    me = await token_for(client, "me@test.com")
    no_show, no_show_pid = await paid(client, me, over_offer, 2)
    live, live_pid = await paid(client, me, live_offer, 1)
    over_stock = await stock(client, over_offer)
    monkeypatch.setattr(container, "_reservations_clock", AtClock(await pickup_end(client, over_offer) + M))

    if path == "self":
        r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(me))
    else:
        r = await withdraw(client, await admin_headers(client), str(await user_id(client, "me@test.com")))
    assert r.status_code == 200, r.text
    assert r.json()["cancelled_reservation_count"] == 1  # 미수령은 세지 않음

    assert await row(client, no_show, no_show_pid) == ("RESERVED", "PAID", 0)  # 환불·취소 없음
    assert await stock(client, over_offer) == over_stock  # 재고 복구 없음
    assert await row(client, live, live_pid) == ("CANCELLED", "REFUNDED", 1)  # 픽업 마감 전 예약은 기존대로


async def test_exactly_at_pickup_end_is_not_no_show(client, monkeypatch):
    _, offer = await make_offer(client, pickup_in=150 * M)
    me = await token_for(client, "me@test.com")
    rid, pid = await paid(client, me, offer)
    monkeypatch.setattr(container, "_reservations_clock", AtClock(await pickup_end(client, offer)))  # 마감 순간
    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(me))
    assert r.status_code == 200 and r.json()["cancelled_reservation_count"] == 1, r.text
    assert await row(client, rid, pid) == ("CANCELLED", "REFUNDED", 1)


async def test_offer_deactivate_skips_no_show(client, monkeypatch):
    owner, offer = await make_offer(client, pickup_in=150 * M)
    a = await token_for(client, "a@test.com")
    no_show, pid = await paid(client, a, offer)
    pending = (await reserve(client, await token_for(client, "b@test.com"), offer, 1)).json()["id"]
    monkeypatch.setattr(container, "_reservations_clock", AtClock(await pickup_end(client, offer) + M))

    r = await deactivate(client, owner, offer)

    assert r.status_code == 200 and r.json()["cancelled_reservation_count"] == 1, r.text  # 결제 대기만 취소
    assert await row(client, no_show, pid) == ("RESERVED", "PAID", 0)
    assert await scalar(client, "SELECT status FROM pickup_reservations WHERE id = :i", i=uuid.UUID(pending)) == "CANCELLED"


async def close_store(c, owner, offer_id):
    store_id = await scalar(
        c,
        "SELECT p.store_id::text FROM discount_offers o JOIN products p ON p.id = o.product_id WHERE o.id = :i",
        i=uuid.UUID(offer_id),
    )
    return await c.post(f"/v1/stores/{store_id}/close", headers=bearer(owner))


async def test_store_close_is_blocked_by_live_reserved_but_not_by_no_show(client, monkeypatch):
    owner, offer = await make_offer(client, pickup_in=150 * M)
    me = await token_for(client, "me@test.com")
    rid, pid = await paid(client, me, offer)
    assert (await deactivate(client, owner, offer, cancel_reservations=False)).status_code == 200  # 열린 할인 없앰
    end = await pickup_end(client, offer)

    monkeypatch.setattr(container, "_reservations_clock", AtClock(end))  # 마감 순간: 아직 픽업 대기
    r = await close_store(client, owner, offer)
    assert r.status_code == 400 and r.json()["error_code"] == "STORE_HAS_RESERVED_RESERVATIONS", r.text

    monkeypatch.setattr(container, "_reservations_clock", AtClock(end + timedelta(microseconds=1)))  # 미수령
    r = await close_store(client, owner, offer)
    assert r.status_code == 200, r.text
    assert await row(client, rid, pid) == ("RESERVED", "PAID", 0)  # 폐점해도 미수령 예약은 그대로


@pytest.mark.parametrize("path", ["self", "admin"])
async def test_owner_withdrawal_not_blocked_by_others_no_show(client, monkeypatch, path):
    owner, offer = await make_offer(client, pickup_in=150 * M)
    me = await token_for(client, "me@test.com")
    rid, pid = await paid(client, me, offer)
    end = await pickup_end(client, offer)

    async def try_withdraw():
        if path == "self":
            return await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(owner))
        return await withdraw(client, await admin_headers(client), str(await user_id(client, "owner@test.com")))

    monkeypatch.setattr(container, "_reservations_clock", AtClock(end))  # 픽업 대기: 막힘
    r = await try_withdraw()
    assert r.status_code == 400 and r.json()["error_code"] == "STORE_HAS_RESERVED_RESERVATIONS", r.text
    assert await scalar(client, "SELECT status FROM users WHERE email = 'owner@test.com'") != "WITHDRAWN"

    monkeypatch.setattr(container, "_reservations_clock", AtClock(end + M))  # 미수령: 막지 않음
    r = await try_withdraw()
    assert r.status_code == 200, r.text
    assert await row(client, rid, pid) == ("RESERVED", "PAID", 0)  # 고객의 미수령 예약은 그대로


async def test_admin_forced_store_close_not_blocked_by_no_show(client, monkeypatch):
    owner, offer = await make_offer(client, pickup_in=150 * M)
    me = await token_for(client, "me@test.com")
    rid, pid = await paid(client, me, offer)
    store_id = await scalar(
        client,
        "SELECT p.store_id::text FROM discount_offers o JOIN products p ON p.id = o.product_id WHERE o.id = :i",
        i=uuid.UUID(offer),
    )
    admin = await admin_headers(client)
    end = await pickup_end(client, offer)

    monkeypatch.setattr(container, "_reservations_clock", AtClock(end))  # 픽업 대기: 막힘
    r = await client.patch(f"/v1/admin/stores/{store_id}/close", json={"reason": "점검"}, headers=admin)
    assert r.status_code == 400 and r.json()["error_code"] == "STORE_HAS_RESERVED_RESERVATIONS", r.text

    monkeypatch.setattr(container, "_reservations_clock", AtClock(end + M))  # 미수령: 막지 않음
    r = await client.patch(f"/v1/admin/stores/{store_id}/close", json={"reason": "점검"}, headers=admin)
    assert r.status_code == 200, r.text
    assert await row(client, rid, pid) == ("RESERVED", "PAID", 0)
