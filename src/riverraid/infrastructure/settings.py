import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    env: str
    auth_username: str
    auth_password: str
    auth_player_id: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_ttl_seconds: int


def load_settings() -> Settings:
    return Settings(
        env=os.getenv("APP_ENV", "dev"),
        auth_username=os.getenv("AUTH_USERNAME", "pilot"),
        auth_password=os.getenv("AUTH_PASSWORD", "pilot1234"),
        auth_player_id=os.getenv("AUTH_PLAYER_ID", "11111111-1111-1111-1111-111111111111"),
        jwt_secret=os.getenv("JWT_SECRET", "dev-secret-at-least-32-characters-long"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_ttl_seconds=int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "3600")),
    )
