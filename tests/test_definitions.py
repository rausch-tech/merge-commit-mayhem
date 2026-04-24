import pytest

from app.game.rooms import ROOM_LAYOUT
from app.game.sabotages import (
    COFFEE_SLOW_SPEED,
    MEETING_DURATION,
    NORMAL_SPEED,
    SABOTAGE_DEFINITIONS,
    sabotage_by_id,
)
from app.game.tasks import (
    TASK_DEFINITIONS,
    TASK_INTERACTION_RADIUS,
    TASK_RESPAWN_COOLDOWN,
    task_by_id,
)


def test_task_ids_are_unique():
    ids = [t.id for t in TASK_DEFINITIONS]
    assert len(ids) == len(set(ids))


def test_task_rooms_exist_in_layout():
    room_ids = {r["id"] for r in ROOM_LAYOUT}
    for task in TASK_DEFINITIONS:
        assert task.room in room_ids, f"{task.id} refers to unknown room {task.room}"


def test_task_positions_are_inside_their_room():
    rooms = {r["id"]: r for r in ROOM_LAYOUT}
    for task in TASK_DEFINITIONS:
        room = rooms[task.room]
        assert room["x"] <= task.x <= room["x"] + room["width"], (
            f"{task.id} x={task.x} outside {task.room} [{room['x']}..{room['x']+room['width']}]"
        )
        assert room["y"] <= task.y <= room["y"] + room["height"], (
            f"{task.id} y={task.y} outside {task.room} [{room['y']}..{room['y']+room['height']}]"
        )


def test_task_rewards_positive_or_zero():
    for task in TASK_DEFINITIONS:
        assert task.release_progress_reward >= 0
        assert task.pipeline_stability_reward >= 0
        assert task.required_seconds > 0


def test_task_by_id_lookup():
    assert task_by_id("fix_unit_tests").title == "Unit Tests fixen"
    with pytest.raises(KeyError):
        task_by_id("not_a_task")


def test_sabotage_ids_are_unique():
    ids = [s.id for s in SABOTAGE_DEFINITIONS]
    assert len(ids) == len(set(ids))


def test_sabotage_cooldowns_positive():
    for sab in SABOTAGE_DEFINITIONS:
        assert sab.cooldown_seconds > 0


def test_sabotage_by_id_lookup():
    assert sabotage_by_id("ci_cd_red").title == "CI/CD Rot"
    with pytest.raises(KeyError):
        sabotage_by_id("not_a_sabotage")


def test_constants_are_sensible():
    assert TASK_INTERACTION_RADIUS > 0
    assert TASK_RESPAWN_COOLDOWN > 0
    assert NORMAL_SPEED > COFFEE_SLOW_SPEED > 0
    assert MEETING_DURATION > 0
