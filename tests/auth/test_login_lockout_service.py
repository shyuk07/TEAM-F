"""REQ-13~13-3 로그인 잠금·REQ-35-1 서비스 테스트 (fake 주입, DB 없음)."""

import inspect
from datetime import timedelta

import pytest

from auth.application.service import AuthApplicationService
from auth.domain.exceptions import AccountLockedError, AccountSuspendedError, InvalidCredentialsError
from tests.auth.test_service import build

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def setup(email="a@b.com"):
    svc, db, parts = build()
    u = await svc.signup(email, "password1", "CUSTOMER", name="n", phone="010")
    db.commits = 0
    return svc, db, parts, u


async def fail(svc, n=1, email="a@b.com"):
    for _ in range(n):
        with pytest.raises(InvalidCredentialsError):
            await svc.login(email, "wrongpass1")


async def test_failures_commit_each_and_count():
    svc, db, _, u = await setup()
    await fail(svc, 4)
    assert db.commits == 4 and u.failed_login_count == 4 and u.login_locked_until is None


async def test_fifth_failure_is_401_but_committed_with_lock_before_exception():
    svc, db, _, u = await setup()
    await fail(svc, 5)
    assert db.commits == 5 and u.login_locked_until is not None and u.failed_login_count == 0


async def test_locked_right_password_is_429_without_commit():
    svc, db, parts, u = await setup()
    await fail(svc, 5)
    db.commits = 0
    until = u.login_locked_until
    with pytest.raises(AccountLockedError) as err:
        await svc.login("a@b.com", "password1")
    assert err.value.retry_after_seconds == 600 and db.commits == 0 and u.login_locked_until == until


async def test_locked_wrong_password_is_401_no_commit_no_change():
    svc, db, parts, u = await setup()
    await fail(svc, 5)
    db.commits = 0
    until = u.login_locked_until
    await fail(svc, 2)
    assert db.commits == 0 and u.failed_login_count == 0 and u.login_locked_until == until


async def test_after_lock_end_right_password_succeeds_and_clears():
    svc, db, parts, u = await setup()
    await fail(svc, 5)
    parts["clock"].advance(minutes=10)
    db.commits = 0
    assert (await svc.login("a@b.com", "password1")).token
    assert u.login_locked_until is None and db.commits == 1


async def test_success_resets_count_and_failure_after_lock_end_starts_from_one():
    svc, db, parts, u = await setup()
    await fail(svc, 3)
    await svc.login("a@b.com", "password1")
    assert u.failed_login_count == 0
    await fail(svc, 5)
    parts["clock"].advance(minutes=10)
    await fail(svc, 1)
    assert u.failed_login_count == 1 and u.login_locked_until is None


async def test_success_without_failures_does_not_commit():
    svc, db, _, _ = await setup()
    await svc.login("a@b.com", "password1")
    assert db.commits == 0


async def test_unknown_email_never_locks_or_saves():
    svc, db, parts, _ = await setup()
    for _ in range(7):
        with pytest.raises(InvalidCredentialsError):
            await svc.login("nobody@b.com", "wrongpass1")
    assert db.commits == 0 and parts["hasher"].dummy_calls == 7


async def test_withdrawn_user_always_401_no_save():
    svc, db, parts, u = await setup()
    await svc.withdraw_user(u.id, "사유", now=parts["clock"].now())
    db.commits = 0
    for pw in ("wrongpass1", "password1"):
        with pytest.raises(InvalidCredentialsError):
            await svc.login("a@b.com", pw)
    assert db.commits == 0 and u.failed_login_count == 0


async def test_suspended_right_password_403_count_unchanged():
    svc, db, parts, u = await setup()
    await fail(svc, 2)
    u.suspend("사유", None, parts["clock"].now())
    db.commits = 0
    with pytest.raises(AccountSuspendedError):
        await svc.login("a@b.com", "password1")
    assert u.failed_login_count == 2 and db.commits == 0


async def test_login_takes_row_lock_after_snapshot():
    svc, _, parts, _ = await setup()
    parts["users"].locked_reads = 0
    await svc.login("a@b.com", "password1")
    assert parts["users"].locked_reads == 1


async def test_password_changed_between_verify_and_lock_gives_401_without_count():
    svc, db, parts, u = await setup()
    original = parts["users"].find_by_id

    async def changed(user_id, for_update=False):
        found = await original(user_id, for_update)
        found.password_hash = "h:other"
        return found

    parts["users"].find_by_id = changed
    snapshot_users = parts["users"]
    # 스냅숏과 잠근 행이 같은 객체인 fake라 비교용으로 복제본을 돌려준다
    import copy

    orig_email = snapshot_users.find_by_email

    async def snap(email):
        return copy.copy(await orig_email(email))

    snapshot_users.find_by_email = snap
    with pytest.raises(InvalidCredentialsError):
        await svc.login("a@b.com", "wrongpass1")
    assert u.failed_login_count == 0 and db.commits == 0


def test_public_signatures_for_other_modules_unchanged():
    for name in ("use_points", "earn_points", "restore_points", "revoke_points"):
        params = list(inspect.signature(getattr(AuthApplicationService, name)).parameters.values())
        assert [p.name for p in params] == ["self", "user_id", "amount", "commit"]
        assert params[3].kind is inspect.Parameter.KEYWORD_ONLY and params[3].default is True
    assert list(inspect.signature(AuthApplicationService.withdraw_user).parameters) == [
        "self", "user_id", "reason", "now", "commit",
    ]
    assert list(inspect.signature(AuthApplicationService.login).parameters) == ["self", "email", "password"]
