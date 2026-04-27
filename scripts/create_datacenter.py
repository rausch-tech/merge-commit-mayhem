"""Create the "datacenter" map — structurally complete, no mapObjects yet.

Eight rooms organised around a central corridor, dominated by two
server-halls with cooling/tape-archive support rooms. All eight task
anchors get an objectType binding, both sabotage panels are placed,
three vents form a chaos-teleport triangle.

mapObjects bleibt absichtlich leer — die Godot-Devs liefern derzeit
neue Assets (server racks, panels, cabling), die wir dann via
populate-style Skript einsetzen, wenn sie gestaged sind.

Run via:
    uv run python scripts/create_datacenter.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.game.game_map import save_map  # noqa: E402

MAP_ID = "datacenter"


def build_map() -> dict[str, Any]:
    """Compose the datacenter layout.

    4800×3200 server-pixels, mirroring default-office's footprint so the
    same camera defaults work. Layout:

      +------------+------+--------+-----------+--------+
      | reception  | noc  | meeting| break_room| tape   |
      |  (600x1100)|(900x | (700x  |  (700x    |archive |
      |            | 1100)| 1100)  |   1100)   | (700x  |
      |            |      |        |           | 1100)  |
      +------------+------+--------+-----------+--------+
      |              corridor (4800x600, y=1100..1700)  |
      +-------------+----------------+------------------+
      | cooling     | server_hall_a  | server_hall_b    |
      |  (1200x1500)|   (1600x1500)  |  (2000x1500)     |
      +-------------+----------------+------------------+
    """
    rooms = [
        _room("reception", "Reception", 0, 0, 600, 1100, "#3a4a5a"),
        _room("noc", "NOC", 600, 0, 900, 1100, "#2a4a70", floor="server"),
        _room("meeting_room", "Meeting Room", 1500, 0, 700, 1100, "#5a3a70"),
        _room("break_room", "Break Room", 2200, 0, 700, 1100, "#7a5030", floor="kitchen"),
        _room("tape_archive", "Tape Archive", 2900, 0, 700, 1100, "#3a6a3a", floor="legacy"),
        # Filler in the top row — corridor wouldn't reach the right edge
        # otherwise; this room hosts no tasks but adds a "secondary entry".
        _room("loading_bay", "Loading Bay", 3600, 0, 1200, 1100, "#3f4754", floor="server"),
        _room("corridor", "Corridor", 0, 1100, 4800, 600, "#26303c"),
        _room("cooling_plant", "Cooling Plant", 0, 1700, 1200, 1500, "#2a607a", floor="server"),
        _room("server_hall_a", "Server Hall A", 1200, 1700, 1600, 1500, "#2a4a70", floor="server"),
        _room("server_hall_b", "Server Hall B", 2800, 1700, 2000, 1500, "#2a4a70", floor="server"),
    ]

    # Door positions — every room touches the corridor (top or bottom edge of
    # the corridor at y=1100 / y=1700). Plus an internal door between the two
    # server halls so chaos can move silently between them.
    doors = [
        # Top row → corridor (shared edge y=1100)
        _door("d_recep_corr", "reception", "corridor", 300),
        _door("d_noc_corr", "noc", "corridor", 1050),
        _door("d_meet_corr", "meeting_room", "corridor", 1850),
        _door("d_break_corr", "break_room", "corridor", 2550),
        _door("d_tape_corr", "tape_archive", "corridor", 3250),
        _door("d_load_corr", "loading_bay", "corridor", 4200),
        # Corridor → bottom row (shared edge y=1700)
        _door("d_cool_corr", "corridor", "cooling_plant", 600),
        _door("d_sa_corr", "corridor", "server_hall_a", 2000),
        _door("d_sb_corr", "corridor", "server_hall_b", 3800),
        # Internal door between the two server halls (shared edge x=2800)
        _door("d_sa_sb", "server_hall_a", "server_hall_b", 2400, kind="vault"),
        # Cooling ↔ server_hall_a internal access door (shared edge x=1200)
        _door("d_cool_sa", "cooling_plant", "server_hall_a", 2300, kind="glass_panel"),
    ]

    # 12 spawn-points spread across the upper rooms + a few in the corridor —
    # avoids spawning anyone inside the server halls (which feel cinematic
    # when you "enter" them).
    spawn_points = [
        {"x": 300, "y": 550},
        {"x": 850, "y": 350},
        {"x": 1050, "y": 750},
        {"x": 1700, "y": 550},
        {"x": 1850, "y": 350},
        {"x": 2400, "y": 350},
        {"x": 2550, "y": 750},
        {"x": 3100, "y": 550},
        {"x": 3250, "y": 350},
        {"x": 4000, "y": 550},
        {"x": 4200, "y": 750},
        {"x": 600, "y": 1400},
    ]

    # Eight task anchors with objectType bindings (matched to the same
    # logical objects as default + office_complex so chaos sabotages bind).
    task_anchors = [
        # NOC: monitoring + CI panels
        {"taskId": "analyze_logs", "x": 850, "y": 600, "objectType": "monitoring_panel"},
        {"taskId": "repair_deployment", "x": 1200, "y": 800, "objectType": "ci_console"},
        # Meeting room: planning
        {"taskId": "reduce_scope", "x": 1850, "y": 600, "objectType": "meeting_screen"},
        # Break room: coffee
        {"taskId": "refill_coffee", "x": 2550, "y": 600, "objectType": "coffee_machine"},
        # Tape archive: legacy
        {"taskId": "calm_legacy_service", "x": 3250, "y": 600, "objectType": "legacy_terminal"},
        # Server Hall A: release work
        {"taskId": "write_release_notes", "x": 2000, "y": 2400, "objectType": "release_console"},
        # Server Hall B: dev work
        {"taskId": "fix_unit_tests", "x": 3500, "y": 2200, "objectType": "qa_terminal"},
        {"taskId": "review_pr", "x": 4400, "y": 2700, "objectType": "git_terminal"},
    ]

    # Sabotage repair panels — co-located with NOC and Server Hall A so
    # repairs feel "mission-critical" inside themed rooms.
    sabotage_panels = [
        {"sabotageId": "lights_out", "x": 800, "y": 900},
        {"sabotageId": "comms_outage", "x": 1800, "y": 2400},
    ]

    # Chaos vents — triangle through the high-traffic + back rooms so chaos
    # always has a non-obvious escape route.
    vents = [
        {"id": "v_noc", "x": 850, "y": 400, "connectedTo": ["v_servers", "v_archive"]},
        {"id": "v_servers", "x": 2300, "y": 2300, "connectedTo": ["v_noc", "v_archive"]},
        {"id": "v_archive", "x": 3250, "y": 400, "connectedTo": ["v_noc", "v_servers"]},
    ]

    return {
        "name": "datacenter",
        "size": {"width": 4800, "height": 3200},
        "rooms": rooms,
        "doors": doors,
        "spawnPoints": spawn_points,
        "taskAnchors": task_anchors,
        "sabotagePanels": sabotage_panels,
        "vents": vents,
        "mapObjects": [],
        "warRoomId": "meeting_room",
    }


def _room(
    rid: str,
    title: str,
    x: int,
    y: int,
    w: int,
    h: int,
    color: str,
    *,
    floor: str = "office",
) -> dict[str, Any]:
    """Build one room dict. Skips floorMaterial when default to keep JSON terse."""
    out: dict[str, Any] = {
        "id": rid,
        "title": title,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "color": color,
    }
    if floor != "office":
        out["floorMaterial"] = floor
    return out


def _door(
    did: str,
    room_a: str,
    room_b: str,
    position: int,
    *,
    width: int = 240,
    kind: str = "office_door",
) -> dict[str, Any]:
    return {
        "id": did,
        "betweenRoomA": room_a,
        "betweenRoomB": room_b,
        "position": position,
        "width": width,
        "doorKind": kind,
    }


def main() -> None:
    raw = build_map()
    parsed = save_map(MAP_ID, raw)
    print(f"datacenter.json written: {len(parsed.rooms)} rooms, {len(parsed.doors)} doors")
    print(f"  taskAnchors={len(parsed.task_anchors)} sabotagePanels={len(parsed.sabotage_panels)}")
    print(f"  vents={len(parsed.vents)} spawnPoints={len(parsed.spawn_points)}")
    print(f"  mapObjects={len(parsed.map_objects)} (intentionally empty — assets pending)")


if __name__ == "__main__":
    main()
