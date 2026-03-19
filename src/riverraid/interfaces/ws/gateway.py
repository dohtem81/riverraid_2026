import asyncio
from datetime import UTC, datetime
import time
from uuid import uuid4

from fastapi import WebSocket

from riverraid.application.ports import GameResultRepositoryPort
from riverraid.application.session_runtime import SessionRuntime, SessionState as _SessionState
from riverraid.application.use_cases import ValidateJoinToken
from riverraid.domain.models import AuthenticatedPlayer
from riverraid.infrastructure.game_config import GameConfig
from riverraid.infrastructure.jwt_token_service import TokenValidationError


class WebSocketGateway:
    def __init__(
        self,
        validate_join_token: ValidateJoinToken,
        cfg: GameConfig | None = None,
        runtime: SessionRuntime | None = None,
        game_result_repo: GameResultRepositoryPort | None = None,
    ) -> None:
        self._validate_join_token = validate_join_token
        self._runtime = runtime or SessionRuntime(cfg=cfg)
        self._cfg = self._runtime.cfg
        self._game_result_repo = game_result_repo

    def __getattr__(self, name: str):
        cfg_name = name.lstrip("_")
        try:
            cfg = object.__getattribute__(self, "_cfg")
            return getattr(cfg, cfg_name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute {name!r}") from None

    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        session_id = f"sess_{uuid4().hex[:10]}"
        joined = False
        game_over = False
        server_seq = 2
        g = self._runtime.new_state()
        last_update_time = time.monotonic()
        current_player: AuthenticatedPlayer | None = None
        game_started_at: datetime | None = None

        try:
            while True:
                current_time = time.monotonic()
                elapsed = current_time - last_update_time
                if joined and g.plane_state and elapsed > 0 and not game_over:
                    world_event, game_over = self._runtime.process_elapsed(g=g, elapsed=elapsed)
                    if world_event is not None:
                        server_seq += 1
                        await self._emit_event(websocket, session_id, server_seq, world_event)
                        if game_over:
                            await self._persist_game_over(current_player, g, game_started_at)
                            server_seq += 1
                            await self._emit_game_over(websocket, session_id, server_seq)
                        else:
                            server_seq += 1
                            await self._emit_snapshot(websocket, session_id, server_seq, g)
                last_update_time = current_time

                try:
                    message = await asyncio.wait_for(websocket.receive_json(), timeout=self._tick_interval_seconds)
                except asyncio.TimeoutError:
                    if joined and g.plane_state and not game_over:
                        g.tick += 1
                        server_seq += 1
                        await self._emit_snapshot(websocket, session_id, server_seq, g)
                    continue

                msg_type = message.get("type")
                seq = message.get("seq", 0)

                if msg_type == "join":
                    token = (message.get("payload") or {}).get("access_token")
                    if not token:
                        await websocket.send_json(
                            self._error_payload(seq=seq, code="UNAUTHORIZED", message="Missing access token")
                        )
                        continue
                    try:
                        player = self._validate_join_token.execute(token)
                    except TokenValidationError:
                        await websocket.send_json(
                            self._error_payload(seq=seq, code="UNAUTHORIZED", message="Invalid access token")
                        )
                        continue
                    joined = True
                    game_over = False
                    current_player = player
                    game_started_at = datetime.now(UTC)
                    self._runtime.reset_for_new_game(g)
                    server_seq = 1
                    await websocket.send_json(
                        {
                            "type": "join_ack",
                            "ts": self._now_ms(),
                            "session_id": session_id,
                            "seq": server_seq,
                            "payload": self._runtime.join_ack_payload(player.player_id),
                        }
                    )
                    server_seq += 1
                    await self._emit_snapshot(websocket, session_id, server_seq, g)
                    continue

                if msg_type == "restart":
                    if not joined:
                        await websocket.send_json(
                            self._error_payload(seq=seq, code="UNAUTHORIZED", message="Join required before restart")
                        )
                        continue
                    game_over = False
                    game_started_at = datetime.now(UTC)
                    self._runtime.reset_for_new_game(g)
                    server_seq += 1
                    await self._emit_event(
                        websocket,
                        session_id,
                        server_seq,
                        {"event_type": "game_restarted", "data": {"lives": g.plane_state.hp}},
                    )
                    server_seq += 1
                    await self._emit_snapshot(websocket, session_id, server_seq, g)
                    continue

                if msg_type == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "ts": self._now_ms(),
                            "session_id": session_id,
                            "seq": seq,
                            "payload": {"nonce": (message.get("payload") or {}).get("nonce")},
                        }
                    )
                    continue

                if msg_type == "input":
                    if not joined:
                        await websocket.send_json(
                            self._error_payload(seq=seq, code="UNAUTHORIZED", message="Join required before input")
                        )
                        continue
                    if game_over:
                        await websocket.send_json(
                            self._error_payload(seq=seq, code="GAME_OVER", message="Game over. Send restart command.")
                        )
                        continue
                    payload = message.get("payload") or {}
                    validation_error = self._runtime._validate_input_payload(payload)
                    if validation_error is not None:
                        await websocket.send_json(
                            self._error_payload(seq=seq, code="INVALID_INPUT", message=validation_error)
                        )
                        continue
                    normalized_input = self._runtime._normalize_input_payload(payload=payload, fallback_input_seq=seq)
                    if not g.plane_state:
                        await websocket.send_json(
                            self._error_payload(
                                seq=seq,
                                code="INTERNAL_STATE",
                                message="Plane state is not initialized",
                            )
                        )
                        continue

                    input_event, collision_event, game_over = self._runtime.process_input(
                        g=g,
                        normalized_input=normalized_input,
                    )
                    await self._emit_event(websocket, session_id, seq, input_event)
                    if collision_event is not None:
                        server_seq += 1
                        await self._emit_event(websocket, session_id, server_seq, collision_event)
                        if game_over:
                            await self._persist_game_over(current_player, g, game_started_at)
                            server_seq += 1
                            await self._emit_game_over(websocket, session_id, server_seq)
                    server_seq += 1
                    await self._emit_snapshot(websocket, session_id, server_seq, g)
                    continue

                if msg_type in {"keydown", "keyup"}:
                    if not joined:
                        await websocket.send_json(
                            self._error_payload(seq=seq, code="UNAUTHORIZED", message="Join required before input")
                        )
                        continue
                    if game_over:
                        await websocket.send_json(
                            self._error_payload(seq=seq, code="GAME_OVER", message="Game over. Send restart command.")
                        )
                        continue
                    payload = message.get("payload") or {}
                    validation_error = self._runtime._validate_key_payload(payload)
                    if validation_error is not None:
                        await websocket.send_json(
                            self._error_payload(seq=seq, code="INVALID_INPUT", message=validation_error)
                        )
                        continue

                    normalized_key_payload = self._runtime._normalize_key_payload(payload)
                    normalized_input = self._runtime.process_key_event(
                        g=g,
                        event_type=msg_type,
                        normalized_payload=normalized_key_payload,
                    )
                    normalized_input["input_seq"] = max(0, int(seq))

                    collision_event = None
                    if normalized_input["fire"]:
                        input_event, collision_event, game_over = self._runtime.process_input(
                            g=g,
                            normalized_input=normalized_input,
                        )
                    else:
                        g.last_processed_input_seq = max(g.last_processed_input_seq, normalized_input["input_seq"])
                        input_event = {
                            "event_type": "input_accepted",
                            "data": {
                                "input_seq": normalized_input["input_seq"],
                                "turn": None,
                                "fast": False,
                                "fire": False,
                                "key_event": msg_type,
                                "key": normalized_key_payload["key"],
                            },
                        }

                    await self._emit_event(websocket, session_id, seq, input_event)
                    if collision_event is not None:
                        server_seq += 1
                        await self._emit_event(websocket, session_id, server_seq, collision_event)
                        if game_over:
                            await self._persist_game_over(current_player, g, game_started_at)
                            server_seq += 1
                            await self._emit_game_over(websocket, session_id, server_seq)
                    server_seq += 1
                    await self._emit_snapshot(websocket, session_id, server_seq, g)
                    continue

                await websocket.send_json(
                    self._error_payload(seq=seq, code="INVALID_TYPE", message="Unknown message type")
                )
        except Exception:
            await websocket.close()

    async def _emit_event(self, websocket: WebSocket, session_id: str, seq: int, payload: dict) -> None:
        await websocket.send_json(
            {"type": "event", "ts": self._now_ms(), "session_id": session_id, "seq": seq, "payload": payload}
        )

    async def _emit_snapshot(self, websocket: WebSocket, session_id: str, seq: int, g: _SessionState) -> None:
        await websocket.send_json(
            {
                "type": "snapshot",
                "ts": self._now_ms(),
                "session_id": session_id,
                "seq": seq,
                "payload": self._runtime.snapshot_for_state(g),
            }
        )

    async def _persist_game_over(
        self,
        player: AuthenticatedPlayer | None,
        g: _SessionState,
        started_at: datetime | None,
    ) -> None:
        """Save the finished game to persistent storage if a repository is wired."""
        if self._game_result_repo is None or player is None or started_at is None:
            return
        score = g.plane_state.score if g.plane_state else 0
        level = g.level
        try:
            await self._game_result_repo.save(
                pilot_name=player.username,
                score=score,
                level=level,
                started_at=started_at,
                finished_at=datetime.now(UTC),
            )
        except Exception:  # pragma: no cover – never crash the game loop
            pass

    async def _emit_game_over(self, websocket: WebSocket, session_id: str, seq: int) -> None:
        await self._emit_event(websocket, session_id, seq, {"event_type": "game_over", "data": {"reason": "no_lives"}})

    def _advance_world(self, g: _SessionState, elapsed: float) -> None:
        self._runtime._advance_world(g, elapsed)

    def _reset_world(self, g: _SessionState) -> None:
        self._runtime._reset_world(g)

    def _apply_crash_respawn(self, event_data: dict, g: _SessionState) -> None:
        self._runtime._apply_crash_respawn(event_data, g)

    def _respawn_camera_y(self, last_crossed_bridge_y: float | None) -> float:
        return self._runtime._respawn_camera_y(last_crossed_bridge_y)

    def _handle_bank_collision(self, plane_state: dict, river_banks: list[dict]) -> dict | None:
        return self._runtime._handle_bank_collision(plane_state=plane_state, river_banks=river_banks)

    def _handle_helicopter_collision(self, plane_state: dict, helicopters: list[dict]) -> dict | None:
        return self._runtime._handle_helicopter_collision(plane_state=plane_state, helicopters=helicopters)

    def _handle_jet_collision(self, plane_state: dict, jets: list[dict]) -> dict | None:
        return self._runtime._handle_jet_collision(plane_state=plane_state, jets=jets)

    def _handle_bridge_collision(self, plane_state: dict, bridges: list[dict]) -> dict | None:
        return self._runtime._handle_bridge_collision(plane_state=plane_state, bridges=bridges)

    def _apply_refuel_from_stations(self, plane_state: dict, fuel_stations: list[dict], elapsed_seconds: float) -> None:
        self._runtime._apply_refuel_from_stations(
            plane_state=plane_state,
            fuel_stations=fuel_stations,
            elapsed_seconds=elapsed_seconds,
        )

    def _apply_fuel_burn_and_crash(self, plane_state: dict, elapsed_seconds: float) -> dict | None:
        return self._runtime._apply_fuel_burn_and_crash(plane_state=plane_state, elapsed_seconds=elapsed_seconds)

    def _advance_missiles_and_check_collisions(
        self,
        missiles: list[dict],
        fuel_stations: list[dict],
        bridges: list[dict],
        plane_state: dict,
        elapsed_seconds: float,
        helicopters: list[dict] | None = None,
    ) -> list[dict]:
        return self._runtime._advance_missiles_and_check_collisions(
            missiles=missiles,
            fuel_stations=fuel_stations,
            bridges=bridges,
            helicopters=helicopters,
            plane_state=plane_state,
            elapsed_seconds=elapsed_seconds,
        )

    def _all_entities_in_view(
        self,
        fuel_stations: list[dict],
        missiles: list[dict],
        bridges: list[dict],
        camera_y: float,
        helicopters: list[dict] | None = None,
        jets: list[dict] | None = None,
    ) -> list[dict]:
        return self._runtime._all_entities_in_view(
            fuel_stations=fuel_stations,
            missiles=missiles,
            bridges=bridges,
            helicopters=helicopters,
            jets=jets,
            camera_y=camera_y,
        )

    def _prune_old_banks(self, river_banks: list[dict], camera_y: float) -> list[dict]:
        return self._runtime._prune_old_banks(river_banks=river_banks, camera_y=camera_y)

    def _ensure_fuel_stations_until(
        self,
        fuel_stations: list[dict],
        next_station_id: int,
        next_eligible_y: float,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        return self._runtime._ensure_fuel_stations_until(
            fuel_stations=fuel_stations,
            next_station_id=next_station_id,
            next_eligible_y=next_eligible_y,
            river_banks=river_banks,
            target_y=target_y,
        )

    def _ensure_bridges_until(
        self,
        bridges: list[dict],
        next_bridge_y: float,
        next_bridge_id: int,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        return self._runtime._ensure_bridges_until(
            bridges=bridges,
            next_bridge_y=next_bridge_y,
            next_bridge_id=next_bridge_id,
            river_banks=river_banks,
            target_y=target_y,
        )

    def _ensure_helicopters_until(
        self,
        helicopters: list[dict],
        next_helicopter_id: int,
        next_helicopter_y: float,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        return self._runtime._ensure_helicopters_until(
            helicopters=helicopters,
            next_helicopter_id=next_helicopter_id,
            next_helicopter_y=next_helicopter_y,
            river_banks=river_banks,
            target_y=target_y,
        )

    def _ensure_jets_until(
        self,
        jets: list[dict],
        next_jet_id: int,
        next_jet_y: float,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        return self._runtime._ensure_jets_until(
            jets=jets,
            next_jet_id=next_jet_id,
            next_jet_y=next_jet_y,
            river_banks=river_banks,
            target_y=target_y,
        )

    @staticmethod
    def _advance_helicopters(helicopters: list[dict], elapsed_seconds: float) -> None:
        SessionRuntime._advance_helicopters(helicopters=helicopters, elapsed_seconds=elapsed_seconds)

    @staticmethod
    def _advance_jets(jets: list[dict], elapsed_seconds: float) -> None:
        SessionRuntime._advance_jets(jets=jets, elapsed_seconds=elapsed_seconds)

    def _prune_old_helicopters(self, helicopters: list[dict], camera_y: float) -> list[dict]:
        return self._runtime._prune_old_helicopters(helicopters=helicopters, camera_y=camera_y)

    def _prune_old_jets(self, jets: list[dict], camera_y: float) -> list[dict]:
        return self._runtime._prune_old_jets(jets=jets, camera_y=camera_y)

    def _initial_plane_state(self) -> dict:
        return self._runtime._initial_plane_state()

    def _snapshot_payload(
        self,
        tick: int,
        last_processed_input_seq: int,
        plane_state: dict,
        river_banks: list[dict],
        entities: list[dict],
        camera_y: float,
        level: int = 1,
    ) -> dict:
        return self._runtime._snapshot_payload(
            tick=tick,
            last_processed_input_seq=last_processed_input_seq,
            plane_state=plane_state,
            river_banks=river_banks,
            entities=entities,
            camera_y=camera_y,
            level=level,
        )

    @staticmethod
    def _now_ms() -> int:
        return int(datetime.now(UTC).timestamp() * 1000)

    def _error_payload(self, seq: int, code: str, message: str) -> dict:
        return {"type": "error", "ts": self._now_ms(), "seq": seq, "payload": {"code": code, "message": message}}

    @staticmethod
    def _validate_input_payload(payload: dict) -> str | None:
        return SessionRuntime._validate_input_payload(payload)

    @staticmethod
    def _normalize_input_payload(payload: dict, fallback_input_seq: int) -> dict:
        return SessionRuntime._normalize_input_payload(payload=payload, fallback_input_seq=fallback_input_seq)

    def _apply_input_to_plane(self, plane_state: dict, normalized_input: dict) -> dict:
        return self._runtime._apply_input_to_plane(plane_state=plane_state, normalized_input=normalized_input)

    def _validate_key_payload(self, payload: dict) -> str | None:
        return self._runtime._validate_key_payload(payload)

    def _normalize_key_payload(self, payload: dict) -> dict:
        return self._runtime._normalize_key_payload(payload)
