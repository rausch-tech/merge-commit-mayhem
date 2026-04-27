"""Tests for the one-shot migration script ``scripts/migrate_walls_to_doors``.

The script is run once at Slice-3 cutover (committed output), but the
algorithm matters: an incorrect migration would silently change the
playable geometry. These tests pin the conversion behavior.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    """Load the migration script as a module without executing main()."""
    path = Path(__file__).parent.parent / "scripts" / "migrate_walls_to_doors.py"
    spec = importlib.util.spec_from_file_location("migrate_walls_to_doors", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["migrate_walls_to_doors"] = module
    spec.loader.exec_module(module)
    return module


migrate_mod = _load_module()


def _legacy_two_room_map():
    return {
        "name": "two-rooms",
        "size": {"width": 200, "height": 100},
        "rooms": [
            {"id": "a", "title": "A", "x": 0, "y": 0, "width": 100, "height": 100, "color": "#fff"},
            {
                "id": "b",
                "title": "B",
                "x": 100,
                "y": 0,
                "width": 100,
                "height": 100,
                "color": "#aaa",
            },
        ],
        "wallLines": [
            {"axis": "x", "position": 100, "doors": [{"center": 50, "width": 30}]},
        ],
        "warRoomId": "a",
    }


def test_migrate_drops_wall_lines_field():
    m = _legacy_two_room_map()
    out, warnings = migrate_mod.migrate(m)
    assert "wallLines" not in out


def test_migrate_emits_one_door_per_legacy_door():
    m = _legacy_two_room_map()
    out, warnings = migrate_mod.migrate(m)
    assert len(out["doors"]) == 1


def test_migrate_finds_correct_room_pair():
    m = _legacy_two_room_map()
    out, warnings = migrate_mod.migrate(m)
    door = out["doors"][0]
    assert {door["betweenRoomA"], door["betweenRoomB"]} == {"a", "b"}
    # Sorted so the output is deterministic.
    assert door["betweenRoomA"] <= door["betweenRoomB"]


def test_migrate_preserves_position_and_width():
    m = _legacy_two_room_map()
    out, warnings = migrate_mod.migrate(m)
    door = out["doors"][0]
    assert door["position"] == 50
    assert door["width"] == 30
    assert door["doorKind"] == "office_door"


def test_migrate_warns_when_door_doesnt_match_any_pair():
    """A door at a position no two rooms share → emit a warning, skip the
    door. Defensive against malformed legacy maps."""
    m = _legacy_two_room_map()
    # Move room B out of the way so the wall line at x=100 has no room
    # adjacent to it.
    m["rooms"][1]["x"] = 150
    out, warnings = migrate_mod.migrate(m)
    assert out["doors"] == []
    assert any("no unique room pair" in w for w in warnings)


def test_migrate_idempotent_when_already_migrated():
    m = {
        "name": "already",
        "size": {"width": 100, "height": 100},
        "rooms": [],
        "doors": [],
        "warRoomId": "",
    }
    out, warnings = migrate_mod.migrate(m)
    assert "already migrated" in warnings[0]
    assert out["doors"] == []


def test_migrate_default_map_produces_seven_doors():
    """End-to-end: take the canonical pre-Slice-3 default-map shape (3
    wallLines + 7 doors total) and verify migration emits 7 new doors."""
    m = {
        "name": "default-office",
        "size": {"width": 4800, "height": 3200},
        "rooms": [
            {
                "id": "open_space",
                "title": "Open Space",
                "x": 0,
                "y": 0,
                "width": 1600,
                "height": 1600,
                "color": "#3a4560",
            },
            {
                "id": "meeting_room",
                "title": "Meeting Room",
                "x": 1600,
                "y": 0,
                "width": 1600,
                "height": 1600,
                "color": "#5a3a70",
            },
            {
                "id": "kitchen",
                "title": "Kitchen",
                "x": 3200,
                "y": 0,
                "width": 1600,
                "height": 1600,
                "color": "#7a5030",
            },
            {
                "id": "server_room",
                "title": "Server Room",
                "x": 0,
                "y": 1600,
                "width": 1600,
                "height": 1600,
                "color": "#2a4a70",
            },
            {
                "id": "war_room",
                "title": "War Room",
                "x": 1600,
                "y": 1600,
                "width": 1600,
                "height": 1600,
                "color": "#2a607a",
            },
            {
                "id": "legacy_basement",
                "title": "Legacy Basement",
                "x": 3200,
                "y": 1600,
                "width": 1600,
                "height": 1600,
                "color": "#3a6a3a",
            },
        ],
        "wallLines": [
            {
                "axis": "x",
                "position": 1600,
                "doors": [{"center": 800, "width": 240}, {"center": 2400, "width": 240}],
            },
            {
                "axis": "x",
                "position": 3200,
                "doors": [{"center": 800, "width": 240}, {"center": 2400, "width": 240}],
            },
            {
                "axis": "y",
                "position": 1600,
                "doors": [
                    {"center": 800, "width": 240},
                    {"center": 2400, "width": 240},
                    {"center": 4000, "width": 240},
                ],
            },
        ],
        "warRoomId": "war_room",
    }
    out, warnings = migrate_mod.migrate(m)
    assert warnings == []
    assert len(out["doors"]) == 7
