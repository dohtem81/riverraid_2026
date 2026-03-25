"""Async repository for persisting game results."""

import uuid
from datetime import datetime

from sqlalchemy import select, update

from riverraid.infrastructure import database
from riverraid.infrastructure.models import GameResult


class GameResultRepository:
    """Concrete SQLAlchemy implementation of the game-result persistence port."""

    async def create_game_started(
        self,
        *,
        session_id: str,
        pilot_name: str,
        started_at: datetime,
    ) -> None:
        """Insert a new :class:`GameResult` row when a game begins (score/level/finished_at filled in later)."""
        session_factory = database._session_factory
        if session_factory is None:
            raise RuntimeError("Database not initialised – call setup_engine() first")

        async with session_factory() as session:
            result = GameResult(
                id=str(uuid.uuid4()),
                session_id=session_id,
                pilot_name=pilot_name,
                score=0,
                level=1,
                started_at=started_at,
                finished_at=None,
            )
            session.add(result)
            await session.commit()

    async def update_game_finished(
        self,
        *,
        session_id: str,
        score: int,
        level: int,
        finished_at: datetime,
    ) -> None:
        """Update the row for *session_id* with final score, level, and finish timestamp."""
        session_factory = database._session_factory
        if session_factory is None:
            raise RuntimeError("Database not initialised – call setup_engine() first")

        async with session_factory() as session:
            await session.execute(
                update(GameResult)
                .where(GameResult.session_id == session_id)
                .values(score=score, level=level, finished_at=finished_at)
            )
            await session.commit()

    async def fetch_top_scores(self, limit: int = 10) -> list[dict]:
        """Return the top *limit* finished-game scores ordered by score descending."""
        session_factory = database._session_factory
        if session_factory is None:
            raise RuntimeError("Database not initialised – call setup_engine() first")

        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(GameResult)
                    .where(GameResult.finished_at.isnot(None))
                    .order_by(GameResult.score.desc())
                    .limit(limit)
                )
            ).scalars().all()
            return [
                {
                    "pilot_name": r.pilot_name,
                    "score": r.score,
                    "level": r.level,
                    "finished_at": r.finished_at.isoformat(),
                }
                for r in rows
            ]

    async def fetch_all_games(self) -> list[dict]:
        """Return all game records (including in-progress) ordered by start time descending."""
        session_factory = database._session_factory
        if session_factory is None:
            raise RuntimeError("Database not initialised – call setup_engine() first")

        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(GameResult)
                    .order_by(GameResult.started_at.desc())
                )
            ).scalars().all()
            return [
                {
                    "id": r.id,
                    "pilot_name": r.pilot_name,
                    "score": r.score,
                    "level": r.level,
                    "started_at": r.started_at.isoformat(),
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                }
                for r in rows
            ]
