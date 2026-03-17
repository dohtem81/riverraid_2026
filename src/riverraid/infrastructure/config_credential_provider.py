from uuid import NAMESPACE_URL, uuid5

from riverraid.domain.models import AuthenticatedPlayer
from riverraid.infrastructure.settings import Settings


class ConfigCredentialProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @staticmethod
    def _player_id_for(username: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"riverraid://player/{username}"))

    def validate(self, username: str) -> AuthenticatedPlayer | None:
        normalized_username = username.strip()
        if not normalized_username:
            return None

        return AuthenticatedPlayer(
            player_id=self._player_id_for(normalized_username),
            username=normalized_username,
        )
