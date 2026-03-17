import pytest

from riverraid.domain.models import AuthenticatedPlayer
from riverraid.infrastructure.jwt_token_service import JwtTokenService, TokenValidationError
from riverraid.infrastructure.settings import Settings


def _settings() -> Settings:
    return Settings(
        env="dev",
        jwt_secret="test-secret-at-least-32-characters-long",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=3600,
        database_url="postgresql+asyncpg://riverraid:riverraid@db:5432/riverraid",
    )


def test_issue_and_validate_token_round_trip():
    service = JwtTokenService(_settings())
    token = service.issue_access_token(AuthenticatedPlayer(player_id="11111111-1111-1111-1111-111111111111", username="pilot"))

    player = service.validate_access_token(token)
    assert player.player_id == "11111111-1111-1111-1111-111111111111"
    assert player.username == "pilot"


def test_validate_invalid_token_raises():
    service = JwtTokenService(_settings())

    with pytest.raises(TokenValidationError):
        service.validate_access_token("not-a-valid-token")
