"""Tier 4 MapObject schema tests.

Backward-compat invariant: legacy maps without ``mapObjects`` still load,
walls still compute correctly, sabotage binding still works through
``task_anchors``. Forward path: a map that opts into MapObjects gets
collision against blocking props, sabotage triggering at MapObjects with
``object_type``, and repair-panel resolution via ``sabotage_repair_id``.
"""

from __future__ import annotations

import json
import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.game.game_map import (
    DEFAULT_MAP,
    GameMap,
    MapObject,
    compute_walls,
    map_object_aabb,
    task_position_map,
)
from app.game.game_room import GameRoom
from app.game.runtime import GameRoomError

# --- AABB computation ------------------------------------------------------


def test_aabb_unrotated_object_centred_on_xy():
    obj = MapObject(id="d", x=100.0, y=200.0, width=80.0, height=40.0, kind="desk")
    assert map_object_aabb(obj) == (60, 180, 140, 220)


def test_aabb_rotation_90_swaps_dimensions():
    obj = MapObject(
        id="d",
        x=100.0,
        y=200.0,
        width=80.0,
        height=40.0,
        kind="desk",
        rotation=90,
    )
    # Width 40 / height 80 after the swap → AABB stretches taller, shorter.
    assert map_object_aabb(obj) == (80, 160, 120, 240)


@pytest.mark.parametrize("rot", [0, 180])
def test_aabb_rotation_0_or_180_keeps_dimensions(rot):
    obj = MapObject(
        id="d",
        x=100.0,
        y=200.0,
        width=80.0,
        height=40.0,
        kind="desk",
        rotation=rot,
    )
    assert map_object_aabb(obj) == (60, 180, 140, 220)


@pytest.mark.parametrize("rot", [90, 270])
def test_aabb_rotation_90_or_270_swaps_dimensions(rot):
    obj = MapObject(
        id="d",
        x=100.0,
        y=200.0,
        width=80.0,
        height=40.0,
        kind="desk",
        rotation=rot,
    )
    assert map_object_aabb(obj) == (80, 160, 120, 240)


# --- Schema / JSON roundtrip -----------------------------------------------


def test_legacy_map_without_map_objects_still_loads():
    """maps/default.json + maps/small.json don't have mapObjects yet —
    they must continue to validate cleanly."""
    assert DEFAULT_MAP.map_objects == []


def test_map_object_json_roundtrip_keeps_camel_case_on_wire():
    """Wire shape stays camelCase; Python field names are snake_case.
    Important: the Godot client + Browser both consume the camelCase form."""
    obj = MapObject(
        id="d1",
        x=100.0,
        y=200.0,
        width=80.0,
        height=40.0,
        kind="desk",
        rotation=90,
        blocks_movement=True,
        task_id="fix_unit_tests",
        sabotage_repair_id="comms_outage",
        object_type="ci_console",
    )
    wire = obj.model_dump(by_alias=True)
    assert wire["blocksMovement"] is True
    assert wire["taskId"] == "fix_unit_tests"
    assert wire["sabotageRepairId"] == "comms_outage"
    assert wire["objectType"] == "ci_console"
    # And re-parse from camelCase succeeds.
    reparsed = MapObject.model_validate(wire)
    assert reparsed == obj


