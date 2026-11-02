import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from auth.domain.exceptions import AuthenticationError
from auth.infrastructure.security import JwtTokenProvider, PasswordHasher
from auth.infrastructure.settings import AuthSettings, get_auth_settings

SECRET = "s" * 40


def provider(secret=SECRET):
    return JwtTokenProvider(AuthSettings(secret_key=secret))


def test_password_hash_roundtrip():
    h = PasswordHasher()
    hashed = h.hash("password123")
    assert hashed != "password123"
    assert h.verify("password123", hashed)
    assert not h.verify("wrong", hashed)
    assert not h.verify("x", "not-a-hash")
    h.dummy_verify("anything")


def test_jwt_roundtrip():
    uid = uuid.uuid4()
    token, claims = provider().issue(uid, "CUSTOMER")
    decoded = provider().decode(token)
    assert decoded.user_id == uid and decoded.role == "CUSTOMER"
    assert decoded.jti == claims.jti
    delta = decoded.expires_at - datetime.now(timezone.utc)
    assert timedelta(minutes=29) < delta <= timedelta(minutes=30)


def test_jti_unique():
    p = provider()
    uid = uuid.uuid4()
    assert p.issue(uid, "CUSTOMER")[1].jti != p.issue(uid, "CUSTOMER")[1].jti


def test_expired():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    token, _ = provider().issue(uuid.uuid4(), "CUSTOMER", now=past)
    with pytest.raises(AuthenticationError, match="만료"):
        provider().decode(token)


def test_tampered_and_wrong_secret():
    token, _ = provider().issue(uuid.uuid4(), "CUSTOMER")
    with pytest.raises(AuthenticationError, match="유효하지 않은"):
        provider().decode(token[:-2] + ("AA" if not token.endswith("AA") else "BB"))
    with pytest.raises(AuthenticationError):
        provider("o" * 40).decode(token)
    with pytest.raises(AuthenticationError):
        provider().decode("garbage")


def test_alg_none_rejected():
    payload = {"sub": str(uuid.uuid4()), "role": "ADMIN", "jti": "j",
               "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())}
    token = jwt.encode(payload, None, algorithm="none")
    with pytest.raises(AuthenticationError):
        provider().decode(token)


@pytest.mark.parametrize("missing", ["exp", "sub", "jti", "role"])
def test_missing_claims(missing):
    payload = {"sub": str(uuid.uuid4()), "role": "CUSTOMER", "jti": "j",
               "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())}
    del payload[missing]
    with pytest.raises(AuthenticationError):
        provider().decode(jwt.encode(payload, SECRET, algorithm="HS256"))


def test_non_uuid_sub():
    payload = {"sub": "abc", "role": "CUSTOMER", "jti": "j",
               "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())}
    with pytest.raises(AuthenticationError):
        provider().decode(jwt.encode(payload, SECRET, algorithm="HS256"))


def test_settings_errors(monkeypatch):
    monkeypatch.setattr("auth.infrastructure.settings.load_dotenv", lambda: None)
    get_auth_settings.cache_clear()
    try:
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(RuntimeError):
            get_auth_settings()
        monkeypatch.setenv("JWT_SECRET_KEY", "short")
        with pytest.raises(RuntimeError):
            get_auth_settings()
        monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
        monkeypatch.setenv("JWT_ALGORITHM", "HS512")
        with pytest.raises(RuntimeError):
            get_auth_settings()
        monkeypatch.setenv("JWT_ALGORITHM", "HS256")
        assert get_auth_settings().secret_key == SECRET
    finally:
        get_auth_settings.cache_clear()
