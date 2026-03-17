import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    env: str
    jwt_secret: str
    jwt_algorithm: str
    access_token_ttl_seconds: int
    database_url: str


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _normalize_database_url(database_url: str) -> str:
    normalized = database_url.strip()
    if normalized.startswith("postgresql+asyncpg://"):
        return normalized
    if normalized.startswith("postgresql://"):
        return normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
    if normalized.startswith("postgres://"):
        return normalized.replace("postgres://", "postgresql+asyncpg://", 1)
    return normalized


def load_settings() -> Settings:
    env = os.getenv("APP_ENV", "dev")
    is_prod = env.lower() == "prod"

    jwt_secret = _get_required_env("JWT_SECRET") if is_prod else os.getenv(
        "JWT_SECRET", "dev-secret-at-least-32-characters-long"
    )
    database_url = _get_required_env("DATABASE_URL") if is_prod else os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://riverraid:riverraid@localhost:5432/riverraid",
    )
    database_url = _normalize_database_url(database_url)

    return Settings(
        env=env,
        jwt_secret=jwt_secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_ttl_seconds=int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "3600")),
        database_url=database_url,
    )
