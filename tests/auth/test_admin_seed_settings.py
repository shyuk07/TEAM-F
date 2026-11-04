import pytest

from auth.infrastructure.settings import AdminSeedSettings, get_admin_seed_settings


@pytest.mark.parametrize(
    "env",
    [{}, {"ADMIN_EMAIL": "", "ADMIN_PASSWORD": ""}, {"ADMIN_EMAIL": "  ", "ADMIN_PASSWORD": ""}],
)
def test_none_when_both_missing(env):
    assert get_admin_seed_settings(env) is None


def test_both_set():
    s = get_admin_seed_settings({"ADMIN_EMAIL": "a@b.com", "ADMIN_PASSWORD": "s3cret-pass"})
    assert s == AdminSeedSettings(email="a@b.com", password="s3cret-pass")


@pytest.mark.parametrize(
    "env", [{"ADMIN_EMAIL": "a@b.com"}, {"ADMIN_PASSWORD": "s3cret-pass-value"}]
)
def test_only_one_raises_without_password(env):
    with pytest.raises(RuntimeError) as exc:
        get_admin_seed_settings(env)
    assert "s3cret-pass-value" not in str(exc.value)


def test_placeholder_password_rejected():
    with pytest.raises(RuntimeError) as exc:
        get_admin_seed_settings({"ADMIN_EMAIL": "a@b.com", "ADMIN_PASSWORD": "change-me-please"})
    assert "change-me-please" not in str(exc.value)
