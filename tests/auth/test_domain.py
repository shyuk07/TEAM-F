import uuid
from datetime import datetime, timedelta, timezone

import pytest

from auth.domain.exceptions import (
    AuthenticationError,
    EmailDuplicatedError,
    InvalidCredentialsError,
    TokenRevokedError,
)
from auth.domain.point_log import PointLog, PointType
from auth.domain.token_blacklist import BlacklistedToken
from auth.domain.token_claims import TokenClaims
from auth.domain.user import Role, User


def make_user(**kw):
    base = dict(email="a@b.com", password_hash="h", role=Role.CUSTOMER)
    base.update(kw)
    return User(**base)


def test_exceptions():
    assert AuthenticationError().error_code == "UNAUTHORIZED"
    assert str(AuthenticationError()) == "로그인이 필요합니다."
    assert str(InvalidCredentialsError()) == "이메일 또는 비밀번호가 올바르지 않습니다."
    assert TokenRevokedError().error_code == "TOKEN_REVOKED"
    assert not issubclass(EmailDuplicatedError, ValueError)


def test_role_for_signup():
    assert Role.for_signup("OWNER") is Role.OWNER
    with pytest.raises(ValueError, match="관리자"):
        Role.for_signup("ADMIN")
    with pytest.raises(ValueError, match="CUSTOMER 또는 OWNER"):
        Role.for_signup("x")


@pytest.mark.parametrize(
    "email", ["", "a b@c.com", "a@@c.com", "@c.com", "a@", "a@c", "a" * 256 + "@c.com"]
)
def test_invalid_email(email):
    with pytest.raises(ValueError):
        make_user(email=email)


def test_email_normalized():
    assert make_user(email="  A@B.Com ").email == "a@b.com"


def test_user_field_validation():
    with pytest.raises(ValueError):
        make_user(password_hash="")
    with pytest.raises(ValueError):
        make_user(role="CUSTOMER")
    with pytest.raises(ValueError):
        make_user(name="  ")
    with pytest.raises(ValueError):
        make_user(name="x" * 101)
    with pytest.raises(ValueError):
        make_user(phone="1" * 101)
    with pytest.raises(ValueError):
        make_user(users_point=-1)
    with pytest.raises(ValueError):
        make_user(created_at=datetime.now())


def test_validate_raw_password():
    User.validate_raw_password("password1")
    for bad in ["short", "        ", "가" * 25]:
        with pytest.raises(ValueError):
            User.validate_raw_password(bad)


def test_register():
    u = User.register("A@b.com", "h", "OWNER", name="n", phone=None, business_number=None)
    assert u.role is Role.OWNER and u.users_point == 0
    assert u.created_at.tzinfo is not None
    with pytest.raises(ValueError):
        User.register("a@b.com", "h", "ADMIN", None, None, None)


def test_roles():
    u = make_user()
    assert u.has_role(Role.CUSTOMER)
    u.require_role(Role.CUSTOMER, Role.OWNER)
    with pytest.raises(PermissionError, match="접근 권한이 없습니다."):
        u.require_role(Role.ADMIN)


def test_points():
    u = make_user()
    u.earn_points(250)
    assert u.users_point == 250
    u.use_points(200)
    assert u.users_point == 50
    for bad in (0, -100, 150, 100):
        with pytest.raises(ValueError):
            u.use_points(bad)
    u.restore_points(50)
    assert u.users_point == 100
    for fn in (u.earn_points, u.restore_points, u.revoke_points):
        with pytest.raises(ValueError):
            fn(0)
    assert u.revoke_points(300) == 100
    assert u.users_point == 0
    assert u.revoke_points(5) == 0


def test_point_log_rules():
    uid = uuid.uuid4()
    assert PointLog.record(uid, PointType.EARN, 10).created_at.tzinfo is not None
    PointLog.record(uid, PointType.USE, -10)
    PointLog.record(uid, PointType.REVOKE, -1)
    PointLog.record(uid, PointType.RESTORE, 1)
    for t, a in [(PointType.EARN, -1), (PointType.RESTORE, -1), (PointType.USE, 1),
                 (PointType.REVOKE, 1), (PointType.EARN, 0)]:
        with pytest.raises(ValueError):
            PointLog(uid, a, t)
    with pytest.raises(ValueError):
        PointLog(uid, 1, "EARN")


def test_point_log_immutable():
    log = PointLog.record(uuid.uuid4(), PointType.EARN, 10)
    with pytest.raises(AttributeError):
        log.amount = 5
    log.id = uuid.uuid4()  # 영속화 시 최초 1회만 허용
    with pytest.raises(AttributeError):
        log.id = uuid.uuid4()


def test_blacklisted_token():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        BlacklistedToken("", now)
    with pytest.raises(ValueError):
        BlacklistedToken("j", datetime.now())
    t = BlacklistedToken("j", now)
    assert t.is_expired(now) and not t.is_expired(now - timedelta(seconds=1))


def test_claims_to_blacklist_entry():
    exp = datetime.now(timezone.utc)
    entry = TokenClaims(uuid.uuid4(), "CUSTOMER", "jti1", exp).to_blacklist_entry()
    assert entry.jti == "jti1" and entry.expires_at == exp
