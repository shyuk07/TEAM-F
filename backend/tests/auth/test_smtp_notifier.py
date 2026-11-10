"""SmtpPasswordResetNotifier 테스트: 가짜 SMTP만 쓰고 소켓·실제 메일은 없다."""

import logging
import smtplib
import ssl
import threading
from datetime import datetime, timezone

import pytest

from auth.domain.exceptions import PasswordResetDeliveryError
from auth.infrastructure.reset_notifier import SmtpPasswordResetNotifier
from auth.infrastructure.settings import MailSettings

pytestmark = pytest.mark.anyio

EMAIL = "user@test.com"
CODE = "123456"
PASSWORD = "smtp-pw-secret"
SETTINGS = MailSettings(
    host="smtp.test.com", port=587, user="mailer-user", password=PASSWORD, mail_from="no-reply@test.com"
)
EXPIRES = datetime(2026, 11, 9, 9, 15, tzinfo=timezone.utc)


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeSMTP:
    instances: list["FakeSMTP"] = []
    fail_at: str | None = None
    error: Exception | None = None

    def __init__(self, host, port, timeout=None):
        self.init = (host, port, timeout)
        self.calls = []
        self.threads = []
        FakeSMTP.instances.append(self)
        self._maybe_fail("connect")

    def _maybe_fail(self, stage):
        if FakeSMTP.fail_at == stage:
            raise FakeSMTP.error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.threads.append(threading.current_thread())
        self.calls.append(("starttls", context))
        self._maybe_fail("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))
        self._maybe_fail("login")

    def send_message(self, message):
        self.calls.append(("send_message", message))
        self._maybe_fail("send")


@pytest.fixture(autouse=True)
def reset_fake():
    FakeSMTP.instances = []
    FakeSMTP.fail_at = None
    FakeSMTP.error = None


def make():
    return SmtpPasswordResetNotifier(SETTINGS, smtp_factory=FakeSMTP)


async def test_sends_in_order_with_settings():
    await make().send_code(EMAIL, CODE, EXPIRES)
    smtp = FakeSMTP.instances[0]
    assert smtp.init == ("smtp.test.com", 587, 10.0)
    assert [c[0] for c in smtp.calls] == ["starttls", "login", "send_message"]
    assert isinstance(smtp.calls[0][1], ssl.SSLContext)
    assert smtp.calls[1] == ("login", "mailer-user", PASSWORD)


async def test_message_content():
    await make().send_code(EMAIL, CODE, EXPIRES)
    message = FakeSMTP.instances[0].calls[2][1]
    assert message["To"] == EMAIL
    assert message["From"] == "no-reply@test.com"
    assert message["Subject"] == "[마감 직전] 비밀번호 재설정 코드 안내"
    body = message.get_content()
    assert CODE in body
    assert "2026-11-09 18:15 (한국 시간)" in body


async def test_runs_off_the_event_loop_thread():
    await make().send_code(EMAIL, CODE, EXPIRES)
    assert FakeSMTP.instances[0].threads[0] is not threading.main_thread()


@pytest.mark.parametrize(
    ("stage", "error", "expected"),
    [
        ("login", smtplib.SMTPAuthenticationError(535, b"bad creds for user@test.com"), "stage=login"),
        ("connect", TimeoutError("timed out smtp.test.com"), "stage=connect"),
        ("connect", ConnectionRefusedError("refused"), "stage=connect"),
        ("send", smtplib.SMTPRecipientsRefused({EMAIL: (550, b"no")}), "stage=send"),
        ("starttls", smtplib.SMTPNotSupportedError("no starttls"), "stage=starttls"),
    ],
)
async def test_failure_becomes_delivery_error_and_logs_safely(caplog, stage, error, expected):
    FakeSMTP.fail_at, FakeSMTP.error = stage, error
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(PasswordResetDeliveryError) as exc:
            await make().send_code(EMAIL, CODE, EXPIRES)
    assert exc.value.__cause__ is None
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    text = caplog.text
    assert expected in text and type(error).__name__ in text
    for secret in (CODE, EMAIL, PASSWORD, "mailer-user", "bad creds", "timed out"):
        assert secret not in text


async def test_header_injection_becomes_delivery_error(caplog):
    with caplog.at_level(logging.DEBUG), pytest.raises(PasswordResetDeliveryError):
        await make().send_code("a@b.com\nBcc: x@y.z", CODE, EXPIRES)
    assert FakeSMTP.instances == []
    assert "Bcc" not in caplog.text and CODE not in caplog.text


async def test_success_logs_no_code_or_email(caplog):
    with caplog.at_level(logging.DEBUG):
        await make().send_code(EMAIL, CODE, EXPIRES)
    for secret in (CODE, EMAIL, PASSWORD, "mailer-user"):
        assert secret not in caplog.text


def test_default_factory_path_does_not_open_socket():
    notifier = SmtpPasswordResetNotifier(SETTINGS)  # 생성만, send_code 호출 없음
    assert notifier._smtp_factory is smtplib.SMTP


async def test_service_swallows_smtp_failure_after_commit(caplog):
    from tests.auth.test_requirements_service import make_reset, signed_up

    FakeSMTP.fail_at, FakeSMTP.error = "login", smtplib.SMTPAuthenticationError(535, b"x")
    reset, svc, db, _, codes, _ = make_reset("123456")
    reset.notifier = make()
    u = await signed_up(svc)
    db.commits = 0
    with caplog.at_level(logging.DEBUG):
        await reset.request_reset("a@b.com")  # 예외 없음
    assert db.commits == 1 and u.id in codes.rows
    for secret in ("123456", "a@b.com", PASSWORD):
        assert secret not in caplog.text
