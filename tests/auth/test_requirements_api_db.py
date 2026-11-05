"""auth 요구조건 정합(§15) API·DB 통합 테스트. skip은 통과가 아니다 (R16)."""

import uuid

import pytest
from sqlalchemy import text

import container
from auth.domain.service import PasswordResetNotifier
from tests.admin.test_api_db import ADMIN_PASSWORD, admin_headers, assert_error, user_id
from tests.helpers import bearer, login, signup, token_for
from tests.payments.test_payments_db import balance, pay_point, set_balance
from tests.reservations.test_api_db import seed, seed_offer
from tests.reservations.test_stock_db import scalar
from tests.reservations.test_withdrawal_db import make_reserved, status_of

pytestmark = [pytest.mark.db, pytest.mark.anyio]


class CollectingNotifier(PasswordResetNotifier):
    def __init__(self):
        self.sent = []

    async def send_code(self, email, code, expires_at):
        self.sent.append((email, code))

    def last(self, email):
        return [c for e, c in self.sent if e == email][-1]


@pytest.fixture
def notifier(monkeypatch):
    fake = CollectingNotifier()
    monkeypatch.setattr(container, "_reset_notifier", fake)
    return fake


async def me(c, token):
    return await c.get("/v1/users/me", headers=bearer(token))


async def tokens_of(c, email="user@test.com"):
    return (await login(c, email)).json()["access_token"]


# ── 가입 필수 (REQ-2·6·7) ──
@pytest.mark.parametrize("missing", ["name", "phone"])
async def test_signup_requires_name_and_phone(client, missing):
    body = {"email": "x@test.com", "password": "password123", "role": "CUSTOMER",
            "name": "홍", "phone": "010"}
    del body[missing]
    r = await client.post("/v1/auth/signup", json=body)
    assert_error(r, 400, "VALIDATION_ERROR")
    assert missing in r.json()["message"]


@pytest.mark.parametrize("name,phone", [("  ", "010"), ("홍", "   "), ("가" * 101, "010"), ("홍", "1" * 101)])
async def test_signup_rejects_blank_and_too_long(client, name, phone):
    r = await client.post("/v1/auth/signup", json={
        "email": "x@test.com", "password": "password123", "role": "CUSTOMER", "name": name, "phone": phone})
    assert_error(r, 400, "VALIDATION_ERROR")


# ── 프로필 (REQ-22·23) ──
async def test_patch_profile(client):
    t = await token_for(client)
    r = await client.patch("/v1/users/me", json={"name": "새이름"}, headers=bearer(t))
    assert r.status_code == 200 and r.json()["name"] == "새이름" and r.json()["phone"] == "010-0000-0000"
    r = await client.patch("/v1/users/me", json={"phone": "011", "email": "hack@x.com", "role": "ADMIN"},
                           headers=bearer(t))
    body = r.json()
    assert r.status_code == 200 and body["phone"] == "011"
    assert body["email"] == "user@test.com" and body["role"] == "CUSTOMER"  # 무시됨
    assert "password_hash" not in body


async def test_patch_profile_errors(client):
    t = await token_for(client)
    assert_error(await client.patch("/v1/users/me", json={}, headers=bearer(t)), 400, "VALIDATION_ERROR",
                 "변경할 항목이 없습니다.")
    assert_error(await client.patch("/v1/users/me", json={"name": "  "}, headers=bearer(t)), 400,
                 "VALIDATION_ERROR")
    assert (await client.patch("/v1/users/me", json={"name": "x"})).status_code == 401


async def test_patch_profile_legacy_member_missing_phone(client):
    t = await token_for(client)
    async with client.session_factory() as s:
        await s.execute(text("UPDATE users SET phone = NULL"))
        await s.commit()
    r = await client.patch("/v1/users/me", json={"name": "새이름"}, headers=bearer(t))
    assert_error(r, 400, "VALIDATION_ERROR")
    r = await client.patch("/v1/users/me", json={"name": "새이름", "phone": "010"}, headers=bearer(t))
    assert r.status_code == 200


