"""환불 사유 길이 + 실제 PostgreSQL (payments REQ-34, 사용자 결정 2026-11-10).

길이는 앞뒤 공백을 뺀 값으로 1~200자이고, 저장도 앞뒤 공백을 뺀 값으로 한다. 그래서 원문이 200자를 넘어도
refunds.reason(VARCHAR(200))에 오류 없이 저장된다. 거절된 요청은 환불·결제·예약·포인트를 바꾸지 않는다.
"""

import uuid

import pytest

from tests.helpers import bearer, token_for
from tests.payments.test_rd40_db import everything
from tests.reservations.test_api_db import reserve, seed_offer
from tests.reservations.test_stock_db import pay, scalar

pytestmark = [pytest.mark.db, pytest.mark.anyio]


async def paid_payment(c):
    _, offer_id, _ = await seed_offer(c, stock=5)
    me = await token_for(c, "me@test.com")
    rid = (await reserve(c, me, offer_id, 1)).json()["id"]
    p = await pay(c, me, rid)
    assert p.status_code == 201, p.text
    return me, p.json()["id"]


async def refund_with(c, token, pid, reason):
    return await c.post(f"/v1/payments/{pid}/refunds", json={"reason": reason}, headers=bearer(token))


@pytest.mark.parametrize(
    "reason,stored",
    [
        ("가" * 200, "가" * 200),
        ("     " + "가" * 200 + "     ", "가" * 200),  # 원문 210자, 저장 200자
        ("　\n" + "나 " * 99 + "나" + "\t ", "나 " * 99 + "나"),  # 단어 사이 공백은 유지
    ],
)
async def test_trimmed_reason_up_to_200_is_stored_without_db_error(client, reason, stored):
    me, pid = await paid_payment(client)
    r = await refund_with(client, me, pid, reason)
    assert r.status_code == 201, r.text
    saved = await scalar(client, "SELECT reason FROM refunds WHERE payment_id = :p", p=uuid.UUID(pid))
    assert saved == stored and len(saved) <= 200


@pytest.mark.parametrize("reason", ["가" * 201, "  " + "가" * 201 + "  ", "   ", "　\n\t"])
async def test_invalid_reason_is_400_and_changes_nothing(client, reason):
    me, pid = await paid_payment(client)
    before = await everything(client)
    r = await refund_with(client, me, pid, reason)
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR", r.text
    assert await everything(client) == before
