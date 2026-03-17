from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse

from riverraid.application.session_runtime import SessionRuntime
from riverraid.application.use_cases import LoginWithConfiguredCredentials, ValidateJoinToken
from riverraid.infrastructure.database import dispose_engine, init_db, setup_engine
from riverraid.infrastructure.game_config import load_game_config
from riverraid.infrastructure.game_result_repository import GameResultRepository
import riverraid.infrastructure.models  # noqa: F401 – registers ORM models with Base.metadata
from riverraid.infrastructure.config_credential_provider import ConfigCredentialProvider
from riverraid.infrastructure.jwt_token_service import JwtTokenService
from riverraid.infrastructure.settings import load_settings
from riverraid.interfaces.http.demo_page import INDEX_HTML
from riverraid.interfaces.http.routes import build_auth_router, build_scores_router
from riverraid.interfaces.ws.gateway import WebSocketGateway


def create_app() -> FastAPI:
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        setup_engine(settings.database_url)
        await init_db()
        yield
        await dispose_engine()

    credential_provider = ConfigCredentialProvider(settings)
    token_service = JwtTokenService(settings)

    login_use_case = LoginWithConfiguredCredentials(
        credential_provider=credential_provider,
        token_service=token_service,
        token_ttl_seconds=settings.access_token_ttl_seconds,
    )
    validate_join = ValidateJoinToken(token_service=token_service)
    game_cfg = load_game_config()
    runtime = SessionRuntime(cfg=game_cfg)
    game_result_repo = GameResultRepository()
    ws_gateway = WebSocketGateway(
        validate_join_token=validate_join,
        runtime=runtime,
        game_result_repo=game_result_repo,
    )

    app = FastAPI(title="RiverRaid Backend", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(Exception)
    async def catch_unhandled(_request, exc: Exception):
        if isinstance(exc, RuntimeError):
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": str(exc),
                    }
                },
            )
        raise exc

    app.include_router(build_auth_router(login_use_case))
    app.include_router(build_scores_router(game_result_repo))

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return INDEX_HTML

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "mode": "phase0-config-auth"}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await ws_gateway.handle(websocket)

    return app


app = create_app()
