from dataclasses import dataclass

from riverraid.application.ports import CredentialProviderPort, TokenServicePort
from riverraid.domain.models import AuthenticatedPlayer


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    token_type: str
    expires_in: int
    player_id: str


class LoginWithConfiguredCredentials:
    def __init__(self, credential_provider: CredentialProviderPort, token_service: TokenServicePort, token_ttl_seconds: int) -> None:
        self._credential_provider = credential_provider
        self._token_service = token_service
        self._token_ttl_seconds = token_ttl_seconds

    def execute(self, username: str) -> LoginResult | None:
        player = self._credential_provider.validate(username=username)
        if player is None:
            return None

        token = self._token_service.issue_access_token(player)
        return LoginResult(
            access_token=token,
            token_type="Bearer",
            expires_in=self._token_ttl_seconds,
            player_id=player.player_id,
        )


class ValidateJoinToken:
    def __init__(self, token_service: TokenServicePort) -> None:
        self._token_service = token_service

    def execute(self, token: str) -> AuthenticatedPlayer:
        return self._token_service.validate_access_token(token)
