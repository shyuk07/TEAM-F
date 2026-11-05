"""auth 요구조건 정합(§15) 도메인 단위 테스트 (DB 없음)."""

import uuid
from datetime import timedelta

import pytest

from auth.domain.exceptions import (
    AdminAccountProtectedError,
    CurrentPasswordMismatchError,
    InvalidResetCodeError,
    TokenRevokedError,
    UserAlreadyWithdrawnError,
    UserWithdrawnError,
)
from auth.domain.password_reset_code import PasswordResetCode
from auth.domain.point_log import PointLog, PointType
from auth.domain.service import PasswordHasher
from auth.domain.user import POINT_MAX_BALANCE, Role, User, UserStatus
from tests.auth.fakes import T0


class Hasher(PasswordHasher):
    def hash(self, raw):
        return "h:" + raw

    def verify(self, raw, hashed):
        return hashed == "h:" + raw

    def dummy_verify(self, raw):
        pass


H = Hasher()


def user(role=Role.CUSTOMER, **kw):
    kw.setdefault("name", "n")
    kw.setdefault("phone", "010")
    u = User(email="a@b.com", password_hash="h:password1", role=role, **kw)
    u.id = uuid.uuid4()
    return u


# ── register 필수값 (REQ-2·6·7) ──
def test_register_requires_name_and_phone():
    ok = User.register("a@b.com", "h", "CUSTOMER", name="n", phone="010")
    assert ok.name == "n" and ok.phone == "010"
    for name, phone in [(None, "1"), ("1", None), ("  ", "1"), ("1", " "), ("", "1")]:
        with pytest.raises(ValueError):
            User.register("a@b.com", "h", "CUSTOMER", name=name, phone=phone)


def test_register_length_boundary():
    User.register("a@b.com", "h", "CUSTOMER", name="가" * 100, phone="1" * 100)
    with pytest.raises(ValueError):
        User.register("a@b.com", "h", "CUSTOMER", name="가" * 101, phone="1")
    with pytest.raises(ValueError):
        User.register("a@b.com", "h", "CUSTOMER", name="n", phone="1" * 101)


def test_constructor_still_accepts_legacy_empty_profile():
    u = User(email="a@b.com", password_hash="h", role=Role.CUSTOMER)
    assert u.name is None and u.phone is None


def test_register_admin_unchanged():
    assert User.register_admin("a@b.com", "h").name is None


# ── update_profile (REQ-22·23) ──
def test_update_profile_partial_and_both():
    u = user()
    u.update_profile("새이름", None)
    assert (u.name, u.phone) == ("새이름", "010")
    u.update_profile(None, "011")
    assert (u.name, u.phone) == ("새이름", "011")
    u.update_profile("x", "y")
    assert (u.name, u.phone) == ("x", "y")


def test_update_profile_rejects_none_blank_long():
    u = user()
    for name, phone in [(None, None), ("  ", None), (None, ""), ("가" * 101, None), (None, "1" * 101)]:
        with pytest.raises(ValueError):
            u.update_profile(name, phone)
    assert (u.name, u.phone) == ("n", "010")


def test_update_profile_legacy_member_must_fill_both():
    u = user(phone=None)
    with pytest.raises(ValueError):
        u.update_profile("새이름", None)  # 적용 뒤 전화번호가 비어 있음
    u.update_profile("새이름", "011")
    assert u.phone == "011"


def test_update_profile_admin_may_stay_empty():
    admin = user(Role.ADMIN, name=None, phone=None)
    admin.update_profile("관리자", None)
    assert admin.name == "관리자" and admin.phone is None


def test_update_profile_withdrawn():
    u = user()
    u.withdraw("사유", T0)
    with pytest.raises(UserWithdrawnError):
        u.update_profile("x", None)


# ── 비밀번호 변경·토큰 세대 (REQ-24, 32) ──
def test_change_password_success_bumps_version_and_keeps_jti():
    u = user()
    u.change_password("password1", "newpassword1", H, keep_jti="j1")
    assert u.password_hash == "h:newpassword1"
    assert (u.token_version, u.token_keep_jti) == (1, "j1")


def test_change_password_same_as_current_allowed():
    u = user()
    u.change_password("password1", "password1", H, keep_jti="j")
    assert u.token_version == 1


def test_change_password_mismatch_and_weak_and_withdrawn_leave_state():
    u = user()
    with pytest.raises(CurrentPasswordMismatchError):
        u.change_password("wrong", "newpassword1", H, keep_jti="j")
    with pytest.raises(ValueError):
        u.change_password("password1", "short", H, keep_jti="j")
    assert (u.password_hash, u.token_version, u.token_keep_jti) == ("h:password1", 0, None)
    u.withdraw("사유", T0)
    with pytest.raises(UserWithdrawnError):
        u.change_password("password1", "newpassword1", H, keep_jti="j")


def test_ensure_token_current_table():
    u = user()
    u.ensure_token_current(0, "a")  # 현재 세대
    u.change_password("password1", "newpassword1", H, keep_jti="keep1")
    with pytest.raises(TokenRevokedError) as err:
        u.ensure_token_current(0, "other")  # 이전 세대
    assert str(err.value) == "비밀번호가 변경되어 무효가 된 토큰입니다."
    u.ensure_token_current(0, "keep1")  # keep jti
    u.ensure_token_current(1, "new-login")  # 새 세대 토큰
    u.change_password("newpassword1", "another1234", H, keep_jti="keep2")  # 두 번째 변경
    with pytest.raises(TokenRevokedError):
        u.ensure_token_current(0, "keep1")  # 이전 keep은 무효
    u.ensure_token_current(1, "keep2")


