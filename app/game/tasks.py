"""
Statische Task-Definitionen für den MVP. Positionen sind absolute
Weltkoordinaten (selbes Koordinatensystem wie ROOM_LAYOUT).
Wechsel auf rooms.json/tasks.json kommt in Sprint 4.
"""

from dataclasses import dataclass, field
from typing import Final

# Global gameplay constants (single source of truth — also reused by game_room).
TASK_INTERACTION_RADIUS: Final[float] = 40.0  # px around task center where E works
TASK_RESPAWN_COOLDOWN: Final[float] = 8.0     # s until a completed task becomes available again


@dataclass(frozen=True)
class TaskDefinition:
    id: str
    title: str
    room: str
    x: float
    y: float
    required_seconds: float
    release_progress_reward: int = 0
    pipeline_stability_reward: int = 0
    coffee_level_set: int | None = None  # if set, coffee_level is clamped to this value


TASK_DEFINITIONS: Final[list[TaskDefinition]] = [
    TaskDefinition(
        id="fix_unit_tests",
        title="Unit Tests fixen",
        room="open_space",
        x=200.0,
        y=200.0,
        required_seconds=5.0,
        release_progress_reward=10,
    ),
    TaskDefinition(
        id="review_pr",
        title="Pull Request reviewen",
        room="open_space",
        x=550.0,
        y=600.0,
        required_seconds=5.0,
        release_progress_reward=8,
    ),
    TaskDefinition(
        id="repair_deployment",
        title="Deployment reparieren",
        room="server_room",
        x=400.0,
        y=1200.0,
        required_seconds=6.0,
        pipeline_stability_reward=15,
    ),
    TaskDefinition(
        id="refill_coffee",
        title="Kaffee auffüllen",
        room="kitchen",
        x=2000.0,
        y=400.0,
        required_seconds=4.0,
        coffee_level_set=100,
    ),
]


def task_by_id(task_id: str) -> TaskDefinition:
    """Lookup helper; raises KeyError if the id is unknown."""
    for task in TASK_DEFINITIONS:
        if task.id == task_id:
            return task
    raise KeyError(task_id)
