"""Tests for app/game/bots/pathfinding.py — pure room-graph utilities.

We hand-build small synthetic GameMaps via the Pydantic models so the
tests stay independent of the on-disk maps (those evolve over time and
would silently break path-shape assertions).
"""

from __future__ import annotations

from app.game.bots.pathfinding import build_room_graph, find_path, room_at
from app.game.game_map import Door, GameMap, MapSize, Room, SpawnPoint


def _box_room(rid: str, x: int, y: int, w: int, h: int) -> Room:
    return Room(id=rid, title=rid, x=x, y=y, width=w, height=h, color="#222")


def _make_map(*, rooms: list[Room], doors: list[Door], war_room_id: str = "a") -> GameMap:
    return GameMap(
        name="test",
        size=MapSize(width=2000, height=2000),
        rooms=rooms,
        doors=doors,
        spawn_points=[SpawnPoint(x=10.0, y=10.0)],
        war_room_id=war_room_id,
    )


# --- room_at ---------------------------------------------------------------


def test_room_at_returns_containing_room() -> None:
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 100, 0, 100, 100)
    m = _make_map(rooms=[a, b], doors=[])
    assert room_at((50.0, 50.0), m) == "a"
    assert room_at((150.0, 50.0), m) == "b"


def test_room_at_returns_none_for_outside_point() -> None:
    a = _box_room("a", 0, 0, 100, 100)
    m = _make_map(rooms=[a], doors=[])
    assert room_at((500.0, 500.0), m) is None


def test_room_at_uses_top_left_inclusive_boundaries() -> None:
    # A point exactly on a shared edge belongs to one room only.
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 100, 0, 100, 100)
    m = _make_map(rooms=[a, b], doors=[])
    # x=100 is on the shared edge — exclusive on a's right, inclusive on b's left.
    assert room_at((100.0, 50.0), m) == "b"


# --- build_room_graph ------------------------------------------------------


def test_room_graph_emits_symmetric_edges() -> None:
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 100, 0, 100, 100)
    door = Door(id="d", between_room_a="a", between_room_b="b", position=50, width=40)
    g = build_room_graph(_make_map(rooms=[a, b], doors=[door]))
    assert ("b", (100.0, 50.0)) in g["a"]
    assert ("a", (100.0, 50.0)) in g["b"]


def test_room_graph_horizontal_door_uses_x_position() -> None:
    # Rooms stacked vertically — door.position is x.
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 0, 100, 100, 100)
    door = Door(id="d", between_room_a="a", between_room_b="b", position=50)
    g = build_room_graph(_make_map(rooms=[a, b], doors=[door]))
    # Shared y = 100, door at x = 50.
    assert ("b", (50.0, 100.0)) in g["a"]


def test_room_graph_skips_self_referential_door() -> None:
    a = _box_room("a", 0, 0, 100, 100)
    door = Door(id="d", between_room_a="a", between_room_b="a", position=50)
    g = build_room_graph(_make_map(rooms=[a], doors=[door]))
    assert g["a"] == []


def test_room_graph_skips_door_referencing_unknown_room() -> None:
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 100, 0, 100, 100)
    door = Door(id="d", between_room_a="a", between_room_b="ghost", position=50)
    g = build_room_graph(_make_map(rooms=[a, b], doors=[door]))
    assert g["a"] == []
    assert g["b"] == []


def test_room_graph_skips_door_between_non_adjacent_rooms() -> None:
    # Rooms that don't actually share an edge — the door is meaningless.
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 500, 500, 100, 100)
    door = Door(id="d", between_room_a="a", between_room_b="b", position=50)
    g = build_room_graph(_make_map(rooms=[a, b], doors=[door]))
    assert g["a"] == []
    assert g["b"] == []


# --- find_path -------------------------------------------------------------


def test_find_path_same_room_returns_empty_list() -> None:
    a = _box_room("a", 0, 0, 100, 100)
    m = _make_map(rooms=[a], doors=[])
    assert find_path((10.0, 10.0), (90.0, 90.0), m) == []


def test_find_path_two_rooms_uses_door() -> None:
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 100, 0, 100, 100)
    door = Door(id="d", between_room_a="a", between_room_b="b", position=50)
    m = _make_map(rooms=[a, b], doors=[door])
    path = find_path((10.0, 10.0), (190.0, 90.0), m)
    assert path == [(100.0, 50.0), (190.0, 90.0)]


def test_find_path_three_room_chain() -> None:
    # a — b — c, in a horizontal row.
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 100, 0, 100, 100)
    c = _box_room("c", 200, 0, 100, 100)
    doors = [
        Door(id="ab", between_room_a="a", between_room_b="b", position=50),
        Door(id="bc", between_room_a="b", between_room_b="c", position=60),
    ]
    m = _make_map(rooms=[a, b, c], doors=doors)
    path = find_path((10.0, 10.0), (290.0, 90.0), m)
    assert path == [(100.0, 50.0), (200.0, 60.0), (290.0, 90.0)]


def test_find_path_returns_none_when_disconnected() -> None:
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 500, 0, 100, 100)
    # No door at all between the islands.
    m = _make_map(rooms=[a, b], doors=[])
    assert find_path((10.0, 10.0), (590.0, 90.0), m) is None


def test_find_path_returns_none_when_target_outside_any_room() -> None:
    a = _box_room("a", 0, 0, 100, 100)
    m = _make_map(rooms=[a], doors=[])
    assert find_path((10.0, 10.0), (5000.0, 5000.0), m) is None


def test_find_path_respects_passed_graph() -> None:
    # Caller-supplied graph wins over rebuilding — an empty graph means
    # no edges, so a two-room path has to fail.
    a = _box_room("a", 0, 0, 100, 100)
    b = _box_room("b", 100, 0, 100, 100)
    door = Door(id="d", between_room_a="a", between_room_b="b", position=50)
    m = _make_map(rooms=[a, b], doors=[door])
    empty = {r.id: [] for r in m.rooms}
    assert find_path((10.0, 10.0), (190.0, 90.0), m, graph=empty) is None
