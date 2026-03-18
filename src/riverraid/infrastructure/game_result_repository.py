"""Async repository for persisting game results."""

import uuid
from datetime import datetime

from sqlalchemy import select

from riverraid.infrastructure import database
from riverraid.infrastructure.models import GameResult


class GameResultRepository:
    """Concrete SQLAlchemy implementation of the game-result persistence port."""

    async def save(
        self,
        *,
        pilot_name: str,
        score: int,
        level: int,
        started_at: datetime,
        finished_at: datetime,
    ) -> None:
        """Insert a new :class:`GameResult` row in its own short-lived session."""
        session_factory = database._session_factory
        if session_factory is None:
            raise RuntimeError("Database not initialised – call setup_engine() first")

        async with session_factory() as session:
            result = GameResult(
                id=str(uuid.uuid4()),
                pilot_name=pilot_name,
                score=score,
                level=level,
                started_at=started_at,
                finished_at=finished_at,
            )
            session.add(result)
            await session.commit()

    async def fetch_top_scores(self, limit: int = 10) -> list[dict]:
        """Return the top *limit* scores ordered by score descending."""
        session_factory = database._session_factory
        if session_factory is None:
            raise RuntimeError("Database not initialised – call setup_engine() first")

        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(GameResult)
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
        """Return all recorded games ordered by finish time descending."""
        session_factory = database._session_factory
        if session_factory is None:
            raise RuntimeError("Database not initialised – call setup_engine() first")

        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(GameResult)
                    .order_by(GameResult.finished_at.desc())
                )
            ).scalars().all()
            return [
                {
                    "id": r.id,
                    "pilot_name": r.pilot_name,
                    "score": r.score,
                    "level": r.level,
                    "started_at": r.started_at.isoformat(),
                    "finished_at": r.finished_at.isoformat(),
                }
                for r in rows
            ]
