from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# Declarative base – import this in model files to register mapped classes
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Engine / session factory (initialised at app startup via setup_engine)
# ---------------------------------------------------------------------------

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def setup_engine(database_url: str) -> None:
    """Create the async engine and session factory from *database_url*."""
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables that are registered on *Base.metadata*."""
    if _engine is None:
        raise RuntimeError("Call setup_engine() before init_db()")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def migrate_db() -> None:
    """Apply any missing schema changes to existing tables.

    This is a lightweight alternative to Alembic for the small number of
    structural changes this project needs.  It is idempotent – safe to run on
    every startup whether the DB is fresh or already has data.

    Current migrations handled:
      1. ``game_results.session_id``  – add column + unique index if absent.
      2. ``game_results.finished_at`` – drop NOT NULL constraint if still set.
    """
    if _engine is None:
        raise RuntimeError("Call setup_engine() before migrate_db()")

    async with _engine.begin() as conn:
        # Read the real column list from the live DB (sync API via run_sync).
        def _get_columns(sync_conn):
            insp = inspect(sync_conn)
            if "game_results" not in insp.get_table_names():
                return None  # fresh DB – create_all already handled it
            return {col["name"]: col for col in insp.get_columns("game_results")}

        columns = await conn.run_sync(_get_columns)
        if columns is None:
            return  # table does not exist yet; create_all will create it

        # 1. Add session_id column if missing.
        if "session_id" not in columns:
            await conn.execute(
                text("ALTER TABLE game_results ADD COLUMN session_id VARCHAR(36)")
            )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_game_results_session_id "
                    "ON game_results (session_id)"
                )
            )

        # 2. Drop NOT NULL from finished_at if the column is still non-nullable.
        if "finished_at" in columns and not columns["finished_at"].get("nullable", True):
            await conn.execute(
                text("ALTER TABLE game_results ALTER COLUMN finished_at DROP NOT NULL")
            )


async def dispose_engine() -> None:
    """Cleanly close all pooled connections."""
    if _engine is not None:
        await _engine.dispose()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session; commit on success, rollback on error."""
    if _session_factory is None:
        raise RuntimeError("Database not initialised")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
