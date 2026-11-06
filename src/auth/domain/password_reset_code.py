import uuid
from datetime import datetime, timedelta

from auth.domain.exceptions import InvalidResetCodeError
from auth.domain.service import PasswordHasher


class PasswordResetCode:
    """비밀번호 재설정 코드(회원당 1개). 원문은 저장하지 않고 해시만 가진다 (D-재설정코드)."""

    CODE_LENGTH = 6
    TTL = timedelta(minutes=15)
    MAX_FAILED_ATTEMPTS = 5
    REQUEST_COOLDOWN = timedelta(seconds=60)  # 임시값: 재요청 최소 간격, 사용자 확정 전 (D-재설정제한)

    def __init__(
        self,
        user_id: uuid.UUID,
        code_hash: str,
        expires_at: datetime,
        failed_attempts: int = 0,
        created_at: datetime | None = None,
    ):
        if not code_hash:
            raise ValueError("코드 해시는 비어 있을 수 없습니다.")
        if expires_at.tzinfo is None:
            raise ValueError("expires_at은 timezone 정보가 있어야 합니다.")
        if failed_attempts < 0:
            raise ValueError("실패 횟수는 0 이상이어야 합니다.")
        self.user_id = user_id
        self.code_hash = code_hash
        self.expires_at = expires_at
        self.failed_attempts = failed_attempts
        self.created_at = created_at

    @classmethod
    def is_valid_format(cls, raw: str) -> bool:
        return len(raw) == cls.CODE_LENGTH and raw.isascii() and raw.isdigit()

    @classmethod
    def is_request_throttled(cls, previous: "PasswordResetCode | None", now: datetime) -> bool:
        """직전 코드 발급 후 REQUEST_COOLDOWN 안이면 True. 이때는 새 코드를 만들지 않는다(무차별 대입 완화)."""
        if previous is None or previous.created_at is None:
            return False
        return now < previous.created_at + cls.REQUEST_COOLDOWN

    @classmethod
    def issue(
        cls,
        user_id: uuid.UUID,
        raw_code: str,
        hasher: PasswordHasher,
        now: datetime,
    ) -> "PasswordResetCode":
        """새 코드 발급. 항상 실패 횟수 0에서 시작한다(REQ-28·REQ-29). 이전 코드는 덮어써서 무효가 된다."""
        if not cls.is_valid_format(raw_code):
            raise ValueError(f"재설정 코드는 {cls.CODE_LENGTH}자리 숫자여야 합니다.")
        if now.tzinfo is None:
            raise ValueError("now는 timezone 정보가 있어야 합니다.")
        return cls(
            user_id=user_id,
            code_hash=hasher.hash(raw_code),
            expires_at=now + cls.TTL,
            failed_attempts=0,
            created_at=now,
        )

    def is_usable(self, now: datetime) -> bool:
        """만료 시각 정각은 만료. 실패 5회면 맞는 코드도 쓸 수 없다."""
        return now < self.expires_at and self.failed_attempts < self.MAX_FAILED_ATTEMPTS

    def check(self, raw: str, hasher: PasswordHasher, now: datetime) -> bool:
        """사용 불가면 InvalidResetCodeError, 불일치면 실패 횟수 +1 후 False, 일치면 True."""
        if not self.is_usable(now):
            raise InvalidResetCodeError()
        if hasher.verify(raw, self.code_hash):
            return True
        self.failed_attempts += 1
        return False
