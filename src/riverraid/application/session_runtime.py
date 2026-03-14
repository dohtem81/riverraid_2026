from dataclasses import dataclass, field

from riverraid.application.session_entities import Bridge, FuelStation, Helicopter, Missile, Plane, RiverBank, Tank
from riverraid.application.game_session_service import GameSessionService
from riverraid.infrastructure.game_config import GameConfig, load_game_config


@dataclass
class SessionState:
    plane_state: Plane | None = None
    river_banks: list[RiverBank] = field(default_factory=list)
    fuel_stations: list[FuelStation] = field(default_factory=list)
    missiles: list[Missile] = field(default_factory=list)
    bridges: list[Bridge] = field(default_factory=list)
    camera_y: float = 0.0
    next_segment_y: float = 0.0
    river_center_x: float = 0.0
    river_width: float = 0.0
    next_fuel_station_id: int = 1
    next_fuel_station_eligible_y: float = 0.0
    next_missile_id: int = 1
    next_bridge_id: int = 1
    next_bridge_y: float = 0.0
    helicopters: list[Helicopter] = field(default_factory=list)
    next_helicopter_id: int = 1
    next_helicopter_y: float = 0.0
    tanks: list[Tank] = field(default_factory=list)
    next_tank_id: int = 1
    next_tank_y: float = 0.0
    tank_missiles: list[Missile] = field(default_factory=list)  # horizontal missiles fired by tanks
    next_tank_missile_id: int = 1
    level: int = 1
    next_level_bridge_y: float = 0.0
    last_crossed_bridge_y: float | None = None
    tick: int = 0
    last_processed_input_seq: int = 0
    keys_down: set[str] = field(default_factory=set)
    game_time: float = 0.0
    last_fired_time: float = -999.0


