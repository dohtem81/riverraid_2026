"""SQLAlchemy ORM models.

Import ``Base`` from :mod:`riverraid.infrastructure.database` in each model file
so that ``Base.metadata.create_all`` picks them up automatically.
Make sure this module is imported before ``init_db()`` is called so that the
metadata is populated.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from riverraid.infrastructure.database import Base


class GameResult(Base):
    """Persisted record of a finished game session."""

    __tablename__ = "game_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    pilot_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<GameResult pilot={self.pilot_name!r} score={self.score} "
            f"level={self.level} finished_at={self.finished_at}>"
        )
