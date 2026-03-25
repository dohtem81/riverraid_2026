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
        self.started_calls: list[dict] = []
        self.finished_calls: list[dict] = []

    async def create_game_started(self, **kwargs) -> None:
        self.started_calls.append(kwargs)

    async def update_game_finished(self, **kwargs) -> None:
        self.finished_calls.append(kwargs)


class _FakeScoresRepo:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.last_limit: int | None = None

    async def fetch_top_scores(self, limit: int = 10) -> list[dict]:
        self.last_limit = limit
        return self.rows[:limit]

    async def fetch_all_games(self) -> list[dict]:
        return self.rows


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

        sid_low = "game-roundtrip-low"
        await repo.create_game_started(
            session_id=sid_low,
            pilot_name="pilot_low",
            started_at=now - timedelta(minutes=5),
        )
        await repo.update_game_finished(
            session_id=sid_low,
            score=100,
            level=2,
            finished_at=now - timedelta(minutes=4),
        )

        sid_high = "game-roundtrip-high"
        await repo.create_game_started(
            session_id=sid_high,
            pilot_name="pilot_high",
            started_at=now - timedelta(minutes=3),
        )
        await repo.update_game_finished(
            session_id=sid_high,
            score=999,
            level=8,
            finished_at=now - timedelta(minutes=2),
        )

        sid_mid = "game-roundtrip-mid"
        await repo.create_game_started(
            session_id=sid_mid,
            pilot_name="pilot_mid",
            started_at=now - timedelta(minutes=1),
        )
        await repo.update_game_finished(
            session_id=sid_mid,
            score=500,
            level=5,
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


def test_scores_router_all_games_returns_full_rows():
    expected = [
        {
            "id": "row-1",
            "pilot_name": "ace",
            "score": 1200,
            "level": 7,
            "started_at": "2026-03-17T09:57:00+00:00",
            "finished_at": "2026-03-17T10:00:00+00:00",
        },
        {
            "id": "row-2",
            "pilot_name": "rookie",
            "score": 400,
            "level": 3,
            "started_at": "2026-03-17T09:50:00+00:00",
            "finished_at": None,
        },
    ]
    fake_repo = _FakeScoresRepo(expected)
    app = FastAPI()
    app.include_router(build_scores_router(fake_repo))

    with TestClient(app) as client:
        response = client.get("/api/v1/games")

    assert response.status_code == 200
    assert response.json() == expected


def test_game_result_repository_roundtrip_returns_sorted_top_scores():
    rows = asyncio.run(_repo_roundtrip())

    assert len(rows) == 2
    assert rows[0]["pilot_name"] == "pilot_high"
    assert rows[0]["score"] == 999
    assert rows[1]["pilot_name"] == "pilot_mid"
    assert rows[1]["score"] == 500


def test_gateway_persist_game_started_records_pilot_and_session():
    repo = _RecordingRepo()
    gateway = WebSocketGateway(validate_join_token=_DummyValidateJoinToken(), game_result_repo=repo)
    started_at = datetime.now(UTC)
    player = AuthenticatedPlayer(player_id="p1", username="ace")
    game_id = "game-abc123"

    asyncio.run(gateway._persist_game_started(player, game_id, started_at))

    assert len(repo.started_calls) == 1
    call = repo.started_calls[0]
    assert call["session_id"] == game_id
    assert call["pilot_name"] == "ace"
    assert call["started_at"] == started_at


def test_gateway_persist_game_started_noop_without_player_or_game_id():
    repo = _RecordingRepo()
    gateway = WebSocketGateway(validate_join_token=_DummyValidateJoinToken(), game_result_repo=repo)
    player = AuthenticatedPlayer(player_id="p1", username="ace")
    started_at = datetime.now(UTC)

    asyncio.run(gateway._persist_game_started(None, "game-x", started_at))
    asyncio.run(gateway._persist_game_started(player, None, started_at))
    asyncio.run(gateway._persist_game_started(player, "game-x", None))

    assert repo.started_calls == []


def test_gateway_persist_game_over_saves_score_level_and_game_id():
    repo = _RecordingRepo()
    gateway = WebSocketGateway(validate_join_token=_DummyValidateJoinToken(), game_result_repo=repo)
    started_at = datetime.now(UTC) - timedelta(minutes=2)
    state = SessionState(
        plane_state=Plane(x=0, y=0, vx=0, vy=0, fuel=0, hp=0, score=345),
        level=4,
    )
    player = AuthenticatedPlayer(player_id="p1", username="ace")
    game_id = "game-finish-01"

    asyncio.run(gateway._persist_game_over(player, state, started_at, game_id))

    assert len(repo.finished_calls) == 1
    call = repo.finished_calls[0]
    assert call["session_id"] == game_id
    assert call["score"] == 345
    assert call["level"] == 4
    assert isinstance(call["finished_at"], datetime)


def test_gateway_persist_game_over_noop_without_player_start_or_game_id():
    repo = _RecordingRepo()
    gateway = WebSocketGateway(validate_join_token=_DummyValidateJoinToken(), game_result_repo=repo)
    state = SessionState(plane_state=Plane(x=0, y=0, vx=0, vy=0, fuel=0, hp=0, score=100), level=2)
    player = AuthenticatedPlayer(player_id="p1", username="ace")
    started_at = datetime.now(UTC)

    asyncio.run(gateway._persist_game_over(None, state, started_at, "game-x"))
    asyncio.run(gateway._persist_game_over(player, state, None, "game-x"))
    asyncio.run(gateway._persist_game_over(player, state, started_at, None))

    assert repo.finished_calls == []
