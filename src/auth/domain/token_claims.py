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

    def to_blacklist_entry(self) -> BlacklistedToken:
        return BlacklistedToken(jti=self.jti, expires_at=self.expires_at)
