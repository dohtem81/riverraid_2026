import os

import pytest
from fastapi.testclient import TestClient

from riverraid.main import create_app


@pytest.fixture(autouse=True)
def _phase0_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("AUTH_USERNAME", "pilot")
    monkeypatch.setenv("AUTH_PASSWORD", "pilot1234")
    monkeypatch.setenv("AUTH_PLAYER_ID", "11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_TTL_SECONDS", "3600")
    yield


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
