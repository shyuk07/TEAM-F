"""User 계정 상태 도메인 규칙 (admin.md 3.1, D4~D9, D35, D39)."""

import uuid
from datetime import timedelta

import pytest

from auth.domain.exceptions import (
    AccountSuspendedError,
    AdminAccountProtectedError,
    AuthenticationError,
    InvalidCredentialsError,
    InvalidSuspensionEndError,
    OwnerNotApprovedError,
    OwnerNotFoundError,
    OwnerNotPendingError,
    UserAlreadySuspendedError,
    UserAlreadyWithdrawnError,
    UserNotSuspendableError,
    UserWithdrawnError,
)
from auth.domain.point_log import PointLog, PointType
from auth.domain.user import POINT_MAX_BALANCE, Role, User, UserStatus
from tests.auth.fakes import T0

NOW = T0


def make(role=Role.CUSTOMER, **kw):
    base = dict(email="a@b.com", password_hash="h", role=role)
    base.update(kw)
    return User(**base)


def owner(**kw):
    return make(Role.OWNER, status=UserStatus.PENDING, **kw)


def rejected_owner():
    return make(Role.OWNER, status=UserStatus.REJECTED, rejected_reason="r", rejected_at=NOW)


def suspended(role=Role.CUSTOMER, until=None):
    return make(
        role, status=UserStatus.SUSPENDED, suspended_reason="r",
        suspended_at=NOW - timedelta(days=1), suspended_until=until,
    )


def withdrawn(role=Role.CUSTOMER):
    return make(role, status=UserStatus.WITHDRAWN, deleted_at=NOW)


# ── 생성·불변식 ──
def test_register_status_by_role():
    assert User.register("a@b.com", "h", "OWNER").status is UserStatus.PENDING
    assert User.register("a@b.com", "h", "CUSTOMER").status is UserStatus.APPROVED
    assert User.register_admin("a@b.com", "h").status is UserStatus.APPROVED
    assert make().status is UserStatus.APPROVED


@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.ADMIN])
def test_pending_rejected_only_for_owner(role):
    with pytest.raises(ValueError):
        make(role, status=UserStatus.PENDING)
    with pytest.raises(ValueError):
        make(role, status=UserStatus.REJECTED, rejected_reason="r", rejected_at=NOW)


def test_state_invariants():
    with pytest.raises(ValueError):
        make(Role.OWNER, status=UserStatus.REJECTED, rejected_at=NOW)
    with pytest.raises(ValueError):
        make(Role.OWNER, status=UserStatus.REJECTED, rejected_reason="r")
    with pytest.raises(ValueError):
        make(status=UserStatus.SUSPENDED, suspended_at=NOW)
    with pytest.raises(ValueError):
        make(status=UserStatus.SUSPENDED, suspended_reason="r")
    with pytest.raises(ValueError):
        make(status=UserStatus.SUSPENDED, suspended_reason="r", suspended_at=NOW, suspended_until=NOW)
    with pytest.raises(ValueError):
        make(status=UserStatus.WITHDRAWN)
    with pytest.raises(ValueError):
        make(approved_at=NOW.replace(tzinfo=None))
    make(Role.OWNER, status=UserStatus.APPROVED)  # 기존 상점주 행: approved_at NULL 허용


# ── 승인·거부 ──
def test_approve_owner():
    u = owner()
    u.approve_owner(NOW)
    assert u.status is UserStatus.APPROVED and u.approved_at == NOW


def test_approve_error_order():
    with pytest.raises(OwnerNotFoundError, match="상점주를 찾을 수 없습니다."):
        make().approve_owner(NOW)
    with pytest.raises(OwnerNotPendingError) as e:
        make(Role.OWNER).approve_owner(NOW)  # APPROVED
    assert e.value.error_code == "OWNER_NOT_PENDING"
    assert str(e.value) == "승인 대기 중인 상점주가 아닙니다."
    with pytest.raises(ValueError, match="timezone"):
        owner().approve_owner(NOW.replace(tzinfo=None))


def test_reject_owner_and_terminal():
    u = owner()
    u.reject_owner("  서류 미비 ", NOW)
    assert u.status is UserStatus.REJECTED and u.rejected_reason == "서류 미비"
    assert u.rejected_at == NOW
    with pytest.raises(OwnerNotPendingError):
        u.approve_owner(NOW)
    with pytest.raises(OwnerNotPendingError):
        u.reject_owner("x", NOW)


