"""Room-graph pathfinding for bots.

Bots navigate the map by hopping room → door → room → door → … → target.
This is way coarser than A* over a navmesh, but the maps are small
(~10 rooms, ~12 doors) and rooms are convex rectangles — once a bot is
inside the destination room they can steer straight to the in-room
target in a straight line, walls already cleared by the door.

Public:
- `build_room_graph(game_map)` — adjacency `{room_id: [(neighbor, door_xy)]}`
- `room_at(point, game_map)` — which room contains the point, or None
- `find_path(start_xy, target_xy, game_map, graph)` — list of waypoints
  (door centers in order, then target_xy). Empty path means already
  in the target room (caller can steer straight). `None` means the
  target room is unreachable from start (disconnected graph).
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.game.game_map import GameMap

Point = tuple[float, float]
RoomGraph = dict[str, list[tuple[str, Point]]]


def build_room_graph(game_map: GameMap) -> RoomGraph:
    """Adjacency list keyed by room id. Each edge carries the door's center.

    Doors with `between_room_a == between_room_b` (malformed) are skipped.
    Symmetric edges are emitted (A→B *and* B→A) so BFS works in either
    direction. Doors that reference unknown rooms are silently skipped —
    the map loader already validates room ids on its own pass.
    """
    rooms_by_id = {r.id: r for r in game_map.rooms}
    graph: RoomGraph = {rid: [] for rid in rooms_by_id}

    for door in game_map.doors:
        a = rooms_by_id.get(door.between_room_a)
        b = rooms_by_id.get(door.between_room_b)
        if a is None or b is None or a.id == b.id:
            continue

        # Door.position is along the shared edge. Figure out which axis
        # the rooms share to convert (axis-coord, position) into (x, y).
        # Two adjacencies are possible:
        #   - vertical shared edge (rooms side-by-side): door.position is y
        #   - horizontal shared edge (rooms top/bottom): door.position is x
        a_right = a.x + a.width
        a_bottom = a.y + a.height
        b_right = b.x + b.width
        b_bottom = b.y + b.height

        door_xy: Point | None = None
        if a_right == b.x or b_right == a.x:
            # Vertical shared edge — door at (shared-x, position).
            shared_x = a_right if a_right == b.x else b_right
            door_xy = (float(shared_x), float(door.position))
        elif a_bottom == b.y or b_bottom == a.y:
            shared_y = a_bottom if a_bottom == b.y else b_bottom
            door_xy = (float(door.position), float(shared_y))

        if door_xy is None:
            continue

        graph[a.id].append((b.id, door_xy))
        graph[b.id].append((a.id, door_xy))

    return graph


def room_at(point: Point, game_map: GameMap) -> str | None:
    """Return the id of the room containing `point`, or None.

    Edge-inclusive on the top/left, exclusive on bottom/right so a point
    on a shared boundary belongs to exactly one room (the one with the
    edge on its right/bottom).
    """
    x, y = point
    for room in game_map.rooms:
        if room.x <= x < room.x + room.width and room.y <= y < room.y + room.height:
            return room.id
    return None


def find_path(
    start_xy: Point,
    target_xy: Point,
    game_map: GameMap,
    graph: RoomGraph | None = None,
) -> list[Point] | None:
    """BFS in the room graph; return waypoints to reach `target_xy`.

    Return value:
      - `[]` — start and target are in the same room (steer straight).
      - `[door1, door2, …, target_xy]` — door centers in order plus the
        final in-room target.
      - `None` — start or target is outside any room, or the rooms are
        in disconnected components.
    """
    if graph is None:
        graph = build_room_graph(game_map)

    start_room = room_at(start_xy, game_map)
    target_room = room_at(target_xy, game_map)
    if start_room is None or target_room is None:
        return None
    if start_room == target_room:
        return []

    # BFS over rooms. parent[room_id] = (prev_room_id, door_xy_used).
    parent: dict[str, tuple[str, Point]] = {}
    visited = {start_room}
    queue: deque[str] = deque([start_room])
    while queue:
        cur = queue.popleft()
        if cur == target_room:
            break
        for neighbor, door_xy in graph.get(cur, ()):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            parent[neighbor] = (cur, door_xy)
            queue.append(neighbor)

    if target_room not in parent:
        return None

    # Reconstruct: walk parents back to start, accumulating door centers.
    doors: list[Point] = []
    cur = target_room
    while cur in parent:
        prev, door_xy = parent[cur]
        doors.append(door_xy)
        cur = prev
    doors.reverse()
    doors.append(target_xy)
    return doors
