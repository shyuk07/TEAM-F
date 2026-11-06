"""RD-40 결정(payments REQ-35, reservations REQ-15·16) + 실제 PostgreSQL.

결제 대기 예약에 이미 환불된(REFUNDED) 결제가 연결되어 있으면 데이터 불일치로 본다.
결제 요청, 환불 요청, 고객 취소, 판매 중단 일괄 취소, 회원 탈퇴 일괄 취소를 모두 500 DATA_INCONSISTENT로 막고
예약·결제·환불·재고·재고 기록·포인트를 하나도 바꾸지 않는다. 본인의 결제·환불 조회는 계속 된다.
"""

import logging
import uuid

import pytest

from tests.admin.test_api_db import admin_headers, user_id
from tests.helpers import bearer, token_for
from tests.payments.test_inconsistency_db import INCONSISTENT, _rows, cancel, errors, make_payment, scalar
from tests.reservations.test_api_db import seed, seed_offer
from tests.reservations.test_stock_db import deactivate, pay, refund
from tests.reservations.test_withdrawal_db import withdraw

pytestmark = [pytest.mark.db, pytest.mark.anyio]

KIND = "REFUNDED_PAYMENT_ON_PENDING_RESERVATION"


async def everything(c):
    """예약·결제·환불·재고·재고 기록·포인트·회원 상태 전체."""
    return (
        sorted(await _rows(c, "SELECT id::text || status FROM pickup_reservations")),
        sorted(await _rows(c, "SELECT id::text || status FROM payments")),
        sorted(await _rows(c, "SELECT id::text FROM refunds")),
        sorted(await _rows(c, "SELECT id::text || remaining_stock || status FROM discount_offers")),
        await scalar(c, "SELECT count(*) FROM stock_log"),
        await scalar(c, "SELECT coalesce(sum(amount), 0) FROM stock_log"),
        await scalar(c, "SELECT count(*) FROM point_log"),
        sorted(await _rows(c, "SELECT email || ':' || coalesce(users_point, 0) || ':' || status FROM users")),
    )


async def broken(c, email="me@test.com"):
    """결제 대기 예약 + REFUNDED 결제(불일치). 같은 할인에 다른 회원의 정상 결제 대기 예약도 하나 둔다."""
    owner, offer_id, _ = await seed_offer(c, stock=10)
    me = await token_for(c, email)
    rid, _ = await seed(c, me, offer_id, 1)  # PENDING_PAYMENT
    payment = await make_payment(c, rid, me, status="REFUNDED")
    other = await token_for(c, "other@test.com")
    normal, _ = await seed(c, other, offer_id, 1)
    return owner, offer_id, me, rid, payment, normal


def assert_one_error(caplog):
    records = errors(caplog)
    assert len(records) == 1, [r.getMessage() for r in records]
    assert KIND in records[0].getMessage()


async def test_customer_cancel_is_500_and_changes_nothing(client, caplog):
    _, _, me, rid, payment, _ = await broken(client)
    before = await everything(client)
    with caplog.at_level(logging.DEBUG):
        r = await cancel(client, me, rid)
    assert r.status_code == 500 and r.json() == INCONSISTENT, r.text
    assert rid not in r.text and str(payment.id) not in r.text
    assert await everything(client) == before
    assert_one_error(caplog)


async def test_pay_is_500_not_409_and_changes_nothing(client, caplog):
    _, _, me, rid, _, _ = await broken(client)
    before = await everything(client)
    with caplog.at_level(logging.DEBUG):
        r = await pay(client, me, rid)
    assert r.status_code == 500 and r.json() == INCONSISTENT, r.text
    assert await everything(client) == before
    assert_one_error(caplog)


async def test_refund_is_500_not_409_and_changes_nothing(client, caplog):
    _, _, me, _, payment, _ = await broken(client)
    before = await everything(client)
    with caplog.at_level(logging.DEBUG):
        r = await refund(client, me, str(payment.id))
    assert r.status_code == 500 and r.json() == INCONSISTENT, r.text
    assert await everything(client) == before
    assert_one_error(caplog)


