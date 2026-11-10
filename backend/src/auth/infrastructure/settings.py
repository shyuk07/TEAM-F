import hashlib
import hmac
import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

MIN_SECRET_LENGTH = 32
# .env.example의 예시값을 그대로 쓰면 누구나 아는 키로 토큰을 위조할 수 있으므로 거부한다.
PLACEHOLDER_PREFIX = "change-me"


@dataclass(frozen=True)
class AuthSettings:
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


@lru_cache
def get_auth_settings() -> AuthSettings:
    load_dotenv()
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret or len(secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"JWT_SECRET_KEY 환경변수가 없거나 {MIN_SECRET_LENGTH}자 미만입니다."
        )
    if secret.startswith(PLACEHOLDER_PREFIX):
        raise RuntimeError("JWT_SECRET_KEY가 .env.example의 예시값입니다. 임의의 값으로 바꾸세요.")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    if algorithm != "HS256":
        raise RuntimeError("JWT_ALGORITHM은 HS256만 지원합니다.")
    try:
        minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    except ValueError as err:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES는 정수여야 합니다.") from err
    if minutes <= 0:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES는 1 이상이어야 합니다.")
    return AuthSettings(secret_key=secret, algorithm=algorithm, access_token_expire_minutes=minutes)


_WITHDRAWN_EMAIL_KEY_LABEL = b"lastcall:withdrawn-email:v1"


def get_withdrawn_email_key(env: Mapping[str, str] | None = None) -> bytes:
    """탈퇴 이메일 해시 키. WITHDRAWN_EMAIL_HASH_KEY가 있으면 그 값, 없으면 JWT_SECRET_KEY에서 용도 분리로 만든다.

    오류 메시지에 값을 넣지 않는다. 키를 바꾸면 기존 탈퇴 이메일의 재가입 차단이 풀린다.
    """
    if env is None:
        load_dotenv()
        env = os.environ
    own = env.get("WITHDRAWN_EMAIL_HASH_KEY") or ""
    if own:
        if len(own) < MIN_SECRET_LENGTH:
            raise RuntimeError(f"WITHDRAWN_EMAIL_HASH_KEY는 {MIN_SECRET_LENGTH}자 이상이어야 합니다.")
        if own.startswith(PLACEHOLDER_PREFIX):
            raise RuntimeError("WITHDRAWN_EMAIL_HASH_KEY가 .env.example의 예시값입니다. 임의의 값으로 바꾸세요.")
        return own.encode("utf-8")
    base = get_auth_settings().secret_key if env is os.environ else (env.get("JWT_SECRET_KEY") or "")
    if len(base) < MIN_SECRET_LENGTH or base.startswith(PLACEHOLDER_PREFIX):
        raise RuntimeError("탈퇴 이메일 해시 키를 만들 수 없습니다. JWT_SECRET_KEY를 확인하세요.")
    return hmac.new(base.encode("utf-8"), _WITHDRAWN_EMAIL_KEY_LABEL, hashlib.sha256).digest()


@dataclass(frozen=True)
class AdminSeedSettings:
    email: str
    password: str


def get_admin_seed_settings(env: Mapping[str, str] | None = None) -> AdminSeedSettings | None:
    """ADMIN_EMAIL/ADMIN_PASSWORD를 읽는다. 둘 다 없으면 None(건너뜀). 오류 메시지에 값을 넣지 않는다."""
    if env is None:
        load_dotenv()
        env = os.environ
    email = (env.get("ADMIN_EMAIL") or "").strip()
    password = env.get("ADMIN_PASSWORD") or ""
    if not email and not password:
        return None
    if not email or not password:
        raise RuntimeError("ADMIN_EMAIL과 ADMIN_PASSWORD는 함께 설정해야 합니다.")
    if password.startswith(PLACEHOLDER_PREFIX):
        raise RuntimeError("ADMIN_PASSWORD가 .env.example의 예시값입니다. 임의의 값으로 바꾸세요.")
    return AdminSeedSettings(email=email, password=password)


DEFAULT_SMTP_PORT = 587
_MAIL_REQUIRED_KEYS = ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM")


@dataclass(frozen=True)
class MailSettings:
    host: str
    port: int
    user: str
    password: str
    mail_from: str
    timeout_seconds: float = 10.0


def get_mail_settings(env: Mapping[str, str] | None = None) -> MailSettings | None:
    """SMTP_*·MAIL_FROM을 읽는다. 전부 비면 None(로그 전달). 일부만 있으면 RuntimeError(키 이름만, 값 없음)."""
    if env is None:
        load_dotenv()
        env = os.environ
    values = {
        key: (env.get(key) or "").strip()
        for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "MAIL_FROM")
    }
    if not any(values.values()):
        return None
    missing = [key for key in _MAIL_REQUIRED_KEYS if not values[key]]
    if missing:
        raise RuntimeError(f"SMTP 설정이 불완전합니다. 누락: {', '.join(missing)}")
    raw_port = values["SMTP_PORT"] or str(DEFAULT_SMTP_PORT)
    try:
        port = int(raw_port)
    except ValueError as err:
        raise RuntimeError("SMTP_PORT는 정수여야 합니다.") from err
    if not 1 <= port <= 65535:
        raise RuntimeError("SMTP_PORT는 1~65535 사이여야 합니다.")
    if port == 465:
        raise RuntimeError("SMTP_PORT 465(암묵적 TLS)는 지원하지 않습니다. STARTTLS(587)를 사용하세요.")
    mail_from = values["MAIL_FROM"]
    if "@" not in mail_from or "\r" in mail_from or "\n" in mail_from:
        raise RuntimeError("MAIL_FROM 형식이 올바르지 않습니다.")
    return MailSettings(
        host=values["SMTP_HOST"],
        port=port,
        user=values["SMTP_USER"],
        password=values["SMTP_PASSWORD"],
        mail_from=mail_from,
    )
