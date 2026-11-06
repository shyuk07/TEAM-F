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
        self,
        user_id: uuid.UUID,
        role: str,
        now: datetime | None = None,
        *,
        token_version: int = 0,
    ) -> tuple[str, TokenClaims]: ...

    @abstractmethod
    def decode(self, token: str) -> TokenClaims:
        """만료·위조·필수 클레임 누락은 AuthenticationError."""


class ResetCodeGenerator(ABC):
    """비밀번호 재설정 코드(6자리 숫자 문자열)를 만든다."""

    @abstractmethod
    def generate(self) -> str: ...


class PasswordResetNotifier(ABC):
    """재설정 코드를 회원에게 전달한다(메일 등). 실패해도 요청 응답에는 드러내지 않는다.

    구현체는 비동기 논블로킹이어야 한다(응답 뒤 같은 이벤트 루프에서 실행되므로, 막으면 다음 요청이 느려진다).
    """

    @abstractmethod
    async def send_code(self, email: str, code: str, expires_at: datetime) -> None: ...
