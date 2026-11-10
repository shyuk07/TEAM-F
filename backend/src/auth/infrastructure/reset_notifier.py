import asyncio
import logging
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from auth.domain.exceptions import PasswordResetDeliveryError
from auth.domain.service import PasswordResetNotifier
from auth.infrastructure.settings import MailSettings

logger = logging.getLogger("auth.password_reset")

KST = timezone(timedelta(hours=9))
MAIL_SUBJECT = "[마감 직전] 비밀번호 재설정 코드 안내"
MAIL_BODY = """안녕하세요, 마감 직전입니다.

비밀번호 재설정 코드는 아래와 같습니다.

    {code}

이 코드는 {expires_at_kst} (한국 시간)까지 한 번만 사용할 수 있습니다.
코드와 새 비밀번호를 앱의 재설정 화면에 입력해 주세요.

본인이 요청하지 않았다면 이 메일을 무시해 주세요. 비밀번호는 바뀌지 않습니다.
코드를 다른 사람에게 알려 주지 마세요. 마감 직전은 코드를 묻지 않습니다.
"""


class LoggingPasswordResetNotifier(PasswordResetNotifier):
    """임시(개발·시연 전용) 전달 구현: 재설정 코드 원문을 로그에 남긴다 (REQ-26 "운영 기록에서 확인").

    SMTP 설정이 없을 때만 쓰인다(src/container.py `build_reset_notifier`).
    원문 코드가 로그에 남으므로 이 구현이 선택된 상태로는 배포하지 않는다.
    """

    async def send_code(self, email: str, code: str, expires_at: datetime) -> None:
        logger.warning(
            "[임시/개발용] 비밀번호 재설정 코드 email=%s code=%s expires_at=%s",
            email,
            code,
            expires_at.isoformat(),
        )


class SmtpPasswordResetNotifier(PasswordResetNotifier):
    """SMTP(STARTTLS)로 재설정 코드를 메일로 보낸다. 코드·이메일·자격증명·예외 메시지는 로그에 남기지 않는다."""

    def __init__(self, settings: MailSettings, smtp_factory=smtplib.SMTP):
        self._settings = settings
        self._smtp_factory = smtp_factory

    async def send_code(self, email: str, code: str, expires_at: datetime) -> None:
        try:
            message = self._build_message(email, code, expires_at)
        except ValueError as err:
            self._fail("build", err)
        await asyncio.to_thread(self._send_blocking, message)
        logger.info("비밀번호 재설정 메일 발송 완료")

    def _build_message(self, email: str, code: str, expires_at: datetime) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._settings.mail_from
        message["To"] = email
        message["Subject"] = MAIL_SUBJECT
        message.set_content(
            MAIL_BODY.format(
                code=code,
                expires_at_kst=expires_at.astimezone(KST).strftime("%Y-%m-%d %H:%M"),
            )
        )
        return message

    def _send_blocking(self, message: EmailMessage) -> None:
        s = self._settings
        stage = "connect"
        try:
            with self._smtp_factory(s.host, s.port, timeout=s.timeout_seconds) as smtp:
                stage = "starttls"
                smtp.starttls(context=ssl.create_default_context())
                stage = "login"
                smtp.login(s.user, s.password)
                stage = "send"
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as err:
            self._fail(stage, err)

    @staticmethod
    def _fail(stage: str, err: Exception):
        detail = type(err).__name__
        if isinstance(err, smtplib.SMTPResponseException):
            detail += f" {err.smtp_code}"
        logger.warning("비밀번호 재설정 메일 발송 실패 stage=%s error=%s", stage, detail)
        raise PasswordResetDeliveryError() from None
