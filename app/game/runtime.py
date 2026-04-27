"""Room-runtime data types shared by ``GameRoom`` and its controllers.

Living in their own module so the controller modules don't have to
``from app.game.game_room import ...`` and rebuild a circular dependency.
GameRoom owns the **instances**; controllers reach in through their
``self._room`` reference. Keep this module light — pure data only, no
gameplay logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.game.sabotages import SabotageDefinition
from app.game.tasks import TaskDefinition


class GameRoomError(Exception):
    """Domain-level error surfaced from any controller. The WS layer turns
    these into ``error`` frames with the matching ``code``."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


VALID_EVENT_SEVERITIES = ("info", "warn", "danger")


@dataclass
class EventEntry:
    seq: int  # monotonic per room, starts at 1, only increases
    severity: str  # "info" | "warn" | "danger"
    message: str  # plain German text shown to all players


@dataclass
class TaskRuntime:
    definition: TaskDefinition
    x: float
    y: float
    status: str = "available"  # "available" | "in_progress" | "cooldown"
    cooldown_remaining: float = 0.0
    per_player_progress: dict[str, float] = field(default_factory=dict)


@dataclass
class SabotageRuntime:
    definition: SabotageDefinition
    cooldown_remaining: float = 0.0
    # True for coffee_outage while coffee==0, for meeting while meeting_active_for>0.
    active: bool = False


@dataclass
class Body:
    id: str  # uuid hex
    x: float
    y: float
    victim_player_id: str
    victim_name: str
    color: str  # victim's color, for rendering


@dataclass
class MiniGameSession:
    """Tier 3.1: per-player live mini-game state. The framework owns this
    dict; the plugin owns its inner ``state`` schema."""

    plugin_id: str
    task_id: str
    state: dict