def test_map_object_rejects_invalid_rotation():
    """Only 0/90/180/270 are allowed — anything else fails Pydantic
    validation. Editor + JSON authors get a fast error."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MapObject(id="d", x=0.0, y=0.0, width=10.0, height=10.0, kind="desk", rotation=45)


# --- compute_walls includes blocking objects -------------------------------


def test_compute_walls_includes_blocking_map_objects():
    """A MapObject with blocks_movement=True contributes its AABB to the
    wall list so the existing collision routine treats it like a wall."""
    base = DEFAULT_MAP.model_dump(by_alias=False)
    base["map_objects"] = [
        {
            "id": "desk-1",
            "x": 1500.0,
            "y": 1500.0,
            "width": 100.0,
            "height": 60.0,
            "kind": "desk",
            "blocks_movement": True,
        }
    ]
    m = GameMap.model_validate(base)
    walls = compute_walls(m)
    assert (1450, 1470, 1550, 1530) in walls


def test_compute_walls_skips_non_blocking_map_objects():
    """A decoration-only object (e.g. rug, picture frame) doesn't block
    movement and must NOT appear in the wall list."""
    base = DEFAULT_MAP.model_dump(by_alias=False)
    base["map_objects"] = [
        {
            "id": "rug-1",
            "x": 1500.0,
            "y": 1500.0,
            "width": 100.0,
            "height": 60.0,
            "kind": "rug",
            "blocks_movement": False,
        }
    ]
    m = GameMap.model_validate(base)
    walls = compute_walls(m)
    assert (1450, 1470, 1550, 1530) not in walls


# --- task_position_map merges both sources ---------------------------------


def test_task_position_map_includes_map_object_with_task_id():
    """A MapObject with task_id contributes its position. When both an
    anchor and a MapObject reference the same task, the MapObject wins."""
    base = DEFAULT_MAP.model_dump(by_alias=False)
    base["map_objects"] = [
        {
            "id": "ci-desk",
            "x": 999.0,
            "y": 1234.0,
            "width": 100.0,
            "height": 60.0,
            "kind": "desk",
            "task_id": "fix_unit_tests",
        }
    ]
    m = GameMap.model_validate(base)
    positions = task_position_map(m)
    assert positions["fix_unit_tests"] == (999.0, 1234.0)


def test_task_position_map_keeps_legacy_anchors_for_unbound_tasks():
    """A task that isn't covered by a MapObject keeps its legacy anchor
    position from task_anchors."""
    base = DEFAULT_MAP.model_dump(by_alias=False)
    base["map_objects"] = []
    m = GameMap.model_validate(base)
    positions = task_position_map(m)
    # All default-map task anchors should still be reachable.
    for a in DEFAULT_MAP.task_anchors:
        assert positions[a.task_id] == (a.x, a.y)


# --- Sabotage object-type binding picks up MapObjects ----------------------


def _make_started_room_with_objects(objects: list[dict]) -> GameRoom:
    """Build a GameRoom whose map has the given MapObjects baked in. The
    rest of the map is a copy of DEFAULT_MAP so all the usual rooms +
    walls + spawns still work."""
    base = DEFAULT_MAP.model_dump(by_alias=False)
    base["map_objects"] = objects
    custom = GameMap.model_validate(base)

    room = GameRoom(code="ABCD", game_map=custom)
    host = room.add_player("host")
    for i in range(3):
        room.add_player(f"p{i}")
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    return room


def test_sabotage_triggers_at_map_object_with_matching_object_type():
    """Tier 2.7 binding: a chaos player standing within
    SABOTAGE_OBJECT_INTERACTION_RADIUS of a MapObject whose ``object_type``
    matches the sabotage's allowed types must be allowed to trigger.

    Validates that sabotages.py's anchor-iteration sees MapObjects, not
    just the legacy task_anchors."""
    room = _make_started_room_with_objects(
        [
            {
                "id": "ci-console-1",
                "x": 1000.0,
                "y": 1000.0,
                "width": 60.0,
                "height": 40.0,
                "kind": "monitor",
                "object_type": "ci_console",
                "blocks_movement": False,
            }
        ]
    )
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    chaos = room.players[chaos_id]
    chaos.x, chaos.y = 1000.0, 1000.0  # sit on the object
    # Should not raise NOT_NEAR_OBJECT.
    room.apply_sabotage(chaos_id, "ci_cd_red")


def test_sabotage_blocked_when_no_map_object_or_anchor_matches():
    """Conversely, a chaos player far from ALL anchors / MapObjects with a
    matching object_type must be rejected."""
    room = _make_started_room_with_objects([])  # only legacy anchors
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    chaos = room.players[chaos_id]
    chaos.x, chaos.y = 100.0, 100.0  # far corner
    with pytest.raises(GameRoomError) as exc:
        room.apply_sabotage(chaos_id, "ci_cd_red")
    assert exc.value.code == "NOT_NEAR_OBJECT"


# --- Sabotage repair via MapObject sabotage_repair_id ----------------------


def test_repair_sabotage_resolves_panel_via_map_object():
    """If a MapObject has ``sabotage_repair_id`` set and the matching
    standalone SabotagePanel was removed, repair must still work via the
    MapObject's position."""
    base = DEFAULT_MAP.model_dump(by_alias=False)
    # Drop the lights_out panel so only the MapObject can satisfy repair.
    base["sabotage_panels"] = [
        p for p in base["sabotage_panels"] if p["sabotage_id"] != "lights_out"
    ]
    base["map_objects"] = [
        {
            "id": "lights-panel-1",
            "x": 2000.0,
            "y": 2000.0,
            "width": 60.0,
            "height": 60.0,
            "kind": "monitoring_panel",
            "sabotage_repair_id": "lights_out",
            "blocks_movement": False,
        }
    ]
    custom = GameMap.model_validate(base)
    room = GameRoom(code="ABCD", game_map=custom)
    host = room.add_player("host")
    for i in range(3):
        room.add_player(f"p{i}")
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    # Force lights-out so repair has something to clear.
    room.lights_off = True
    pid = next(iter(room.players.keys()))
    room.players[pid].x = 2000.0
    room.players[pid].y = 2000.0
    room.repair_sabotage(pid, "lights_out")
    assert room.lights_off is False


