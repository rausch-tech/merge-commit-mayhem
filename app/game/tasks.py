"""
Statische Task-Definitionen fuer den MVP. Positionen kommen aus dem
Map-JSON (taskAnchors) und werden bei GameRoom-Init eingesetzt.
"""

from dataclasses import dataclass
from typing import Final

# Global gameplay constants (single source of truth -- also reused by game_room).
TASK_INTERACTION_RADIUS: Final[float] = 40.0  # px around task center where E works
TASK_RESPAWN_COOLDOWN: Final[float] = 8.0     # s until a completed task becomes available again


@dataclass(frozen=True)
class TaskDefinition:
    id: str
    title: str
    room: str   # display label only, e.g. "open_space"
    required_seconds: float
    release_progress_reward: int = 0
    pipeline_stability_reward: int = 0
    coffee_level_set: int | None = None  # if set, coffee_level is clamped to this value


TASK_DEFINITIONS: Final[list[TaskDefinition]] = [
    TaskDefinition(
        id="fix_unit_tests",
        title="Unit Tests fixen",
        room="open_space",
        required_seconds=5.0,
        release_progress_reward=10,
    ),
    TaskDefinition(
        id="review_pr",
        title="Pull Request reviewen",
        room="open_space",
        required_seconds=5.0,
        release_progress_reward=8,
    ),
    TaskDefinition(
        id="repair_deployment",
        title="Deployment reparieren",
        room="server_room",
        required_seconds=6.0,
        pipeline_stability_reward=15,
    ),
    TaskDefinition(
        id="refill_coffee",
        title="Kaffee auffuellen",
        room="kitchen",
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
