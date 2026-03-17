from datetime import datetime
from typing import Protocol

from riverraid.domain.models import AuthenticatedPlayer


class CredentialProviderPort(Protocol):
    def validate(self, username: str) -> AuthenticatedPlayer | None:
        ...


class TokenServicePort(Protocol):
    def issue_access_token(self, player: AuthenticatedPlayer) -> str:
        ...

    def validate_access_token(self, token: str) -> AuthenticatedPlayer:
        ...


class GameResultRepositoryPort(Protocol):
    async def save(
        self,
        *,
        pilot_name: str,
        score: int,
        level: int,
        started_at: datetime,
        finished_at: datetime,
    ) -> None:
        ...

    async def fetch_top_scores(self, limit: int = 10) -> list[dict]:
        """Return the top *limit* scores ordered by score descending."""
        ...
