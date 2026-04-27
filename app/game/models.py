import time
from enum import Enum

from pydantic import BaseModel, Field


class Phase(str, Enum):  # noqa: UP042
    LOBBY = "lobby"
    PLAYING = "playing"
    MEETING = "meeting"
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
    is_alive: bool = True
    is_connected: bool = True
    disconnected_at_monotonic: float | None = None
    x: float = 0.0
    y: float = 0.0
    input_state: InputState = Field(default_factory=InputState)
    joined_at: float = Field(default_factory=time.monotonic)
    # Tier 3.5: lobby preference (one of the release-team role ids, or None).
    # Server respects best-effort during _assign_roles; ignored for chaos.
    preferred_role: str | None = None
    # Tier 3.5: PER-PLAYER coffee energy (0..max_coffee from role). NOT to
    # be confused with the room-level ``coffee_level`` (int 0..100) used for
    # team-wide UI signals + the coffee_outage sabotage gate. coffee_energy
    # drives this player's movement penalty and task-speed bonus only.
    # Defaults to 100 so legacy code paths that don't init it stay sensible.
    coffee_energy: float = 100.0
    max_coffee: float = 100.0
    # Tier 3.5: ability used this round (single-use for now). Reset on round.
    ability_used: bool = False
    # Tier 3.5: list of personal task ids (release: real, chaos: fake).
    assigned_task_ids: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": False}
