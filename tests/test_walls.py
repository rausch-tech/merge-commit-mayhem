import random

import pytest

from app.game.game_room import GameRoom
from app.game.models import InputState, Phase
from app.game.walls import (
    DOOR_WIDTH,
    PLAYER_COLLISION_RADIUS,
    WALLS,
    WALL_THICKNESS,
    resolve_wall_collision,
)


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
    new_x, new_y = resolve_wall_collision(100.0, 100.0, 5.0, 0.0)
    assert new_x == 100.0
    assert new_y == 100.0


def test_resolve_blocks_horizontal_against_vertical_wall():
    # Vertical wall at x=800 thickness 8 each side; player radius 20.
    # Player tried to move right and ended up at x=800 (inside the wall + radius).
    new_x, _ = resolve_wall_collision(800.0, 100.0, 5.0, 0.0)
    # Must be pushed left to 800 - 8 - 20 = 772.
    assert new_x == pytest.approx(800 - WALL_THICKNESS - PLAYER_COLLISION_RADIUS)


def test_resolve_blocks_vertical_against_horizontal_wall():
    # x=700 is between the doors at x=400 (range 340-460) and x=1200 (range 1140-1260),
    # so there IS a wall segment here.
    new_y, = (resolve_wall_collision(700.0, 800.0, 0.0, 5.0)[1],)
    assert new_y == pytest.approx(800 - WALL_THICKNESS - PLAYER_COLLISION_RADIUS)


# --- door passage --------------------------------------------------------


def test_door_in_vertical_wall_lets_player_pass():
    # Door at y=400 on the x=800 wall, half-width = DOOR_WIDTH/2 = 60.
    # Player centered at y=400 tries to move from x=799 to x=801.
    new_x, _ = resolve_wall_collision(801.0, 400.0, 2.0, 0.0)
    assert new_x == 801.0


def test_door_in_horizontal_wall_lets_player_pass():
    new_x, new_y = resolve_wall_collision(400.0, 801.0, 0.0, 2.0)
    assert new_y == 801.0


# --- sliding behavior in the room tick ---------------------------------


def test_player_slides_along_wall_when_moving_diagonally():
    """
    Player at (770, 100) moves right+down. The wall at x=800 blocks the right
    movement, but the y movement should still advance.
    """
    room, pid = _started_room_with_player(770.0, 100.0)
    room.apply_input(pid, InputState(right=True, down=True))
    room.tick(0.5)  # 75 px requested in each axis
    p = room.players[pid]
    # x is blocked at the wall: 800 - 8 - 20 = 772.
    assert p.x == pytest.approx(772.0, abs=0.5)
    # y advanced by 75/sqrt(2) ≈ 53 px (since input was diagonal but y was free).
    # Actually with axis-by-axis: x first (blocked), y next (free) — y gets the
    # full diagonal y-component which is 53 px.
    assert p.y > 100.0 + 30.0  # advanced clearly forward


def test_player_walks_through_door():
    """Player at y=400 (center of door) walks freely past the wall."""
    room, pid = _started_room_with_player(770.0, 400.0)
    room.apply_input(pid, InputState(right=True))
    room.tick(0.5)  # 75 px attempted
    p = room.players[pid]
    # Door allows passage. Player should be at 770 + 75 = 845.
    assert p.x == pytest.approx(845.0, abs=1.0)


def test_player_blocked_by_wall_cannot_cross():
    """Player at y=200 (well clear of any door) cannot cross the wall."""
    room, pid = _started_room_with_player(770.0, 200.0)
    room.apply_input(pid, InputState(right=True))
    # Tick repeatedly; should never cross x=800 - 8 - 20 = 772.
    for _ in range(20):
        room.tick(0.1)
    p = room.players[pid]
    assert p.x <= 800 - WALL_THICKNESS - PLAYER_COLLISION_RADIUS + 0.5  # tolerance


def test_walls_dont_break_existing_movement_in_open_space():
    """Sanity: free movement inside a room is unchanged."""
    room, pid = _started_room_with_player(200.0, 200.0)
    room.apply_input(pid, InputState(right=True))
    room.tick(0.1)
    p = room.players[pid]
    # 0.1 s × 150 px/s = 15 px right, no walls in the way.
    assert p.x == pytest.approx(215.0, abs=0.5)


def test_wall_segment_count_matches_design():
    """Defensive: 10 wall rects total (3 per vertical wall × 2, plus 4 horizontal segments)."""
    assert len(WALLS) == 10
