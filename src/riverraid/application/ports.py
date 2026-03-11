from typing import Protocol

from riverraid.domain.models import AuthenticatedPlayer


class CredentialProviderPort(Protocol):
    def validate(self, username: str, password: str) -> AuthenticatedPlayer | None:
        ...


class TokenServicePort(Protocol):
    def issue_access_token(self, player: AuthenticatedPlayer) -> str:
        ...

    def validate_access_token(self, token: str) -> AuthenticatedPlayer:
        ...
