import random


class GameSessionService:
    def __init__(
        self,
        world_width: float,
        step_x: float,
        segment_height: float,
        river_max_width: float,
        bank_margin: float,
        viewport_height: float,
        plane_offset_from_camera: float,
        river_generation_buffer: float,
        plane_half_width: float,
        fuel_burn_per_second: float,
        fuel_capacity: float,
        plane_width: float,
        river_min_width: float,
        river_width_variation_step: float,
        fuel_refill_per_second: float,
        fuel_station_width: float,
        fuel_station_letter_count: int,
        fuel_station_height: float,
        fuel_station_min_spacing: float,
        missile_speed: float,
        missile_width: float,
        missile_height: float,
        bridge_interval_y: float,
        bridge_height: float,
        bridge_narrow_min: float,
        bridge_narrow_max: float,
        helicopter_speed: float,
        helicopter_width: float,
        helicopter_height: float,
        helicopter_min_spacing: float,
        helicopter_score: int,
    ) -> None:
        self._world_width = world_width
        self._step_x = step_x
        self._segment_height = segment_height
        self._river_max_width = river_max_width
        self._bank_margin = bank_margin
        self._viewport_height = viewport_height
        self._plane_offset_from_camera = plane_offset_from_camera
        self._river_generation_buffer = river_generation_buffer
        self._plane_half_width = plane_half_width
        self._fuel_burn_per_second = fuel_burn_per_second
        self._fuel_capacity = fuel_capacity
        self._plane_width = plane_width
        self._river_min_width = river_min_width
        self._river_width_variation_step = river_width_variation_step
        self._fuel_refill_per_second = fuel_refill_per_second
        self._fuel_station_width = fuel_station_width
        self._fuel_station_letter_count = fuel_station_letter_count
        self._fuel_station_height = fuel_station_height
        self._fuel_station_min_spacing = fuel_station_min_spacing
        self._missile_speed = missile_speed
        self._missile_width = missile_width
        self._missile_height = missile_height
        self._bridge_interval_y = bridge_interval_y
        self._bridge_height = bridge_height
        self._bridge_narrow_min = bridge_narrow_min
        self._bridge_narrow_max = bridge_narrow_max
        self._helicopter_speed = helicopter_speed
        self._helicopter_width = helicopter_width
        self._helicopter_height = helicopter_height
        self._helicopter_min_spacing = helicopter_min_spacing
        self._helicopter_score = helicopter_score

    def initial_plane_state(self) -> dict:
        return {
            "x": self._world_width / 2,
            "y": self._plane_offset_from_camera,
            "vx": 0.0,
            "vy": 0.0,
            "fuel": self._fuel_capacity,
            "hp": 3,
            "score": 0,
            "actor": "plane",
        }

    def apply_input_to_plane(self, plane_state: dict, normalized_input: dict) -> dict:
        next_state = dict(plane_state)
        turn = normalized_input["turn"]

        if turn == "left":
            next_state["x"] = max(0.0, next_state["x"] - self._step_x)
        elif turn == "right":
            next_state["x"] = min(self._world_width, next_state["x"] + self._step_x)

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
        while next_segment_y <= target_y:
            y = next_segment_y
            dist_to_bridge = min(
                y % self._bridge_interval_y,
                self._bridge_interval_y - (y % self._bridge_interval_y),
            )
            near_bridge = dist_to_bridge <= 2.0 * self._segment_height
            effective_min = self._bridge_narrow_min if near_bridge else self._river_min_width
            effective_max = self._bridge_narrow_max if near_bridge else self._river_max_width
            river_width += random.uniform(-self._river_width_variation_step, self._river_width_variation_step)
            river_width = max(effective_min, min(effective_max, river_width))

            min_center_x = self._bank_margin + (river_width / 2)
            max_center_x = self._world_width - self._bank_margin - (river_width / 2)
            center_x += random.uniform(-20.0, 20.0)
            center_x = max(min_center_x, min(max_center_x, center_x))

            left_x = max(0.0, center_x - (river_width / 2))
            right_x = min(self._world_width, center_x + (river_width / 2))
            river_banks.append(
                {
                    "y": y,
                    "left_x": round(left_x, 2),
                    "right_x": round(right_x, 2),
                }
            )
            next_segment_y += self._segment_height

        return river_banks, next_segment_y, center_x, river_width

    def ensure_fuel_stations_until(
        self,
        fuel_stations: list[dict],
        next_station_id: int,
        next_eligible_y: float,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        while next_eligible_y <= target_y:
            station_y = next_eligible_y + random.uniform(0.0, self._fuel_station_min_spacing)
            if station_y > target_y:
                break

            left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=station_y)
            half_width = self._fuel_station_width / 2
            min_x = left_x + half_width
            max_x = right_x - half_width
            if min_x < max_x:
                station_x = random.uniform(min_x, max_x)
                fuel_stations.append(
                    {
                        "id": f"fuel_{next_station_id}",
                        "x": round(station_x, 2),
                        "y": round(station_y, 2),
                        "width": self._fuel_station_width,
                        "height": self._fuel_station_height,
                    }
                )
                next_station_id += 1

            next_eligible_y = station_y + self._fuel_station_min_spacing

        return fuel_stations, next_station_id, next_eligible_y

    def prune_old_banks(self, river_banks: list[dict], camera_y: float) -> list[dict]:
        last_crossed_bridge_index = int(max(0.0, (camera_y - self._bridge_height) // self._bridge_interval_y))
        min_y = max(0.0, (last_crossed_bridge_index - 1) * self._bridge_interval_y)
        return [segment for segment in river_banks if segment["y"] >= min_y]

    def banks_in_view(self, river_banks: list[dict], camera_y: float) -> list[dict]:
        min_y = camera_y - self._segment_height
        max_y = camera_y + self._viewport_height + self._segment_height
        return [segment for segment in river_banks if min_y <= segment["y"] <= max_y]

    def prune_old_fuel_stations(self, fuel_stations: list[dict], camera_y: float) -> list[dict]:
        min_y = camera_y - self._fuel_station_height
        return [station for station in fuel_stations if station["y"] + station["height"] >= min_y]

    def fuel_station_entities_in_view(self, fuel_stations: list[dict], camera_y: float) -> list[dict]:
        max_y = camera_y + self._viewport_height + self._segment_height
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
        left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=plane_state["y"])
        if (plane_state["x"] - self._plane_half_width) > left_x and (plane_state["x"] + self._plane_half_width) < right_x:
            return None

        plane_state["hp"] = max(0, int(plane_state["hp"]) - 1)
        plane_state["x"] = self._world_width / 2
        if plane_state["hp"] > 0:
            plane_state["fuel"] = self._fuel_capacity
        else:
            plane_state["fuel"] = 0.0
        return {
            "event_type": "collision_bank",
            "data": {
                "hp": plane_state["hp"],
                "fuel": int(plane_state["fuel"]),
            },
        }

    def apply_refuel_from_stations(self, plane_state: dict, fuel_stations: list[dict], elapsed_seconds: float) -> None:
        if elapsed_seconds <= 0 or plane_state["fuel"] >= self._fuel_capacity:
            return

        plane_x = float(plane_state["x"])
        plane_y = float(plane_state["y"])
        plane_half_width = self._plane_half_width

        for station in fuel_stations:
            station_left = float(station["x"]) - (float(station["width"]) / 2)
            station_right = float(station["x"]) + (float(station["width"]) / 2)
            station_top = float(station["y"])
            station_bottom = station_top + float(station["height"])

            x_overlap = (plane_x + plane_half_width) >= station_left and (plane_x - plane_half_width) <= station_right
            y_overlap = station_top <= plane_y <= station_bottom
            if x_overlap and y_overlap:
                plane_state["fuel"] = min(
                    self._fuel_capacity,
                    float(plane_state["fuel"]) + (self._fuel_refill_per_second * elapsed_seconds),
                )
                return

    def apply_fuel_burn_and_crash(self, plane_state: dict, elapsed_seconds: float) -> dict | None:
        if elapsed_seconds <= 0:
            return None

        plane_state["fuel"] = max(0.0, float(plane_state["fuel"]) - (self._fuel_burn_per_second * elapsed_seconds))
        if plane_state["fuel"] > 0:
            return None

        plane_state["hp"] = max(0, int(plane_state["hp"]) - 1)
        plane_state["x"] = self._world_width / 2
        plane_state["fuel"] = 0.0 if plane_state["hp"] <= 0 else self._fuel_capacity

        return {
            "event_type": "crash_fuel",
            "data": {
                "hp": plane_state["hp"],
                "fuel": int(plane_state["fuel"]),
            },
        }

    def advance_missiles_and_check_collisions(
        self, missiles: list[dict], fuel_stations: list[dict], bridges: list[dict], plane_state: dict,
        elapsed_seconds: float, helicopters: list[dict] | None = None,
    ) -> list[dict]:
        kept: list[dict] = []
        delta_y = self._missile_speed * elapsed_seconds
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
                s_bottom = float(station["y"])
                s_top = float(station["y"]) + float(station["height"])
                if m_right >= s_left and m_left <= s_right and m_top >= s_bottom and m_bottom <= s_top:
                    fuel_stations.remove(station)
                    plane_state["score"] = int(plane_state["score"]) + 10
                    hit = True
                    break
            if not hit:
                for bridge in bridges:
                    if bridge.get("destroyed"):
                        continue
                    b_left = float(bridge["left_x"])
                    b_right = float(bridge["right_x"])
                    b_bottom = float(bridge["y"])
                    b_top = b_bottom + float(bridge["height"])
                    if m_right >= b_left and m_left <= b_right and m_top >= b_bottom and m_bottom <= b_top:
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
                    h_bottom = float(heli["y"])
                    h_top = h_bottom + float(heli["height"])
                    if m_right >= h_left and m_left <= h_right and m_top >= h_bottom and m_bottom <= h_top:
                        heli["destroyed"] = True
                        plane_state["score"] = int(plane_state["score"]) + self._helicopter_score
                        hit = True
                        break
            if not hit:
                kept.append(missile)
        return kept

    def prune_old_missiles(self, missiles: list[dict], camera_y: float) -> list[dict]:
        max_y = camera_y + self._viewport_height + self._river_generation_buffer
        return [m for m in missiles if m["y"] <= max_y]

    def all_entities_in_view(
        self, fuel_stations: list[dict], missiles: list[dict], bridges: list[dict],
        camera_y: float, helicopters: list[dict] | None = None,
    ) -> list[dict]:
        entities = self.fuel_station_entities_in_view(fuel_stations=fuel_stations, camera_y=camera_y)
        min_y = camera_y - self._missile_height
        max_y = camera_y + self._viewport_height + self._missile_height
        for missile in missiles:
            if min_y <= missile["y"] <= max_y:
                entities.append(
                    {
                        "id": missile["id"],
                        "kind": "missile",
                        "x": missile["x"],
                        "y": missile["y"],
                        "width": missile["width"],
                        "height": missile["height"],
                    }
                )
        bridge_min_y = camera_y - self._bridge_height
        bridge_max_y = camera_y + self._viewport_height + self._bridge_height
        for bridge in bridges:
            if bridge["y"] + bridge["height"] >= bridge_min_y and bridge["y"] <= bridge_max_y:
                entities.append(
                    {
                        "id": bridge["id"],
                        "kind": "road" if bridge.get("destroyed") else "bridge",
                        "x": bridge["x"],
                        "y": bridge["y"],
                        "left_x": bridge["left_x"],
                        "right_x": bridge["right_x"],
                        "width": bridge["width"],
                        "height": bridge["height"],
                    }
                )
        if helicopters:
            heli_margin = self._helicopter_height
            heli_min_y = camera_y - heli_margin
            heli_max_y = camera_y + self._viewport_height + heli_margin
            for heli in helicopters:
                if heli.get("destroyed"):
                    continue
                if heli["y"] + heli["height"] >= heli_min_y and heli["y"] <= heli_max_y:
                    entities.append(
                        {
                            "id": heli["id"],
                            "kind": "helicopter",
                            "x": heli["x"],
                            "y": heli["y"],
                            "width": heli["width"],
                            "height": heli["height"],
                        }
                    )
        return entities

    def ensure_bridges_until(
        self,
        bridges: list[dict],
        next_bridge_y: float,
        next_bridge_id: int,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        while next_bridge_y <= target_y:
            left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=next_bridge_y)
            center_x = (left_x + right_x) / 2
            bridges.append(
                {
                    "id": f"bridge_{next_bridge_id}",
                    "x": round(center_x, 2),
                    "y": round(next_bridge_y, 2),
                    "left_x": round(left_x, 2),
                    "right_x": round(right_x, 2),
                    "width": round(right_x - left_x, 2),
                    "height": self._bridge_height,
                }
            )
            next_bridge_id += 1
            next_bridge_y += self._bridge_interval_y
        return bridges, next_bridge_id, next_bridge_y

    def prune_old_bridges(self, bridges: list[dict], camera_y: float) -> list[dict]:
        min_y = camera_y - self._bridge_height
        return [b for b in bridges if b["y"] + b["height"] >= min_y]

    def handle_bridge_collision(self, plane_state: dict, bridges: list[dict]) -> dict | None:
        plane_x = float(plane_state["x"])
        plane_y = float(plane_state["y"])
        for bridge in bridges:
            if bridge.get("destroyed"):
                continue
            b_bottom = float(bridge["y"])
            b_top = b_bottom + float(bridge["height"])
            b_left = float(bridge["left_x"])
            b_right = float(bridge["right_x"])
            if b_bottom <= plane_y <= b_top and b_left <= plane_x <= b_right:
                plane_state["hp"] = max(0, int(plane_state["hp"]) - 1)
                plane_state["x"] = self._world_width / 2
                plane_state["fuel"] = self._fuel_capacity if plane_state["hp"] > 0 else 0.0
                return {
                    "event_type": "collision_bridge",
                    "data": {
                        "hp": plane_state["hp"],
                        "fuel": int(plane_state["fuel"]),
                    },
                }
        return None

    def ensure_helicopters_until(
        self,
        helicopters: list[dict],
        next_helicopter_id: int,
        next_helicopter_y: float,
        river_banks: list[dict],
        target_y: float,
    ) -> tuple[list[dict], int, float]:
        while next_helicopter_y <= target_y:
            heli_y = next_helicopter_y + random.uniform(
                self._helicopter_min_spacing * 0.3,
                self._helicopter_min_spacing,
            )
            if heli_y > target_y:
                break
            left_x, right_x = self.bank_bounds_at_y(river_banks=river_banks, y=heli_y)
            river_width = right_x - left_x
            if river_width < self._helicopter_width * 2:
                next_helicopter_y = heli_y + self._helicopter_min_spacing
                continue
            half_w = self._helicopter_width / 2
            left_bound = left_x + half_w
            right_bound = right_x - half_w
            side = random.choice(["left", "right"])
            start_x = left_bound if side == "left" else right_bound
            direction = 1 if side == "left" else -1
            helicopters.append(
                {
                    "id": f"heli_{next_helicopter_id}",
                    "x": round(start_x, 2),
                    "y": round(heli_y, 2),
                    "width": self._helicopter_width,
                    "height": self._helicopter_height,
                    "speed": self._helicopter_speed,
                    "direction": direction,
                    "left_bound": round(left_bound, 2),
                    "right_bound": round(right_bound, 2),
                }
            )
            next_helicopter_id += 1
            next_helicopter_y = heli_y + self._helicopter_min_spacing
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
        min_y = camera_y - self._helicopter_height
        return [h for h in helicopters if h["y"] + h["height"] >= min_y]

    def handle_helicopter_collision(self, plane_state: dict, helicopters: list[dict]) -> dict | None:
        plane_x = float(plane_state["x"])
        plane_y = float(plane_state["y"])
        for heli in helicopters:
            if heli.get("destroyed"):
                continue
            h_left = float(heli["x"]) - float(heli["width"]) / 2
            h_right = float(heli["x"]) + float(heli["width"]) / 2
            h_bottom = float(heli["y"])
            h_top = h_bottom + float(heli["height"])
            x_hit = (plane_x + self._plane_half_width) >= h_left and (plane_x - self._plane_half_width) <= h_right
            if x_hit and h_bottom <= plane_y <= h_top:
                heli["destroyed"] = True
                plane_state["hp"] = max(0, int(plane_state["hp"]) - 1)
                plane_state["x"] = self._world_width / 2
                plane_state["fuel"] = self._fuel_capacity if plane_state["hp"] > 0 else 0.0
                return {
                    "event_type": "collision_helicopter",
                    "data": {
                        "hp": plane_state["hp"],
                        "fuel": int(plane_state["fuel"]),
                    },
                }
        return None

    @staticmethod
    def bank_bounds_at_y(river_banks: list[dict], y: float) -> tuple[float, float]:
        if not river_banks:
            return (0.0, 1000.0)

        nearest_segment = min(river_banks, key=lambda segment: abs(segment["y"] - y))
        return float(nearest_segment["left_x"]), float(nearest_segment["right_x"])
