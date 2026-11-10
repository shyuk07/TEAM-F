"""관리자 강제 탈퇴 사유 길이 + 실제 PostgreSQL (사용자 결정 2026-11-10).

관리자 탈퇴 사유는 최대 500자(auth D27)이고 원문은 탈퇴 기록(users.deleted_reason)에 보존한다.
예약 취소·환불·재고 기록에는 200자 제한이 있으므로 고정 문구 "관리자 강제 탈퇴"를 쓴다.
그래서 사유가 201~500자이고 결제 완료 예약이 있어도 탈퇴와 전액 환불이 정상 처리된다.
본인 탈퇴의 사유("회원 본인 탈퇴")와 기존 트랜잭션·불일치 검사는 그대로다.
"""

import uuid

import pytest

from tests.admin.test_api_db import admin_headers, user_id
from tests.helpers import bearer, token_for
from tests.payments.test_rd40_db import everything
from tests.reservations.test_api_db import reserve, seed_offer
from tests.reservations.test_stock_db import pay, scalar
from tests.reservations.test_withdrawal_db import withdraw

pytestmark = [pytest.mark.db, pytest.mark.anyio]

FIXED = "관리자 강제 탈퇴"


async def customer_with_paid_and_pending(c):
    _, offer_id, _ = await seed_offer(c, stock=10)
    _, other_offer, _ = await seed_offer(c, stock=10, email="owner2@test.com")
    me = await token_for(c, "me@test.com")
    rid = (await reserve(c, me, offer_id, 2)).json()["id"]
    p = await pay(c, me, rid)
    assert p.status_code == 201, p.text
    pending = (await reserve(c, me, other_offer, 1)).json()["id"]
    return me, rid, p.json()["id"], pending, offer_id


@pytest.mark.parametrize("length", [200, 201, 300, 500])
async def test_admin_withdrawal_with_long_reason_refunds_in_full(client, length):
    _, rid, pid, pending, offer_id = await customer_with_paid_and_pending(client)
    admin = await admin_headers(client)
    uid = await user_id(client, "me@test.com")
    reason = ("사유" * 300)[:length]
    stock_before = await scalar(client, "SELECT remaining_stock FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id))

    r = await withdraw(client, admin, str(uid), reason=reason)

    assert r.status_code == 200, r.text
    assert r.json()["status"] == "WITHDRAWN" and r.json()["cancelled_reservation_count"] == 2
    # 원문 사유는 탈퇴 기록에 그대로
    assert await scalar(client, "SELECT deleted_reason FROM users WHERE id = :u", u=uid) == reason
    # 환불은 전액, 사유는 고정 문구
    amount = await scalar(client, "SELECT amount FROM payments WHERE id = :p", p=uuid.UUID(pid))
    refund_amount, penalty, refund_reason = (
        await scalar(client, "SELECT refund_amount FROM refunds WHERE payment_id = :p", p=uuid.UUID(pid)),
        await scalar(client, "SELECT penalty_amount FROM refunds WHERE payment_id = :p", p=uuid.UUID(pid)),
        await scalar(client, "SELECT reason FROM refunds WHERE payment_id = :p", p=uuid.UUID(pid)),
    )
    assert (refund_amount, penalty, refund_reason) == (amount, 0, FIXED)
    assert await scalar(client, "SELECT status FROM payments WHERE id = :p", p=uuid.UUID(pid)) == "REFUNDED"
    # 예약 둘 다 취소, 재고 복구. 재고 기록 사유는 Catalog 고정 문구이고 관리자 원문 사유는 들어가지 않는다
    for res in (rid, pending):
        assert await scalar(client, "SELECT status FROM pickup_reservations WHERE id = :i", i=uuid.UUID(res)) == "CANCELLED"
    assert await scalar(client, "SELECT remaining_stock FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id)) == stock_before + 2
    reasons = await scalar(
        client, "SELECT string_agg(DISTINCT reason, ',') FROM stock_log WHERE amount > 0 AND reason <> '최초 입고'"
    )
    assert reasons == "예약 취소 복구"
    assert await scalar(client, "SELECT count(*) FROM stock_log WHERE reason = :r", r=reason) == 0


async def test_admin_withdrawal_reason_over_500_is_rejected_and_changes_nothing(client):
    await customer_with_paid_and_pending(client)
    admin = await admin_headers(client)
    uid = await user_id(client, "me@test.com")
    before = await everything(client)
    r = await withdraw(client, admin, str(uid), reason="가" * 501)
    assert r.status_code == 400, r.text
    assert await everything(client) == before


async def test_self_withdrawal_reason_is_unchanged(client):
    me, _, pid, _, _ = await customer_with_paid_and_pending(client)
    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(me))
    assert r.status_code == 200, r.text
    assert await scalar(client, "SELECT reason FROM refunds WHERE payment_id = :p", p=uuid.UUID(pid)) == "회원 본인 탈퇴"