# ── 비밀번호 변경 (REQ-24) ──
async def test_change_password_keeps_current_token_only(client):
    await signup(client)
    a, b = await tokens_of(client), await tokens_of(client)
    r = await client.post("/v1/users/me/password",
                          json={"current_password": "password123", "new_password": "newpassword1"},
                          headers=bearer(a))
    assert r.status_code == 204 and r.content == b""
    assert (await me(client, a)).status_code == 200
    r = await me(client, b)
    assert_error(r, 401, "TOKEN_REVOKED", "비밀번호가 변경되어 무효가 된 토큰입니다.")
    assert r.headers["www-authenticate"] == "Bearer"
    assert (await login(client, password="password123")).status_code == 401
    c = await tokens_of_pw(client, "newpassword1")
    assert (await me(client, c)).status_code == 200
    assert (await me(client, a)).status_code == 200  # 변경에 쓴 토큰은 계속 유효


async def tokens_of_pw(c, pw, email="user@test.com"):
    return (await login(c, email, pw)).json()["access_token"]


async def test_change_password_errors(client):
    t = await token_for(client)
    r = await client.post("/v1/users/me/password",
                          json={"current_password": "wrong-pass", "new_password": "newpassword1"},
                          headers=bearer(t))
    assert_error(r, 400, "CURRENT_PASSWORD_MISMATCH")
    r = await client.post("/v1/users/me/password",
                          json={"current_password": "password123", "new_password": "short"}, headers=bearer(t))
    assert_error(r, 400, "VALIDATION_ERROR")
    r = await client.post("/v1/users/me/password", json={"current_password": "password123"}, headers=bearer(t))
    assert_error(r, 400, "VALIDATION_ERROR")
    assert (await tokens_of_pw(client, "password123"))  # 실패는 비밀번호·토큰을 바꾸지 않음
    assert (await me(client, t)).status_code == 200


async def test_second_change_revokes_previous_kept_token(client):
    await signup(client)
    a = await tokens_of(client)
    await client.post("/v1/users/me/password",
                      json={"current_password": "password123", "new_password": "newpassword1"}, headers=bearer(a))
    b = await tokens_of_pw(client, "newpassword1")
    r = await client.post("/v1/users/me/password",
                          json={"current_password": "newpassword1", "new_password": "third-pass1"},
                          headers=bearer(b))
    assert r.status_code == 204
    assert_error(await me(client, a), 401, "TOKEN_REVOKED")
    assert (await me(client, b)).status_code == 200


# ── 재설정 (REQ-25~32) ──
async def test_password_reset_flow_revokes_all_tokens(client, notifier):
    await signup(client)
    t1, t2 = await tokens_of(client), await tokens_of(client)
    r = await client.post("/v1/auth/password-reset/request", json={"email": "USER@test.com"})
    assert r.status_code == 204
    code = notifier.last("user@test.com")
    assert len(code) == 6 and code.isdigit()
    stored = await scalar(client, "SELECT code_hash FROM password_reset_codes")
    assert stored != code and stored.startswith("$2")  # 해시 저장
    r = await client.post("/v1/auth/password-reset/confirm",
                          json={"email": "user@test.com", "code": code, "new_password": "resetpass12"})
    assert r.status_code == 204
    assert await scalar(client, "SELECT count(*) FROM password_reset_codes") == 0
    assert_error(await me(client, t1), 401, "TOKEN_REVOKED")
    assert_error(await me(client, t2), 401, "TOKEN_REVOKED")
    assert (await login(client, password="password123")).status_code == 401
    assert (await me(client, await tokens_of_pw(client, "resetpass12"))).status_code == 200
    r = await client.post("/v1/auth/password-reset/confirm",
                          json={"email": "user@test.com", "code": code, "new_password": "resetpass34"})
    assert_error(r, 400, "INVALID_RESET_CODE", "재설정 코드가 올바르지 않거나 만료되었습니다.")


