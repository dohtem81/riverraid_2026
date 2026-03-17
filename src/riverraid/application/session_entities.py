from abc import ABC, abstractmethod
from dataclasses import dataclass


class BaseSessionEntity(ABC):
    @abstractmethod
    def to_dict(self) -> dict:
        raise NotImplementedError

    @staticmethod
    def _with_optional_fields(payload: dict, **optional_fields) -> dict:
        for key, value in optional_fields.items():
            if value is not None:
                payload[key] = value
        return payload


@dataclass
class Plane(BaseSessionEntity):
    x: float
    y: float
    vx: float
    vy: float
    fuel: float
    hp: int
    score: int
    actor: str = "plane"

    @classmethod
    def from_dict(cls, data: dict) -> "Plane":
        return cls(
            x=float(data["x"]),
            y=float(data["y"]),
            vx=float(data.get("vx", 0.0)),
            vy=float(data.get("vy", 0.0)),
            fuel=float(data["fuel"]),
            hp=int(data["hp"]),
            score=int(data["score"]),
            actor=str(data.get("actor", "plane")),
        )

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "vy": self.vy,
            "fuel": self.fuel,
            "hp": self.hp,
            "score": self.score,
            "actor": self.actor,
        }


@dataclass
class RiverBank(BaseSessionEntity):
    y: float
    left_x: float
    right_x: float

    @classmethod
    def from_dict(cls, data: dict) -> "RiverBank":
        return cls(y=float(data["y"]), left_x=float(data["left_x"]), right_x=float(data["right_x"]))

    def to_dict(self) -> dict:
        return {"y": self.y, "left_x": self.left_x, "right_x": self.right_x}


@dataclass
class FuelStation(BaseSessionEntity):
    id: str
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_dict(cls, data: dict) -> "FuelStation":
        return cls(
            id=str(data["id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            width=float(data["width"]),
            height=float(data["height"]),
        )

    def to_dict(self) -> dict:
        return {"id": self.id, "x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass
class Missile(BaseSessionEntity):
    id: str
    x: float
    y: float
    width: float
    height: float
    fired_at: float = 0.0
    vx: float = 0.0  # non-zero for tank missiles (horizontal travel)
    prev_x: float | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Missile":
        return cls(
            id=str(data["id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            width=float(data["width"]),
            height=float(data["height"]),
            fired_at=float(data.get("fired_at", 0.0)),
            vx=float(data.get("vx", 0.0)),
            prev_x=float(data["prev_x"]) if data.get("prev_x") is not None else None,
        )

    def to_dict(self) -> dict:
        payload = {"id": self.id, "x": self.x, "y": self.y, "width": self.width, "height": self.height, "fired_at": self.fired_at, "vx": self.vx}
        if self.prev_x is not None:
            payload["prev_x"] = self.prev_x
        return payload


@dataclass
class Bridge(BaseSessionEntity):
    id: str
    x: float
    y: float
    left_x: float
    right_x: float
    width: float
    height: float
    destroyed: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "Bridge":
        return cls(
            id=str(data["id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            left_x=float(data["left_x"]),
            right_x=float(data["right_x"]),
            width=float(data["width"]),
            height=float(data["height"]),
            destroyed=bool(data.get("destroyed", False)),
        )

    def to_dict(self) -> dict:
        return self._with_optional_fields(
            {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "left_x": self.left_x,
            "right_x": self.right_x,
            "width": self.width,
            "height": self.height,
            },
            destroyed=True if self.destroyed else None,
        )


@dataclass
class Helicopter(BaseSessionEntity):
    id: str
    x: float
    y: float
    width: float
    height: float
    speed: float
    direction: int
    left_bound: float
    right_bound: float
    destroyed: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "Helicopter":
        return cls(
            id=str(data["id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            width=float(data["width"]),
            height=float(data["height"]),
            speed=float(data["speed"]),
            direction=int(data["direction"]),
            left_bound=float(data["left_bound"]),
            right_bound=float(data["right_bound"]),
            destroyed=bool(data.get("destroyed", False)),
        )

    def to_dict(self) -> dict:
        return self._with_optional_fields(
            {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "speed": self.speed,
            "direction": self.direction,
            "left_bound": self.left_bound,
            "right_bound": self.right_bound,
            },
            destroyed=True if self.destroyed else None,
        )


@dataclass
class Tank(BaseSessionEntity):
    id: str
    x: float
    y: float
    width: float
    height: float
    side: str  # "left" or "right" (which bank it sits on)
    last_shot_at: float = 0.0
    destroyed: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "Tank":
        return cls(
            id=str(data["id"]),
            x=float(data["x"]),
            y=float(data["y"]),
            width=float(data["width"]),
            height=float(data["height"]),
            side=str(data["side"]),
            last_shot_at=float(data.get("last_shot_at", 0.0)),
            destroyed=bool(data.get("destroyed", False)),
        )

    def to_dict(self) -> dict:
        return self._with_optional_fields(
            {
                "id": self.id,
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height,
                "side": self.side,
                "last_shot_at": self.last_shot_at,
            },
            destroyed=True if self.destroyed else None,
        )