class SessionRuntime:
    def __init__(self, cfg: GameConfig | None = None, session: GameSessionService | None = None) -> None:
        self._cfg = cfg or load_game_config()
        self._session = session or GameSessionService(cfg=self._cfg)

    def __getattr__(self, name: str):
        # Guard: don't recurse when _cfg itself hasn't been set yet
        if name in ("_cfg", "_session"):
            raise AttributeError(name)
        cfg_name = name.lstrip("_")
        try:
            return getattr(self._cfg, cfg_name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute {name!r}") from None

    @property
    def cfg(self) -> GameConfig:
        return self._cfg

    def new_state(self) -> SessionState:
        return SessionState(
            river_center_x=self._world_width / 2,
            river_width=self._river_max_width,
            next_bridge_y=self._bridge_interval_y,
            next_level_bridge_y=self._bridge_interval_y,
        )

    def process_elapsed(self, g: SessionState, elapsed: float) -> tuple[dict | None, bool]:
        if elapsed <= 0 or not g.plane_state:
            return None, False

        self._advance_world(g, elapsed)
        plane_state = g.plane_state.to_dict()
        fuel_event = self._apply_fuel_burn_and_crash(plane_state=plane_state, elapsed_seconds=elapsed)
        g.plane_state = Plane.from_dict(plane_state)
        if fuel_event is not None:
            if g.plane_state.hp > 0:
                self._apply_crash_respawn(fuel_event["data"], g)
            if g.plane_state.hp <= 0:
                return fuel_event, True
            g.tick += 1
            return fuel_event, False

        fuel_stations = [station.to_dict() for station in g.fuel_stations]
        self._apply_refuel_from_stations(plane_state=plane_state, fuel_stations=fuel_stations, elapsed_seconds=elapsed)
        missiles = [missile.to_dict() for missile in g.missiles]
        bridges = [bridge.to_dict() for bridge in g.bridges]
        helicopters = [helicopter.to_dict() for helicopter in g.helicopters]
        tanks = [tank.to_dict() for tank in g.tanks]
        missiles = self._advance_missiles_and_check_collisions(
            missiles=missiles,
            fuel_stations=fuel_stations,
            bridges=bridges,
            helicopters=helicopters,
            tanks=tanks,
            plane_state=plane_state,
            elapsed_seconds=elapsed,
        )
        g.plane_state = Plane.from_dict(plane_state)
        g.fuel_stations = [FuelStation.from_dict(station) for station in fuel_stations]
        g.bridges = [Bridge.from_dict(bridge) for bridge in bridges]
        g.helicopters = [Helicopter.from_dict(helicopter) for helicopter in helicopters]
        g.tanks = [Tank.from_dict(tank) for tank in tanks]
        missiles = self._session.prune_old_missiles(missiles=missiles, camera_y=g.camera_y)
        g.missiles = [Missile.from_dict(missile) for missile in missiles]
        # Expire missiles older than missile_lifetime_seconds
        g.missiles = [m for m in g.missiles if g.game_time - m.fired_at <= self._missile_lifetime_seconds]

        # Fire from tanks, advance tank missiles, check collision with plane
        tanks = [tank.to_dict() for tank in g.tanks]
        new_tank_missiles, g.next_tank_missile_id = self._session.maybe_fire_from_tanks(
            tanks=tanks, game_time=g.game_time, next_tank_missile_id=g.next_tank_missile_id
        )
        g.tanks = [Tank.from_dict(tank) for tank in tanks]
        g.tank_missiles.extend([Missile.from_dict(tm) for tm in new_tank_missiles])
        tank_missiles = [tm.to_dict() for tm in g.tank_missiles]
        tank_missiles = self._session.advance_tank_missiles(tank_missiles=tank_missiles, elapsed_seconds=elapsed)
        g.tank_missiles = [Missile.from_dict(tm) for tm in tank_missiles]
        # Tank missile vs player plane
        tank_missiles_for_coll = [tm.to_dict() for tm in g.tank_missiles]
        tank_missile_event = self._session.handle_tank_missile_collision(
            plane_state=plane_state, tank_missiles=tank_missiles_for_coll
        )
        g.tank_missiles = [Missile.from_dict(tm) for tm in tank_missiles_for_coll]
        g.plane_state = Plane.from_dict(plane_state)
        if tank_missile_event is not None:
            if g.plane_state.hp > 0:
                self._apply_crash_respawn(tank_missile_event["data"], g)
            if g.plane_state.hp <= 0:
                return tank_missile_event, True
            g.tick += 1
            return tank_missile_event, False

        river_banks = [segment.to_dict() for segment in g.river_banks]
        bridges = [bridge.to_dict() for bridge in g.bridges]
        helicopters = [helicopter.to_dict() for helicopter in g.helicopters]

        for coll_event in [
            self._handle_bank_collision(plane_state=plane_state, river_banks=river_banks),
            self._handle_bridge_collision(plane_state=plane_state, bridges=bridges),
            self._handle_helicopter_collision(plane_state=plane_state, helicopters=helicopters),
        ]:
            g.plane_state = Plane.from_dict(plane_state)
            g.helicopters = [Helicopter.from_dict(helicopter) for helicopter in helicopters]
            if coll_event is None:
                continue
            if g.plane_state.hp > 0:
                self._apply_crash_respawn(coll_event["data"], g)
            if g.plane_state.hp <= 0:
                return coll_event, True
            g.tick += 1
            return coll_event, False

        return None, False

    def join_ack_payload(self, player_id: str) -> dict:
        return {
            "player_id": player_id,
            "tick_rate": 30,
            "snapshot_rate": 12,
            "render_config": {
                "world_width": self._world_width,
                "viewport_height": self._viewport_height,
            },
        }

    def snapshot_for_state(self, g: SessionState) -> dict:
        if g.plane_state is None:
            raise RuntimeError("Plane state is not initialized")
        return self._session.snapshot_payload(
            tick=g.tick,
            last_processed_input_seq=g.last_processed_input_seq,
            plane_state=g.plane_state.to_dict(),
            river_banks=self._session.banks_in_view(
                river_banks=[segment.to_dict() for segment in g.river_banks],
                camera_y=g.camera_y,
            ),
            entities=self._session.all_entities_in_view(
                fuel_stations=[station.to_dict() for station in g.fuel_stations],
                missiles=[missile.to_dict() for missile in g.missiles],
                bridges=[bridge.to_dict() for bridge in g.bridges],
                helicopters=[helicopter.to_dict() for helicopter in g.helicopters],
                tanks=[tank.to_dict() for tank in g.tanks],
                tank_missiles=[tm.to_dict() for tm in g.tank_missiles],
                camera_y=g.camera_y,
            ),
            camera_y=g.camera_y,
            level=g.level,
        )

    def reset_for_new_game(self, g: SessionState) -> None:
        g.tick = 0
        g.last_processed_input_seq = 0
        self._reset_world(g)

    def _advance_world(self, g: SessionState, elapsed: float) -> None:
        g.game_time += elapsed
        g.camera_y += self._scroll_speed * elapsed
        if g.plane_state is None:
            raise RuntimeError("Plane state is not initialized")
        move_speed = self._step_x / self._tick_interval_seconds if self._tick_interval_seconds > 0 else self._step_x
        if "left" in g.keys_down and "right" not in g.keys_down:
            g.plane_state.x = max(0.0, g.plane_state.x - (move_speed * elapsed))
        elif "right" in g.keys_down and "left" not in g.keys_down:
            g.plane_state.x = min(self._world_width, g.plane_state.x + (move_speed * elapsed))
        g.plane_state.y = g.camera_y + self._plane_offset_from_camera
        gen_target = g.camera_y + self._viewport_height + self._river_generation_buffer
        river_banks = [segment.to_dict() for segment in g.river_banks]
        river_banks, g.next_segment_y, g.river_center_x, g.river_width = self._session.ensure_river_banks_until(
            river_banks=river_banks,
            next_segment_y=g.next_segment_y,
            center_x=g.river_center_x,
            river_width=g.river_width,
            target_y=gen_target,
        )
        fuel_stations = [station.to_dict() for station in g.fuel_stations]
        fuel_stations, g.next_fuel_station_id, g.next_fuel_station_eligible_y = self._session.ensure_fuel_stations_until(
            fuel_stations=fuel_stations,
            next_station_id=g.next_fuel_station_id,
            next_eligible_y=g.next_fuel_station_eligible_y,
            river_banks=river_banks,
            target_y=gen_target,
        )
        river_banks = self._session.prune_old_banks(river_banks=river_banks, camera_y=g.camera_y)
        fuel_stations = self._session.prune_old_fuel_stations(fuel_stations=fuel_stations, camera_y=g.camera_y)
        bridges = [bridge.to_dict() for bridge in g.bridges]
        bridges, g.next_bridge_id, g.next_bridge_y = self._session.ensure_bridges_until(
            bridges=bridges,
            next_bridge_y=g.next_bridge_y,
            next_bridge_id=g.next_bridge_id,
            river_banks=river_banks,
            target_y=gen_target,
        )
        bridges = self._session.prune_old_bridges(bridges=bridges, camera_y=g.camera_y)
        helicopters = [helicopter.to_dict() for helicopter in g.helicopters]
        helicopters, g.next_helicopter_id, g.next_helicopter_y = self._session.ensure_helicopters_until(
            helicopters=helicopters,
            next_helicopter_id=g.next_helicopter_id,
            next_helicopter_y=g.next_helicopter_y,
            river_banks=river_banks,
            target_y=gen_target,
        )
        self._session.advance_helicopters(helicopters=helicopters, elapsed_seconds=elapsed)
        helicopters = self._session.prune_old_helicopters(helicopters=helicopters, camera_y=g.camera_y)
        g.river_banks = [RiverBank.from_dict(segment) for segment in river_banks]
        g.fuel_stations = [FuelStation.from_dict(station) for station in fuel_stations]
        g.bridges = [Bridge.from_dict(bridge) for bridge in bridges]
        g.helicopters = [Helicopter.from_dict(helicopter) for helicopter in helicopters]
        # Tank generation and pruning
        tanks = [tank.to_dict() for tank in g.tanks]
        tanks, g.next_tank_id, g.next_tank_y = self._session.ensure_tanks_until(
            tanks=tanks,
            next_tank_id=g.next_tank_id,
            next_tank_y=g.next_tank_y,
            river_banks=river_banks,
            target_y=gen_target,
        )
        tanks = self._session.prune_old_tanks(tanks=tanks, camera_y=g.camera_y)
        g.tanks = [Tank.from_dict(tank) for tank in tanks]
        while g.camera_y > g.next_level_bridge_y + self._bridge_height:
            g.last_crossed_bridge_y = g.next_level_bridge_y
            g.level += 1
            g.next_level_bridge_y += self._bridge_interval_y

    def _reset_world(self, g: SessionState) -> None:
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
        river_banks, g.next_segment_y, g.river_center_x, g.river_width = self._session.ensure_river_banks_until(
            river_banks=[],
            next_segment_y=g.next_segment_y,
            center_x=g.river_center_x,
            river_width=g.river_width,
            target_y=gen_target,
        )
        fuel_stations, g.next_fuel_station_id, g.next_fuel_station_eligible_y = self._session.ensure_fuel_stations_until(
            fuel_stations=[],
            next_station_id=g.next_fuel_station_id,
            next_eligible_y=g.next_fuel_station_eligible_y,
            river_banks=river_banks,
            target_y=gen_target,
        )
        g.river_banks = [RiverBank.from_dict(segment) for segment in river_banks]
        g.fuel_stations = [FuelStation.from_dict(station) for station in fuel_stations]
        g.missiles = []
        g.bridges = []
        g.helicopters = []
        g.next_helicopter_id = 1
        g.next_helicopter_y = 0.0
        g.tanks = []
        g.tank_missiles = []
        g.next_tank_id = 1
        g.next_tank_y = 0.0
        g.next_tank_missile_id = 1
        g.keys_down.clear()
        g.game_time = 0.0
        g.last_fired_time = -999.0
        g.plane_state = Plane.from_dict(self._session.initial_plane_state())

    def _apply_crash_respawn(self, event_data: dict, g: SessionState) -> None:
        if g.plane_state is None:
            raise RuntimeError("Plane state is not initialized")
        respawn_camera_y = self._respawn_camera_y(g.last_crossed_bridge_y)
        event_data["respawn_camera_y"] = round(respawn_camera_y, 2)
        g.camera_y = respawn_camera_y
        plane_y = respawn_camera_y + self._plane_offset_from_camera
        g.plane_state.y = plane_y
        g.next_fuel_station_eligible_y = respawn_camera_y
        g.missiles = []
        g.tank_missiles = []
        left_x, right_x = self._session.bank_bounds_at_y(
            river_banks=[segment.to_dict() for segment in g.river_banks],
            y=plane_y,
        )
        g.plane_state.x = (left_x + right_x) / 2.0

    def _respawn_camera_y(self, last_crossed_bridge_y: float | None) -> float:
        if last_crossed_bridge_y is None:
            return 0.0
        return last_crossed_bridge_y + self._bridge_height

    def _handle_bank_collision(self, plane_state: dict, river_banks: list[dict]) -> dict | None:
        return self._session.handle_bank_collision(plane_state=plane_state, river_banks=river_banks)

    def _handle_helicopter_collision(self, plane_state: dict, helicopters: list[dict]) -> dict | None:
        return self._session.handle_helicopter_collision(plane_state=plane_state, helicopters=helicopters)

    def _handle_bridge_collision(self, plane_state: dict, bridges: list[dict]) -> dict | None:
        return self._session.handle_bridge_collision(plane_state=plane_state, bridges=bridges)

    def _apply_refuel_from_stations(self, plane_state: dict, fuel_stations: list[dict], elapsed_seconds: float) -> None:
        self._session.apply_refuel_from_stations(
            plane_state=plane_state,
            fuel_stations=fuel_stations,
            elapsed_seconds=elapsed_seconds,
        )

    def _apply_fuel_burn_and_crash(self, plane_state: dict, elapsed_seconds: float) -> dict | None:
        return self._session.apply_fuel_burn_and_crash(plane_state=plane_state, elapsed_seconds=elapsed_seconds)

    def _advance_missiles_and_check_collisions(
        self,
        missiles: list[dict],
        fuel_stations: list[dict],
        bridges: list[dict],
        plane_state: dict,
        elapsed_seconds: float,
        helicopters: list[dict] | None = None,
        tanks: list[dict] | None = None,
    ) -> list[dict]:
        return self._session.advance_missiles_and_check_collisions(
            missiles=missiles,
            fuel_stations=fuel_stations,
            bridges=bridges,
            helicopters=helicopters,
            tanks=tanks,
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
    ) -> list[dict]:
        return self._session.all_entities_in_view(
            fuel_stations=fuel_stations,
            missiles=missiles,
            bridges=bridges,
            helicopters=helicopters,
            camera_y=camera_y,
        )

    def _prune_old_banks(self, river_banks: list[dict], camera_y: float) -> list[dict]:
        return self._session.prune_old_banks(river_banks=river_banks, camera_y=camera_y)

    def _ensure_fuel_stations_until(
        self,
        fuel_stations: list[dict],
        next_station_id: int,
        next_eligible_y: float,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        return self._session.ensure_fuel_stations_until(
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
        return self._session.ensure_bridges_until(
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
        return self._session.ensure_helicopters_until(
            helicopters=helicopters,
            next_helicopter_id=next_helicopter_id,
            next_helicopter_y=next_helicopter_y,
            river_banks=river_banks,
            target_y=target_y,
        )

    @staticmethod
    def _advance_helicopters(helicopters: list[dict], elapsed_seconds: float) -> None:
        GameSessionService.advance_helicopters(helicopters=helicopters, elapsed_seconds=elapsed_seconds)

    def _prune_old_helicopters(self, helicopters: list[dict], camera_y: float) -> list[dict]:
        return self._session.prune_old_helicopters(helicopters=helicopters, camera_y=camera_y)

    def _initial_plane_state(self) -> dict:
        return self._session.initial_plane_state()

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
        return self._session.snapshot_payload(
            tick=tick,
            last_processed_input_seq=last_processed_input_seq,
            plane_state=plane_state,
            river_banks=river_banks,
            entities=entities,
            camera_y=camera_y,
            level=level,
        )

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

    def _normalize_key(self, key: str) -> str:
        mapping = {
            "ArrowLeft": "left",
            "ArrowRight": "right",
            "ArrowUp": "up",
            "ArrowDown": "down",
            " ": "space",
            "Space": "space",
            "Spacebar": "space",
        }
        return mapping.get(key, key).lower()

    def _validate_key_payload(self, payload: dict) -> str | None:
        key = payload.get("key")
        if not isinstance(key, str) or not key.strip():
            return "key must be a non-empty string"
        normalized_key = self._normalize_key(key)
        if normalized_key not in {"left", "right", "up", "down", "space"}:
            return "key must be ArrowLeft, ArrowRight, ArrowUp, ArrowDown, or Space"
        return None

    def _normalize_key_payload(self, payload: dict) -> dict:
        return {"key": self._normalize_key(payload["key"])}

    def process_key_event(self, g: SessionState, event_type: str, normalized_payload: dict) -> dict:
        key = normalized_payload["key"]
        if event_type == "keydown":
            g.keys_down.add(key)
        else:
            g.keys_down.discard(key)
        should_fire = event_type == "keydown" and key == "space"
        return {
            "input_seq": g.last_processed_input_seq,
            "turn": None,
            "fast": False,
            "fire": should_fire,
        }

    def process_input(self, g: SessionState, normalized_input: dict) -> tuple[dict, dict | None, bool]:
        if g.plane_state is None:
            raise RuntimeError("Plane state is not initialized")

        plane_state = g.plane_state.to_dict()
        plane_state = self._apply_input_to_plane(plane_state=plane_state, normalized_input=normalized_input)
        g.plane_state = Plane.from_dict(plane_state)
        if normalized_input["fire"] and (g.game_time - g.last_fired_time >= self._missile_cooldown_seconds):
            g.missiles.append(
                Missile(
                    id=f"missile_{g.next_missile_id}",
                    x=float(g.plane_state.x),
                    y=float(g.plane_state.y),
                    width=self._missile_width,
                    height=self._missile_height,
                    fired_at=g.game_time,
                )
            )
            g.next_missile_id += 1
            g.last_fired_time = g.game_time

        g.tick += 1
        g.last_processed_input_seq = normalized_input["input_seq"]

        collision_event = self._handle_bank_collision(
            plane_state=plane_state,
            river_banks=[segment.to_dict() for segment in g.river_banks],
        )
        g.plane_state = Plane.from_dict(plane_state)
        input_accepted_event = {
            "event_type": "input_accepted",
            "data": {
                "input_seq": normalized_input["input_seq"],
                "turn": normalized_input["turn"],
                "fast": normalized_input["fast"],
                "fire": normalized_input["fire"],
            },
        }
        return input_accepted_event, collision_event, bool(collision_event and g.plane_state.hp <= 0)