import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from auth.domain.token_claims import TokenClaims


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, raw_password: str) -> str: ...

    @abstractmethod
    def verify(self, raw_password: str, hashed_password: str) -> bool:
        """형식이 깨진 해시도 예외 없이 False."""

    @abstractmethod
    def dummy_verify(self, raw_password: str) -> None:
        """사용자가 없을 때도 verify와 같은 비용을 쓰게 하는 타이밍 방어. 결과는 버린다."""


class Clock(ABC):
    """현재 시각(tz-aware UTC). 정지 만료 판정에 쓴다 (D33)."""

    @abstractmethod
    def now(self) -> datetime: ...


class TokenProvider(ABC):
    @abstractmethod
    def issue(
        self, user_id: uuid.UUID, role: str, now: datetime | None = None
    ) -> tuple[str, TokenClaims]: ...

    @abstractmethod
    def decode(self, token: str) -> TokenClaims:
        """만료·위조·필수 클레임 누락은 AuthenticationError."""
