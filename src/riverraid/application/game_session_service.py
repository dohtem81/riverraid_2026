import random

from riverraid.infrastructure.game_config import GameConfig


class GameSessionService:
    def __init__(self, cfg: GameConfig) -> None:
        self._cfg = cfg

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _aabb_overlap(
        ax_left: float, ax_right: float, ay_bottom: float, ay_top: float,
        bx_left: float, bx_right: float, by_bottom: float, by_top: float,
    ) -> bool:
        return ax_right >= bx_left and ax_left <= bx_right and ay_top >= by_bottom and ay_bottom <= by_top

    def _apply_plane_hit(self, plane_state: dict) -> dict:
        """Deduct one HP; reset position and fuel. Returns the ``data`` dict for the collision event."""
        c = self._cfg
        plane_state["hp"] = max(0, int(plane_state["hp"]) - 1)
        plane_state["x"] = c.world_width / 2
        plane_state["fuel"] = c.fuel_capacity if plane_state["hp"] > 0 else 0.0
        return {"hp": plane_state["hp"], "fuel": int(plane_state["fuel"])}

    # ── Plane ─────────────────────────────────────────────────────────────────

    def initial_plane_state(self) -> dict:
        c = self._cfg
        return {
            "x": c.world_width / 2,
            "y": c.plane_offset_from_camera,
            "vx": 0.0,
            "vy": 0.0,
            "fuel": c.fuel_capacity,
            "hp": 3,
            "score": 0,
            "actor": "plane",
        }

    def apply_input_to_plane(self, plane_state: dict, normalized_input: dict) -> dict:
        c = self._cfg
        next_state = dict(plane_state)
        turn = normalized_input["turn"]
        if turn == "left":
            next_state["x"] = max(0.0, next_state["x"] - c.step_x)
        elif turn == "right":
            next_state["x"] = min(c.world_width, next_state["x"] + c.step_x)
        return next_state

    @staticmethod
    def snapshot_payload(
        tick: int,
        last_processed_input_seq: int,
        plane_state: dict,
        river_banks: list[dict],
        entities: list[dict],
        camera_y: float,
        level: int = 1,
    ) -> dict:
        return {
            "tick": tick,
            "last_processed_input_seq": last_processed_input_seq,
            "player": plane_state,
            "hud": {
                "lives": int(plane_state["hp"]),
                "score": int(plane_state["score"]),
                "level": level,
                "fuel": int(plane_state["fuel"]),
            },
            "river_banks": river_banks,
            "camera_y": round(camera_y, 2),
            "entities": entities,
        }

    def ensure_river_banks_until(
        self,
        river_banks: list[dict],
        next_segment_y: float,
        center_x: float,
        river_width: float,
        target_y: float,
    ) -> tuple[list[dict], float, float, float]:
        c = self._cfg
        while next_segment_y <= target_y:
            y = next_segment_y
            dist_to_bridge = min(
                y % c.bridge_interval_y,
                c.bridge_interval_y - (y % c.bridge_interval_y),
            )
            near_bridge = dist_to_bridge <= 2.0 * c.segment_height
            effective_min = c.bridge_narrow_min if near_bridge else c.river_min_width
            effective_max = c.bridge_narrow_max if near_bridge else c.river_max_width
            river_width += random.uniform(-c.river_width_variation_step, c.river_width_variation_step)
            river_width = max(effective_min, min(effective_max, river_width))
            min_center_x = c.bank_margin + (river_width / 2)
            max_center_x = c.world_width - c.bank_margin - (river_width / 2)
            center_x += random.uniform(-20.0, 20.0)
            center_x = max(min_center_x, min(max_center_x, center_x))
            left_x = max(0.0, center_x - (river_width / 2))
            right_x = min(c.world_width, center_x + (river_width / 2))
            river_banks.append({"y": y, "left_x": round(left_x, 2), "right_x": round(right_x, 2)})
            next_segment_y += c.segment_height
        return river_banks, next_segment_y, center_x, river_width

    def ensure_fuel_stations_until(
        self,
        fuel_stations: list[dict],
        next_station_id: int,
        next_eligible_y: float,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        c = self._cfg
        while next_eligible_y <= target_y:
            station_y = next_eligible_y + random.uniform(0.0, c.fuel_station_min_spacing)
            if station_y > target_y:
                break
            left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=station_y)
            half_width = c.fuel_station_width / 2
            min_x = left_x + half_width
            max_x = right_x - half_width
            if min_x < max_x:
                station_x = random.uniform(min_x, max_x)
                fuel_stations.append({
                    "id": f"fuel_{next_station_id}",
                    "x": round(station_x, 2),
                    "y": round(station_y, 2),
                    "width": c.fuel_station_width,
                    "height": c.fuel_station_height,
                })
                next_station_id += 1
            next_eligible_y = station_y + c.fuel_station_min_spacing
        return fuel_stations, next_station_id, next_eligible_y

    def prune_old_banks(self, river_banks: list[dict], camera_y: float) -> list[dict]:
        c = self._cfg
        last_crossed_bridge_index = int(max(0.0, (camera_y - c.bridge_height) // c.bridge_interval_y))
        min_y = max(0.0, (last_crossed_bridge_index - 1) * c.bridge_interval_y)
        return [segment for segment in river_banks if segment["y"] >= min_y]

    def banks_in_view(self, river_banks: list[dict], camera_y: float) -> list[dict]:
        c = self._cfg
        min_y = camera_y - c.segment_height
        max_y = camera_y + c.viewport_height + c.segment_height
        return [segment for segment in river_banks if min_y <= segment["y"] <= max_y]

    def prune_old_fuel_stations(self, fuel_stations: list[dict], camera_y: float) -> list[dict]:
        min_y = camera_y - self._cfg.fuel_station_height
        return [station for station in fuel_stations if station["y"] + station["height"] >= min_y]

    def fuel_station_entities_in_view(self, fuel_stations: list[dict], camera_y: float) -> list[dict]:
        c = self._cfg
        max_y = camera_y + c.viewport_height + c.segment_height
        entities: list[dict] = []
        for station in fuel_stations:
            station_top = station["y"]
            station_bottom = station_top + station["height"]
            if station_bottom < camera_y or station_top > max_y:
                continue
            entities.append(
                {
                    "id": station["id"],
                    "kind": "fuel_station",
                    "x": station["x"],
                    "y": station["y"],
                    "width": station["width"],
                    "height": station["height"],
                    "label": "FUEL",
                }
            )
        return entities

    def handle_bank_collision(self, plane_state: dict, river_banks: list[dict]) -> dict | None:
        c = self._cfg
        left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=plane_state["y"])
        if (plane_state["x"] - c.plane_half_width) > left_x and (plane_state["x"] + c.plane_half_width) < right_x:
            return None
        return {"event_type": "collision_bank", "data": self._apply_plane_hit(plane_state)}

    def apply_refuel_from_stations(self, plane_state: dict, fuel_stations: list[dict], elapsed_seconds: float) -> None:
        c = self._cfg
        if elapsed_seconds <= 0 or plane_state["fuel"] >= c.fuel_capacity:
            return
        plane_x = float(plane_state["x"])
        plane_y = float(plane_state["y"])
        for station in fuel_stations:
            station_left = float(station["x"]) - (float(station["width"]) / 2)
            station_right = float(station["x"]) + (float(station["width"]) / 2)
            station_top = float(station["y"])
            station_bottom = station_top + float(station["height"])
            x_overlap = (plane_x + c.plane_half_width) >= station_left and (plane_x - c.plane_half_width) <= station_right
            y_overlap = station_top <= plane_y <= station_bottom
            if x_overlap and y_overlap:
                plane_state["fuel"] = min(
                    c.fuel_capacity,
                    float(plane_state["fuel"]) + (c.fuel_refill_per_second * elapsed_seconds),
                )
                return

    def apply_fuel_burn_and_crash(self, plane_state: dict, elapsed_seconds: float) -> dict | None:
        if elapsed_seconds <= 0:
            return None
        plane_state["fuel"] = max(0.0, float(plane_state["fuel"]) - (self._cfg.fuel_burn_per_second * elapsed_seconds))
        if plane_state["fuel"] > 0:
            return None
        return {"event_type": "crash_fuel", "data": self._apply_plane_hit(plane_state)}

    def advance_missiles_and_check_collisions(
        self, missiles: list[dict], fuel_stations: list[dict], bridges: list[dict], plane_state: dict,
        elapsed_seconds: float, helicopters: list[dict] | None = None, tanks: list[dict] | None = None,
    ) -> list[dict]:
        c = self._cfg
        kept: list[dict] = []
        delta_y = c.missile_speed * elapsed_seconds
        for missile in missiles:
            missile["y"] += delta_y
            m_left = float(missile["x"]) - float(missile["width"]) / 2
            m_right = float(missile["x"]) + float(missile["width"]) / 2
            m_bottom = float(missile["y"])
            m_top = float(missile["y"]) + float(missile["height"])
            hit = False
            for station in fuel_stations:
                s_left = float(station["x"]) - float(station["width"]) / 2
                s_right = float(station["x"]) + float(station["width"]) / 2
                if self._aabb_overlap(m_left, m_right, m_bottom, m_top, s_left, s_right, float(station["y"]), float(station["y"]) + float(station["height"])):
                    fuel_stations.remove(station)
                    plane_state["score"] = int(plane_state["score"]) + 10
                    hit = True
                    break
            if not hit:
                for bridge in bridges:
                    if bridge.get("destroyed"):
                        continue
                    if self._aabb_overlap(m_left, m_right, m_bottom, m_top, float(bridge["left_x"]), float(bridge["right_x"]), float(bridge["y"]), float(bridge["y"]) + float(bridge["height"])):
                        bridge["destroyed"] = True
                        plane_state["score"] = int(plane_state["score"]) + 20
                        hit = True
                        break
            if not hit and helicopters:
                for heli in helicopters:
                    if heli.get("destroyed"):
                        continue
                    h_left = float(heli["x"]) - float(heli["width"]) / 2
                    h_right = float(heli["x"]) + float(heli["width"]) / 2
                    if self._aabb_overlap(m_left, m_right, m_bottom, m_top, h_left, h_right, float(heli["y"]), float(heli["y"]) + float(heli["height"])):
                        heli["destroyed"] = True
                        plane_state["score"] = int(plane_state["score"]) + c.helicopter_score
                        hit = True
                        break
            if not hit and tanks:
                for tank in tanks:
                    if tank.get("destroyed"):
                        continue
                    t_left = float(tank["x"]) - float(tank["width"]) / 2
                    t_right = float(tank["x"]) + float(tank["width"]) / 2
                    if self._aabb_overlap(m_left, m_right, m_bottom, m_top, t_left, t_right, float(tank["y"]), float(tank["y"]) + float(tank["height"])):
                        tank["destroyed"] = True
                        plane_state["score"] = int(plane_state["score"]) + c.tank_score
                        hit = True
                        break
            if not hit:
                kept.append(missile)
        return kept

    def prune_old_missiles(self, missiles: list[dict], camera_y: float) -> list[dict]:
        c = self._cfg
        max_y = camera_y + c.viewport_height + c.river_generation_buffer
        return [m for m in missiles if m["y"] <= max_y]

    def all_entities_in_view(
        self, fuel_stations: list[dict], missiles: list[dict], bridges: list[dict],
        camera_y: float, helicopters: list[dict] | None = None,
        jets: list[dict] | None = None,
        tanks: list[dict] | None = None, tank_missiles: list[dict] | None = None,
    ) -> list[dict]:
        c = self._cfg
        entities = self.fuel_station_entities_in_view(fuel_stations=fuel_stations, camera_y=camera_y)
        for missile in missiles:
            if (camera_y - c.missile_height) <= missile["y"] <= (camera_y + c.viewport_height + c.missile_height):
                entities.append({"id": missile["id"], "kind": "missile", "x": missile["x"], "y": missile["y"], "width": missile["width"], "height": missile["height"]})
        bridge_min_y = camera_y - c.bridge_height
        bridge_max_y = camera_y + c.viewport_height + c.bridge_height
        for bridge in bridges:
            if bridge["y"] + bridge["height"] >= bridge_min_y and bridge["y"] <= bridge_max_y:
                entities.append({"id": bridge["id"], "kind": "road" if bridge.get("destroyed") else "bridge", "x": bridge["x"], "y": bridge["y"], "left_x": bridge["left_x"], "right_x": bridge["right_x"], "width": bridge["width"], "height": bridge["height"]})
        if helicopters:
            heli_min_y = camera_y - c.helicopter_height
            heli_max_y = camera_y + c.viewport_height + c.helicopter_height
            for heli in helicopters:
                if not heli.get("destroyed") and heli["y"] + heli["height"] >= heli_min_y and heli["y"] <= heli_max_y:
                    entities.append({"id": heli["id"], "kind": "helicopter", "x": heli["x"], "y": heli["y"], "width": heli["width"], "height": heli["height"], "direction": heli.get("direction", 1)})
        if jets:
            jet_min_y = camera_y - c.jet_height
            jet_max_y = camera_y + c.viewport_height + c.jet_height
            for jet in jets:
                if jet["y"] + jet["height"] >= jet_min_y and jet["y"] <= jet_max_y:
                    entities.append({"id": jet["id"], "kind": "jet", "x": jet["x"], "y": jet["y"], "width": jet["width"], "height": jet["height"], "direction": jet.get("direction", 1)})
        if tanks:
            for tank in tanks:
                if not tank.get("destroyed") and tank["y"] + tank["height"] >= camera_y - c.tank_height and tank["y"] <= camera_y + c.viewport_height + c.tank_height:
                    entities.append({"id": tank["id"], "kind": "tank", "x": tank["x"], "y": tank["y"], "width": tank["width"], "height": tank["height"], "side": tank["side"]})
        if tank_missiles:
            for tm in tank_missiles:
                if (camera_y - c.tank_missile_height) <= tm["y"] <= (camera_y + c.viewport_height + c.tank_missile_height):
                    entities.append({"id": tm["id"], "kind": "tank_missile", "x": tm["x"], "y": tm["y"], "width": tm["width"], "height": tm["height"]})
        return entities

    def ensure_bridges_until(
        self,
        bridges: list[dict],
        next_bridge_y: float,
        next_bridge_id: int,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        c = self._cfg
        while next_bridge_y <= target_y:
            left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=next_bridge_y)
            center_x = (left_x + right_x) / 2
            bridges.append({
                "id": f"bridge_{next_bridge_id}",
                "x": round(center_x, 2),
                "y": round(next_bridge_y, 2),
                "left_x": round(left_x, 2),
                "right_x": round(right_x, 2),
                "width": round(right_x - left_x, 2),
                "height": c.bridge_height,
            })
            next_bridge_id += 1
            next_bridge_y += c.bridge_interval_y
        return bridges, next_bridge_id, next_bridge_y

    def prune_old_bridges(self, bridges: list[dict], camera_y: float) -> list[dict]:
        min_y = camera_y - self._cfg.bridge_height
        return [b for b in bridges if b["y"] + b["height"] >= min_y]

    def handle_bridge_collision(self, plane_state: dict, bridges: list[dict]) -> dict | None:
        plane_x = float(plane_state["x"])
        plane_y = float(plane_state["y"])
        for bridge in bridges:
            if bridge.get("destroyed"):
                continue
            b_bottom = float(bridge["y"])
            b_top = b_bottom + float(bridge["height"])
            if b_bottom <= plane_y <= b_top and float(bridge["left_x"]) <= plane_x <= float(bridge["right_x"]):
                return {"event_type": "collision_bridge", "data": self._apply_plane_hit(plane_state)}
        return None

    def ensure_helicopters_until(
        self,
        helicopters: list[dict],
        next_helicopter_id: int,
        next_helicopter_y: float,
        river_banks: list[dict],
        target_y: float,
        spawn_multiplier: float = 1.0,
        level: int = 1,
    ) -> tuple[list[dict], int, float]:
        c = self._cfg
        effective_spacing = c.helicopter_min_spacing / max(0.1, spawn_multiplier)
        group_size = max(1, level)  # Level 1 ← 1 helicopter, Level 2 ← max 2, etc.
        vertical_stack_spacing = c.helicopter_height * 1.5  # Vertical offset between helicopters in a group
        while next_helicopter_y <= target_y:
            group_y = next_helicopter_y + random.uniform(effective_spacing * 0.3, effective_spacing)
            if group_y > target_y:
                break
            left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=group_y)
            if (right_x - left_x) < c.helicopter_width * 2:
                next_helicopter_y = group_y + effective_spacing
                continue
            half_w = c.helicopter_width / 2
            left_bound = left_x + half_w
            right_bound = right_x - half_w
            # Spawn a group: stack helicopters vertically with random X positions
            for offset_idx in range(group_size):
                # Vertical stacking: each helicopter in group gets a different Y
                heli_y = group_y + (offset_idx * vertical_stack_spacing)
                # Get bounds for this specific Y position (in case river curves)
                heli_left_x, heli_right_x = self.bank_bounds_at_y(river_banks=river_banks, y=heli_y)
                heli_left_bound = heli_left_x + half_w
                heli_right_bound = heli_right_x - half_w
                # Random X position within the river
                if heli_right_bound > heli_left_bound:
                    start_x = random.uniform(heli_left_bound, heli_right_bound)
                else:
                    start_x = (heli_left_bound + heli_right_bound) / 2
                # Random starting direction
                direction = random.choice([1, -1])
                helicopters.append({
                    "id": f"heli_{next_helicopter_id}",
                    "x": round(start_x, 2),
                    "y": round(heli_y, 2),
                    "width": c.helicopter_width,
                    "height": c.helicopter_height,
                    "speed": c.helicopter_speed,
                    "direction": direction,
                    "left_bound": round(heli_left_bound, 2),
                    "right_bound": round(heli_right_bound, 2),
                })
                next_helicopter_id += 1
            next_helicopter_y = group_y + effective_spacing
        return helicopters, next_helicopter_id, next_helicopter_y

    @staticmethod
    def advance_helicopters(helicopters: list[dict], elapsed_seconds: float) -> None:
        """Move each helicopter laterally, bouncing between its left/right bounds."""
        for heli in helicopters:
            if heli.get("destroyed"):
                continue
            speed = heli.get("speed", 60.0)
            heli["x"] += speed * heli["direction"] * elapsed_seconds
            if heli["x"] >= heli["right_bound"]:
                heli["x"] = heli["right_bound"]
                heli["direction"] = -1
            elif heli["x"] <= heli["left_bound"]:
                heli["x"] = heli["left_bound"]
                heli["direction"] = 1

    def prune_old_helicopters(self, helicopters: list[dict], camera_y: float) -> list[dict]:
        min_y = camera_y - self._cfg.helicopter_height
        return [h for h in helicopters if h["y"] + h["height"] >= min_y]

    def handle_helicopter_collision(self, plane_state: dict, helicopters: list[dict]) -> dict | None:
        c = self._cfg
        plane_x = float(plane_state["x"])
        plane_y = float(plane_state["y"])
        for heli in helicopters:
            if heli.get("destroyed"):
                continue
            h_left = float(heli["x"]) - float(heli["width"]) / 2
            h_right = float(heli["x"]) + float(heli["width"]) / 2
            h_bottom = float(heli["y"])
            h_top = h_bottom + float(heli["height"])
            x_hit = (plane_x + c.plane_half_width) >= h_left and (plane_x - c.plane_half_width) <= h_right
            if x_hit and h_bottom <= plane_y <= h_top:
                heli["destroyed"] = True
                return {"event_type": "collision_helicopter", "data": self._apply_plane_hit(plane_state)}
        return None

    def ensure_jets_until(
        self,
        jets: list[dict],
        next_jet_id: int,
        next_jet_y: float,
        river_banks: list[dict],
        target_y: float,
        spawn_multiplier: float = 1.0,
    ) -> tuple[list[dict], int, float]:
        c = self._cfg
        effective_spacing = c.jet_min_spacing / max(0.1, spawn_multiplier)
        while next_jet_y <= target_y:
            jet_y = next_jet_y + random.uniform(effective_spacing * 0.35, effective_spacing)
            if jet_y > target_y:
                break
            left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=jet_y)
            if (right_x - left_x) < c.jet_width * 1.8:
                next_jet_y = jet_y + effective_spacing
                continue
            half_w = c.jet_width / 2
            side = random.choice(["left", "right"])
            direction = 1 if side == "left" else -1
            # Jets spawn at the far screen edge and cross all the way through.
            start_x = -half_w if direction == 1 else c.world_width + half_w
            jets.append(
                {
                    "id": f"jet_{next_jet_id}",
                    "x": round(start_x, 2),
                    "y": round(jet_y, 2),
                    "width": c.jet_width,
                    "height": c.jet_height,
                    "speed": c.jet_speed,
                    "direction": direction,
                    "left_bound": round(-half_w, 2),
                    "right_bound": round(c.world_width + half_w, 2),
                }
            )
            next_jet_id += 1
            next_jet_y = jet_y + effective_spacing
        return jets, next_jet_id, next_jet_y

    @staticmethod
    def advance_jets(jets: list[dict], elapsed_seconds: float) -> None:
        for jet in jets:
            speed = jet.get("speed", 260.0)
            jet["x"] += speed * jet["direction"] * elapsed_seconds

    def prune_old_jets(self, jets: list[dict], camera_y: float) -> list[dict]:
        c = self._cfg
        min_y = camera_y - c.jet_height
        kept: list[dict] = []
        for jet in jets:
            if jet["y"] + jet["height"] < min_y:
                continue
            half_w = float(jet["width"]) / 2
            if int(jet.get("direction", 1)) > 0:
                # Moving right: despawn after fully leaving right side.
                if float(jet["x"]) - half_w > c.world_width:
                    continue
            else:
                # Moving left: despawn after fully leaving left side.
                if float(jet["x"]) + half_w < 0.0:
                    continue
            kept.append(jet)
        return kept

    def handle_jet_collision(self, plane_state: dict, jets: list[dict]) -> dict | None:
        c = self._cfg
        plane_x = float(plane_state["x"])
        plane_y = float(plane_state["y"])
        for jet in jets:
            j_left = float(jet["x"]) - float(jet["width"]) / 2
            j_right = float(jet["x"]) + float(jet["width"]) / 2
            j_bottom = float(jet["y"])
            j_top = j_bottom + float(jet["height"])
            x_hit = (plane_x + c.plane_half_width) >= j_left and (plane_x - c.plane_half_width) <= j_right
            if x_hit and j_bottom <= plane_y <= j_top:
                return {"event_type": "collision_jet", "data": self._apply_plane_hit(plane_state)}
        return None

    @staticmethod
    def bank_bounds_at_y(river_banks: list[dict], y: float) -> tuple[float, float]:
        if not river_banks:
            return (0.0, 1000.0)
        nearest_segment = min(river_banks, key=lambda segment: abs(segment["y"] - y))
        return float(nearest_segment["left_x"]), float(nearest_segment["right_x"])

    # ── Tanks ──────────────────────────────────────────────────────────────

    def ensure_tanks_until(
        self,
        tanks: list[dict],
        next_tank_id: int,
        next_tank_y: float,
        river_banks: list[dict],
        target_y: float,
        spawn_multiplier: float = 1.0,
    ) -> tuple[list[dict], int, float]:
        c = self._cfg
        effective_spacing = c.tank_min_spacing / max(0.1, spawn_multiplier)
        while next_tank_y <= target_y:
            tank_y = next_tank_y + random.uniform(effective_spacing * 0.5, effective_spacing)
            if tank_y > target_y:
                break
            left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=tank_y)
            side = random.choice(["left", "right"])
            # Place tank flush against the bank, facing inward
            if side == "left":
                tank_x = left_x - c.tank_width / 2
            else:
                tank_x = right_x + c.tank_width / 2
            tanks.append({
                "id": f"tank_{next_tank_id}",
                "x": round(tank_x, 2),
                "y": round(tank_y, 2),
                "width": c.tank_width,
                "height": c.tank_height,
                "side": side,
                "last_shot_at": -(c.tank_shoot_interval_seconds),  # ready to fire from turn 1
                "destroyed": False,
            })
            next_tank_id += 1
            next_tank_y = tank_y + effective_spacing
        return tanks, next_tank_id, next_tank_y

    def maybe_fire_from_tanks(
        self,
        tanks: list[dict],
        game_time: float,
        next_tank_missile_id: int,
    ) -> tuple[list[dict], int]:
        c = self._cfg
        new_missiles: list[dict] = []
        for tank in tanks:
            if tank.get("destroyed"):
                continue
            if game_time - float(tank["last_shot_at"]) >= c.tank_shoot_interval_seconds:
                side = tank["side"]
                vx = c.tank_missile_speed_x if side == "left" else -c.tank_missile_speed_x
                # Fire from the river-facing edge of the tank
                fire_x = float(tank["x"]) + (c.tank_width / 2 if side == "left" else -c.tank_width / 2)
                new_missiles.append({
                    "id": f"tank_missile_{next_tank_missile_id}",
                    "x": round(fire_x, 2),
                    "y": round(float(tank["y"]) + c.tank_height / 2.0, 2),
                    "width": c.tank_missile_width,
                    "height": c.tank_missile_height,
                    "vx": vx,
                    "prev_x": round(fire_x, 2),
                    "fired_at": game_time,
                })
                next_tank_missile_id += 1
                tank["last_shot_at"] = game_time
        return new_missiles, next_tank_missile_id

    def advance_tank_missiles(self, tank_missiles: list[dict], elapsed_seconds: float) -> list[dict]:
        """Move each tank missile horizontally; discard those that leave the world bounds."""
        c = self._cfg
        kept: list[dict] = []
        for tm in tank_missiles:
            tm["prev_x"] = float(tm.get("x", 0.0))
            tm["x"] += float(tm["vx"]) * elapsed_seconds
            if 0.0 <= tm["x"] <= c.world_width:
                kept.append(tm)
        return kept

    def handle_tank_missile_collision(self, plane_state: dict, tank_missiles: list[dict]) -> dict | None:
        """Check whether any tank missile overlaps the plane; consume the missile if so."""
        c = self._cfg
        plane_x = float(plane_state["x"])
        plane_y = float(plane_state["y"])
        p_left = plane_x - c.plane_half_width
        p_right = plane_x + c.plane_half_width
        p_bottom = plane_y
        p_top = plane_y + c.plane_half_width * 2  # use full plane height approximation
        for tm in list(tank_missiles):
            current_x = float(tm["x"])
            previous_x = float(tm.get("prev_x", current_x))
            half_width = float(tm["width"]) / 2
            tm_left = min(previous_x, current_x) - half_width
            tm_right = max(previous_x, current_x) + half_width
            tm_bottom = float(tm["y"])
            tm_top = tm_bottom + float(tm["height"])
            if self._aabb_overlap(p_left, p_right, p_bottom, p_top, tm_left, tm_right, tm_bottom, tm_top):
                tank_missiles.remove(tm)
                return {"event_type": "collision_tank_missile", "data": self._apply_plane_hit(plane_state)}
        return None

    def prune_old_tanks(self, tanks: list[dict], camera_y: float) -> list[dict]:
        min_y = camera_y - self._cfg.tank_height
        return [t for t in tanks if t["y"] + t["height"] >= min_y]
