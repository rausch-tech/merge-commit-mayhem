"""Tests for app/game/game_map.py: Pydantic models, load_map, and helpers."""

import json
import tempfile
from pathlib import Path

import pytest

from app.game.game_map import (
    DEFAULT_MAP,
    GameMap,
    compute_walls,
    load_map,
    task_position_map,
    war_room_bounds_for,
)
from app.game.walls import WALL_THICKNESS

# --- load_map + validation --------------------------------------------------


def test_default_map_loads_without_error():
    assert DEFAULT_MAP is not None
    assert DEFAULT_MAP.name == "default-office"


def test_default_map_has_expected_size():
    assert DEFAULT_MAP.size.width == 4800
    assert DEFAULT_MAP.size.height == 3200


def test_default_map_has_six_rooms():
    assert len(DEFAULT_MAP.rooms) == 6


def test_default_map_room_ids_are_unique():
    ids = [r.id for r in DEFAULT_MAP.rooms]
    assert len(ids) == len(set(ids))


def test_default_map_has_three_wall_lines():
    assert len(DEFAULT_MAP.wall_lines) == 3


def test_default_map_has_spawn_points():
    assert len(DEFAULT_MAP.spawn_points) == 6


def test_default_map_has_task_anchors():
    assert len(DEFAULT_MAP.task_anchors) == 4


def test_default_map_war_room_id_exists():
    room_ids = {r.id for r in DEFAULT_MAP.rooms}
    assert DEFAULT_MAP.war_room_id in room_ids


def test_load_map_raises_on_missing_required_field():
    minimal = {
        "name": "bad",
        "size": {"width": 100, "height": 100},
        "rooms": [],
        # war_room_id missing
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(minimal, f)
        tmp_path = Path(f.name)
    with pytest.raises((Exception,)):  # noqa: B017 — multiple validation paths can throw
        load_map(tmp_path)


def test_load_map_raises_on_extra_field_in_room():
    data = {
        "name": "test",
        "size": {"width": 100, "height": 100},
        "rooms": [
            {
                "id": "x",
                "title": "X",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 100,
                "color": "#fff",
                "extraField": 99,
            }
        ],
        "warRoomId": "x",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        tmp_path = Path(f.name)
    with pytest.raises((Exception,)):  # noqa: B017 — multiple validation paths can throw
        load_map(tmp_path)


# --- compute_walls -----------------------------------------------------------


def test_compute_walls_returns_10_segments():
    """Default map: 3 vertical wall segs x 2 walls + 4 horizontal segs = 10."""
    walls = compute_walls(DEFAULT_MAP)
    assert len(walls) == 10


def test_compute_walls_are_tuples_of_four_ints():
    walls = compute_walls(DEFAULT_MAP)
    for w in walls:
        assert len(w) == 4
        assert all(isinstance(v, int) for v in w)


def test_compute_walls_vertical_wall_at_1600():
    walls = compute_walls(DEFAULT_MAP)
    # All vertical-wall segments for line x=1600 should have x1 < 1600 < x2.
    vert_1600 = [
        w for w in walls if w[0] == 1600 - WALL_THICKNESS and w[2] == 1600 + WALL_THICKNESS
    ]
    assert len(vert_1600) == 3  # 3 segments (2 doors cut it into 3)


def test_compute_walls_horizontal_wall_at_1600():
    walls = compute_walls(DEFAULT_MAP)
    # Horizontal wall segments for line y=1600.
    horiz_1600 = [
        w for w in walls if w[1] == 1600 - WALL_THICKNESS and w[3] == 1600 + WALL_THICKNESS
    ]
    assert len(horiz_1600) == 4  # 3 doors cut it into 4


# --- war_room_bounds_for -----------------------------------------------------


def test_war_room_bounds_correct():
    x_min, y_min, x_max, y_max = war_room_bounds_for(DEFAULT_MAP)
    assert x_min == 1600
    assert y_min == 1600
    assert x_max == 3200
    assert y_max == 3200


def test_war_room_bounds_raises_if_id_not_found():
    data = DEFAULT_MAP.model_copy(update={"war_room_id": "no_such_room"})
    with pytest.raises(ValueError, match="no_such_room"):
        war_room_bounds_for(data)


# --- task_position_map -------------------------------------------------------


def test_task_position_map_has_all_four_tasks():
    positions = task_position_map(DEFAULT_MAP)
    expected = {"fix_unit_tests", "review_pr", "repair_deployment", "refill_coffee"}
    assert set(positions.keys()) == expected


def test_task_position_map_values_are_float_pairs():
    positions = task_position_map(DEFAULT_MAP)
    for _tid, (x, y) in positions.items():
        assert isinstance(x, float)
        assert isinstance(y, float)


def test_task_positions_match_json():
    positions = task_position_map(DEFAULT_MAP)
    assert positions["fix_unit_tests"] == (400.0, 400.0)
    assert positions["refill_coffee"] == (4000.0, 800.0)


# --- round-trip: model_dump / model_validate --------------------------------


def test_default_map_survives_round_trip():
    dumped = DEFAULT_MAP.model_dump(by_alias=True)
    reloaded = GameMap.model_validate(dumped)
    assert reloaded.name == DEFAULT_MAP.name
    assert len(reloaded.rooms) == len(DEFAULT_MAP.rooms)
    assert reloaded.war_room_id == DEFAULT_MAP.war_room_id
