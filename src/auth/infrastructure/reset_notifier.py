import logging
from datetime import datetime

from auth.domain.service import PasswordResetNotifier

logger = logging.getLogger("auth.password_reset")


class LoggingPasswordResetNotifier(PasswordResetNotifier):
    """임시(개발·시연 전용) 전달 구현: 재설정 코드 원문을 로그에 남긴다 (REQ-26 "운영 기록에서 확인").

    원문 코드가 로그에 남으므로 실제 메일 발송 구현으로 교체(src/container.py `_reset_notifier`)한 뒤에만 배포한다.
    """

    async def send_code(self, email: str, code: str, expires_at: datetime) -> None:
        logger.warning(
            "[임시/개발용] 비밀번호 재설정 코드 email=%s code=%s expires_at=%s",
            email,
            code,
            expires_at.isoformat(),
        )
