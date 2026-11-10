"""탈퇴 후 본인 예약·결제·환불 조회 불가 + 실제 PostgreSQL.

auth 확정 정책(REQ-34 ③, REQ-35): 탈퇴하면 기존 토큰은 무효(401)이고, 본인 기록도 볼 수 없다.
결제·예약 요구조건: 탈퇴 전까지는 본인의 예약·결제·환불을 조회할 수 있다. 본인 탈퇴와 관리자 강제 탈퇴 모두 같다.
기록 자체는 지우지 않는다(보존). 오류 응답은 공통 형식(401 UNAUTHORIZED, WWW-Authenticate: Bearer)을 따른다.
"""

import uuid

import pytest

from tests.admin.test_api_db import admin_headers, user_id
from tests.helpers import bearer, token_for
from tests.reservations.test_api_db import reserve, seed_offer
from tests.reservations.test_stock_db import pay, refund, scalar
from tests.reservations.test_withdrawal_db import withdraw

pytestmark = [pytest.mark.db, pytest.mark.anyio]


async def history(c, email="me@test.com"):
    """환불까지 끝난 예약 1건 + 결제 대기 예약 1건(다른 할인)을 가진 고객."""
    _, offer_a, _ = await seed_offer(c, stock=5)
    _, offer_b, _ = await seed_offer(c, stock=5, email="owner2@test.com")
    me = await token_for(c, email)
    rid = (await reserve(c, me, offer_a, 1)).json()["id"]
    p = await pay(c, me, rid)
    assert p.status_code == 201, p.text
    pid = p.json()["id"]
    rf = await refund(c, me, pid)
    assert rf.status_code == 201, rf.text
    refund_id = rf.json()["id"]
    assert (await reserve(c, me, offer_b, 1)).status_code == 201
    return me, pid, refund_id


def urls(pid, refund_id):
    return ["/v1/users/me/reservations", f"/v1/payments/{pid}", f"/v1/refunds/{refund_id}"]


async def assert_all_200(c, token, pid, refund_id):
    for url in urls(pid, refund_id):
        r = await c.get(url, headers=bearer(token))
        assert r.status_code == 200, (url, r.text)
    body = (await c.get("/v1/users/me/reservations", headers=bearer(token))).json()
    assert body["total"] == 2
    assert (await c.get(f"/v1/payments/{pid}", headers=bearer(token))).json()["status"] == "REFUNDED"
    assert (await c.get(f"/v1/refunds/{refund_id}", headers=bearer(token))).json()["payment_id"] == pid


async def assert_all_401(c, token, pid, refund_id):
    for url in urls(pid, refund_id):
        r = await c.get(url, headers=bearer(token))
        assert r.status_code == 401, (url, r.text)
        assert r.headers.get("www-authenticate") == "Bearer", url
        body = r.json()
        assert body["success"] is False and body["error_code"] == "UNAUTHORIZED", (url, body)
        assert pid not in r.text and refund_id not in r.text  # 기록 정보가 새지 않음


async def records_kept(c, pid, refund_id, email="me@test.com"):
    """탈퇴해도 결제·환불·예약 기록은 지우지 않는다(보존 원칙)."""
    assert await scalar(c, "SELECT count(*) FROM payments WHERE id = :i", i=uuid.UUID(pid)) == 1
    assert await scalar(c, "SELECT count(*) FROM refunds WHERE id = :i", i=uuid.UUID(refund_id)) == 1
    uid = await user_id(c, email)
    assert await scalar(c, "SELECT count(*) FROM pickup_reservations WHERE user_id = :u", u=uid) == 2


async def assert_login_rejected(c, email="me@test.com"):
    """탈퇴 회원은 다시 로그인할 수 없다(없는 계정과 같은 401, auth REQ-35). 새 토큰으로 우회 불가."""
    r = await c.post("/v1/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 401 and r.json()["success"] is False, r.text


async def test_self_withdrawal_blocks_viewing_own_history(client):
    me, pid, refund_id = await history(client)
    await assert_all_200(client, me, pid, refund_id)  # 탈퇴 전: 본인 조회 가능

    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(me))
    assert r.status_code == 200 and r.json()["status"] == "WITHDRAWN", r.text

    await assert_all_401(client, me, pid, refund_id)  # 탈퇴 후: 기존 토큰 401
    await records_kept(client, pid, refund_id)
    await assert_login_rejected(client)


async def test_admin_forced_withdrawal_blocks_viewing_own_history(client):
    me, pid, refund_id = await history(client)
    await assert_all_200(client, me, pid, refund_id)

    admin = await admin_headers(client)
    uid = str(await user_id(client, "me@test.com"))
    r = await withdraw(client, admin, uid)
    assert r.status_code == 200, r.text

    await assert_all_401(client, me, pid, refund_id)
    await records_kept(client, pid, refund_id)
    await assert_login_rejected(client)


async def test_other_user_still_cannot_view_and_is_not_affected(client):
    """탈퇴와 무관한 기존 권한 규칙 유지: 다른 회원은 처음부터 403, 탈퇴는 그 회원에게만 영향."""
    me, pid, refund_id = await history(client)
    other = await token_for(client, "other@test.com")
    assert (await client.get(f"/v1/payments/{pid}", headers=bearer(other))).status_code == 403
    assert (await client.get(f"/v1/refunds/{refund_id}", headers=bearer(other))).status_code == 403
    assert (await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(me))).status_code == 200
    r = await client.get("/v1/users/me/reservations", headers=bearer(other))
    assert r.status_code == 200 and r.json()["total"] == 0  # 다른 회원 토큰은 그대로 유효
