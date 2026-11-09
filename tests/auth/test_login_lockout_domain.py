"""REQ-13·13-1·13-2·13-3 로그인 잠금 도메인 단위 테스트 (DB 없음)."""

from datetime import datetime, timedelta, timezone

import pytest

from auth.domain.exceptions import AccountLockedError, AccountSuspendedError, InvalidCredentialsError
from auth.domain.service import PasswordHasher
from auth.domain.user import Role, User, UserStatus
from tests.auth.fakes import T0


class Hasher(PasswordHasher):
    def hash(self, raw):
        return "h:" + raw

    def verify(self, raw, hashed):
        return hashed == "h:" + raw

    def dummy_verify(self, raw):
        pass


def make(**kw):
    return User(email="a@b.com", password_hash="h:password1", role=Role.CUSTOMER, **kw)


def locked_user():
    u = make()
    for _ in range(5):
        u.record_login_failure(T0)
    return u


def test_failures_1_to_4_increment():
    u = make()
    for i in range(1, 5):
        assert u.record_login_failure(T0) is True
        assert u.failed_login_count == i and u.login_locked_until is None


def test_fifth_failure_locks_for_10_minutes_and_resets_count():
    u = make()
    for _ in range(5):
        assert u.record_login_failure(T0) is True
    assert u.failed_login_count == 0 and u.login_locked_until == T0 + timedelta(minutes=10)
    assert (User.LOGIN_MAX_FAILURES, User.LOGIN_LOCK_DURATION) == (5, timedelta(minutes=10))


def test_attempts_during_lock_are_not_counted_or_extended():  # REQ-13-3
    u = locked_user()
    until = u.login_locked_until
    assert u.record_login_failure(T0 + timedelta(minutes=5)) is False
    assert u.failed_login_count == 0 and u.login_locked_until == until


def test_lock_boundary():
    u = locked_user()
    assert u.is_login_locked(u.login_locked_until - timedelta(seconds=1)) is True
    assert u.is_login_locked(u.login_locked_until) is False


def test_failure_after_lock_end_counts_from_one():  # REQ-13-3
    u = locked_user()
    assert u.record_login_failure(T0 + timedelta(minutes=10)) is True
    assert u.failed_login_count == 1 and u.login_locked_until is None


def test_clear_login_failures_return_value():
    u = make()
    assert u.clear_login_failures() is False
    u.record_login_failure(T0)
    assert u.clear_login_failures() is True and u.failed_login_count == 0
    u = locked_user()
    assert u.clear_login_failures() is True and u.login_locked_until is None


def test_withdrawn_user_failure_is_noop():
    u = make()
    u.withdraw("사유", T0)
    assert u.record_login_failure(T0) is False and u.failed_login_count == 0


def test_remaining_seconds_rounds_up():
    u = locked_user()
    assert u.login_lock_remaining_seconds(T0) == 600
    assert u.login_lock_remaining_seconds(T0 + timedelta(milliseconds=500)) == 600
    assert u.login_lock_remaining_seconds(T0 + timedelta(seconds=599, milliseconds=1)) == 1
    assert u.login_lock_remaining_seconds(T0 + timedelta(minutes=10)) == 0


def test_ensure_can_login_order_withdrawn_then_locked_then_suspended():
    u = locked_user()
    u.suspend("사유", None, T0)
    with pytest.raises(AccountLockedError):  # 잠금 + 정지 -> 429
        u.ensure_can_login(T0)
    after = T0 + timedelta(minutes=10)
    with pytest.raises(AccountSuspendedError):  # 정지만 -> 403
        u.ensure_can_login(after)
    u2 = locked_user()
    u2.withdraw("사유", T0)
    with pytest.raises(InvalidCredentialsError):  # 탈퇴 + 잠금 -> 401
        u2.ensure_can_login(T0)
    assert u2.status is UserStatus.WITHDRAWN


def test_suspended_owner_may_login_even_unlocked():
    u = User(email="o@b.com", password_hash="h", role=Role.OWNER)
    u.suspend("사유", None, T0)
    u.ensure_can_login(T0)


def test_reset_password_clears_failures_and_lock():  # REQ-13-2
    u = locked_user()
    u.reset_password("newpassword1", Hasher())
    assert u.failed_login_count == 0 and u.login_locked_until is None


def test_constructor_validation():
    with pytest.raises(ValueError, match="로그인 실패 횟수"):
        make(failed_login_count=-1)
    with pytest.raises(ValueError):
        make(login_locked_until=datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        make().is_login_locked(datetime(2026, 1, 1))
    assert make(login_locked_until=datetime(2026, 1, 1, tzinfo=timezone.utc)).failed_login_count == 0


def test_account_locked_error_message_and_seconds():
    e = AccountLockedError(601)
    assert e.retry_after_seconds == 601 and "11분" in str(e) and e.error_code == "ACCOUNT_LOCKED"
    assert "1분" in str(AccountLockedError(1)) and AccountLockedError(0).retry_after_seconds == 1
    assert not isinstance(e, (ValueError, PermissionError, LookupError))
