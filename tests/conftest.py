import os

import pytest
from fastapi.testclient import TestClient

from riverraid.main import create_app


@pytest.fixture(autouse=True)
def _phase0_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("JWT_SECRET", "test-secret-at-least-32-characters-long")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_TTL_SECONDS", "3600")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://riverraid:riverraid@db:5432/riverraid",
    )
    yield


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
