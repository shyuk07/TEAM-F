from abc import ABC, abstractmethod
from datetime import datetime

from auth.domain.token_blacklist import BlacklistedToken


class TokenBlacklistRepository(ABC):
    @abstractmethod
    async def add(self, token: BlacklistedToken) -> None:
        """같은 jti가 이미 있으면 무시(멱등)."""

    @abstractmethod
    async def exists(self, jti: str) -> bool: ...

    @abstractmethod
    async def delete_expired(self, now: datetime | None = None) -> int: ...
