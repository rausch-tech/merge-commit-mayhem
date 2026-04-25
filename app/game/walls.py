"""
Wall geometry helpers. Concrete wall rectangles are computed from a map's
wallLines at GameMap-load time -- see app/game/game_map.py.
"""

from typing import Final

WALL_THICKNESS: Final[int] = 8
DOOR_WIDTH_DEFAULT: Final[int] = 120
PLAYER_COLLISION_RADIUS: Final[float] = 20.0


def vertical_wall_segments(
    line_x: int,
    doors: list[tuple[int, int]],
    map_height: int,
) -> list[tuple[int, int, int, int]]:
    """Return wall rectangles for a vertical line at line_x with door cutouts.
    Each door is (center_y, width). map_height defines the bottom edge."""
    segments: list[tuple[int, int, int, int]] = []
    last_y = 0
    for cy, w in sorted(doors, key=lambda d: d[0]):
        top = cy - w // 2
        if top > last_y:
            segments.append((line_x - WALL_THICKNESS, last_y, line_x + WALL_THICKNESS, top))
        last_y = cy + w // 2
    if last_y < map_height:
        segments.append((line_x - WALL_THICKNESS, last_y, line_x + WALL_THICKNESS, map_height))
    return segments


def horizontal_wall_segments(
    line_y: int,
    doors: list[tuple[int, int]],
    map_width: int,
) -> list[tuple[int, int, int, int]]:
    """Same as vertical_wall_segments but for a horizontal wall line."""
    segments: list[tuple[int, int, int, int]] = []
    last_x = 0
    for cx, w in sorted(doors, key=lambda d: d[0]):
        left = cx - w // 2
        if left > last_x:
            segments.append((last_x, line_y - WALL_THICKNESS, left, line_y + WALL_THICKNESS))
        last_x = cx + w // 2
    if last_x < map_width:
        segments.append((last_x, line_y - WALL_THICKNESS, map_width, line_y + WALL_THICKNESS))
    return segments


def resolve_wall_collision(
    new_x: float,
    new_y: float,
    moved_dx: float,
    moved_dy: float,
    walls: list[tuple[int, int, int, int]],
    radius: float = PLAYER_COLLISION_RADIUS,
) -> tuple[float, float]:
    """
    Given a candidate (new_x, new_y) reached by moving (moved_dx, moved_dy),
    push the player out of any overlapping wall along the axis they moved on.
    The two move components must be applied separately for sliding behavior.

    Returns (resolved_x, resolved_y).
    """
    for (wx1, wy1, wx2, wy2) in walls:
        # AABB-vs-circle test (cheap & sufficient for axis-aligned rects).
        if (new_x + radius > wx1 and new_x - radius < wx2
                and new_y + radius > wy1 and new_y - radius < wy2):
            if moved_dx > 0 and moved_dy == 0:
                new_x = wx1 - radius
            elif moved_dx < 0 and moved_dy == 0:
                new_x = wx2 + radius
            elif moved_dy > 0 and moved_dx == 0:
                new_y = wy1 - radius
            elif moved_dy < 0 and moved_dx == 0:
                new_y = wy2 + radius
            else:
                # Both axes moved -- caller should split the move into
                # x-only then y-only sub-steps. Defensive fallback: snap on
                # whichever axis has the smaller required correction.
                d_left = new_x + radius - wx1
                d_right = wx2 - (new_x - radius)
                d_top = new_y + radius - wy1
                d_bottom = wy2 - (new_y - radius)
                min_d = min(d_left, d_right, d_top, d_bottom)
                if min_d == d_left:
                    new_x = wx1 - radius
                elif min_d == d_right:
                    new_x = wx2 + radius
                elif min_d == d_top:
                    new_y = wy1 - radius
                else:
                    new_y = wy2 + radius
    return new_x, new_y
