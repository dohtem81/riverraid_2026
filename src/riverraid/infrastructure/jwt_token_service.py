from datetime import UTC, datetime, timedelta

import jwt

from riverraid.domain.models import AuthenticatedPlayer
from riverraid.infrastructure.settings import Settings


class TokenValidationError(Exception):
    pass


class JwtTokenService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def issue_access_token(self, player: AuthenticatedPlayer) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": player.player_id,
            "username": player.username,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self._settings.access_token_ttl_seconds)).timestamp()),
        }
        return jwt.encode(payload, self._settings.jwt_secret, algorithm=self._settings.jwt_algorithm)

    def validate_access_token(self, token: str) -> AuthenticatedPlayer:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
            )
        except jwt.PyJWTError as exc:
            raise TokenValidationError("invalid_token") from exc

        sub = payload.get("sub")
        username = payload.get("username")
        if not sub or not username:
            raise TokenValidationError("invalid_token_claims")

        return AuthenticatedPlayer(player_id=str(sub), username=str(username))
