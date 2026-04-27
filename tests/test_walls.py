import random

import pytest

from app.game.game_map import DEFAULT_MAP, compute_walls
from app.game.game_room import GameRoom
from app.game.models import InputState
from app.game.sabotages import NORMAL_SPEED
from app.game.walls import (
    DOOR_WIDTH_DEFAULT,
    PLAYER_COLLISION_RADIUS,
    WALL_THICKNESS,
    resolve_wall_collision,
)

# Compute walls from the default map (replaces the old module-level WALLS constant).
WALLS = compute_walls(DEFAULT_MAP)
DOOR_WIDTH = DOOR_WIDTH_DEFAULT


def _started_room_with_player(x: float, y: float) -> tuple[GameRoom, str]:
    """Create a room, place a single player at (x, y) and start in demo mode."""
    room = GameRoom(code="WALL")
    p = room.add_player("Solo")
    room.start(requesting_player_id=p.id, rng=random.Random(0), demo=True)
    p.x = x
    p.y = y
    return room, p.id


# --- raw resolver --------------------------------------------------------


def test_resolve_returns_unchanged_when_no_overlap():
    new_x, new_y = resolve_wall_collision(100.0, 100.0, 5.0, 0.0, WALLS)
    assert new_x == 100.0
    assert new_y == 100.0


def test_resolve_blocks_horizontal_against_vertical_wall():
    # Vertical wall at x=1600 thickness 8 each side; player radius 20.
    # Player tried to move right and ended up at x=1600 (inside the wall + radius).
    # y=100 is in a walled segment (door 1 at y=800 starts at 680, so y=100 has wall).
    new_x, _ = resolve_wall_collision(1600.0, 100.0, 5.0, 0.0, WALLS)
    # Must be pushed left to 1600 - 8 - 20 = 1572.
    assert new_x == pytest.approx(1600 - WALL_THICKNESS - PLAYER_COLLISION_RADIUS)


def test_resolve_blocks_vertical_against_horizontal_wall():
    # x=500 is in the first wall segment of the y=1600 horizontal wall (0-680 range,
    # before door 1 which starts at x=680), so there IS a wall segment here.
    (new_y,) = (resolve_wall_collision(500.0, 1600.0, 0.0, 5.0, WALLS)[1],)
    assert new_y == pytest.approx(1600 - WALL_THICKNESS - PLAYER_COLLISION_RADIUS)


# --- door passage --------------------------------------------------------


def test_door_in_vertical_wall_lets_player_pass():
    # Door at y=800 on the x=1600 wall, half-width = DOOR_WIDTH/2 = 120.
    # Player centered at y=800 tries to move from x=1599 to x=1601.
    new_x, _ = resolve_wall_collision(1601.0, 800.0, 2.0, 0.0, WALLS)
    assert new_x == 1601.0


def test_door_in_horizontal_wall_lets_player_pass():
    # Door at x=800 on the y=1600 wall, half-width = 120.
    new_x, new_y = resolve_wall_collision(800.0, 1601.0, 0.0, 2.0, WALLS)
    assert new_y == 1601.0


# --- sliding behavior in the room tick ---------------------------------


def test_player_slides_along_wall_when_moving_diagonally():
    """
    Player at (1570, 100) moves right+down. The wall at x=1600 blocks the right
    movement, but the y movement should still advance.
    """
    room, pid = _started_room_with_player(1570.0, 100.0)
    room.apply_input(pid, InputState(right=True, down=True))
    # Tick at the server's real cadence (20 Hz) for 0.5 s so the per-step
    # displacement stays smaller than the wall+radius margin (no tunneling).
    for _ in range(10):
        room.tick(0.05)
    p = room.players[pid]
    # x is blocked at the wall: 1600 - 8 - 20 = 1572.
    assert p.x == pytest.approx(1572.0, abs=0.5)
    # y advances diagonally — clearly forward of the start.
    assert p.y > 100.0 + 30.0


def test_player_walks_through_door():
    """Player at y=800 (center of door) walks freely past the wall."""
    room, pid = _started_room_with_player(1570.0, 800.0)
    room.apply_input(pid, InputState(right=True))
    room.tick(0.5)
    p = room.players[pid]
    # Door allows passage. Player advances by NORMAL_SPEED * 0.5.
    assert p.x == pytest.approx(1570.0 + NORMAL_SPEED * 0.5, abs=1.0)


def test_player_blocked_by_wall_cannot_cross():
    """Player at y=200 (well clear of any door) cannot cross the wall."""
    room, pid = _started_room_with_player(1570.0, 200.0)
    room.apply_input(pid, InputState(right=True))
    # Tick repeatedly; should never cross x=1600 - 8 - 20 = 1572.
    for _ in range(20):
        room.tick(0.1)
    p = room.players[pid]
    assert p.x <= 1600 - WALL_THICKNESS - PLAYER_COLLISION_RADIUS + 0.5  # tolerance


def test_walls_dont_break_existing_movement_in_open_space():
    """Sanity: free movement inside a room is unchanged."""
    room, pid = _started_room_with_player(200.0, 200.0)
    room.apply_input(pid, InputState(right=True))
    room.tick(0.1)
    p = room.players[pid]
    # NORMAL_SPEED * 0.1 px right, no walls in the way.
    assert p.x == pytest.approx(200.0 + NORMAL_SPEED * 0.1, abs=0.5)


def test_wall_segment_count_matches_design():
    """Slice-3 schema: walls auto-derived from room edges + doors. Default
    map has 7 shared room-pair edges, each split into 2 segments by a
    single door → 14 room-derived walls. Plus one AABB per blocking
    MapObject (Tier 4 props)."""
    from app.game.game_map import DEFAULT_MAP

    blocking = sum(1 for o in DEFAULT_MAP.map_objects if o.blocks_movement)
    assert len(WALLS) == 14 + blocking