def test_reset_password_invalidates_everything():
    u = user()
    u.change_password("password1", "newpassword1", H, keep_jti="keep1")
    u.reset_password("resetpass1", H)
    assert u.password_hash == "h:resetpass1" and u.token_keep_jti is None and u.token_version == 2
    with pytest.raises(TokenRevokedError):
        u.ensure_token_current(0, "keep1")
    with pytest.raises(ValueError):
        u.reset_password("short", H)
    u.withdraw("사유", T0)
    with pytest.raises(UserWithdrawnError):
        u.reset_password("resetpass2", H)
    assert u.can_reset_password is False


def test_negative_token_version_rejected():
    with pytest.raises(ValueError):
        user(token_version=-1)


# ── 포인트 상한·탈퇴 소멸 (REQ-34-1, 37) ──
def test_point_cap_for_earn_restore_grant():
    for op in (
        lambda u: u.earn_points(1),
        lambda u: u.restore_points(1),
        lambda u: u.grant_points(1, "사유"),
    ):
        u = user(users_point=POINT_MAX_BALANCE)
        with pytest.raises(ValueError, match="포인트 잔액이 한도를 넘습니다."):
            op(u)
        assert u.users_point == POINT_MAX_BALANCE  # 실패 시 불변
    u = user(users_point=POINT_MAX_BALANCE - 5)
    u.earn_points(5)
    assert u.users_point == POINT_MAX_BALANCE


def test_earn_restore_rejected_for_withdrawn():
    u = user()
    u.withdraw("사유", T0)
    with pytest.raises(UserWithdrawnError):
        u.earn_points(10)
    with pytest.raises(UserWithdrawnError):
        u.restore_points(10)


def test_withdraw_returns_expired_amount():
    u = user(users_point=1234)
    assert u.withdraw("사유", T0) == 1234
    assert u.users_point == 0 and u.status is UserStatus.WITHDRAWN
    assert user().withdraw("사유", T0) == 0


def test_withdraw_rejection_keeps_balance():
    admin = user(Role.ADMIN, users_point=500)
    with pytest.raises(AdminAccountProtectedError):
        admin.withdraw("사유", T0)
    assert admin.users_point == 500
    u = user(users_point=500)
    u.withdraw("사유", T0)
    u.users_point = 500  # 방어 확인용 직접 대입
    with pytest.raises(UserAlreadyWithdrawnError):
        u.withdraw("사유", T0)
    assert u.users_point == 500
    with pytest.raises(ValueError):
        user(users_point=500).withdraw("  ", T0)


# ── PointLog 불변식 (REQ-53·55) ──
def test_point_log_expire_invariants():
    uid = uuid.uuid4()
    log = PointLog.record(uid, PointType.EXPIRE, -300, 0)
    assert log.amount == -300 and log.balance_after == 0
    with pytest.raises(ValueError):
        PointLog.record(uid, PointType.EXPIRE, 300, 0)
    with pytest.raises(ValueError):
        PointLog.record(uid, PointType.EXPIRE, -300, 5)


def test_point_log_grant_and_other_types_reason_creator():
    uid, admin = uuid.uuid4(), uuid.uuid4()
    PointLog.record(uid, PointType.GRANT, 100, 100, reason="이벤트", created_by=admin)
    for kw in ({}, {"reason": "r"}, {"created_by": admin}):
        with pytest.raises(ValueError):
            PointLog.record(uid, PointType.GRANT, 100, 100, **kw)
    with pytest.raises(ValueError):
        PointLog.record(uid, PointType.EARN, 10, 10, reason="r")
    with pytest.raises(ValueError):
        PointLog.record(uid, PointType.USE, -10, 0, created_by=admin)
    PointLog.record(uid, PointType.USE, -10, 0)


# ── PasswordResetCode (REQ-28·29) ──
def issued(raw="123456"):
    return PasswordResetCode.issue(uuid.uuid4(), raw, H, T0)


def test_reset_code_issue_validates_format():
    code = issued()
    assert code.code_hash == "h:123456" and code.expires_at == T0 + timedelta(minutes=15)
    for bad in ("12345", "1234567", "12345a", "١٢٣٤٥٦", ""):
        with pytest.raises(ValueError):
            issued(bad)


def test_reset_code_expiry_boundary():
    code = issued()
    assert code.is_usable(T0 + timedelta(minutes=15) - timedelta(seconds=1))
    assert not code.is_usable(T0 + timedelta(minutes=15))  # 정각은 만료
    with pytest.raises(InvalidResetCodeError):
        code.check("123456", H, T0 + timedelta(minutes=15))


def test_reset_code_attempt_limit():
    code = issued()
    for _ in range(4):
        assert code.check("000000", H, T0) is False
    assert code.failed_attempts == 4
    assert code.check("123456", H, T0) is True  # 4회 실패 뒤 일치 OK
    assert code.failed_attempts == 4  # 성공 시 횟수 불변
    code2 = issued()
    for _ in range(5):
        assert code2.check("000000", H, T0) is False
    with pytest.raises(InvalidResetCodeError):
        code2.check("123456", H, T0)  # 5회 뒤에는 맞는 코드도 거부
    assert code2.failed_attempts == 5
