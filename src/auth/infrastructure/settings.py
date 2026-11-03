import os
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
