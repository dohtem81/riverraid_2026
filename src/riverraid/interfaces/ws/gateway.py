import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import time
from uuid import uuid4

from fastapi import WebSocket

from riverraid.application.game_session_service import GameSessionService
from riverraid.application.use_cases import ValidateJoinToken
from riverraid.infrastructure.jwt_token_service import TokenValidationError


@dataclass
class _SessionState:
    plane_state: dict = field(default_factory=dict)
    river_banks: list[dict] = field(default_factory=list)
    fuel_stations: list[dict] = field(default_factory=list)
    missiles: list[dict] = field(default_factory=list)
    bridges: list[dict] = field(default_factory=list)
    camera_y: float = 0.0
    next_segment_y: float = 0.0
    river_center_x: float = 0.0
    river_width: float = 0.0
    next_fuel_station_id: int = 1
    next_fuel_station_eligible_y: float = 0.0
    next_missile_id: int = 1
    next_bridge_id: int = 1
    next_bridge_y: float = 0.0
    level: int = 1
    next_level_bridge_y: float = 0.0
    last_crossed_bridge_y: float | None = None
    tick: int = 0
    last_processed_input_seq: int = 0


class WebSocketGateway:
    def __init__(self, validate_join_token: ValidateJoinToken) -> None:
        self._validate_join_token = validate_join_token
        self._world_width = 1000.0
        self._step_x = 5.0
        self._segment_height = 40.0
        self._river_max_width = 420.0
        self._bank_margin = 60.0
        self._viewport_height = 600.0
        self._plane_offset_from_camera = 60.0
        self._scroll_speed = 120.0
        self._tick_interval_seconds = 0.1
        self._river_generation_buffer = 200.0
        self._plane_half_width = 8.0
        self._fuel_burn_per_second = 1.0
        self._fuel_capacity = 100.0
        self._plane_width = self._plane_half_width * 2.0
        self._river_min_width = self._plane_width * 9.0
        self._river_width_variation_step = 18.0
        self._fuel_refill_per_second = 20.0
        self._fuel_station_width = self._plane_width
        self._fuel_station_letter_count = 4
        self._fuel_station_height = self._plane_width * self._fuel_station_letter_count
        self._fuel_station_min_spacing = self._scroll_speed * 8.0
        self._missile_speed = 300.0
        self._missile_width = 4.0
        self._missile_height = 12.0
        self._bridge_interval_y = self._scroll_speed * 30.0
        self._bridge_height = 20.0
        self._bridge_narrow_min = self._plane_width * 5.0
        self._bridge_narrow_max = self._plane_width * 10.0
        self._session = GameSessionService(
            world_width=self._world_width,
            step_x=self._step_x,
            segment_height=self._segment_height,
            river_max_width=self._river_max_width,
            bank_margin=self._bank_margin,
            viewport_height=self._viewport_height,
            plane_offset_from_camera=self._plane_offset_from_camera,
            river_generation_buffer=self._river_generation_buffer,
            plane_half_width=self._plane_half_width,
            fuel_burn_per_second=self._fuel_burn_per_second,
            fuel_capacity=self._fuel_capacity,
            plane_width=self._plane_width,
            river_min_width=self._river_min_width,
            river_width_variation_step=self._river_width_variation_step,
            fuel_refill_per_second=self._fuel_refill_per_second,
            fuel_station_width=self._fuel_station_width,
            fuel_station_letter_count=self._fuel_station_letter_count,
            fuel_station_height=self._fuel_station_height,
            fuel_station_min_spacing=self._fuel_station_min_spacing,
            missile_speed=self._missile_speed,
            missile_width=self._missile_width,
            missile_height=self._missile_height,
            bridge_interval_y=self._bridge_interval_y,
            bridge_height=self._bridge_height,
            bridge_narrow_min=self._bridge_narrow_min,
            bridge_narrow_max=self._bridge_narrow_max,
        )

    async def handle(self, websocket: WebSocket) -> None:
        await websocket.accept()
        session_id = f"sess_{uuid4().hex[:10]}"
        joined = False
        game_over = False
        server_seq = 2
        g = _SessionState(
            river_center_x=self._world_width / 2,
            river_width=self._river_max_width,
            next_bridge_y=self._bridge_interval_y,
            next_level_bridge_y=self._bridge_interval_y,
        )
        last_update_time = time.monotonic()

        try:
            while True:
                current_time = time.monotonic()
                elapsed = current_time - last_update_time
                if joined and g.plane_state and elapsed > 0 and not game_over:
                    self._advance_world(g, elapsed)
                    fuel_event = self._apply_fuel_burn_and_crash(plane_state=g.plane_state, elapsed_seconds=elapsed)
                    if fuel_event is not None:
                        if g.plane_state["hp"] > 0:
                            self._apply_crash_respawn(fuel_event["data"], g)
                        server_seq += 1
                        await self._emit_event(websocket, session_id, server_seq, fuel_event)
                        if g.plane_state["hp"] <= 0:
                            game_over = True
                            server_seq += 1
                            await self._emit_game_over(websocket, session_id, server_seq)
                        else:
                            g.tick += 1
                            server_seq += 1
                            await self._emit_snapshot(websocket, session_id, server_seq, g)
                    else:
                        self._apply_refuel_from_stations(plane_state=g.plane_state, fuel_stations=g.fuel_stations, elapsed_seconds=elapsed)
                        g.missiles = self._advance_missiles_and_check_collisions(
                            missiles=g.missiles, fuel_stations=g.fuel_stations, bridges=g.bridges,
                            plane_state=g.plane_state, elapsed_seconds=elapsed,
                        )
                        g.missiles = self._session.prune_old_missiles(missiles=g.missiles, camera_y=g.camera_y)
                        for coll_event in [
                            self._handle_bank_collision(plane_state=g.plane_state, river_banks=g.river_banks),
                            self._handle_bridge_collision(plane_state=g.plane_state, bridges=g.bridges),
                        ]:
                            if coll_event is None:
                                continue
                            if g.plane_state["hp"] > 0:
                                self._apply_crash_respawn(coll_event["data"], g)
                            server_seq += 1
                            await self._emit_event(websocket, session_id, server_seq, coll_event)
                            if g.plane_state["hp"] <= 0:
                                game_over = True
                                server_seq += 1
                                await self._emit_game_over(websocket, session_id, server_seq)
                            else:
                                g.tick += 1
                                server_seq += 1
                                await self._emit_snapshot(websocket, session_id, server_seq, g)
                            break
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
                        await websocket.send_json(self._error_payload(seq=seq, code="UNAUTHORIZED", message="Missing access token"))
                        continue
                    try:
                        player = self._validate_join_token.execute(token)
                    except TokenValidationError:
                        await websocket.send_json(self._error_payload(seq=seq, code="UNAUTHORIZED", message="Invalid access token"))
                        continue
                    joined = True
                    game_over = False
                    g.tick = 0
                    g.last_processed_input_seq = 0
                    self._reset_world(g)
                    server_seq = 1
                    await websocket.send_json(
                        {
                            "type": "join_ack",
                            "ts": self._now_ms(),
                            "session_id": session_id,
                            "seq": server_seq,
                            "payload": {
                                "player_id": player.player_id,
                                "tick_rate": 30,
                                "snapshot_rate": 12,
                                "render_config": {
                                    "world_width": self._world_width,
                                    "viewport_height": self._viewport_height,
                                },
                            },
                        }
                    )
                    server_seq += 1
                    await self._emit_snapshot(websocket, session_id, server_seq, g)
                    continue

                if msg_type == "restart":
                    if not joined:
                        await websocket.send_json(self._error_payload(seq=seq, code="UNAUTHORIZED", message="Join required before restart"))
                        continue
                    game_over = False
                    g.tick = 0
                    g.last_processed_input_seq = 0
                    self._reset_world(g)
                    server_seq += 1
                    await self._emit_event(websocket, session_id, server_seq, {
                        "event_type": "game_restarted",
                        "data": {"lives": g.plane_state["hp"]},
                    })
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
                        await websocket.send_json(self._error_payload(seq=seq, code="UNAUTHORIZED", message="Join required before input"))
                        continue
                    if game_over:
                        await websocket.send_json(self._error_payload(seq=seq, code="GAME_OVER", message="Game over. Send restart command."))
                        continue
                    payload = message.get("payload") or {}
                    validation_error = self._validate_input_payload(payload)
                    if validation_error is not None:
                        await websocket.send_json(self._error_payload(seq=seq, code="INVALID_INPUT", message=validation_error))
                        continue
                    normalized_input = self._normalize_input_payload(payload=payload, fallback_input_seq=seq)
                    if not g.plane_state:
                        await websocket.send_json(self._error_payload(seq=seq, code="INTERNAL_STATE", message="Plane state is not initialized"))
                        continue
                    g.plane_state = self._apply_input_to_plane(plane_state=g.plane_state, normalized_input=normalized_input)
                    if normalized_input["fire"]:
                        g.missiles.append({
                            "id": f"missile_{g.next_missile_id}",
                            "x": float(g.plane_state["x"]),
                            "y": float(g.plane_state["y"]),
                            "width": self._missile_width,
                            "height": self._missile_height,
                        })
                        g.next_missile_id += 1
                    g.tick += 1
                    g.last_processed_input_seq = normalized_input["input_seq"]
                    collision_event = self._handle_bank_collision(plane_state=g.plane_state, river_banks=g.river_banks)
                    await self._emit_event(websocket, session_id, seq, {
                        "event_type": "input_accepted",
                        "data": {
                            "input_seq": normalized_input["input_seq"],
                            "turn": normalized_input["turn"],
                            "fast": normalized_input["fast"],
                            "fire": normalized_input["fire"],
                        },
                    })
                    if collision_event is not None:
                        server_seq += 1
                        await self._emit_event(websocket, session_id, server_seq, collision_event)
                        if g.plane_state["hp"] <= 0:
                            game_over = True
                            server_seq += 1
                            await self._emit_game_over(websocket, session_id, server_seq)
                    server_seq += 1
                    await self._emit_snapshot(websocket, session_id, server_seq, g)
                    continue

                await websocket.send_json(self._error_payload(seq=seq, code="INVALID_TYPE", message="Unknown message type"))
        except Exception:
            await websocket.close()

    # ── world helpers ──────────────────────────────────────────────────────────

    def _advance_world(self, g: _SessionState, elapsed: float) -> None:
        g.camera_y += self._scroll_speed * elapsed
        g.plane_state["y"] = g.camera_y + self._plane_offset_from_camera
        gen_target = g.camera_y + self._viewport_height + self._river_generation_buffer
        g.river_banks, g.next_segment_y, g.river_center_x, g.river_width = self._session.ensure_river_banks_until(
            river_banks=g.river_banks, next_segment_y=g.next_segment_y,
            center_x=g.river_center_x, river_width=g.river_width, target_y=gen_target,
        )
        g.fuel_stations, g.next_fuel_station_id, g.next_fuel_station_eligible_y = self._session.ensure_fuel_stations_until(
            fuel_stations=g.fuel_stations, next_station_id=g.next_fuel_station_id,
            next_eligible_y=g.next_fuel_station_eligible_y, river_banks=g.river_banks, target_y=gen_target,
        )
        g.river_banks = self._session.prune_old_banks(river_banks=g.river_banks, camera_y=g.camera_y)
        g.fuel_stations = self._session.prune_old_fuel_stations(fuel_stations=g.fuel_stations, camera_y=g.camera_y)
        g.bridges, g.next_bridge_id, g.next_bridge_y = self._session.ensure_bridges_until(
            bridges=g.bridges, next_bridge_y=g.next_bridge_y, next_bridge_id=g.next_bridge_id,
            river_banks=g.river_banks, target_y=gen_target,
        )
        g.bridges = self._session.prune_old_bridges(bridges=g.bridges, camera_y=g.camera_y)
        while g.camera_y > g.next_level_bridge_y + self._bridge_height:
            g.last_crossed_bridge_y = g.next_level_bridge_y
            g.level += 1
            g.next_level_bridge_y += self._bridge_interval_y

    def _reset_world(self, g: _SessionState) -> None:
        g.camera_y = 0.0
        g.next_segment_y = 0.0
        g.river_center_x = self._world_width / 2
        g.river_width = self._river_max_width
        g.next_fuel_station_id = 1
        g.next_fuel_station_eligible_y = 0.0
        g.next_missile_id = 1
        g.next_bridge_id = 1
        g.next_bridge_y = self._bridge_interval_y
        g.level = 1
        g.next_level_bridge_y = self._bridge_interval_y
        g.last_crossed_bridge_y = None
        gen_target = self._viewport_height + self._river_generation_buffer
        g.river_banks, g.next_segment_y, g.river_center_x, g.river_width = self._session.ensure_river_banks_until(
            river_banks=[], next_segment_y=g.next_segment_y, center_x=g.river_center_x,
            river_width=g.river_width, target_y=gen_target,
        )
        g.fuel_stations, g.next_fuel_station_id, g.next_fuel_station_eligible_y = self._session.ensure_fuel_stations_until(
            fuel_stations=[], next_station_id=g.next_fuel_station_id,
            next_eligible_y=g.next_fuel_station_eligible_y, river_banks=g.river_banks, target_y=gen_target,
        )
        g.missiles = []
        g.bridges = []
        g.plane_state = self._session.initial_plane_state()

    def _apply_crash_respawn(self, event_data: dict, g: _SessionState) -> None:
        respawn_camera_y = self._respawn_camera_y(g.last_crossed_bridge_y)
        event_data["respawn_camera_y"] = round(respawn_camera_y, 2)
        g.camera_y = respawn_camera_y
        g.plane_state["y"] = respawn_camera_y + self._plane_offset_from_camera
        g.next_fuel_station_eligible_y = respawn_camera_y
        g.missiles = []

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
                "payload": self._session.snapshot_payload(
                    tick=g.tick,
                    last_processed_input_seq=g.last_processed_input_seq,
                    plane_state=g.plane_state,
                    river_banks=self._session.banks_in_view(river_banks=g.river_banks, camera_y=g.camera_y),
                    entities=self._session.all_entities_in_view(
                        fuel_stations=g.fuel_stations, missiles=g.missiles, bridges=g.bridges, camera_y=g.camera_y,
                    ),
                    camera_y=g.camera_y,
                    level=g.level,
                ),
            }
        )

    async def _emit_game_over(self, websocket: WebSocket, session_id: str, seq: int) -> None:
        await self._emit_event(websocket, session_id, seq, {"event_type": "game_over", "data": {"reason": "no_lives"}})

    # ── kept for test access ───────────────────────────────────────────────────

    def _respawn_camera_y(self, last_crossed_bridge_y: float | None) -> float:
        if last_crossed_bridge_y is None:
            return 0.0
        return last_crossed_bridge_y + self._bridge_height

    def _handle_bank_collision(self, plane_state: dict, river_banks: list[dict]) -> dict | None:
        return self._session.handle_bank_collision(plane_state=plane_state, river_banks=river_banks)

    def _handle_bridge_collision(self, plane_state: dict, bridges: list[dict]) -> dict | None:
        return self._session.handle_bridge_collision(plane_state=plane_state, bridges=bridges)

    def _apply_refuel_from_stations(self, plane_state: dict, fuel_stations: list[dict], elapsed_seconds: float) -> None:
        self._session.apply_refuel_from_stations(
            plane_state=plane_state, fuel_stations=fuel_stations, elapsed_seconds=elapsed_seconds,
        )

    def _apply_fuel_burn_and_crash(self, plane_state: dict, elapsed_seconds: float) -> dict | None:
        return self._session.apply_fuel_burn_and_crash(plane_state=plane_state, elapsed_seconds=elapsed_seconds)

    def _advance_missiles_and_check_collisions(
        self, missiles: list[dict], fuel_stations: list[dict], bridges: list[dict], plane_state: dict, elapsed_seconds: float
    ) -> list[dict]:
        return self._session.advance_missiles_and_check_collisions(
            missiles=missiles, fuel_stations=fuel_stations, bridges=bridges,
            plane_state=plane_state, elapsed_seconds=elapsed_seconds,
        )

    def _all_entities_in_view(self, fuel_stations: list[dict], missiles: list[dict], bridges: list[dict], camera_y: float) -> list[dict]:
        return self._session.all_entities_in_view(
            fuel_stations=fuel_stations, missiles=missiles, bridges=bridges, camera_y=camera_y,
        )

    def _prune_old_banks(self, river_banks: list[dict], camera_y: float) -> list[dict]:
        return self._session.prune_old_banks(river_banks=river_banks, camera_y=camera_y)

    def _ensure_fuel_stations_until(
        self, fuel_stations: list[dict], next_station_id: int, next_eligible_y: float,
        river_banks: list[dict], target_y: float,
    ) -> tuple[list[dict], int, float]:
        return self._session.ensure_fuel_stations_until(
            fuel_stations=fuel_stations, next_station_id=next_station_id,
            next_eligible_y=next_eligible_y, river_banks=river_banks, target_y=target_y,
        )

    def _ensure_bridges_until(
        self, bridges: list[dict], next_bridge_y: float, next_bridge_id: int,
        river_banks: list[dict], target_y: float,
    ) -> tuple[list[dict], int, float]:
        return self._session.ensure_bridges_until(
            bridges=bridges, next_bridge_y=next_bridge_y, next_bridge_id=next_bridge_id,
            river_banks=river_banks, target_y=target_y,
        )

    def _initial_plane_state(self) -> dict:
        return self._session.initial_plane_state()

    def _snapshot_payload(
        self, tick: int, last_processed_input_seq: int, plane_state: dict,
        river_banks: list[dict], entities: list[dict], camera_y: float, level: int = 1,
    ) -> dict:
        return self._session.snapshot_payload(
            tick=tick, last_processed_input_seq=last_processed_input_seq, plane_state=plane_state,
            river_banks=river_banks, entities=entities, camera_y=camera_y, level=level,
        )

    # ── message helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _now_ms() -> int:
        return int(datetime.now(UTC).timestamp() * 1000)

    def _error_payload(self, seq: int, code: str, message: str) -> dict:
        return {"type": "error", "ts": self._now_ms(), "seq": seq, "payload": {"code": code, "message": message}}

    @staticmethod
    def _validate_input_payload(payload: dict) -> str | None:
        input_seq = payload.get("input_seq")
        if input_seq is not None and (not isinstance(input_seq, int) or input_seq < 0):
            return "input_seq must be a non-negative integer"
        turn = payload.get("turn")
        if turn is not None and turn not in {"left", "right"}:
            return "turn must be 'left', 'right', or omitted"
        fast = payload.get("fast")
        if fast is not None and not isinstance(fast, bool):
            return "fast must be a boolean"
        fire = payload.get("fire")
        if fire is not None and not isinstance(fire, bool):
            return "fire must be a boolean"
        return None

    @staticmethod
    def _normalize_input_payload(payload: dict, fallback_input_seq: int) -> dict:
        input_seq = payload.get("input_seq")
        if input_seq is None:
            input_seq = max(0, int(fallback_input_seq))
        return {
            "input_seq": input_seq,
            "turn": payload.get("turn"),
            "fast": payload.get("fast", False),
            "fire": payload.get("fire", False),
        }

    def _apply_input_to_plane(self, plane_state: dict, normalized_input: dict) -> dict:
        return self._session.apply_input_to_plane(plane_state=plane_state, normalized_input=normalized_input)