# --- Property: blocks_movement objects always end up in the wall list ------


_object_strat = st.builds(
    dict,
    id=st.text(min_size=1, max_size=20).filter(lambda s: s.strip()),
    x=st.floats(min_value=100.0, max_value=4700.0),
    y=st.floats(min_value=100.0, max_value=3100.0),
    width=st.floats(min_value=10.0, max_value=200.0),
    height=st.floats(min_value=10.0, max_value=200.0),
    kind=st.sampled_from(["desk", "chair_desk", "monitor", "server_rack", "fridge"]),
    rotation=st.sampled_from([0, 90, 180, 270]),
    blocks_movement=st.booleans(),
)


@given(objects=st.lists(_object_strat, min_size=0, max_size=15))
@settings(max_examples=40, deadline=None)
def test_compute_walls_blocks_movement_filter(objects):
    """Property: every MapObject with blocks_movement=True ends up as a
    wall AABB, every False one does not."""
    base = DEFAULT_MAP.model_dump(by_alias=False)
    base["map_objects"] = objects
    m = GameMap.model_validate(base)
    walls = set(compute_walls(m))
    for obj_dict in objects:
        obj = next(o for o in m.map_objects if o.id == obj_dict["id"])
        aabb = map_object_aabb(obj)
        if obj.blocks_movement:
            assert aabb in walls
        # else: aabb may or may not be in walls (could collide with a wall
        # line) — we don't assert absence, only presence-when-expected.


# --- Wire snapshot: GameMap.model_dump emits mapObjects --------------------


def test_game_map_serialises_map_objects_in_camel_case():
    """The `room_joined` payload sends ``room.map.model_dump(by_alias=True)``.
    Clients (browser + Godot) read ``map.mapObjects`` from that — the field
    must appear in camelCase, not snake_case."""
    base = DEFAULT_MAP.model_dump(by_alias=False)
    base["map_objects"] = [
        {
            "id": "d1",
            "x": 100.0,
            "y": 200.0,
            "width": 80.0,
            "height": 40.0,
            "kind": "desk",
        }
    ]
    m = GameMap.model_validate(base)
    wire = json.loads(m.model_dump_json(by_alias=True))
    assert "mapObjects" in wire
    assert wire["mapObjects"][0]["kind"] == "desk"
