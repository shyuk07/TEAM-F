"""계정 상태·포인트 확장 DB·API 테스트 (D4, D5, D8, D9, D35, D38, D39, D40)."""

import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from auth.domain.point_log import PointType
from auth.domain.user import Role, User, UserStatus
from auth.infrastructure.clock import SystemClock
from auth.infrastructure.repositories import (
    SqlAlchemyPointLogRepository,
    SqlAlchemyUserRepository,
)
from auth.presentation.dependencies import (
    ApprovedOwnerUser,
    SuspendedAllowedOwnerUser,
    provide_auth_service,
)
from error_handlers import register_exception_handlers
from main import app
from tests.auth.test_api_db import auth_service
from tests.helpers import bearer, login, signup, token_for

pytestmark = [pytest.mark.db, pytest.mark.anyio]


async def user_id_of(client, email):
    async with client.session_factory() as s:
        return (await s.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email})).scalar_one()


async def run_service(client, fn):
    """요청 밖에서 서비스 메서드를 직접 실행하고 commit한다."""
    async with client.session_factory() as s:
        svc = auth_service(s)
        result = await fn(svc)
        await s.commit()
        return result


async def suspend(client, email, until=None):
    uid = await user_id_of(client, email)
    now = datetime.now(timezone.utc)
    await run_service(client, lambda svc: svc.suspend_user(uid, "테스트", until, now=now))
    return uid


async def force_status(client, email, status):
    async with client.session_factory() as s:
        await s.execute(text("UPDATE users SET status = :st WHERE email = :e"), {"st": status, "e": email})
        await s.commit()


# ── 가입·응답 (D4, D38) ──
async def test_signup_status_by_role(client):
    owner = (await signup(client, "o@test.com", "OWNER")).json()
    customer = (await signup(client, "c@test.com", "CUSTOMER")).json()
    assert owner["status"] == "PENDING" and customer["status"] == "APPROVED"
    assert "suspended_reason" not in owner and "password_hash" not in owner


async def test_token_for_owner_is_approved_and_me_shows_status(client):
    t = await token_for(client, "o@test.com", "OWNER")
    me = await client.get("/v1/users/me", headers=bearer(t))
    assert me.status_code == 200 and me.json()["status"] == "APPROVED"
    t2 = await token_for(client, "c@test.com", "CUSTOMER")
    assert (await client.get("/v1/users/me", headers=bearer(t2))).json()["status"] == "APPROVED"


# ── 로그인 응답 status (D40) ──
async def test_login_status_pending_owner_and_customer(client):
    await signup(client, "o@test.com", "OWNER")
    await signup(client, "c@test.com", "CUSTOMER")
    o = await login(client, "o@test.com")
    assert o.status_code == 200 and o.json()["status"] == "PENDING"  # D5: 로그인 허용
    assert (await login(client, "c@test.com")).json()["status"] == "APPROVED"


async def test_login_status_rejected_owner(client):
    await signup(client, "o@test.com", "OWNER")
    uid = await user_id_of(client, "o@test.com")
    await run_service(client, lambda s: s.reject_owner(uid, "서류 미비", now=datetime.now(timezone.utc)))
    r = await login(client, "o@test.com")
    assert r.status_code == 200 and r.json()["status"] == "REJECTED"


async def test_suspended_owner_can_login_with_status_and_no_leak(client):
    await token_for(client, "o@test.com", "OWNER")
    await suspend(client, "o@test.com")
    r = await login(client, "o@test.com")
    assert r.status_code == 200 and r.json()["status"] == "SUSPENDED"
    assert set(r.json()) == {"access_token", "token_type", "status"}  # 사유·기간 비노출


async def test_suspended_customer_login_403_wrong_password_401(client):
    await signup(client, "c@test.com")
    await suspend(client, "c@test.com")
    r = await login(client, "c@test.com")
    assert r.status_code == 403 and r.json() == {
        "success": False, "error_code": "FORBIDDEN", "message": "정지된 계정입니다."
    }
    bad = await login(client, "c@test.com", password="wrongpass1")
    assert bad.status_code == 401 and bad.json()["error_code"] == "INVALID_CREDENTIALS"


