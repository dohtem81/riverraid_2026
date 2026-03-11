import hmac

from riverraid.domain.models import AuthenticatedPlayer
from riverraid.infrastructure.settings import Settings


class ConfigCredentialProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def validate(self, username: str, password: str) -> AuthenticatedPlayer | None:
        is_username_valid = hmac.compare_digest(username, self._settings.auth_username)
        is_password_valid = hmac.compare_digest(password, self._settings.auth_password)
        if not (is_username_valid and is_password_valid):
            return None

        return AuthenticatedPlayer(player_id=self._settings.auth_player_id, username=self._settings.auth_username)
