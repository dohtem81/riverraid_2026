from dataclasses import dataclass


@dataclass(frozen=True)
class AuthenticatedPlayer:
    player_id: str
    username: str


@dataclass(frozen=True)
class InputCommand:
    input_seq: int
    thrust: str
    turn: str
    fire: bool
    dock_request: bool
