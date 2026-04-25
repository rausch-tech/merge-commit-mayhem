"""
Statische Wand-Definitionen für die MVP-Map. Wände sind achsen-parallele
Rechtecke; Türen sind Lücken zwischen Wand-Segmenten.

Wechsel auf walls.json kommt in Sprint 4.
"""

from typing import Final

WALL_THICKNESS: Final[int] = 8         # half-width on each side of the wall line
DOOR_WIDTH: Final[int] = 120           # gap between segments
PLAYER_COLLISION_RADIUS: Final[float] = 20.0


def _vertical_wall_segments(line_x: int, door_ys: list[int], map_height: int = 1600) -> list[tuple[int, int, int, int]]:
    """Return rectangles for a vertical wall at x=line_x with door cutouts at the given y centers."""
    half_door = DOOR_WIDTH // 2
    segments: list[tuple[int, int, int, int]] = []
    last_y = 0
    for door_y in sorted(door_ys):
        top = door_y - half_door
        if top > last_y:
            segments.append((line_x - WALL_THICKNESS, last_y, line_x + WALL_THICKNESS, top))
        last_y = door_y + half_door
    if last_y < map_height:
        segments.append((line_x - WALL_THICKNESS, last_y, line_x + WALL_THICKNESS, map_height))
    return segments


def _horizontal_wall_segments(line_y: int, door_xs: list[int], map_width: int = 2400) -> list[tuple[int, int, int, int]]:
    """Return rectangles for a horizontal wall at y=line_y with door cutouts at the given x centers."""
    half_door = DOOR_WIDTH // 2
    segments: list[tuple[int, int, int, int]] = []
    last_x = 0
    for door_x in sorted(door_xs):
        left = door_x - half_door
        if left > last_x:
            segments.append((last_x, line_y - WALL_THICKNESS, left, line_y + WALL_THICKNESS))
        last_x = door_x + half_door
    if last_x < map_width:
        segments.append((last_x, line_y - WALL_THICKNESS, map_width, line_y + WALL_THICKNESS))
    return segments


# Each wall is (x1, y1, x2, y2). Doors centered at the listed positions.
WALLS: Final[list[tuple[int, int, int, int]]] = [
    *_vertical_wall_segments(800, [400, 1200]),
    *_vertical_wall_segments(1600, [400, 1200]),
    *_horizontal_wall_segments(800, [400, 1200, 2000]),
]


def resolve_wall_collision(
    new_x: float,
    new_y: float,
    moved_dx: float,
    moved_dy: float,
    walls: list[tuple[int, int, int, int]] = WALLS,
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
                # Both axes moved — caller should split the move into
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
