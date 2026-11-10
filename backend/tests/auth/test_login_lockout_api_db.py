"""REQ-13~13-3 로그인 잠금, REQ-27-1 전달 분리, REQ-35-1 코드 삭제 API·DB 통합 테스트. skip은 통과가 아니다 (R16)."""

import asyncio

import pytest
from sqlalchemy import text

import container
from auth.domain.service import PasswordResetNotifier
from tests.admin.test_api_db import ADMIN_PASSWORD, admin_headers, assert_error, user_id
from tests.helpers import bearer, login, signup
from tests.reservations.test_stock_db import scalar

pytestmark = [pytest.mark.db, pytest.mark.anyio]

EMAIL = "user@test.com"


class CollectingNotifier(PasswordResetNotifier):
    def __init__(self):
        self.sent = []

    async def send_code(self, email, code, expires_at):
        self.sent.append((email, code))


@pytest.fixture
def notifier(monkeypatch):
    fake = CollectingNotifier()
    monkeypatch.setattr(container, "_reset_notifier", fake)
    return fake


async def wrong(c, n, email=EMAIL):
    return [await login(c, email, "wrong-pass12") for _ in range(n)]


async def row(c, email=EMAIL):
    async with c.session_factory() as s:
        return (await s.execute(
            text("SELECT failed_login_count, login_locked_until FROM users WHERE email = :e"), {"e": email}
        )).one()


async def test_locked_right_password_is_429_with_retry_after(client):
    await signup(client)
    for r in await wrong(client, 5):
        assert_error(r, 401, "INVALID_CREDENTIALS")  # 5번째 실패도 보통의 401
    r = await login(client)
    assert r.status_code == 429
    body = r.json()
    assert set(body) == {"success", "error_code", "message"}
    assert body["success"] is False and body["error_code"] == "ACCOUNT_LOCKED"
    assert "10분" in body["message"]
    assert 1 <= int(r.headers["retry-after"]) <= 600
    assert "www-authenticate" not in r.headers


async def test_locked_wrong_password_is_401_and_lock_not_extended(client):
    await signup(client)
    await wrong(client, 5)
    before = await row(client)
    assert before.failed_login_count == 0 and before.login_locked_until is not None
    for r in await wrong(client, 3):
        assert_error(r, 401, "INVALID_CREDENTIALS")
    assert (await login(client)).status_code == 429
    assert await row(client) == before  # 횟수·잠금 시각 불변 (REQ-13-3)


async def test_other_accounts_and_unknown_email_are_not_affected(client):
    await signup(client)
    await signup(client, "other@test.com")
    await wrong(client, 5)
    assert (await login(client, "other@test.com")).status_code == 200
    for r in await wrong(client, 7, "nobody@test.com"):
        assert_error(r, 401, "INVALID_CREDENTIALS")
    assert_error(await login(client, "nobody@test.com", "password123"), 401, "INVALID_CREDENTIALS")


async def test_success_resets_count_and_lock_expiry_allows_login(client):
    await signup(client)
    await wrong(client, 3)
    assert (await login(client)).status_code == 200
    assert (await row(client)).failed_login_count == 0
    await wrong(client, 5)
    async with client.session_factory() as s:  # 잠금 시각을 과거로 돌려 만료를 흉내
        await s.execute(text("UPDATE users SET login_locked_until = now() - interval '1 second'"))
        await s.commit()
    assert (await login(client)).status_code == 200
    assert (await row(client)).login_locked_until is None


async def test_password_reset_unlocks_login(client, notifier):
    await signup(client)
    await wrong(client, 5)
    assert (await login(client)).status_code == 429
    assert (await client.post("/v1/auth/password-reset/request", json={"email": EMAIL})).status_code == 204
    code = notifier.sent[-1][1]  # BackgroundTasks가 응답 뒤 전달한 코드
    r = await client.post("/v1/auth/password-reset/confirm",
                          json={"email": EMAIL, "code": code, "new_password": "resetpass12"})
    assert r.status_code == 204
    assert (await login(client, EMAIL, "resetpass12")).status_code == 200
    assert (await row(client)).failed_login_count == 0


