from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from auth.domain.token_blacklist import BlacklistedToken


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    role: str
    jti: str
    expires_at: datetime
    token_version: int = 0  # 비밀번호 변경·재설정 시 무효화용 세대 (D-토큰무효화)

    def to_blacklist_entry(self) -> BlacklistedToken:
        return BlacklistedToken(jti=self.jti, expires_at=self.expires_at)
