import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from auth.domain.exceptions import AuthenticationError
from auth.domain.service import EmailFingerprint, PasswordHasher, ResetCodeGenerator, TokenProvider
from auth.domain.token_claims import TokenClaims
from auth.domain.user import WITHDRAWN_EMAIL_PREFIX
from auth.infrastructure.settings import AuthSettings, get_auth_settings, get_withdrawn_email_key

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptPasswordHasher(PasswordHasher):
    def __init__(self):
        # 사용자가 없을 때도 같은 비용의 검증을 하기 위한 더미 해시 (첫 사용 시 생성)
        self._dummy_hash: str | None = None

    def hash(self, raw_password: str) -> str:
        return _pwd_context.hash(raw_password)

    def verify(self, raw_password: str, hashed_password: str) -> bool:
        try:
            return _pwd_context.verify(raw_password, hashed_password)
        except (ValueError, TypeError):
            return False

    def dummy_verify(self, raw_password: str) -> None:
        if self._dummy_hash is None:
            self._dummy_hash = _pwd_context.hash("dummy-password-for-timing")
        self.verify(raw_password, self._dummy_hash)


class HmacEmailFingerprint(EmailFingerprint):
    """HMAC-SHA256(비밀키, 정규화 이메일). 비밀키가 없으면 사전 대입으로 원문을 되찾을 수 있어 키를 쓴다.

    키를 바꾸면 이전에 탈퇴한 이메일의 재가입 차단이 풀리므로 키는 교체하지 않는다.
    """

    def __init__(self, key: bytes | None = None):
        self._key = key

    def tombstone(self, normalized_email: str) -> str:
        if self._key is None:
            self._key = get_withdrawn_email_key()
        digest = hmac.new(self._key, normalized_email.encode("utf-8"), hashlib.sha256).hexdigest()
        return WITHDRAWN_EMAIL_PREFIX + digest


class JwtTokenProvider(TokenProvider):
    def __init__(self, settings: AuthSettings | None = None):
        self._settings = settings

    @property
    def settings(self) -> AuthSettings:
        if self._settings is None:
            self._settings = get_auth_settings()
        return self._settings

    def issue(
        self,
        user_id: uuid.UUID,
        role: str,
        now: datetime | None = None,
        *,
        token_version: int = 0,
    ) -> tuple[str, TokenClaims]:
        now = now or datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.settings.access_token_expire_minutes)
        jti = str(uuid.uuid4())
        payload = {
            "sub": str(user_id),
            "role": str(role),
            "jti": jti,
            "ver": token_version,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self.settings.secret_key, algorithm=self.settings.algorithm)
        claims = TokenClaims(
            user_id=user_id,
            role=str(role),
            jti=jti,
            expires_at=datetime.fromtimestamp(int(expires_at.timestamp()), tz=timezone.utc),
            token_version=token_version,
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
            version = payload.get("ver", 0)  # 클레임 없는 기존 토큰은 세대 0
            if isinstance(version, bool) or not isinstance(version, int):
                raise AuthenticationError("유효하지 않은 토큰입니다.")
            return TokenClaims(
                user_id=uuid.UUID(payload["sub"]),
                role=str(payload["role"]),
                jti=str(payload["jti"]),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                token_version=version,
            )
        except jwt.ExpiredSignatureError as err:
            raise AuthenticationError("토큰이 만료되었습니다.") from err
        except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError) as err:
            raise AuthenticationError("유효하지 않은 토큰입니다.") from err


class SecretsResetCodeGenerator(ResetCodeGenerator):
    def generate(self) -> str:
        return f"{secrets.randbelow(10**6):06d}"