async def test_owner_can_still_view_payment_and_refund(client):
    _, _, me, _, payment, _ = await broken(client)
    r = await client.get(f"/v1/payments/{payment.id}", headers=bearer(me))
    assert r.status_code == 200 and r.json()["status"] == "REFUNDED", r.text
    refund_id = await scalar(client, "SELECT id::text FROM refunds WHERE payment_id = :p", p=payment.id)
    r = await client.get(f"/v1/refunds/{refund_id}", headers=bearer(me))
    assert r.status_code == 200, r.text
    other = await token_for(client, "stranger@test.com")
    assert (await client.get(f"/v1/payments/{payment.id}", headers=bearer(other))).status_code == 403


async def test_offer_deactivate_bulk_cancel_is_500_and_cancels_nothing(client, caplog):
    owner, offer_id, _, rid, _, normal = await broken(client)
    before = await everything(client)
    with caplog.at_level(logging.DEBUG):
        r = await deactivate(client, owner, offer_id)
    assert r.status_code == 500 and r.json()["error_code"] == "DATA_INCONSISTENT", r.text
    assert await everything(client) == before  # 정상 예약(normal)도 취소되지 않음, 할인도 열린 채
    statuses = await _rows(client, "SELECT status FROM pickup_reservations")
    assert sorted(statuses) == ["PENDING_PAYMENT", "PENDING_PAYMENT"]
    assert_one_error(caplog)


async def test_withdrawal_bulk_cancel_is_500_and_changes_nothing(client, caplog):
    _, offer_id, me, rid, _, _ = await broken(client)
    # 같은 회원의 정상 결제 대기 예약도 하나 더(다른 할인): 탈퇴 묶음 전체가 중단돼야 한다
    _, other_offer, _ = await seed_offer(client, stock=5, email="owner2@test.com")
    await seed(client, me, other_offer, 1)
    admin = await admin_headers(client)
    uid = str(await user_id(client, "me@test.com"))
    before = await everything(client)
    with caplog.at_level(logging.DEBUG):
        r = await withdraw(client, admin, uid)
    assert r.status_code == 500 and r.json()["error_code"] == "DATA_INCONSISTENT", r.text
    assert await everything(client) == before  # 예약·재고·포인트·회원 상태(탈퇴 안 됨) 그대로
    assert (await client.get("/v1/users/me", headers=bearer(me))).status_code == 200
    assert_one_error(caplog)


async def test_self_withdrawal_is_500_and_changes_nothing(client, caplog):
    """본인 탈퇴(/v1/users/me/withdraw)도 같은 일괄 취소 경로라 막힌다."""
    _, _, me, _, _, _ = await broken(client)
    before = await everything(client)
    with caplog.at_level(logging.DEBUG):
        r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(me))
    assert r.status_code == 500 and r.json()["error_code"] == "DATA_INCONSISTENT", r.text
    assert await everything(client) == before
    assert (await client.get("/v1/users/me", headers=bearer(me))).status_code == 200  # 탈퇴되지 않음
    assert_one_error(caplog)


async def test_normal_refunded_then_cancelled_is_not_inconsistent(client):
    """정상 흐름(결제 → 환불 = 예약 취소)은 불일치가 아니다. 다시 환불하면 기존대로 409."""
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await client.post("/v1/reservations", json={"offer_id": offer_id, "quantity": 1}, headers=bearer(me))).json()["id"]
    pid = (await pay(client, me, rid)).json()["id"]
    assert (await refund(client, me, pid)).status_code == 201
    r = await refund(client, me, pid)
    assert r.status_code == 409, r.text
    assert (await cancel(client, me, rid)).status_code == 409  # 이미 취소된 예약
    assert uuid.UUID(pid)
