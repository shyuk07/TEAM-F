"""탈퇴 회원 개인정보 파기(개인정보 B안) 단위 테스트: 도메인 규칙, 이메일 대체값, 키 설정."""

from datetime import datetime, timezone

import pytest

from auth.domain.user import WITHDRAWN_EMAIL_PREFIX, WITHDRAWN_PASSWORD_HASH, User, UserStatus
from auth.infrastructure.security import BcryptPasswordHasher, HmacEmailFingerprint
from auth.infrastructure.settings import get_withdrawn_email_key

NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)
KEY = b"k" * 32


def customer():
    u = User.register(email="me@test.com", password_hash="h", role="CUSTOMER", name="홍길동", phone="010")
    u.business_number = "123"
    return u


def test_erase_requires_withdrawn_status():
    u = customer()
    with pytest.raises(ValueError):
        u.erase_personal_data(HmacEmailFingerprint(KEY).tombstone(u.email))
    assert u.email == "me@test.com" and u.name == "홍길동"


@pytest.mark.parametrize("bad", ["me@test.com", "withdrawn:a@b", "x" * 10, "withdrawn:" + "a" * 250])
def test_erase_rejects_malformed_tombstone(bad):
    u = customer()
    u.withdraw("사유", NOW)
    with pytest.raises(ValueError):
        u.erase_personal_data(bad)
    assert u.email == "me@test.com"


def test_erase_clears_personal_fields_and_keeps_records():
    u = customer()
    u.withdraw("사유", NOW)
    tomb = HmacEmailFingerprint(KEY).tombstone(u.email)
    u.erase_personal_data(tomb)
    assert u.email == tomb and u.password_hash == WITHDRAWN_PASSWORD_HASH
    assert (u.name, u.phone, u.business_number) == (None, None, None)
    assert u.status is UserStatus.WITHDRAWN and u.deleted_reason == "사유" and u.deleted_at == NOW


def test_withdrawn_password_hash_never_verifies():
    assert BcryptPasswordHasher().verify("password123", WITHDRAWN_PASSWORD_HASH) is False
    assert BcryptPasswordHasher().verify("", WITHDRAWN_PASSWORD_HASH) is False


def test_tombstone_is_deterministic_keyed_and_has_no_at_sign():
    a = HmacEmailFingerprint(KEY)
    t = a.tombstone("me@test.com")
    assert t == a.tombstone("me@test.com") and t.startswith(WITHDRAWN_EMAIL_PREFIX) and "@" not in t
    assert len(t) == len(WITHDRAWN_EMAIL_PREFIX) + 64
    assert t != a.tombstone("you@test.com")
    assert t != HmacEmailFingerprint(b"z" * 32).tombstone("me@test.com")  # 키가 다르면 값이 다르다


JWT = "j" * 40


def test_key_falls_back_to_jwt_secret_with_domain_separation():
    k = get_withdrawn_email_key({"JWT_SECRET_KEY": JWT})
    assert len(k) == 32 and k != JWT.encode()
    assert k == get_withdrawn_email_key({"JWT_SECRET_KEY": JWT})


def test_own_key_is_used_when_set():
    own = "o" * 32
    assert get_withdrawn_email_key({"JWT_SECRET_KEY": JWT, "WITHDRAWN_EMAIL_HASH_KEY": own}) == own.encode()


@pytest.mark.parametrize(
    "env",
    [
        {"JWT_SECRET_KEY": JWT, "WITHDRAWN_EMAIL_HASH_KEY": "short"},
        {"JWT_SECRET_KEY": JWT, "WITHDRAWN_EMAIL_HASH_KEY": "change-me" + "x" * 30},
        {"JWT_SECRET_KEY": "short"},
        {"JWT_SECRET_KEY": "change-me" + "x" * 30},
        {},
    ],
)
def test_bad_key_settings_fail_without_leaking_value(env):
    with pytest.raises(RuntimeError) as e:
        get_withdrawn_email_key(env)
    for v in env.values():
        assert v not in str(e.value)


def test_tombstone_email_loads_only_for_withdrawn_user():
    tomb = HmacEmailFingerprint(KEY).tombstone("me@test.com")
    u = User(email=tomb, password_hash=WITHDRAWN_PASSWORD_HASH, role=customer().role,
             status=UserStatus.WITHDRAWN, deleted_at=NOW)
    assert u.email == tomb
    with pytest.raises(ValueError):  # 이용 중인 회원은 대체값을 가질 수 없다
        User(email=tomb, password_hash="h", role=customer().role)
