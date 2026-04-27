"""One-shot populator: fills maps/office_complex.json with thematic
furniture per room.

Run via:
    uv run python scripts/populate_office_complex.py

Why a script and not raw JSON? 60+ map-objects with bindings to task ids
and sabotage repairs are easier to reason about as Python literals than
a wall of JSON. The script:

1. Reads the existing office_complex.json (rooms / doors / spawns).
2. Adds object_type to the 8 task anchors so chaos sabotages bind.
3. Generates a mapObjects list per room (workstations, racks, kitchen,
   meeting tables, decor).
4. Hands the merged dict to ``save_map()`` so Pydantic validates schema
   and atomic-rename writes the file.

Idempotent — re-running replaces office_complex.json with a fresh
generation. Tweak the per-room helpers below to iterate on layout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Make ``app.*`` importable when this script is run as a plain CLI.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.game.game_map import save_map  # noqa: E402

MAP_PATH = REPO_ROOT / "maps" / "office_complex.json"


# Task -> objectType binding lifted from default.json so sabotages target
# the same logical objects across both maps. Without this binding chaos
# can't trigger the matching sabotage at the task spot.
TASK_OBJECT_TYPES: dict[str, str] = {
    "fix_unit_tests": "qa_terminal",
    "review_pr": "git_terminal",
    "repair_deployment": "ci_console",
    "refill_coffee": "coffee_machine",
    "analyze_logs": "monitoring_panel",
    "calm_legacy_service": "legacy_terminal",
    "reduce_scope": "meeting_screen",
    "write_release_notes": "release_console",
}


# Per-Room floor material — drives the procedural texture in the 3D-Vorschau
# (and later real materials in the Godot client). Falls back to "office" if
# a room id isn't listed here.
ROOM_FLOOR_MATERIALS: dict[str, str] = {
    "reception": "office",
    "open_space": "office",
    "open_space_east": "office",
    "meeting_room": "office",
    "corridor": "office",
    "server_room": "server",
    "war_room": "office",
    "kitchen": "kitchen",
    "legacy_basement": "legacy",
}


def _id_seq(prefix: str) -> Any:
    """Tiny id generator so we can `next(seq)` without manual counters."""
    counter = 0
    while True:
        counter += 1
        yield f"{prefix}-{counter}"


# Per-kind defaults, mirrors editor-kinds.js. Keep the script self-contained
# so it doesn't have to re-parse the JS catalogue.
KIND_DEFAULTS: dict[str, tuple[int, int, bool]] = {
    "desk": (110, 60, True),
    "desk_large": (180, 80, True),
    "chair_desk": (50, 50, False),
    "chair_meeting": (50, 50, False),
    "chair_stool": (50, 50, False),
    "monitor": (60, 30, False),
    "keyboard": (50, 20, False),
    "mug": (20, 20, False),
    "lamp_desk": (30, 30, False),
    "server_rack": (80, 100, True),
    "monitoring_panel": (200, 60, False),
    "cabinet": (80, 80, True),
    "meeting_table": (480, 140, True),
    "presentation_screen": (200, 30, False),
    "kitchen_counter": (320, 80, True),
    "kitchen_corner": (120, 120, True),
    "kitchen_sink": (120, 80, True),
    "coffee_machine": (90, 90, False),
    "fridge": (100, 130, True),
    "plant_cactus": (60, 60, False),
    "picture_frame": (80, 30, False),
    "rug": (200, 120, False),
    "crate": (70, 70, True),
    "old_workstation": (110, 60, True),
}


def make(
    seq,
    kind: str,
    x: int,
    y: int,
    rotation: int = 0,
    *,
    width: int | None = None,
    height: int | None = None,
    blocks_movement: bool | None = None,
    task_id: str | None = None,
    object_type: str | None = None,
    sabotage_repair_id: str | None = None,
) -> dict[str, Any]:
    """Build one MapObject record. Defaults are pulled from KIND_DEFAULTS so
    the call sites stay terse — you only override when shape differs."""
    dw, dh, db = KIND_DEFAULTS[kind]
    obj: dict[str, Any] = {
        "id": next(seq),
        "x": x,
        "y": y,
        "width": width if width is not None else dw,
        "height": height if height is not None else dh,
        "kind": kind,
        "rotation": rotation,
        "blocksMovement": db if blocks_movement is None else blocks_movement,
    }
    if task_id is not None:
        obj["taskId"] = task_id
    if sabotage_repair_id is not None:
        obj["sabotageRepairId"] = sabotage_repair_id
    if object_type is not None:
        obj["objectType"] = object_type
    return obj


# --- Compose helpers: Cluster mehrerer Kinds um ein logisches Element rum.
# Designer-Mehrwert: ein "workstation"-Aufruf produziert die ganze
# Bürocluster-Szene (Tisch + Stuhl + Monitor + Tastatur + Mug + Lampe), statt
# 6 manueller Calls. Hält die Per-Room-Helfer kurz und konsistent.


def workstation(
    seq,
    cx: int,
    cy: int,
    *,
    desk_kind: str = "desk",
    chair_offset: int = 70,
    monitor_count: int = 1,
    with_keyboard: bool = True,
    with_mug: bool = True,
    with_lamp: bool = True,
    task_id: str | None = None,
    object_type: str | None = None,
    sabotage_repair_id: str | None = None,
) -> list[dict[str, Any]]:
    """Standard-Arbeitsplatz: Desk + Chair (südlich) + Monitor(e) + Tastatur,
    optional Mug + Schreibtischlampe. ``task_id``/``object_type`` landen NUR
    auf dem Desk selbst (Anchor-Bindung); die anderen Stücke sind dekorativ.
    """
    out = [
        make(
            seq,
            desk_kind,
            cx,
            cy,
            task_id=task_id,
            object_type=object_type,
            sabotage_repair_id=sabotage_repair_id,
        ),
        make(seq, "chair_desk", cx, cy + chair_offset),
    ]
    if monitor_count == 1:
        out.append(make(seq, "monitor", cx, cy - 22))
    elif monitor_count == 2:
        out.append(make(seq, "monitor", cx - 32, cy - 22))
        out.append(make(seq, "monitor", cx + 32, cy - 22))
    elif monitor_count >= 3:
        out.append(make(seq, "monitor", cx - 38, cy - 22))
        out.append(make(seq, "monitor", cx, cy - 22))
        out.append(make(seq, "monitor", cx + 38, cy - 22))
    if with_keyboard:
        out.append(make(seq, "keyboard", cx, cy + 8))
    if with_mug:
        out.append(make(seq, "mug", cx + 38, cy + 5))
    if with_lamp:
        out.append(make(seq, "lamp_desk", cx - 38, cy - 8))
    return out


def picture_wall(
    seq, anchor_x: int, anchor_y: int, *, count: int = 3, gap: int = 200
) -> list[dict[str, Any]]:
    """Galerie-Reihe aus picture_frames horizontal entlang einer Wand.
    Zentriert auf (anchor_x, anchor_y) — die Frames spreizen ±(count-1)/2*gap.
    """
    out: list[dict[str, Any]] = []
    start = anchor_x - ((count - 1) * gap) // 2
    for i in range(count):
        out.append(make(seq, "picture_frame", start + i * gap, anchor_y))
    return out


def plant_line(seq, x_start: int, y: int, *, count: int = 4, gap: int = 90) -> list[dict[str, Any]]:
    """Plant-Cluster für Fenster-/Wand-Akzent."""
    return [make(seq, "plant_cactus", x_start + i * gap, y) for i in range(count)]


def crate_stack(seq, cx: int, cy: int) -> list[dict[str, Any]]:
    """3-Crate-Cluster für Legacy/Storage-Look. Crates sind 70x70, leichte
    Überlappung gibt einen 'gestapelt'-Eindruck im 3D-Render."""
    return [
        make(seq, "crate", cx, cy),
        make(seq, "crate", cx + 60, cy),
        make(seq, "crate", cx + 30, cy - 50),
    ]


# --- Per-room helpers -------------------------------------------------------

# Layout style per room is intentionally distinct so designers can scan the
# 3D-Vorschau and immediately tell "that's the kitchen" / "that's legacy".


def furnish_reception(seq) -> list[dict[str, Any]]:
    """800x1200 entrance. Reception desk + waiting area + gallery wall."""
    out: list[dict[str, Any]] = []
    # Reception counter — desk_large with full kit, faces the door
    out.extend(
        workstation(
            seq,
            240,
            340,
            desk_kind="desk_large",
            monitor_count=2,
            chair_offset=70,
        )
    )
    # Side cabinet for storage decoration
    out.append(make(seq, "cabinet", 600, 320))
    # Waiting area: small rug + 4 lounge stools around a low table
    out.append(make(seq, "rug", 400, 760, width=380, height=200))
    out.append(make(seq, "meeting_table", 400, 760, width=180, height=80))
    out.append(make(seq, "mug", 400, 760))  # mug ON the lounge table
    out.append(make(seq, "chair_stool", 290, 700))
    out.append(make(seq, "chair_stool", 510, 700))
    out.append(make(seq, "chair_stool", 290, 820))
    out.append(make(seq, "chair_stool", 510, 820))
    # Gallery wall (3 frames) above reception desk
    out.extend(picture_wall(seq, 400, 60, count=3, gap=200))
    # Plants flanking entrance + back corner
    out.append(make(seq, "plant_cactus", 80, 1080))
    out.append(make(seq, "plant_cactus", 720, 1080))
    out.append(make(seq, "plant_cactus", 80, 700))
    out.append(make(seq, "plant_cactus", 720, 470))
    return out


def furnish_open_space_west(seq) -> list[dict[str, Any]]:
    """1600x1200 open-plan, x∈[800,2400], y∈[0,1200]. fix_unit_tests anchor
    at (1200, 400). Vent v_open at (1600, 600) — strict no-go zone.
    """
    out: list[dict[str, Any]] = []
    # Task anchor desk (qa_terminal) — fully kitted, 2 monitors for the QA lead
    out.extend(
        workstation(
            seq,
            1200,
            400,
            task_id="fix_unit_tests",
            object_type="qa_terminal",
            monitor_count=2,
        )
    )
    # 7 more desk clusters in a 4-col × 2-row grid, avoiding x=1600 (vent).
    # Top row y=200, bottom row y=1000. Cols at 950 / 1450 / 1900 / 2250.
    for cx in (950, 1450, 1900, 2250):
        out.extend(workstation(seq, cx, 200))
    for cx in (950, 1900, 2250):  # skip (1450, 1000) to leave room for break corner
        out.extend(workstation(seq, cx, 1000))
    # Break corner: rug + small lounge table + 4 stools — south-central, away from vent
    out.append(make(seq, "rug", 1450, 1000, width=320, height=180))
    out.append(make(seq, "meeting_table", 1450, 1000, width=240, height=110))
    out.append(make(seq, "mug", 1430, 990))
    out.append(make(seq, "mug", 1480, 1010))
    out.append(make(seq, "chair_stool", 1320, 950))
    out.append(make(seq, "chair_stool", 1580, 950))
    out.append(make(seq, "chair_stool", 1320, 1050))
    out.append(make(seq, "chair_stool", 1580, 1050))
    # North-wall gallery (4 frames) above the top row of desks
    out.extend(picture_wall(seq, 1600, 50, count=4, gap=380))
    # Plant cluster at the south-east window
    out.extend(plant_line(seq, 2160, 1130, count=3, gap=80))
    out.append(make(seq, "plant_cactus", 850, 1130))
    out.append(make(seq, "plant_cactus", 2300, 50))
    # Storage cabinets along the south wall
    out.append(make(seq, "cabinet", 2350, 1130))
    out.append(make(seq, "cabinet", 850, 1130))
    return out


def furnish_open_space_east(seq) -> list[dict[str, Any]]:
    """1600x1200 sister floor, x∈[2400,4000]. review_pr anchor at (3200, 400)."""
    out: list[dict[str, Any]] = []
    out.extend(
        workstation(
            seq,
            3200,
            400,
            task_id="review_pr",
            object_type="git_terminal",
            monitor_count=3,  # the senior dev's triple-screen setup
        )
    )
    # 7 more clusters, mirrored layout from west.
    for cx in (2550, 2900, 3500, 3850):
        out.extend(workstation(seq, cx, 200))
    for cx in (2550, 2900, 3850):
        out.extend(workstation(seq, cx, 1000))
    # Break corner south-east
    out.append(make(seq, "rug", 3500, 1000, width=320, height=180))
    out.append(make(seq, "meeting_table", 3500, 1000, width=240, height=110))
    out.append(make(seq, "mug", 3480, 1010))
    out.append(make(seq, "chair_stool", 3370, 950))
    out.append(make(seq, "chair_stool", 3630, 950))
    out.append(make(seq, "chair_stool", 3370, 1050))
    out.append(make(seq, "chair_stool", 3630, 1050))
    # Gallery — 4 frames above
    out.extend(picture_wall(seq, 3200, 50, count=4, gap=380))
    out.extend(plant_line(seq, 3760, 1130, count=3, gap=80))
    out.append(make(seq, "plant_cactus", 2500, 1130))
    out.append(make(seq, "plant_cactus", 3900, 50))
    out.append(make(seq, "cabinet", 2500, 1130))
    out.append(make(seq, "cabinet", 3900, 1130))
    return out


def furnish_meeting_room(seq) -> list[dict[str, Any]]:
    """1600x1200. reduce_scope anchor at (4800, 600). Boardroom-vibe."""
    out: list[dict[str, Any]] = []
    # Big central table + 10 chairs
    out.append(make(seq, "meeting_table", 4800, 600))
    for offset in (-200, -100, 0, 100, 200):
        out.append(make(seq, "chair_meeting", 4800 + offset, 510))
        out.append(make(seq, "chair_meeting", 4800 + offset, 690))
    # Mood: lamps on the table corners, mugs at every other seat
    out.append(make(seq, "lamp_desk", 4600, 600))
    out.append(make(seq, "lamp_desk", 5000, 600))
    for offset in (-200, 0, 200):
        out.append(make(seq, "mug", 4800 + offset, 540))
        out.append(make(seq, "mug", 4800 + offset, 660))
    # Presentation screen at the front (task anchor)
    out.append(
        make(
            seq,
            "presentation_screen",
            4800,
            120,
            task_id="reduce_scope",
            object_type="meeting_screen",
        )
    )
    # Side cabinet (whiteboard markers etc.) + secondary side-screen
    out.append(make(seq, "cabinet", 4150, 1130))
    out.append(make(seq, "cabinet", 5450, 1130))
    out.append(make(seq, "presentation_screen", 4400, 1170, rotation=180))
    out.append(make(seq, "presentation_screen", 5200, 1170, rotation=180))
    # Rug under the table
    out.append(make(seq, "rug", 4800, 600, width=560, height=200))
    # Gallery wall along the south
    out.extend(picture_wall(seq, 4800, 1200 - 30, count=3, gap=320))
    # Corner plants
    out.append(make(seq, "plant_cactus", 4080, 80))
    out.append(make(seq, "plant_cactus", 5520, 80))
    out.append(make(seq, "plant_cactus", 4080, 1120))
    out.append(make(seq, "plant_cactus", 5520, 1120))
    return out


def furnish_corridor(seq) -> list[dict[str, Any]]:
    """5600x800 central spine, y∈[1200,2000]. Long art-gallery look —
    keep walking-paths clear (rugs + frames hug the walls)."""
    out: list[dict[str, Any]] = []
    # North wall gallery: 8 frames evenly spaced, sitting just inside the wall
    out.extend(picture_wall(seq, 2800, 1230, count=7, gap=720))
    # South wall gallery: 7 frames offset
    out.extend(picture_wall(seq, 2800, 1970, count=7, gap=720))
    # Welcome rugs at door entries (one per door to a room)
    for door_x in (400, 1600, 3200, 4800, 700, 2100, 3500, 4900):
        out.append(make(seq, "rug", door_x, 1600, width=240, height=140))
    # Plant clusters every ~1100px on alternating sides
    for x in (300, 1400, 2500, 3600, 4700, 5500):
        out.append(make(seq, "plant_cactus", x, 1280))
        out.append(make(seq, "plant_cactus", x, 1900))
    # A "you are here"-style monitoring panel at midspan
    out.append(make(seq, "monitoring_panel", 2800, 1280))
    return out


def furnish_server_room(seq) -> list[dict[str, Any]]:
    """1400x1200, x∈[0,1400], y∈[2000,3200]. Two task anchors:
    - analyze_logs / lights_out repair at (700, 2400) — monitoring_panel
    - repair_deployment at (700, 2700) — ci_console
    Vent v_server at (700, 2400) sits on top of the panel.
    """
    out: list[dict[str, Any]] = []
    # Monitoring panel + lights_out repair anchor (back wall, north)
    out.append(
        make(
            seq,
            "monitoring_panel",
            700,
            2400,
            task_id="analyze_logs",
            object_type="monitoring_panel",
            sabotage_repair_id="lights_out",
        )
    )
    # Secondary monitoring panel cluster — looks like a NOC
    out.append(make(seq, "monitoring_panel", 400, 2400))
    out.append(make(seq, "monitoring_panel", 1000, 2400))
    # CI ops desk (task anchor) — full kit, 3 monitors
    out.extend(
        workstation(
            seq,
            700,
            2700,
            task_id="repair_deployment",
            object_type="ci_console",
            monitor_count=3,
        )
    )
    # Side ops desk (no anchor)
    out.extend(workstation(seq, 250, 2700, monitor_count=2))
    # Server racks: dense rows along the side walls + a center aisle
    for cy in (2080, 2280, 2480, 2680, 2880, 3080):
        out.append(make(seq, "server_rack", 80, cy))
        out.append(make(seq, "server_rack", 1320, cy))
    # Center-aisle racks (in front of the ops desk, leaves walking room)
    for cy in (3000, 3100):
        out.append(make(seq, "server_rack", 400, cy))
        out.append(make(seq, "server_rack", 1000, cy))
    # Spare-parts crates at the south wall
    out.extend(crate_stack(seq, 200, 3120))
    out.extend(crate_stack(seq, 1100, 3120))
    out.append(make(seq, "cabinet", 350, 3120))
    out.append(make(seq, "cabinet", 1250, 3120))
    return out


def furnish_war_room(seq) -> list[dict[str, Any]]:
    """1400x1200, x∈[1400,2800]. write_release_notes + comms_outage at
    (2100, 2400). Battle-station vibe: status walls + meeting table."""
    out: list[dict[str, Any]] = []
    # Release-console (task anchor + comms_outage repair) — desk_large + 3 monitors
    out.extend(
        workstation(
            seq,
            2100,
            2400,
            desk_kind="desk_large",
            monitor_count=3,
            task_id="write_release_notes",
            object_type="release_console",
            sabotage_repair_id="comms_outage",
        )
    )
    # Big status screen behind the desk
    out.append(make(seq, "presentation_screen", 2100, 2080))
    # Side status panels
    out.append(make(seq, "monitoring_panel", 1700, 2080))
    out.append(make(seq, "monitoring_panel", 2500, 2080))
    # War-table closer to the front
    out.append(make(seq, "meeting_table", 2100, 2900, width=360, height=120))
    for offset in (-120, 0, 120):
        out.append(make(seq, "chair_meeting", 2100 + offset, 2820))
        out.append(make(seq, "chair_meeting", 2100 + offset, 2980))
    # Coffee mugs on the table — long meetings happen here
    out.append(make(seq, "mug", 1980, 2900))
    out.append(make(seq, "mug", 2100, 2900))
    out.append(make(seq, "mug", 2220, 2900))
    out.append(make(seq, "lamp_desk", 1900, 2900))
    out.append(make(seq, "lamp_desk", 2300, 2900))
    out.append(make(seq, "rug", 2100, 2900, width=440, height=200))
    # Corner plants + side cabinets
    out.append(make(seq, "plant_cactus", 1480, 3120))
    out.append(make(seq, "plant_cactus", 2720, 3120))
    out.append(make(seq, "plant_cactus", 1480, 2080))
    out.append(make(seq, "plant_cactus", 2720, 2080))
    out.append(make(seq, "cabinet", 1480, 3120))
    out.append(make(seq, "cabinet", 2720, 3120))
    # Gallery wall (3 frames between the side panels)
    out.extend(picture_wall(seq, 2100, 2050, count=3, gap=280))
    return out


def furnish_kitchen(seq) -> list[dict[str, Any]]:
    """1400x1200, x∈[2800,4200]. refill_coffee at (3500, 2700). Lounge feel."""
    out: list[dict[str, Any]] = []
    # L-shaped counter run — denser, with corner unit
    out.append(make(seq, "kitchen_counter", 2960, 2080))
    out.append(make(seq, "kitchen_counter", 3280, 2080))
    out.append(make(seq, "kitchen_sink", 3600, 2080))
    out.append(make(seq, "kitchen_counter", 3760, 2080))
    out.append(make(seq, "kitchen_corner", 4080, 2080))
    out.append(make(seq, "kitchen_counter", 4080, 2280, rotation=90))
    out.append(make(seq, "kitchen_counter", 4080, 2480, rotation=90))
    # Mugs lining the back counter (the staff stash)
    for x in (2960, 3120, 3280, 3760, 3920):
        out.append(make(seq, "mug", x, 2060))
    # Coffee machine — task anchor (THE wow moment)
    out.append(
        make(
            seq,
            "coffee_machine",
            3500,
            2700,
            task_id="refill_coffee",
            object_type="coffee_machine",
        )
    )
    # Secondary "second coffee bar" (without binding) for the deluxe feel
    out.append(make(seq, "coffee_machine", 3340, 2080))
    # Fridges — main + decorative
    out.append(make(seq, "fridge", 4080, 2900))
    out.append(make(seq, "fridge", 2920, 2900))
    # High table + stools for the lunch corner
    out.append(make(seq, "meeting_table", 3500, 2950, width=360, height=120))
    for x in (3340, 3500, 3660):
        out.append(make(seq, "chair_stool", x, 2860))
        out.append(make(seq, "chair_stool", x, 3040))
    out.append(make(seq, "rug", 3500, 2950, width=440, height=200))
    # Plant cluster at the windows
    out.extend(plant_line(seq, 2880, 3120, count=3, gap=70))
    out.extend(plant_line(seq, 3100, 2080, count=2, gap=80))
    # "Coffee = productivity" wall art
    out.extend(picture_wall(seq, 3500, 2050, count=3, gap=280))
    out.append(make(seq, "lamp_desk", 3340, 2950))
    out.append(make(seq, "lamp_desk", 3660, 2950))
    return out


def furnish_legacy_basement(seq) -> list[dict[str, Any]]:
    """1400x1200, x∈[4200,5600]. calm_legacy_service at (4900, 2700).
    The abandoned-PHP corner: dim, cluttered, retro."""
    out: list[dict[str, Any]] = []
    # Legacy terminal (task anchor) — full kit but old_workstation desk
    out.extend(
        workstation(
            seq,
            4900,
            2700,
            desk_kind="old_workstation",
            task_id="calm_legacy_service",
            object_type="legacy_terminal",
            with_lamp=True,
        )
    )
    # 4 more old workstations in two rows
    for cx in (4400, 5400):
        out.extend(workstation(seq, cx, 2700, desk_kind="old_workstation"))
    out.extend(workstation(seq, 4400, 2400, desk_kind="old_workstation"))
    out.extend(workstation(seq, 5400, 2400, desk_kind="old_workstation"))
    # Storage chaos: stacked crates galore
    out.extend(crate_stack(seq, 4290, 2090))
    out.extend(crate_stack(seq, 4520, 2090))
    out.extend(crate_stack(seq, 5310, 2090))
    out.extend(crate_stack(seq, 5510, 2090))
    out.extend(crate_stack(seq, 4290, 3050))
    out.extend(crate_stack(seq, 5510, 3050))
    # Cabinets along the south wall
    out.append(make(seq, "cabinet", 4310, 3120))
    out.append(make(seq, "cabinet", 5500, 3120))
    out.append(make(seq, "cabinet", 4900, 3120))
    # A broken/decorative coffee machine — legacy joke
    out.append(make(seq, "coffee_machine", 5550, 2300))
    # One sad plant survives
    out.append(make(seq, "plant_cactus", 4290, 3120))
    # Gallery — old framed retro logos
    out.extend(picture_wall(seq, 4900, 2050, count=3, gap=320))
    return out


# --- Main -------------------------------------------------------------------


def main() -> None:
    raw = json.loads(MAP_PATH.read_text(encoding="utf-8"))

    # Stamp objectType onto each task anchor so chaos sabotages bind.
    for ta in raw["taskAnchors"]:
        ot = TASK_OBJECT_TYPES.get(ta["taskId"])
        if ot:
            ta["objectType"] = ot

    # Stamp per-room floorMaterial so the 3D-Vorschau picks the right
    # procedural texture (carpet/tiles/concrete/old-carpet).
    for room in raw["rooms"]:
        fm = ROOM_FLOOR_MATERIALS.get(room["id"], "office")
        if fm != "office":
            room["floorMaterial"] = fm
        else:
            # Reset any previous explicit "office" so the JSON stays terse;
            # default in the schema covers it.
            room.pop("floorMaterial", None)

    seq = _id_seq("oc")
    raw["mapObjects"] = []
    raw["mapObjects"].extend(furnish_reception(seq))
    raw["mapObjects"].extend(furnish_open_space_west(seq))
    raw["mapObjects"].extend(furnish_open_space_east(seq))
    raw["mapObjects"].extend(furnish_meeting_room(seq))
    raw["mapObjects"].extend(furnish_corridor(seq))
    raw["mapObjects"].extend(furnish_server_room(seq))
    raw["mapObjects"].extend(furnish_war_room(seq))
    raw["mapObjects"].extend(furnish_kitchen(seq))
    raw["mapObjects"].extend(furnish_legacy_basement(seq))

    # Validate + write atomically. save_map raises ValidationError if
    # anything in raw breaks the GameMap schema.
    parsed = save_map("office_complex", raw)
    print(f"office_complex.json updated: {len(parsed.map_objects)} mapObjects")
    print(f"  rooms={len(parsed.rooms)} doors={len(parsed.doors)}")
    print(f"  taskAnchors={len(parsed.task_anchors)} sabotagePanels={len(parsed.sabotage_panels)}")


if __name__ == "__main__":
    main()
