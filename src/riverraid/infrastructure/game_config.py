"""Loads game constants from riverraid/config/game.yaml (shipped with the package).

Derived values (those computed from other values) are computed here so the
YAML stays minimal and human-writable.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.resources
from pathlib import Path

import yaml


@dataclass(frozen=True)
class GameConfig:
    # ── World ─────────────────────────────────────────────────────────────────
    world_width: float
    viewport_height: float
    scroll_speed: float
    tick_interval_seconds: float
    river_generation_buffer: float

    # ── River ─────────────────────────────────────────────────────────────────
    segment_height: float
    river_max_width: float
    bank_margin: float
    river_width_variation_step: float

    # ── Rendering ─────────────────────────────────────────────────────────────
    land_decoration_coverage: float

    # ── Plane ─────────────────────────────────────────────────────────────────
    plane_half_width: float
    step_x: float
    high_speed_multiplier: float
    low_speed_multiplier: float
    plane_offset_from_camera: float

    # ── Fuel ──────────────────────────────────────────────────────────────────
    fuel_burn_per_second: float
    fuel_capacity: float
    fuel_refill_per_second: float

    # ── Fuel station ──────────────────────────────────────────────────────────
    fuel_station_letter_count: int

    # ── Missiles ──────────────────────────────────────────────────────────────
    missile_speed: float
    missile_width: float
    missile_height: float
    missile_lifetime_seconds: float
    missile_cooldown_seconds: float

    # ── Bridges ───────────────────────────────────────────────────────────────
    bridge_height: float

    # ── Helicopters ───────────────────────────────────────────────────────────
    helicopter_speed: float
    helicopter_width: float
    helicopter_height: float
    helicopter_min_spacing: float
    helicopter_score: int
    # ── Jets ─────────────────────────────────────────────────────────────────
    jet_speed: float
    jet_width: float
    jet_height: float
    jet_min_spacing: float
    # ── Tanks ─────────────────────────────────────────────────────────────────
    tank_width: float
    tank_height: float
    tank_shoot_interval_seconds: float
    tank_missile_speed_x: float
    tank_missile_width: float
    tank_missile_height: float
    tank_min_spacing: float
    tank_score: int
    # ── Derived (computed from the values above) ──────────────────────────────
    plane_width: float           # = plane_half_width * 2
    river_min_width: float       # = plane_width * 9
    fuel_station_width: float    # = plane_width
    fuel_station_height: float   # = plane_width * fuel_station_letter_count
    fuel_station_min_spacing: float  # = scroll_speed * 8
    bridge_interval_y: float     # = scroll_speed * 30
    bridge_narrow_min: float     # = plane_width * 5
    bridge_narrow_max: float     # = plane_width * 10


def load_game_config(path: Path | None = None) -> GameConfig:
    """Load and return a GameConfig from a YAML file.

    Args:
        path: Optional explicit path override. When omitted the bundled
              ``riverraid/config/game.yaml`` is read via importlib.resources.
    """
    if path is not None:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        ref = importlib.resources.files("riverraid.config").joinpath("game.yaml")
        raw = yaml.safe_load(ref.read_text(encoding="utf-8"))

    # Base values
    plane_half_width: float = float(raw["plane_half_width"])
    scroll_speed: float = float(raw["scroll_speed"])
    plane_width = plane_half_width * 2
    fuel_station_letter_count: int = int(raw["fuel_station_letter_count"])
    land_decoration_coverage = float(raw.get("land_decoration_coverage", 0.20))
    if not 0.0 <= land_decoration_coverage <= 1.0:
        raise ValueError("land_decoration_coverage must be between 0.0 and 1.0")

    return GameConfig(
        # World
        world_width=float(raw["world_width"]),
        viewport_height=float(raw["viewport_height"]),
        scroll_speed=scroll_speed,
        tick_interval_seconds=float(raw["tick_interval_seconds"]),
        river_generation_buffer=float(raw["river_generation_buffer"]),
        # River
        segment_height=float(raw["segment_height"]),
        river_max_width=float(raw["river_max_width"]),
        bank_margin=float(raw["bank_margin"]),
        river_width_variation_step=float(raw["river_width_variation_step"]),
        # Rendering
        land_decoration_coverage=land_decoration_coverage,
        # Plane
        plane_half_width=plane_half_width,
        step_x=float(raw["step_x"]),
        high_speed_multiplier=float(raw.get("high_speed_multiplier", 1.2)),
        low_speed_multiplier=float(raw.get("low_speed_multiplier", 0.8)),
        plane_offset_from_camera=float(raw["plane_offset_from_camera"]),
        # Fuel
        fuel_burn_per_second=float(raw["fuel_burn_per_second"]),
        fuel_capacity=float(raw["fuel_capacity"]),
        fuel_refill_per_second=float(raw["fuel_refill_per_second"]),
        # Fuel station
        fuel_station_letter_count=fuel_station_letter_count,
        # Missiles
        missile_speed=float(raw["missile_speed"]),
        missile_width=float(raw["missile_width"]),
        missile_height=float(raw["missile_height"]),
        missile_lifetime_seconds=float(raw["missile_lifetime_seconds"]),
        missile_cooldown_seconds=float(raw["missile_cooldown_seconds"]),
        # Bridges
        bridge_height=float(raw["bridge_height"]),
        # Helicopters
        helicopter_speed=float(raw["helicopter_speed"]),
        helicopter_width=float(raw["helicopter_width"]),
        helicopter_height=float(raw["helicopter_height"]),
        helicopter_min_spacing=float(raw["helicopter_min_spacing"]),
        helicopter_score=int(raw["helicopter_score"]),
        # Jets
        jet_speed=float(raw.get("jet_speed", 260.0)),
        jet_width=float(raw.get("jet_width", 44.0)),
        jet_height=float(raw.get("jet_height", 16.0)),
        jet_min_spacing=float(raw.get("jet_min_spacing", 520.0)),
        # Tanks
        tank_width=float(raw["tank_width"]),
        tank_height=float(raw["tank_height"]),
        tank_shoot_interval_seconds=float(raw["tank_shoot_interval_seconds"]),
        tank_missile_speed_x=float(raw["tank_missile_speed_x"]),
        tank_missile_width=float(raw["tank_missile_width"]),
        tank_missile_height=float(raw["tank_missile_height"]),
        tank_min_spacing=float(raw["tank_min_spacing"]),
        tank_score=int(raw["tank_score"]),
        # Derived
        plane_width=plane_width,
        river_min_width=plane_width * 9.0,
        fuel_station_width=plane_width,
        fuel_station_height=plane_width * fuel_station_letter_count,
        fuel_station_min_spacing=scroll_speed * 8.0,
        bridge_interval_y=scroll_speed * 30.0,
        bridge_narrow_min=plane_width * 5.0,
        bridge_narrow_max=plane_width * 10.0,
    )
