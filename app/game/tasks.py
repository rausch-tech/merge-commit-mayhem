"""
Statische Task-Definitionen fuer den MVP. Positionen kommen aus dem
Map-JSON (taskAnchors) und werden bei GameRoom-Init eingesetzt.
"""

from dataclasses import dataclass
from typing import Final

# Global gameplay constants (single source of truth -- also reused by game_room).
TASK_INTERACTION_RADIUS: Final[float] = 40.0  # px around task center where E works
TASK_RESPAWN_COOLDOWN: Final[float] = 8.0  # s until a completed task becomes available again
SABOTAGE_PANEL_INTERACTION_RADIUS: Final[float] = 50.0  # Tier 2.4: repair-panel reach
VENT_INTERACTION_RADIUS: Final[float] = 50.0  # Tier 2.3: chaos-only vent reach


@dataclass(frozen=True)
class TaskDefinition:
    id: str
    title: str
    room: str  # display label only, e.g. "open_space"
    required_seconds: float
    release_progress_reward: int = 0
    pipeline_stability_reward: int = 0
    coffee_level_set: int | None = None  # if set, coffee_level is clamped to this value
    incidents_change: int = 0  # negative reduces incidents on completion
    # Tier 3: when set, task_hold_start opens the named mini-game instead of
    # starting the hold-E progress bar. ``required_seconds`` is ignored on
    # this path; the mini-game decides its own duration via plugin logic.
    mini_game: str | None = None


TASK_DEFINITIONS: Final[list[TaskDefinition]] = [
    TaskDefinition(
        id="fix_unit_tests",
        title="Unit Tests fixen",
        room="open_space",
        required_seconds=5.0,
        release_progress_reward=10,
        mini_game="test_suite_repair",
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
        mini_game="cable_pairing",
    ),
    TaskDefinition(
        id="refill_coffee",
        title="Kaffee auffuellen",
        room="kitchen",
        required_seconds=4.0,
        coffee_level_set=100,
        mini_game="coffee_pour",
    ),
    TaskDefinition(
        id="analyze_logs",
        title="Logs analysieren",
        room="server_room",
        required_seconds=7.0,
        incidents_change=-15,
    ),
    TaskDefinition(
        id="calm_legacy_service",
        title="Legacy-Service beruhigen",
        room="legacy_basement",
        required_seconds=8.0,
        incidents_change=-20,
    ),
    TaskDefinition(
        id="reduce_scope",
        title="Scope reduzieren",
        room="meeting_room",
        required_seconds=5.0,
        release_progress_reward=12,
    ),
    TaskDefinition(
        id="write_release_notes",
        title="Release Notes schreiben",
        room="meeting_room",
        required_seconds=4.0,
        release_progress_reward=6,
    ),
]


def task_by_id(task_id: str) -> TaskDefinition:
    """Lookup helper; raises KeyError if the id is unknown."""
    for task in TASK_DEFINITIONS:
        if task.id == task_id:
            return task
    raise KeyError(task_id)
