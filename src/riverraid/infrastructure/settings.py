import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    env: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_ttl_seconds: int
    database_url: str


def load_settings() -> Settings:
    return Settings(
        env=os.getenv("APP_ENV", "dev"),
        jwt_secret=os.getenv("JWT_SECRET", "dev-secret-at-least-32-characters-long"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_ttl_seconds=int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "3600")),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://riverraid:riverraid@localhost:5432/riverraid",
        ),
    )