async def test_expired_suspension_login_ok(client):
    await signup(client, "c@test.com")
    uid = await user_id_of(client, "c@test.com")
    past = datetime.now(timezone.utc) - timedelta(days=2)
    async with client.session_factory() as s:
        await s.execute(
            text("UPDATE users SET status='SUSPENDED', suspended_reason='r', suspended_at=:a, "
                 "suspended_until=:u WHERE id=:i"),
            {"a": past - timedelta(days=1), "u": past, "i": uid},
        )
        await s.commit()
    r = await login(client, "c@test.com")
    assert r.status_code == 200 and r.json()["status"] == "APPROVED"


@pytest.mark.parametrize("role", ["CUSTOMER", "OWNER"])
async def test_withdrawn_login_401_and_token_401_and_resignup_409(client, role):
    t = await token_for(client, "w@test.com", role)
    uid = await user_id_of(client, "w@test.com")
    await run_service(client, lambda s: s.withdraw_user(uid, "r", now=datetime.now(timezone.utc)))
    r = await login(client, "w@test.com")
    assert r.status_code == 401 and r.json()["error_code"] == "INVALID_CREDENTIALS"
    assert r.headers["www-authenticate"] == "Bearer"
    me = await client.get("/v1/users/me", headers=bearer(t))
    assert me.status_code == 401 and me.json()["message"] == "유효하지 않은 토큰입니다."
    assert (await signup(client, "w@test.com", role)).status_code == 409


# ── 보호 API (D8) / 허용 의존성 (D35) ──
async def test_suspended_token_blocked_on_protected_api(client):
    t = await token_for(client, "c@test.com")
    await suspend(client, "c@test.com")
    r = await client.get("/v1/users/me", headers=bearer(t))
    assert r.status_code == 403 and r.json()["message"] == "정지된 계정입니다."


def probe_client(client):
    """전용 의존성만 노출하는 별도 앱 (공용 app의 라우트·OpenAPI를 건드리지 않는다)."""
    probe = FastAPI()
    register_exception_handlers(probe)
    probe.dependency_overrides.update(app.dependency_overrides)

    @probe.get("/allowed")
    async def allowed(user: SuspendedAllowedOwnerUser):
        return {"id": str(user.id)}

    @probe.get("/approved")
    async def approved(user: ApprovedOwnerUser):
        return {"id": str(user.id)}

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=probe), base_url="http://p")


async def test_suspended_owner_token_blocked_except_allow_dependency(client):
    t = await token_for(client, "o@test.com", "OWNER")
    await suspend(client, "o@test.com")
    assert (await client.get("/v1/users/me", headers=bearer(t))).status_code == 200  # B-2: 내 정보 조회만 허용
    assert (await client.patch("/v1/users/me", headers=bearer(t), json={"name": "x"})).status_code == 403
    async with probe_client(client) as p:
        assert (await p.get("/allowed", headers=bearer(t))).status_code == 200
        assert (await p.get("/approved", headers=bearer(t))).status_code == 403  # 정지 차단
        cust = await token_for(client, "c@test.com")
        assert (await p.get("/allowed", headers=bearer(cust))).status_code == 403  # 역할
        uid = await user_id_of(client, "o@test.com")
        await run_service(client, lambda s: s.withdraw_user(uid, "r", now=datetime.now(timezone.utc)))
        assert (await p.get("/allowed", headers=bearer(t))).status_code == 401


async def test_approved_owner_dependency_pending_rejected_approved(client):
    await signup(client, "o@test.com", "OWNER")
    t = (await login(client, "o@test.com")).json()["access_token"]
    async with probe_client(client) as p:
        r = await p.get("/approved", headers=bearer(t))
        assert r.status_code == 403 and r.json()["message"] == "승인 대기 중인 상점주 계정입니다."
        await force_status(client, "o@test.com", "APPROVED")
        assert (await p.get("/approved", headers=bearer(t))).status_code == 200
        cust = await token_for(client, "c@test.com")
        assert (await p.get("/approved", headers=bearer(cust))).status_code == 403
        assert (await p.get("/approved")).status_code == 401