async def test_password_reset_request_is_204_for_unknown_and_withdrawn(client, notifier):
    assert (await client.post("/v1/auth/password-reset/request", json={"email": "no@test.com"})).status_code == 204
    await signup(client)
    async with client.session_factory() as s:
        await s.execute(text("UPDATE users SET status='WITHDRAWN', deleted_at=now(), deleted_reason='x'"))
        await s.commit()
    assert (await client.post("/v1/auth/password-reset/request", json={"email": "user@test.com"})).status_code == 204
    assert notifier.sent == [] and await scalar(client, "SELECT count(*) FROM password_reset_codes") == 0
    r = await client.post("/v1/auth/password-reset/confirm",
                          json={"email": "user@test.com", "code": "123456", "new_password": "resetpass12"})
    assert_error(r, 400, "INVALID_RESET_CODE")
    assert (await client.post("/v1/auth/password-reset/request", json={})).status_code == 400


async def test_password_reset_five_failures_lock_even_right_code(client, notifier):
    await signup(client)
    await client.post("/v1/auth/password-reset/request", json={"email": "user@test.com"})
    code = notifier.last("user@test.com")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        r = await client.post("/v1/auth/password-reset/confirm",
                              json={"email": "user@test.com", "code": wrong, "new_password": "resetpass12"})
        assert_error(r, 400, "INVALID_RESET_CODE")
    assert await scalar(client, "SELECT failed_attempts FROM password_reset_codes") == 5  # 예외에도 저장됨
    r = await client.post("/v1/auth/password-reset/confirm",
                          json={"email": "user@test.com", "code": code, "new_password": "resetpass12"})
    assert_error(r, 400, "INVALID_RESET_CODE")
    assert (await login(client, password="password123")).status_code == 200  # 비밀번호 그대로


async def test_password_reset_validation_does_not_count_attempts(client, notifier):
    await signup(client)
    await client.post("/v1/auth/password-reset/request", json={"email": "user@test.com"})
    code = notifier.last("user@test.com")
    for body in (
        {"email": "user@test.com", "code": "12345", "new_password": "resetpass12"},  # 형식
        {"email": "user@test.com", "code": "abcdef", "new_password": "resetpass12"},
        {"email": "user@test.com", "code": "000000", "new_password": "short"},  # 약한 비밀번호
    ):
        assert_error(await client.post("/v1/auth/password-reset/confirm", json=body), 400, "VALIDATION_ERROR")
    assert await scalar(client, "SELECT failed_attempts FROM password_reset_codes") == 0
    r = await client.post("/v1/auth/password-reset/confirm",
                          json={"email": "user@test.com", "code": code, "new_password": "resetpass12"})
    assert r.status_code == 204


async def test_password_reset_expired_and_rerequest(client, notifier):
    await signup(client)
    await client.post("/v1/auth/password-reset/request", json={"email": "user@test.com"})
    first = notifier.last("user@test.com")
    await client.post("/v1/auth/password-reset/request", json={"email": "user@test.com"})
    second = notifier.last("user@test.com")
    assert await scalar(client, "SELECT count(*) FROM password_reset_codes") == 1  # 회원당 1행
    if first != second:
        r = await client.post("/v1/auth/password-reset/confirm",
                              json={"email": "user@test.com", "code": first, "new_password": "resetpass12"})
        assert_error(r, 400, "INVALID_RESET_CODE")
    async with client.session_factory() as s:
        await s.execute(text("UPDATE password_reset_codes SET expires_at = now() - interval '1 second'"))
        await s.commit()
    r = await client.post("/v1/auth/password-reset/confirm",
                          json={"email": "user@test.com", "code": second, "new_password": "resetpass12"})
    assert_error(r, 400, "INVALID_RESET_CODE")


# ── 정지 회원 로그아웃 (B-2) ──
async def test_suspended_member_can_logout_but_not_use_other_apis(client):
    await signup(client, "u@test.com")
    t = await tokens_of(client, "u@test.com")
    uid = str(await user_id(client, "u@test.com"))
    admin = await admin_headers(client)
    r = await client.patch(f"/v1/admin/users/{uid}/suspend", json={"reason": "점검", "suspended_until": None},
                           headers=admin)
    assert r.status_code == 200, r.text
    assert (await me(client, t)).status_code == 403
    assert (await client.post("/v1/auth/logout", headers=bearer(t))).status_code == 204
    assert_error(await client.post("/v1/auth/logout", headers=bearer(t)), 401, "TOKEN_REVOKED")


