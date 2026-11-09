import pytest

from auth.infrastructure.settings import MailSettings, get_mail_settings

FULL = {
    "SMTP_HOST": "smtp.test.com",
    "SMTP_USER": "mailer",
    "SMTP_PASSWORD": "pw-secret-value",
    "MAIL_FROM": "no-reply@test.com",
}


@pytest.mark.parametrize(
    "env",
    [
        {},
        {k: "" for k in [*FULL, "SMTP_PORT"]},
        {k: "   " for k in [*FULL, "SMTP_PORT"]},
    ],
)
def test_none_when_all_empty(env):
    assert get_mail_settings(env) is None


def test_required_only_uses_defaults():
    s = get_mail_settings(FULL)
    assert s == MailSettings(
        host="smtp.test.com",
        port=587,
        user="mailer",
        password="pw-secret-value",
        mail_from="no-reply@test.com",
        timeout_seconds=10.0,
    )


def test_all_five_with_strip():
    env = {k: f"  {v}  " for k, v in FULL.items()} | {"SMTP_PORT": " 2525 "}
    s = get_mail_settings(env)
    assert s.port == 2525 and s.host == "smtp.test.com" and s.mail_from == "no-reply@test.com"
    assert s.user == "mailer" and s.password == "pw-secret-value"


@pytest.mark.parametrize("missing", list(FULL))
def test_missing_required_key_raises_with_key_name_only(missing):
    env = {k: v for k, v in FULL.items() if k != missing}
    with pytest.raises(RuntimeError) as exc:
        get_mail_settings(env)
    assert missing in str(exc.value)
    for value in env.values():
        assert value not in str(exc.value)


@pytest.mark.parametrize("env", [{"SMTP_PORT": "587"}, {"SMTP_HOST": "smtp.test.com"}])
def test_partial_settings_raise(env):
    with pytest.raises(RuntimeError, match="누락"):
        get_mail_settings(env)


@pytest.mark.parametrize("port", ["abc", "0", "70000", "465"])
def test_invalid_port_raises(port):
    with pytest.raises(RuntimeError):
        get_mail_settings(FULL | {"SMTP_PORT": port})


@pytest.mark.parametrize("mail_from", ["no-at", "a@b.com\nBcc: x@y.z", "a@b.com\rX"])
def test_invalid_mail_from_raises(mail_from):
    with pytest.raises(RuntimeError):
        get_mail_settings(FULL | {"MAIL_FROM": mail_from})