# ── 레포지토리 왕복·제약 ──
async def test_user_columns_roundtrip_with_timezone(client):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    async with client.session_factory() as s:
        repo = SqlAlchemyUserRepository(s)
        u = User.register("r@test.com", "h", "OWNER", name="n", phone="010-0000-0000")
        await repo.save(u)
        u.reject_owner("서류 미비", now)
        await repo.save(u)
        await s.commit()
    async with client.session_factory() as s:
        got = await SqlAlchemyUserRepository(s).find_by_id(u.id)
        assert got.status is UserStatus.REJECTED and got.rejected_reason == "서류 미비"
        assert got.rejected_at == now and got.rejected_at.tzinfo is not None
        assert got.approved_at is None and got.suspended_until is None and got.deleted_at is None
        got.status = UserStatus.WITHDRAWN
        got.deleted_at, got.deleted_reason = now, "r"
        await SqlAlchemyUserRepository(s).save(got)
        await s.commit()
    async with client.session_factory() as s:
        got = await SqlAlchemyUserRepository(s).find_by_id(u.id)
        assert got.status is UserStatus.WITHDRAWN and got.deleted_reason == "r"


async def test_suspension_columns_roundtrip(client):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    until = now + timedelta(days=3)
    async with client.session_factory() as s:
        repo = SqlAlchemyUserRepository(s)
        u = User.register("s@test.com", "h", "CUSTOMER", name="n", phone="010-0000-0000")
        await repo.save(u)
        u.suspend("욕설", until, now)
        await repo.save(u)
        await s.commit()
        got = await repo.find_by_id(u.id, for_update=True)
        assert (got.status, got.suspended_reason, got.suspended_at, got.suspended_until) == (
            UserStatus.SUSPENDED, "욕설", now, until)


async def test_status_check_constraint_and_default(client):
    async with client.session_factory() as s:
        await s.execute(text("INSERT INTO users (email, password_hash, role) VALUES ('d@t.com','h','CUSTOMER')"))
        assert (await s.execute(text("SELECT status FROM users WHERE email='d@t.com'"))).scalar_one() == "APPROVED"
        with pytest.raises(IntegrityError):
            await s.execute(
                text("INSERT INTO users (email, password_hash, role, status) VALUES ('e@t.com','h','CUSTOMER','BOGUS')")
            )


async def test_point_log_grant_roundtrip_and_check(client):
    await signup(client, "u@test.com")
    await signup(client, "adm@test.com")
    uid = await user_id_of(client, "u@test.com")
    admin_id = await user_id_of(client, "adm@test.com")
    log = await run_service(
        client, lambda s: s.grant_points(uid, 50, "이벤트", admin_id, now=datetime.now(timezone.utc))
    )
    async with client.session_factory() as s:
        repo = SqlAlchemyPointLogRepository(s)
        (got,) = await repo.find_by_user(uid)
        assert got.id == log.id and got.point_type is PointType.GRANT
        assert (got.reason, got.balance_after, got.created_by) == ("이벤트", 50, admin_id)
        assert (await s.execute(text("SELECT users_point FROM users WHERE id=:i"), {"i": uid})).scalar_one() == 50
    async with client.session_factory() as s:
        with pytest.raises(IntegrityError):
            await s.execute(
                text("INSERT INTO point_log (user_id, amount, point_type) VALUES (:u, 1, 'BOGUS')"), {"u": uid}
            )


async def test_grant_fk_created_by_must_exist(client):
    await signup(client, "u@test.com")
    uid = await user_id_of(client, "u@test.com")
    with pytest.raises(IntegrityError):
        await run_service(
            client, lambda s: s.grant_points(uid, 5, "r", uuid.uuid4(), now=datetime.now(timezone.utc))
        )


async def test_legacy_and_system_logs_have_balance_after(client):
    await signup(client, "u@test.com")
    uid = await user_id_of(client, "u@test.com")
    await run_service(client, lambda s: s.earn_points(uid, 300))
    await run_service(client, lambda s: s.use_points(uid, 100))
    async with client.session_factory() as s:
        logs = await SqlAlchemyPointLogRepository(s).find_by_user(uid)
        assert sorted(x.balance_after for x in logs) == [200, 300]
        assert all(x.reason is None and x.created_by is None for x in logs)
        # 기존 행(balance_after NULL)도 읽힌다
        await s.execute(text("UPDATE point_log SET balance_after = NULL"))
        await s.commit()
        assert all(x.balance_after is None for x in await SqlAlchemyPointLogRepository(s).find_by_user(uid))