async def test_withdrawn_token_logout_is_401(client):
    t = await token_for(client)
    async with client.session_factory() as s:
        await s.execute(text("UPDATE users SET status='WITHDRAWN', deleted_at=now(), deleted_reason='x'"))
        await s.commit()
    assert (await client.post("/v1/auth/logout", headers=bearer(t))).status_code == 401


# ── 탈퇴: 환불 -> 포인트 복구 -> 소멸 (자진·admin 공통 순서) ──
async def point_logs(c, email):
    async with c.session_factory() as s:
        rows = (await s.execute(text(
            "SELECT p.point_type, p.amount, p.balance_after FROM point_log p JOIN users u ON u.id = p.user_id "
            "WHERE u.email = :e ORDER BY p.created_at, p.id"), {"e": email})).all()
    return [tuple(r) for r in rows]


async def paid_customer(c, email="me@test.com"):
    """잔액 2000, 포인트 1000 사용 결제 완료(예약 RESERVED) 상태의 고객. (token, reservation_id) 반환."""
    owner, offer_id, _ = await seed_offer(c, stock=10)
    token = await token_for(c, email)
    rid, _ = await seed(c, token, offer_id)  # 총액 6000
    await set_balance(c, email, 2000)
    r = await pay_point(c, token, rid, 1000)
    assert r.status_code == 201, r.text
    assert await balance(c, email) == 1050  # -1000 사용, +50 적립
    return token, rid, offer_id


async def assert_refunded_then_expired(c, email, rid, uid):
    assert await status_of(c, rid) == "CANCELLED"
    assert await scalar(c, "SELECT count(*) FROM refunds") == 1
    assert await scalar(c, "SELECT status FROM users WHERE id = :i", i=uid) == "WITHDRAWN"
    assert await balance(c, email) == 0
    logs = await point_logs(c, email)
    types = [t for t, _, _ in logs]
    # 환불의 복구(+1000)와 회수(-50)가 소멸보다 먼저, 소멸량은 복구된 잔액 전체
    assert types == ["USE", "EARN", "RESTORE", "REVOKE", "EXPIRE"], logs
    assert logs[-1] == ("EXPIRE", -2000, 0)


async def test_self_withdraw_paid_reservation_refunds_restores_then_expires(client):
    token, rid, _ = await paid_customer(client)
    uid = await user_id(client, "me@test.com")
    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "WITHDRAWN" and body["cancelled_reservation_count"] == 1
    assert body["id"] == str(uid) and body["deleted_at"]
    await assert_refunded_then_expired(client, "me@test.com", rid, uid)
    assert await scalar(client, "SELECT deleted_reason FROM users WHERE id = :i", i=uid) == "회원 본인 탈퇴"
    assert (await login(client, "me@test.com")).status_code == 401
    assert (await me(client, token)).status_code == 401


async def test_admin_forced_withdraw_paid_reservation_refunds_restores_then_expires(client):
    token, rid, _ = await paid_customer(client)
    uid = await user_id(client, "me@test.com")
    admin = await admin_headers(client)
    r = await client.request("DELETE", f"/v1/admin/users/{uid}", json={"reason": "약관 위반"}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["cancelled_reservation_count"] == 1
    await assert_refunded_then_expired(client, "me@test.com", rid, uid)


async def test_withdraw_zero_balance_leaves_no_expire_log(client):
    token = await token_for(client)
    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(token))
    assert r.status_code == 200 and r.json()["cancelled_reservation_count"] == 0
    assert await scalar(client, "SELECT count(*) FROM point_log") == 0


async def test_withdraw_errors(client):
    token = await token_for(client)
    assert_error(await client.post("/v1/users/me/withdraw", json={"password": "bad-pass12"}, headers=bearer(token)),
                 400, "CURRENT_PASSWORD_MISMATCH")
    assert_error(await client.post("/v1/users/me/withdraw", json={}, headers=bearer(token)), 400, "VALIDATION_ERROR")
    assert (await client.post("/v1/users/me/withdraw", json={"password": "password123"})).status_code == 401
    assert await scalar(client, "SELECT status FROM users") == "APPROVED"
    admin = await admin_headers(client)
    r = await client.post("/v1/users/me/withdraw", json={"password": ADMIN_PASSWORD}, headers=admin)
    assert_error(r, 400, "ADMIN_ACCOUNT_PROTECTED")


