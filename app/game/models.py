import time
from enum import Enum

from pydantic import BaseModel, Field


class Phase(str, Enum):
    LOBBY = "lobby"
    PLAYING = "playing"
    ENDED = "ended"


class InputState(BaseModel):
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False


class Player(BaseModel):
    id: str
    name: str
    color: str
    is_host: bool = False
    role: str | None = None
    team: str | None = None
    x: float = 0.0
    y: float = 0.0
    input_state: InputState = Field(default_factory=InputState)
    joined_at: float = Field(default_factory=time.monotonic)

    model_config = {"arbitrary_types_allowed": False}