async def test_concurrent_wrong_attempts_do_not_lose_updates(client):
    await signup(client)
    results = await asyncio.gather(*[login(client, EMAIL, "wrong-pass12") for _ in range(4)])
    assert all(r.status_code == 401 for r in results)
    assert (await row(client)).failed_login_count == 4


async def test_ten_concurrent_wrong_attempts_lock_once(client):
    await signup(client)
    results = await asyncio.gather(*[login(client, EMAIL, "wrong-pass12") for _ in range(10)])
    assert all(r.status_code == 401 for r in results)
    r = await row(client)
    assert r.failed_login_count == 0 and r.login_locked_until is not None
    assert (await login(client)).status_code == 429


async def test_reset_request_same_204_and_delivery_after_response(client, notifier):
    await signup(client)
    a = await client.post("/v1/auth/password-reset/request", json={"email": EMAIL})
    b = await client.post("/v1/auth/password-reset/request", json={"email": "nobody@test.com"})
    assert a.status_code == b.status_code == 204 and a.content == b.content == b""
    assert [e for e, _ in notifier.sent] == [EMAIL]  # 미가입에는 전달 없음


async def test_self_withdraw_deletes_reset_code(client, notifier):
    await signup(client)
    token = (await login(client)).json()["access_token"]
    await client.post("/v1/auth/password-reset/request", json={"email": EMAIL})
    assert await scalar(client, "SELECT count(*) FROM password_reset_codes") == 1
    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(token))
    assert r.status_code == 200, r.text
    assert await scalar(client, "SELECT count(*) FROM password_reset_codes") == 0


async def test_admin_forced_withdraw_deletes_reset_code(client, notifier):
    h = await admin_headers(client)
    await signup(client)
    uid = await user_id(client, EMAIL)
    await client.post("/v1/auth/password-reset/request", json={"email": EMAIL})
    assert await scalar(client, "SELECT count(*) FROM password_reset_codes") == 1
    r = await client.request("DELETE", f"/v1/admin/users/{uid}", json={"reason": "약관 위반"}, headers=h)
    assert r.status_code == 200, r.text
    assert await scalar(client, "SELECT count(*) FROM password_reset_codes") == 0


async def test_concurrent_withdraw_and_reset_request_no_deadlock_no_leftover_code(client, notifier):
    h = await admin_headers(client)
    await signup(client)
    uid = await user_id(client, EMAIL)

    async def withdraw():
        return await client.request("DELETE", f"/v1/admin/users/{uid}", json={"reason": "사유"}, headers=h)

    async def request():
        return await client.post("/v1/auth/password-reset/request", json={"email": EMAIL})

    for _ in range(1):
        w, *reqs = await asyncio.gather(withdraw(), request(), request(), request())
    assert w.status_code == 200 and all(r.status_code == 204 for r in reqs)
    assert await scalar(client, "SELECT count(*) FROM password_reset_codes") == 0  # 회원 행 -> 코드 행 순서


async def test_concurrent_withdraw_and_confirm_no_deadlock(client, notifier):
    h = await admin_headers(client)
    await signup(client)
    uid = await user_id(client, EMAIL)
    await client.post("/v1/auth/password-reset/request", json={"email": EMAIL})
    code = notifier.sent[-1][1]
    w, c = await asyncio.gather(
        client.request("DELETE", f"/v1/admin/users/{uid}", json={"reason": "사유"}, headers=h),
        client.post("/v1/auth/password-reset/confirm",
                    json={"email": EMAIL, "code": code, "new_password": "resetpass12"}),
    )
    assert w.status_code == 200 and c.status_code in (204, 400)
    assert await scalar(client, "SELECT count(*) FROM password_reset_codes") == 0