async def test_withdraw_suspended_member_is_403(client):
    token = await token_for(client, "u@test.com")
    uid = str(await user_id(client, "u@test.com"))
    admin = await admin_headers(client)
    await client.patch(f"/v1/admin/users/{uid}/suspend", json={"reason": "x", "suspended_until": None}, headers=admin)
    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(token))
    assert r.status_code == 403
    assert await scalar(client, "SELECT status FROM users WHERE id = :i", i=uuid.UUID(uid)) == "SUSPENDED"


async def test_self_withdraw_owner_blocked_by_other_customer_reservation_rolls_back(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    owner_id = await user_id(client, "owner@test.com")
    other = await token_for(client, "other@test.com")
    await make_reserved(client, other, offer_id, 1)
    own = await make_reserved(client, owner, offer_id, 1)
    before = await balance(client, "owner@test.com")  # 본인 결제 적립분 포함
    assert before > 0
    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(owner))
    assert_error(r, 400, "STORE_HAS_RESERVED_RESERVATIONS")
    assert await status_of(client, own) == "RESERVED"  # 전체 롤백
    assert await scalar(client, "SELECT status FROM users WHERE id = :i", i=owner_id) == "APPROVED"
    assert await scalar(client, "SELECT users_point FROM users WHERE id = :i", i=owner_id) == before
    assert await scalar(client, "SELECT count(*) FROM stores WHERE closed_at IS NOT NULL") == 0


async def test_self_withdraw_owner_closes_store_and_cancels_own_reservation(client):
    owner, offer_id, store_id = await seed_offer(client, stock=10)
    owner_id = await user_id(client, "owner@test.com")
    own = await make_reserved(client, owner, offer_id, 1)
    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(owner))
    assert r.status_code == 200, r.text
    assert r.json()["cancelled_reservation_count"] == 1
    assert await status_of(client, own) == "CANCELLED"
    assert await scalar(client, "SELECT closed_at IS NOT NULL FROM stores WHERE id = :i", i=uuid.UUID(store_id))
    assert await scalar(client, "SELECT status FROM users WHERE id = :i", i=owner_id) == "WITHDRAWN"


# ── 포인트 내역: EXPIRE·balance_after (REQ-53·55) ──
async def test_points_api_exposes_expire_and_balance_after(client):
    token, rid, _ = await paid_customer(client)
    r = await client.get("/v1/users/me/points", headers=bearer(token))
    logs = r.json()["logs"]
    assert {(x["point_type"], x["balance_after"]) for x in logs} == {("USE", 1000), ("EARN", 1050)}
    admin = await admin_headers(client)
    uid = await user_id(client, "me@test.com")
    assert (await client.request("DELETE", f"/v1/admin/users/{uid}", json={"reason": "x"}, headers=admin)).status_code == 200
    # 탈퇴 회원의 토큰은 401이므로 관리자 이력 조회로 확인
    r = await client.get(f"/v1/admin/users/{uid}/points", headers=admin)
    assert r.status_code == 200, r.text
    expire = [x for x in r.json()["history"] if x["type"] == "EXPIRE"]
    assert len(expire) == 1 and expire[0]["amount"] == -2000 and expire[0]["balance_after"] == 0
    assert r.json()["balance"] == 0


async def test_points_type_filter_accepts_expire(client):
    token = await token_for(client)
    r = await client.get("/v1/users/me/points?type=EXPIRE", headers=bearer(token))
    assert r.status_code == 200 and r.json()["logs"] == []
    assert_error(await client.get("/v1/users/me/points?type=BOGUS", headers=bearer(token)), 400, "VALIDATION_ERROR")


async def test_user_columns_default_and_reset_table_fk(client):
    await signup(client)
    assert await scalar(client, "SELECT token_version FROM users") == 0
    assert await scalar(client, "SELECT token_keep_jti IS NULL FROM users")
    async with client.session_factory() as s:
        with pytest.raises(Exception):
            await s.execute(text(
                "INSERT INTO password_reset_codes (user_id, code_hash, expires_at) "
                "VALUES (gen_random_uuid(), 'h', now())"))
            await s.commit()
