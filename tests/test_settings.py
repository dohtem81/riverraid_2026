import pytest

from riverraid.infrastructure.settings import load_settings


def test_load_settings_dev_uses_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = load_settings()

    assert settings.env == "dev"
    assert settings.jwt_secret == "dev-secret-at-least-32-characters-long"
    assert settings.database_url == "postgresql+asyncpg://riverraid:riverraid@localhost:5432/riverraid"


def test_load_settings_prod_requires_jwt_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/app")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        load_settings()


def test_load_settings_prod_requires_database_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "super-secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        load_settings()


def test_load_settings_prod_uses_provided_values(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("JWT_SECRET", "super-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/app")

    settings = load_settings()

    assert settings.env == "prod"
    assert settings.jwt_secret == "super-secret"
    assert settings.database_url == "postgresql+asyncpg://u:p@db:5432/app"