def test_reject_reason_checked_first():
    with pytest.raises(ValueError, match="거부 사유를 입력해 주세요."):
        make().reject_owner("  ", NOW)  # 고객이어도 사유가 먼저
    with pytest.raises(ValueError, match="500자"):
        owner().reject_owner("x" * 501, NOW)
    with pytest.raises(OwnerNotFoundError):
        make().reject_owner("x", NOW)


# ── 정지 ──
def test_suspend_ok_and_indefinite():
    u = make()
    u.suspend(" 욕설 ", NOW + timedelta(days=3), NOW)
    assert u.status is UserStatus.SUSPENDED and u.suspended_reason == "욕설"
    assert u.suspended_at == NOW and u.suspended_until == NOW + timedelta(days=3)
    v = make()
    v.suspend("r", None, NOW)
    assert v.suspended_until is None and v.is_suspended(NOW + timedelta(days=9999))


def test_suspend_error_order():
    with pytest.raises(ValueError, match="정지 사유를 입력해 주세요."):
        make(role=Role.ADMIN).suspend("", NOW - timedelta(days=1), NOW)  # 사유가 until보다 먼저
    with pytest.raises(InvalidSuspensionEndError) as e:
        suspended().suspend("r", NOW, NOW)  # until <= now 가 '이미 정지'보다 먼저
    assert e.value.error_code == "INVALID_SUSPENSION_END"
    with pytest.raises(ValueError, match="timezone"):
        make().suspend("r", NOW.replace(tzinfo=None), NOW)
    with pytest.raises(UserAlreadySuspendedError):
        suspended(until=NOW + timedelta(days=1)).suspend("r", None, NOW)
    with pytest.raises(UserWithdrawnError):
        withdrawn().suspend("r", None, NOW)
    with pytest.raises(AdminAccountProtectedError, match="정지할 수 없습니다"):
        make(Role.ADMIN).suspend("r", None, NOW)
    with pytest.raises(UserNotSuspendableError) as e2:
        owner().suspend("r", None, NOW)
    assert e2.value.error_code == "USER_NOT_SUSPENDABLE"
    with pytest.raises(UserNotSuspendableError):
        rejected_owner().suspend("r", None, NOW)


def test_effective_status_expiry_boundary():
    u = suspended(until=NOW)
    assert u.effective_status(NOW) is UserStatus.APPROVED  # until == now 는 만료
    assert u.effective_status(NOW - timedelta(seconds=1)) is UserStatus.SUSPENDED
    assert u.status is UserStatus.SUSPENDED  # 저장 값은 그대로
    assert not u.is_suspended(NOW)


def test_expired_suspension_can_be_resuspended():
    u = suspended(until=NOW - timedelta(hours=1))
    u.suspend("again", None, NOW)
    assert u.suspended_reason == "again" and u.suspended_until is None


# ── 탈퇴 ──
def test_withdraw_from_every_live_status():
    for u in (owner(), make(), suspended(), rejected_owner()):
        u.withdraw(" 약관 위반 ", NOW)
        assert u.status is UserStatus.WITHDRAWN and u.deleted_at == NOW
        assert u.deleted_reason == "약관 위반"


def test_withdraw_errors():
    u = make()
    with pytest.raises(ValueError, match="탈퇴 사유를 입력해 주세요."):
        u.ensure_withdrawable(" ")
    with pytest.raises(AdminAccountProtectedError, match="탈퇴시킬 수 없습니다"):
        make(Role.ADMIN).withdraw("r", NOW)
    with pytest.raises(ValueError, match="500자"):
        make().withdraw("x" * 501, NOW)
    u.withdraw("r", NOW)
    with pytest.raises(UserAlreadyWithdrawnError):
        u.withdraw("r", NOW)


def test_ensure_withdrawable_has_no_side_effect():
    u = make()
    u.ensure_withdrawable("r")
    assert u.status is UserStatus.APPROVED and u.deleted_at is None


# ── 로그인·인증 ──
@pytest.mark.parametrize("role", [Role.CUSTOMER, Role.OWNER, Role.ADMIN])
def test_login_withdrawn_is_401_for_every_role(role):
    with pytest.raises(InvalidCredentialsError):
        withdrawn(role).ensure_can_login(NOW)


