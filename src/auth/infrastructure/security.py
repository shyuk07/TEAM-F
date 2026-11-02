import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from auth.domain.exceptions import AuthenticationError
from auth.domain.token_claims import TokenClaims
from auth.infrastructure.settings import AuthSettings, get_auth_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordHasher:
    def __init__(self):
        # 사용자가 없을 때도 같은 비용의 검증을 하기 위한 더미 해시
        self._dummy_hash = _pwd_context.hash("dummy-password-for-timing")

    def hash(self, raw: str) -> str:
        return _pwd_context.hash(raw)

    def verify(self, raw: str, hashed: str) -> bool:
        try:
            return _pwd_context.verify(raw, hashed)
        except (ValueError, TypeError):
            return False

    def dummy_verify(self, raw: str) -> None:
        self.verify(raw, self._dummy_hash)


class JwtTokenProvider:
    def __init__(self, settings: AuthSettings | None = None):
        self._settings = settings

    @property
    def settings(self) -> AuthSettings:
        if self._settings is None:
            self._settings = get_auth_settings()
        return self._settings

    def issue(
        self, user_id: uuid.UUID, role: str, now: datetime | None = None
    ) -> tuple[str, TokenClaims]:
        now = now or datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.settings.access_token_expire_minutes)
        jti = str(uuid.uuid4())
        payload = {
            "sub": str(user_id),
            "role": str(role),
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self.settings.secret_key, algorithm=self.settings.algorithm)
        claims = TokenClaims(
            user_id=user_id,
            role=str(role),
            jti=jti,
            expires_at=datetime.fromtimestamp(int(expires_at.timestamp()), tz=timezone.utc),
        )
        return token, claims

    def decode(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key,
                algorithms=[self.settings.algorithm],
                options={"require": ["exp", "sub", "jti", "role"]},
            )
            return TokenClaims(
                user_id=uuid.UUID(payload["sub"]),
                role=str(payload["role"]),
                jti=str(payload["jti"]),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
        except jwt.ExpiredSignatureError as err:
            raise AuthenticationError("토큰이 만료되었습니다.") from err
        except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError) as err:
            raise AuthenticationError("유효하지 않은 토큰입니다.") from err
