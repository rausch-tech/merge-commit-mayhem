"""One-shot migration: pre-Slice-3 ``wallLines`` -> Slice-3 ``doors``.

Reads each map JSON in-place, removes the old ``wallLines`` key (and its
nested ``doors``), and writes a new top-level ``doors`` array where each
entry references the two adjacent rooms separated by that door. The
resulting JSON is loadable by the new ``GameMap`` Pydantic model.

Walls themselves are NOT stored anymore — they are auto-derived from
room rectangles minus doors at runtime (see ``game_map.compute_walls``).

Idempotent: a map without ``wallLines`` (already migrated) is left
untouched. Output is committed.

Run via:
    uv run python scripts/migrate_walls_to_doors.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DOOR_KIND_DEFAULT = "office_door"


def _find_room_pair(
    rooms: list[dict],
    axis: str,
    line_position: int,
    door_center: int,
) -> tuple[str, str] | None:
    """Find the two rooms whose shared edge sits at (axis, line_position)
    and whose perpendicular range contains ``door_center``. Returns
    ``(room_a_id, room_b_id)`` sorted, or None if no clean pair found."""
    candidates: list[str] = []
    for room in rooms:
        rx, ry, rw, rh = room["x"], room["y"], room["width"], room["height"]
        if axis == "x":
            # Vertical wall line at x=line_position. Candidate rooms have
            # their left or right edge AT line_position, AND their y-range
            # contains the door center (which is a y-coord).
            edge_match = rx == line_position or rx + rw == line_position
            range_match = ry <= door_center <= ry + rh
        else:
            edge_match = ry == line_position or ry + rh == line_position
            range_match = rx <= door_center <= rx + rw
        if edge_match and range_match:
            candidates.append(room["id"])
    if len(candidates) != 2:
        return None
    return tuple(sorted(candidates))


def migrate(map_dict: dict) -> tuple[dict, list[str]]:
    """Mutate ``map_dict`` in place: drop ``wallLines``, add ``doors``.
    Returns the (mutated) dict plus a list of warnings."""
    warnings: list[str] = []
    if "wallLines" not in map_dict:
        return map_dict, ["already migrated (no wallLines field)"]

    old_lines = map_dict.pop("wallLines")
    rooms = map_dict.get("rooms", [])
    new_doors: list[dict] = []

    for line in old_lines:
        axis = line["axis"]
        position = int(line["position"])
        for door in line.get("doors", []):
            center = int(door["center"])
            width = int(door.get("width", 240))
            pair = _find_room_pair(rooms, axis, position, center)
            if pair is None:
                warnings.append(
                    f"Skipped door axis={axis} position={position} center={center}: "
                    f"no unique room pair found"
                )
                continue
            new_doors.append(
                {
                    "id": f"d{len(new_doors) + 1}",
                    "betweenRoomA": pair[0],
                    "betweenRoomB": pair[1],
                    "position": center,
                    "width": width,
                    "doorKind": DOOR_KIND_DEFAULT,
                }
            )

    map_dict["doors"] = new_doors
    return map_dict, warnings


def _ordered_keys(map_dict: dict) -> dict:
    """Re-emit with a stable key order so diffs stay readable."""
    order = (
        "name",
        "size",
        "rooms",
        "doors",
        "spawnPoints",
        "taskAnchors",
        "sabotagePanels",
        "vents",
        "mapObjects",
        "warRoomId",
    )
    out = {key: map_dict[key] for key in order if key in map_dict}
    # Append any remaining keys (forward compat for Slice-5 polish etc.).
    for key, value in map_dict.items():
        if key not in out:
            out[key] = value
    return out


def main(argv: list[str]) -> int:
    target_dir = Path(argv[1]) if len(argv) > 1 else Path("maps")
    if not target_dir.exists():
        print(f"directory {target_dir} not found", file=sys.stderr)
        return 1

    files = sorted(target_dir.glob("*.json"))
    if not files:
        print(f"no *.json files in {target_dir}", file=sys.stderr)
        return 1

    for path in files:
        raw = json.loads(path.read_text(encoding="utf-8"))
        migrated, warnings = migrate(raw)
        ordered = _ordered_keys(migrated)
        path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        n = len(migrated.get("doors", []))
        warn_suffix = f" ({len(warnings)} warnings)" if warnings else ""
        print(f"{path.name}: {n} doors{warn_suffix}")
        for w in warnings:
            print(f"  ! {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