def test_login_pending_rejected_allowed():
    owner().ensure_can_login(NOW)
    rejected_owner().ensure_can_login(NOW)


def test_login_suspended_customer_403_owner_allowed():
    with pytest.raises(AccountSuspendedError, match="정지된 계정입니다."):
        suspended(Role.CUSTOMER).ensure_can_login(NOW)
    suspended(Role.OWNER).ensure_can_login(NOW)  # D39
    suspended(Role.CUSTOMER, until=NOW).ensure_can_login(NOW)  # 만료되면 허용


def test_authenticate_rules():
    with pytest.raises(AccountSuspendedError):
        suspended().ensure_can_authenticate(NOW)
    suspended().ensure_can_authenticate(NOW, allow_suspended=True)
    suspended(until=NOW).ensure_can_authenticate(NOW)
    for allow in (False, True):
        with pytest.raises(AuthenticationError, match="유효하지 않은 토큰입니다.") as e:
            withdrawn().ensure_can_authenticate(NOW, allow_suspended=allow)
        assert e.value.error_code == "UNAUTHORIZED"
    owner().ensure_can_authenticate(NOW)


def test_ensure_approved_owner():
    with pytest.raises(OwnerNotApprovedError, match="승인 대기 중인 상점주 계정입니다."):
        owner().ensure_approved_owner()
    with pytest.raises(OwnerNotApprovedError, match="거부"):
        rejected_owner().ensure_approved_owner()
    make(Role.OWNER).ensure_approved_owner()
    suspended(Role.OWNER).ensure_approved_owner()
    assert issubclass(OwnerNotApprovedError, PermissionError)


# ── 포인트 지급 ──
def test_grant_points_ok():
    u = make(users_point=10)
    assert u.grant_points(90, " 이벤트 ") == "이벤트"
    assert u.users_point == 100


@pytest.mark.parametrize("amount", [0, -1, True, 1.5])
def test_grant_amount_invalid(amount):
    with pytest.raises(ValueError, match="지급 포인트는 1 이상이어야 합니다."):
        make().grant_points(amount, "r")


def test_grant_error_order_and_limits():
    w = make(status=UserStatus.WITHDRAWN, deleted_at=NOW, users_point=POINT_MAX_BALANCE)
    with pytest.raises(ValueError, match="지급 사유를 입력해 주세요."):
        w.grant_points(1, " ")  # 사유가 탈퇴보다 먼저
    with pytest.raises(UserWithdrawnError):
        w.grant_points(1, "r")  # 탈퇴가 한도보다 먼저
    u = make(users_point=POINT_MAX_BALANCE - 1)
    with pytest.raises(ValueError, match="포인트 잔액이 한도를 넘습니다."):
        u.grant_points(2, "r")
    assert u.users_point == POINT_MAX_BALANCE - 1
    u.grant_points(1, "r")
    assert u.users_point == POINT_MAX_BALANCE


def test_grant_allowed_for_suspended_pending_admin():
    for u in (suspended(), owner(), make(Role.ADMIN)):
        u.grant_points(1, "r")


# ── PointLog ──
def test_point_log_grant_and_extras():
    uid, admin = uuid.uuid4(), uuid.uuid4()
    log = PointLog.record(uid, PointType.GRANT, 50, 150, reason="이벤트", created_by=admin)
    assert (log.reason, log.balance_after, log.created_by) == ("이벤트", 150, admin)
    with pytest.raises(ValueError):
        PointLog(uid, -1, PointType.GRANT)
    with pytest.raises(ValueError):
        PointLog.record(uid, PointType.EARN, 1, None)
    with pytest.raises(ValueError):
        PointLog.record(uid, PointType.EARN, 1, -1)
    with pytest.raises(AttributeError):
        log.balance_after = 0
    legacy = PointLog(uid, 5, PointType.EARN)  # 기존 행: 새 컬럼 NULL
    assert legacy.balance_after is None and legacy.reason is None and legacy.created_by is None


def test_is_owner_property():
    assert make(Role.OWNER).is_owner is True
    assert make(Role.CUSTOMER).is_owner is False
    assert make(Role.ADMIN).is_owner is False
