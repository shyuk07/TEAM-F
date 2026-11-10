"""탈퇴 회원 개인정보 파기(개인정보 B안, 사용자 결정 2026-11-10) + 실제 PostgreSQL.

- 이메일 원문은 비밀키 해시 대체값(withdrawn:<hex>)으로, 비밀번호 해시는 쓸 수 없는 값으로 바뀐다
- 이름·전화번호·사업자번호는 지운다. 행·역할·상태·사유·시각과 거래 기록 연결(user_id)은 남는다
- 같은 이메일로 재가입·관리자 생성은 계속 막힌다(REQ-4·REQ-35)
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from auth.domain.exceptions import EmailDuplicatedError
from auth.domain.user import WITHDRAWN_PASSWORD_HASH
from tests.admin.test_api_db import admin_headers
from tests.auth.test_api_db import auth_service
from tests.helpers import bearer, login, signup, token_for
from tests.reservations.test_withdrawal_db import withdraw

pytestmark = [pytest.mark.db, pytest.mark.anyio]


async def one(c, sql, **params):
    async with c.session_factory() as s:
        return (await s.execute(text(sql), params)).mappings().one()


async def uid_of(c, email):
    return (await one(c, "SELECT id FROM users WHERE email = :e", e=email))["id"]


async def user(c, uid):
    return await one(
        c,
        "SELECT email, password_hash, name, phone, business_number, role, status, deleted_at, deleted_reason "
        "FROM users WHERE id = :i",
        i=uid,
    )


def assert_erased(row):
    assert row["email"].startswith("withdrawn:") and "@" not in row["email"]
    assert len(row["email"]) == len("withdrawn:") + 64
    assert row["password_hash"] == WITHDRAWN_PASSWORD_HASH
    assert row["name"] is None and row["phone"] is None and row["business_number"] is None
    assert row["status"] == "WITHDRAWN" and row["deleted_at"] is not None and row["deleted_reason"]


async def test_self_withdrawal_erases_personal_data_and_blocks_resignup(client):
    t = await token_for(client, "me@test.com")
    uid = await uid_of(client, "me@test.com")
    async with client.session_factory() as s:  # 거래 기록 연결 확인용 포인트 기록
        await auth_service(s).earn_points(uid, 100)
    r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(t))
    assert r.status_code == 200, r.text

    row = await user(client, uid)
    assert_erased(row)
    assert row["role"] == "CUSTOMER"
    raw = await one(client, "SELECT count(*) AS n FROM users WHERE email LIKE '%me@test.com%'")
    assert raw["n"] == 0  # 원문 이메일은 어디에도 없다
    logs = await one(client, "SELECT count(*) AS n FROM point_log WHERE user_id = :i", i=uid)
    assert logs["n"] == 2  # 적립 + 탈퇴 소멸 기록은 회원 ID로 그대로 연결

    for variant in ("me@test.com", "  ME@Test.com "):  # 정규화한 이메일 기준으로 막힌다
        r = await signup(client, variant)
        assert r.status_code == 409 and r.json()["error_code"] == "EMAIL_DUPLICATED", r.text
    r = await login(client, "me@test.com")
    assert r.status_code == 401 and r.json()["error_code"] == "INVALID_CREDENTIALS"
    assert (await client.get("/v1/users/me", headers=bearer(t))).status_code == 401


async def test_admin_withdrawal_erases_owner_business_number_and_keeps_reason(client):
    await token_for(client, "owner@test.com", "OWNER")
    uid = await uid_of(client, "owner@test.com")
    async with client.session_factory() as s:
        await s.execute(text("UPDATE users SET business_number = '123-45-67890' WHERE id = :i"), {"i": uid})
        await s.commit()
    r = await withdraw(client, await admin_headers(client), str(uid), reason="약관 위반 반복")
    assert r.status_code == 200, r.text

    row = await user(client, uid)
    assert_erased(row)
    assert row["role"] == "OWNER" and row["deleted_reason"] == "약관 위반 반복"  # 운영 기록은 남긴다
    assert (await signup(client, "owner@test.com", "OWNER")).status_code == 409


async def test_different_emails_get_different_tombstones_and_other_emails_unaffected(client):
    for e in ("a@test.com", "b@test.com"):
        t = await token_for(client, e)
        r = await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(t))
        assert r.status_code == 200, r.text
    rows = await one(client, "SELECT count(DISTINCT email) AS n FROM users WHERE email LIKE 'withdrawn:%'")
    assert rows["n"] == 2
    assert (await signup(client, "c@test.com")).status_code == 201  # 다른 이메일은 그대로 가입된다


async def test_admin_list_shows_tombstone_not_original_email(client):
    t = await token_for(client, "gone@test.com")
    uid = await uid_of(client, "gone@test.com")
    await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(t))
    headers = await admin_headers(client)
    r = await client.get(f"/v1/admin/users/{uid}", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"].startswith("withdrawn:") and body["status"] == "WITHDRAWN"
    assert "gone@test.com" not in r.text and "홍길동" not in r.text


async def test_ensure_admin_rejects_withdrawn_email(client):
    t = await token_for(client, "boss@test.com")
    await client.post("/v1/users/me/withdraw", json={"password": "password123"}, headers=bearer(t))
    async with client.session_factory() as s:
        with pytest.raises(EmailDuplicatedError):
            await auth_service(s).ensure_admin("boss@test.com", "password123")
    n = await one(client, "SELECT count(*) AS n FROM users WHERE role = 'ADMIN' AND email = 'boss@test.com'")
    assert n["n"] == 0


async def test_legacy_withdrawn_row_with_plain_email_still_blocks_resignup(client):
    """이 변경 전에 탈퇴해 원문 이메일이 남은 행(소급 파기 안 함)도 계속 재가입을 막는다."""
    await signup(client, "old@test.com")
    async with client.session_factory() as s:
        await s.execute(
            text("UPDATE users SET status = 'WITHDRAWN', deleted_at = :n, deleted_reason = '이전 탈퇴' WHERE email = 'old@test.com'"),
            {"n": datetime.now(timezone.utc)},
        )
        await s.commit()
    assert (await signup(client, "old@test.com")).status_code == 409
