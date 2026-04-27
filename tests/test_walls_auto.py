"""Slice-3 (Wand-Modell C) tests for auto-derived walls.

The new ``compute_walls`` ALG: for each room, iterate its 4 edges. Shared
portions with adjacent rooms become walls (with door cutouts), perimeter
portions become walls (unless the edge sits on the map outer boundary),
all dedup'd per room pair. Hypothesis property tests pin the invariants
that the unit tests can't enumerate.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.game.game_map import (
    Door,
    GameMap,
    MapSize,
    Room,
    compute_walls,
)
from app.game.walls import WALL_THICKNESS


def _room(id_, x, y, w, h):
    return Room(id=id_, title=id_, x=x, y=y, width=w, height=h, color="#3a4560")


def _two_room_map(door: Door | None = None) -> GameMap:
    """Two 100x100 rooms side-by-side at the centre of a 300x300 map.
    Shared edge at x=100, y in [0, 100]."""
    return GameMap(
        name="two-rooms",
        size=MapSize(width=300, height=300),
        rooms=[_room("a", 0, 0, 100, 100), _room("b", 100, 0, 100, 100)],
        doors=[door] if door is not None else [],
        war_room_id="a",
    )


# --- shared edges ----------------------------------------------------------


def test_two_adjacent_rooms_share_one_wall_segment():
    m = _two_room_map()
    walls = compute_walls(m)
    # The shared edge runs along x=100 from y=0 to y=100. With no doors,
    # it's one wall rect: (92, 0, 108, 100).
    assert (100 - WALL_THICKNESS, 0, 100 + WALL_THICKNESS, 100) in walls


def test_door_cuts_shared_edge_into_two_segments():
    door = Door(
        id="d1",
        between_room_a="a",
        between_room_b="b",
        position=50,
        width=20,
        door_kind="office_door",
    )
    m = _two_room_map(door)
    walls = compute_walls(m)
    # Door at y=50 ± 10 → walls (92, 0, 108, 40) and (92, 60, 108, 100).
    assert (100 - WALL_THICKNESS, 0, 100 + WALL_THICKNESS, 40) in walls
    assert (100 - WALL_THICKNESS, 60, 100 + WALL_THICKNESS, 100) in walls
    # The shared edge is fully covered by these two segments — no other
    # vertical wall at x=100 should exist.
    vertical_at_100 = [
        w for w in walls if w[0] == 100 - WALL_THICKNESS and w[2] == 100 + WALL_THICKNESS
    ]
    assert len(vertical_at_100) == 2


def test_door_filling_entire_edge_leaves_no_wall():
    """A door wider than the shared edge is clamped to the edge — no wall
    segments remain. Edge case for very tall corridors with full-height
    archways."""
    door = Door(
        id="d1",
        between_room_a="a",
        between_room_b="b",
        position=50,
        width=200,  # much wider than the 100-tall shared edge
        door_kind="office_door",
    )
    m = _two_room_map(door)
    walls = compute_walls(m)
    vertical_at_100 = [
        w for w in walls if w[0] == 100 - WALL_THICKNESS and w[2] == 100 + WALL_THICKNESS
    ]
    assert vertical_at_100 == []


# --- perimeter walls -------------------------------------------------------


def test_room_in_middle_of_map_gets_four_perimeter_walls():
    """An isolated room not touching any other room and not on the map
    boundary becomes a closed box of 4 walls."""
    m = GameMap(
        name="floating",
        size=MapSize(width=400, height=400),
        rooms=[_room("a", 100, 100, 200, 200)],
        war_room_id="a",
    )
    walls = compute_walls(m)
    # Top, bottom, left, right at the room's edges (none on the map perimeter).
    assert (100, 100 - WALL_THICKNESS, 300, 100 + WALL_THICKNESS) in walls  # top
    assert (100, 300 - WALL_THICKNESS, 300, 300 + WALL_THICKNESS) in walls  # bottom
    assert (100 - WALL_THICKNESS, 100, 100 + WALL_THICKNESS, 300) in walls  # left
    assert (300 - WALL_THICKNESS, 100, 300 + WALL_THICKNESS, 300) in walls  # right
    assert len(walls) == 4


def test_map_perimeter_edges_are_not_walled():
    """If a room sits flush with the map outer edge, that edge is not
    walled — the MovementController clamps perimeter."""
    m = GameMap(
        name="full",
        size=MapSize(width=200, height=200),
        rooms=[_room("a", 0, 0, 200, 200)],
        war_room_id="a",
    )
    walls = compute_walls(m)
    # Single room covers the whole map — no walls anywhere.
    assert walls == []


def test_l_shape_corridor_keeps_internal_perimeter_walls():
    """Two rooms forming an L-shape (no shared edge) on a larger map →
    each room gets perimeter walls on the sides not flush with the map
    edge."""
    # Room A in top-left corner, Room B in bottom-right. They don't touch.
    m = GameMap(
        name="L",
        size=MapSize(width=500, height=500),
        rooms=[_room("a", 0, 0, 200, 200), _room("b", 300, 300, 200, 200)],
        war_room_id="a",
    )
    walls = compute_walls(m)
    # Room A's right edge (x=200, internal) → perimeter wall.
    assert (200 - WALL_THICKNESS, 0, 200 + WALL_THICKNESS, 200) in walls
    # Room A's bottom edge (y=200, internal) → perimeter wall.
    assert (0, 200 - WALL_THICKNESS, 200, 200 + WALL_THICKNESS) in walls
    # Room B's left edge (x=300, internal) → perimeter wall.
    assert (300 - WALL_THICKNESS, 300, 300 + WALL_THICKNESS, 500) in walls


# --- property: every room edge is fully covered ---------------------------


_room_strat = st.tuples(
    st.integers(min_value=0, max_value=400),
    st.integers(min_value=0, max_value=400),
    st.integers(min_value=50, max_value=200),
    st.integers(min_value=50, max_value=200),
)


@given(seed=st.integers(min_value=0, max_value=2**31 - 1))
@settings(max_examples=20, deadline=None)
def test_compute_walls_is_deterministic(seed):
    """Same map → same walls (modulo iteration order — sort to compare)."""
    import random

    rng = random.Random(seed)
    rooms = []
    placed = set()
    for i in range(rng.randint(2, 4)):
        x = rng.choice([0, 100, 200, 300])
        y = rng.choice([0, 100, 200, 300])
        w = rng.choice([100, 200])
        h = rng.choice([100, 200])
        if (x, y, w, h) in placed:
            continue
        placed.add((x, y, w, h))
        rooms.append(_room(f"r{i}", x, y, w, h))
    m = GameMap(
        name="rng",
        size=MapSize(width=600, height=600),
        rooms=rooms,
        war_room_id=rooms[0].id,
    )
    a = sorted(compute_walls(m))
    b = sorted(compute_walls(m))
    assert a == b
