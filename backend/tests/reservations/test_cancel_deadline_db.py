"""결제 완료 예약의 고객 취소·환불 시간 제한 + 실제 PostgreSQL (payments REQ-6, reservations REQ-26).

마감 시각은 Catalog 할인의 취소 정책(pickup_start - 1시간, D55)에서 온다. 정확한 경계 시각은 허용, 지나면 거절.
고객 취소 API와 직접 환불 API 모두 막고, 결제 대기 취소와 일괄 취소(판매 중단·탈퇴)는 제외한다.
데이터 불일치(500)는 시간 제한(400)보다 먼저다. 거절된 요청은 아무것도 바꾸지 않는다.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

import container
from tests.admin.test_api_db import admin_headers, user_id
from tests.helpers import bearer, token_for
from tests.payments.test_rd40_db import everything
from tests.reservations.test_api_db import reserve, seed
from tests.reservations.test_stock_db import cancel, deactivate, pay, refund, scalar
from tests.reservations.test_withdrawal_db import withdraw

pytestmark = [pytest.mark.db, pytest.mark.anyio]

M = timedelta(minutes=1)
DEADLINE = {
    "success": False,
    "error_code": "CANCELLATION_DEADLINE_PASSED",
    "message": "취소 가능 시각이 지나 취소·환불할 수 없습니다.",
}


async def make_offer(c, *, pickup_in: timedelta, email="owner@test.com", stock=10):
    """픽업 시작을 지금부터 pickup_in 뒤로 둔 할인. 판매는 2시간 뒤까지 열려 있다."""
    now = datetime.now(timezone.utc)
    owner = await token_for(c, email, "OWNER")
    r = await c.post("/v1/stores", json={"pickup_address": f"서울 강남구 {email}"}, headers=bearer(owner))
    assert r.status_code == 201, r.text
    r = await c.post(
        f"/v1/stores/{r.json()['id']}/products",
        json={"name": "샌드위치", "original_price": 6000}, headers=bearer(owner),
    )
    assert r.status_code == 201, r.text
    r = await c.post(
        f"/v1/products/{r.json()['id']}/offers",
        json={
            "sale_price": 3000, "initial_stock": stock,
            "sales_end": (now + 120 * M).isoformat(),
            "pickup_start": (now + pickup_in).isoformat(),
            "pickup_end": (now + 180 * M).isoformat(),
        },
        headers=bearer(owner),
    )
    assert r.status_code == 201, r.text
    return owner, r.json()["id"]


async def paid_reservation(c, offer_id, email="me@test.com"):
    me = await token_for(c, email)
    r = await reserve(c, me, offer_id, 1)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    p = await pay(c, me, rid)
    assert p.status_code == 201, p.text
    return me, rid, p.json()["id"]


async def test_paid_cancel_and_refund_after_deadline_are_rejected_and_change_nothing(client):
    _, offer_id = await make_offer(client, pickup_in=30 * M)  # 마감 = 30분 전(이미 지남)
    me, rid, pid = await paid_reservation(client, offer_id)
    before = await everything(client)
    r = await cancel(client, me, rid)
    assert r.status_code == 400 and r.json() == DEADLINE, r.text
    r = await refund(client, me, pid)
    assert r.status_code == 400 and r.json() == DEADLINE, r.text
    assert await everything(client) == before  # 예약·결제·환불·재고·포인트 그대로


async def test_paid_cancel_before_deadline_still_refunds(client):
    _, offer_id = await make_offer(client, pickup_in=150 * M)  # 마감 = 1시간 30분 뒤
    me, rid, _ = await paid_reservation(client, offer_id)
    r = await cancel(client, me, rid)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED", r.text
    assert await scalar(client, "SELECT count(*) FROM refunds") == 1


async def test_pending_cancel_has_no_time_limit(client):
    _, offer_id = await make_offer(client, pickup_in=30 * M)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 1)).json()["id"]
    r = await cancel(client, me, rid)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED", r.text


async def test_offer_deactivate_bulk_cancel_refunds_after_deadline(client):
    owner, offer_id = await make_offer(client, pickup_in=30 * M)
    await paid_reservation(client, offer_id)
    r = await deactivate(client, owner, offer_id)
    assert r.status_code == 200 and r.json()["cancelled_reservation_count"] == 1, r.text
    assert await scalar(client, "SELECT count(*) FROM refunds") == 1


async def test_withdrawal_bulk_cancel_refunds_after_deadline(client):
    _, offer_id = await make_offer(client, pickup_in=30 * M)
    await paid_reservation(client, offer_id)
    admin = await admin_headers(client)
    uid = str(await user_id(client, "me@test.com"))
    r = await withdraw(client, admin, uid)
    assert r.status_code == 200 and r.json()["cancelled_reservation_count"] == 1, r.text
    assert await scalar(client, "SELECT count(*) FROM refunds") == 1


class AtClock:
    def __init__(self, at):
        self.at = at

    def now(self):
        return self.at


@pytest.mark.parametrize("offset,expected", [(timedelta(0), 200), (timedelta(microseconds=1), 400)])
@pytest.mark.parametrize("path", ["cancel", "refund"])
async def test_exact_deadline_is_allowed_and_one_microsecond_after_is_rejected(client, monkeypatch, path, offset, expected):
    _, offer_id = await make_offer(client, pickup_in=150 * M)
    me, rid, pid = await paid_reservation(client, offer_id)
    pickup_start = await scalar(client, "SELECT pickup_start FROM discount_offers WHERE id = :i", i=uuid.UUID(offer_id))
    at = pickup_start - timedelta(hours=1) + offset  # Catalog 정책의 취소 가능 시각 기준
    monkeypatch.setattr(container, "_payments_clock", AtClock(at))
    monkeypatch.setattr(container, "_reservations_clock", AtClock(at))
    r = await (cancel(client, me, rid) if path == "cancel" else refund(client, me, pid))
    assert r.status_code == (201 if path == "refund" and expected == 200 else expected), r.text
    if expected == 400:
        assert r.json() == DEADLINE


async def test_inconsistency_500_beats_deadline_400(client):
    """예약은 결제 완료인데 결제 기록이 없는 불일치(RD-38 ①) + 마감 지남 -> 500이 먼저."""
    _, offer_id = await make_offer(client, pickup_in=30 * M)
    me = await token_for(client, "me@test.com")
    rid, _ = await seed(client, me, offer_id, 1, paid=True)  # RESERVED, 결제 행 없음
    before = await everything(client)
    r = await cancel(client, me, rid)
    assert r.status_code == 500 and r.json()["error_code"] == "DATA_INCONSISTENT", r.text
    assert await everything(client) == before
