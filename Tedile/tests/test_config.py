import importlib

import pytest


def load_config(monkeypatch, app_env, **values):
    monkeypatch.setenv("APP_ENV", app_env)
    for key in ("DATABASE_URL", "SECRET_KEY", "ENCRYPTION_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    import config

    return importlib.reload(config)


def test_development_environment_uses_development_config(monkeypatch):
    config = load_config(monkeypatch, "development")

    assert isinstance(config.DevelopmentConfig(), config.DevelopmentConfig)


def test_uat_environment_uses_uat_config(monkeypatch):
    config = load_config(
        monkeypatch,
        "uat",
        DATABASE_URL="postgresql://uat-host/tedile_uat",
        SECRET_KEY="uat-secret",
        ENCRYPTION_KEY="invalid-for-config-only",
    )

    assert config.UATConfig().DEBUG is False
    assert config.UATConfig().TESTING is False
    assert config.UATConfig().SESSION_COOKIE_SECURE is True


def test_production_environment_uses_production_config(monkeypatch):
    config = load_config(
        monkeypatch,
        "production",
        DATABASE_URL="postgresql://prod-host/tedile_prod",
        SECRET_KEY="prod-secret",
        ENCRYPTION_KEY="invalid-for-config-only",
        OTP_DELIVERY_PROVIDER="msg91",
        OTP_REQUIRED="true",
    )

    assert config.ProductionConfig().DEBUG is False


@pytest.mark.parametrize(
    "values, message",
    [
        ({"OTP_REQUIRED": "false", "OTP_DELIVERY_PROVIDER": "msg91"}, "OTP_REQUIRED"),
        ({"OTP_REQUIRED": "true", "OTP_DELIVERY_PROVIDER": "console"}, "console"),
    ],
)
def test_production_rejects_unsafe_otp_configuration(monkeypatch, values, message):
    config = load_config(
        monkeypatch,
        "production",
        DATABASE_URL="postgresql://prod-host/tedile_prod",
        SECRET_KEY="prod-secret",
        ENCRYPTION_KEY="invalid-for-config-only",
        **values,
    )
    with pytest.raises(RuntimeError, match=message):
        config.ProductionConfig()


def test_unknown_environment_fails_clearly(monkeypatch):
    monkeypatch.setenv("APP_ENV", "unknown")

    from app import create_app

    with pytest.raises(RuntimeError, match="Unsupported APP_ENV"):
        create_app()


@pytest.mark.parametrize("app_env", ["uat", "production"])
def test_deployed_environment_requires_database_url(monkeypatch, app_env):
    config = load_config(
        monkeypatch,
        app_env,
        SECRET_KEY="secret",
        ENCRYPTION_KEY="key",
    )
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        (config.UATConfig() if app_env == "uat" else config.ProductionConfig())


@pytest.mark.parametrize("app_env", ["uat", "production"])
def test_deployed_environment_rejects_sqlite(monkeypatch, app_env):
    config = load_config(
        monkeypatch,
        app_env,
        DATABASE_URL="sqlite:///unsafe.db",
        SECRET_KEY="secret",
        ENCRYPTION_KEY="key",
    )
    with pytest.raises(RuntimeError, match="SQLite is not allowed"):
        (config.UATConfig() if app_env == "uat" else config.ProductionConfig())