async def test_grant_rolls_back_balance_and_log_together(client):
    await signup(client, "u@test.com")
    uid = await user_id_of(client, "u@test.com")
    with pytest.raises(IntegrityError):  # created_by FK 위반 -> 잔액 변경도 롤백
        await run_service(client, lambda s: s.grant_points(uid, 5, "r", uuid.uuid4(), now=datetime.now(timezone.utc)))
    async with client.session_factory() as s:
        assert (await s.execute(text("SELECT users_point FROM users WHERE id=:i"), {"i": uid})).scalar_one() == 0
        assert (await s.execute(text("SELECT count(*) FROM point_log"))).scalar_one() == 0


async def test_system_clock_is_aware():
    assert SystemClock().now().tzinfo is not None


async def test_list_points_db_ordering_and_total(client):
    await signup(client, "u@test.com")
    await signup(client, "adm@test.com")
    uid = await user_id_of(client, "u@test.com")
    admin_id = await user_id_of(client, "adm@test.com")
    for i in range(3):
        await run_service(client, lambda s, i=i: s.grant_points(uid, 10, f"r{i}", admin_id, now=datetime.now(timezone.utc)))
    page = await run_service(client, lambda s: s.list_points(uid, 1, 2))
    assert page.total == 3 and page.balance == 30 and [x.reason for x in page.history] == ["r2", "r1"]


async def test_dependency_placeholder_wired():
    assert provide_auth_service in app.dependency_overrides
    assert Role.OWNER in Role


# ── 잠금 후 최신 상태 재조회 (populate_existing) ──
async def test_for_update_refreshes_stale_identity_map(client):
    from auth.domain.exceptions import UserWithdrawnError
    from auth.infrastructure.models import UserModel

    await signup(client, "stale@test.com", "CUSTOMER")
    uid = await user_id_of(client, "stale@test.com")
    now = datetime.now(timezone.utc)
    async with client.session_factory() as a:
        svc_a = auth_service(a)
        await svc_a.get_account(uid)  # 잠금 없이 적재 -> identity map에 APPROVED
        held = await a.get(UserModel, uid)  # 모델을 강하게 참조해 identity map에 유지
        assert held.status == "APPROVED"
        await run_service(client, lambda svc: svc.withdraw_user(uid, "탈퇴", now=now))  # 다른 세션
        with pytest.raises(UserWithdrawnError):
            await svc_a.suspend_user(uid, "사유", None, now=now)


# ── 내 정보 조회와 정지 (요구조건 B-2) ──
async def test_me_suspended_owner_200_with_suspended_status(client):
    t = await token_for(client, "o@test.com", "OWNER")
    await suspend(client, "o@test.com")
    r = await client.get("/v1/users/me", headers=bearer(t))
    assert r.status_code == 200 and r.json()["status"] == "SUSPENDED"


async def test_me_suspended_customer_403(client):
    t = await token_for(client, "c@test.com")
    await suspend(client, "c@test.com")
    r = await client.get("/v1/users/me", headers=bearer(t))
    assert r.status_code == 403 and r.json()["message"] == "정지된 계정입니다."


async def test_me_withdrawn_owner_401_and_normal_users_200(client):
    t = await token_for(client, "o@test.com", "OWNER")
    c = await token_for(client, "c@test.com")
    assert (await client.get("/v1/users/me", headers=bearer(c))).status_code == 200
    assert (await client.get("/v1/users/me", headers=bearer(t))).status_code == 200
    assert (await client.get("/v1/users/me")).status_code == 401
    uid = await user_id_of(client, "o@test.com")
    await suspend(client, "o@test.com")
    await run_service(client, lambda s: s.withdraw_user(uid, "r", now=datetime.now(timezone.utc)))
    assert (await client.get("/v1/users/me", headers=bearer(t))).status_code == 401
