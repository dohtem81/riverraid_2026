import asyncio
import os
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from riverraid.application.session_entities import Plane
from riverraid.application.session_runtime import SessionState
from riverraid.domain.models import AuthenticatedPlayer
from riverraid.infrastructure import database
from riverraid.infrastructure.database import dispose_engine, init_db, setup_engine
from riverraid.infrastructure.game_result_repository import GameResultRepository
import riverraid.infrastructure.models  # noqa: F401
from riverraid.interfaces.http.routes import build_scores_router
from riverraid.interfaces.ws.gateway import WebSocketGateway


class _DummyValidateJoinToken:
    def execute(self, _token: str) -> AuthenticatedPlayer:
        return AuthenticatedPlayer(player_id="dummy", username="dummy")


class _RecordingRepo:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def save(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _FakeScoresRepo:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.last_limit: int | None = None

    async def fetch_top_scores(self, limit: int = 10) -> list[dict]:
        self.last_limit = limit
        return self.rows[:limit]


async def _repo_roundtrip() -> list[dict]:
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://riverraid:riverraid@db:5432/riverraid")
    setup_engine(db_url)
    await init_db()
    try:
        session_factory = database._session_factory
        if session_factory is None:
            raise RuntimeError("Database not initialized")

        async with session_factory() as session:
            await session.execute(text("DELETE FROM game_results"))
            await session.commit()

        repo = GameResultRepository()
        now = datetime.now(UTC)
        await repo.save(
            pilot_name="pilot_low",
            score=100,
            level=2,
            started_at=now - timedelta(minutes=5),
            finished_at=now - timedelta(minutes=4),
        )
        await repo.save(
            pilot_name="pilot_high",
            score=999,
            level=8,
            started_at=now - timedelta(minutes=3),
            finished_at=now - timedelta(minutes=2),
        )
        await repo.save(
            pilot_name="pilot_mid",
            score=500,
            level=5,
            started_at=now - timedelta(minutes=1),
            finished_at=now,
        )

        return await repo.fetch_top_scores(limit=2)
    finally:
        await dispose_engine()


def test_scores_router_returns_repo_payload_and_uses_limit_10():
    expected = [
        {"pilot_name": "ace", "score": 1200, "level": 7, "finished_at": "2026-03-17T10:00:00+00:00"},
        {"pilot_name": "rookie", "score": 400, "level": 3, "finished_at": "2026-03-17T09:55:00+00:00"},
    ]
    fake_repo = _FakeScoresRepo(expected)
    app = FastAPI()
    app.include_router(build_scores_router(fake_repo))

    with TestClient(app) as client:
        response = client.get("/api/v1/scores")

    assert response.status_code == 200
    assert response.json() == expected
    assert fake_repo.last_limit == 10


def test_game_result_repository_roundtrip_returns_sorted_top_scores():
    rows = asyncio.run(_repo_roundtrip())

    assert len(rows) == 2
    assert rows[0]["pilot_name"] == "pilot_high"
    assert rows[0]["score"] == 999
    assert rows[1]["pilot_name"] == "pilot_mid"
    assert rows[1]["score"] == 500


def test_gateway_persist_game_over_saves_score_level_and_name():
    repo = _RecordingRepo()
    gateway = WebSocketGateway(validate_join_token=_DummyValidateJoinToken(), game_result_repo=repo)
    started_at = datetime.now(UTC) - timedelta(minutes=2)
    state = SessionState(
        plane_state=Plane(x=0, y=0, vx=0, vy=0, fuel=0, hp=0, score=345),
        level=4,
    )
    player = AuthenticatedPlayer(player_id="p1", username="ace")

    asyncio.run(gateway._persist_game_over(player, state, started_at))

    assert len(repo.calls) == 1
    call = repo.calls[0]
    assert call["pilot_name"] == "ace"
    assert call["score"] == 345
    assert call["level"] == 4
    assert call["started_at"] == started_at
    assert isinstance(call["finished_at"], datetime)


def test_gateway_persist_game_over_noop_without_player_or_start():
    repo = _RecordingRepo()
    gateway = WebSocketGateway(validate_join_token=_DummyValidateJoinToken(), game_result_repo=repo)
    state = SessionState(plane_state=Plane(x=0, y=0, vx=0, vy=0, fuel=0, hp=0, score=100), level=2)

    asyncio.run(gateway._persist_game_over(None, state, datetime.now(UTC)))
    asyncio.run(gateway._persist_game_over(AuthenticatedPlayer(player_id="p1", username="ace"), state, None))

    assert repo.calls == []
