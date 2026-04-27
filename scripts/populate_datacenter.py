"""One-shot populator: fills maps/datacenter.json with ~110 thematic
MapObjects spread across the 10 rooms.

Datacenter is the "server-heavy" sister of office_complex — same task
anchors and sabotage-panels, but the layout leans into compute
infrastructure (server halls, cooling, tape archive) rather than
office furniture. Many server_racks, fewer chairs.

Idempotent: re-running regenerates the populated map. Per-room helper
functions are the tweak points.

Run via:
    uv run python scripts/populate_datacenter.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.game.game_map import save_map  # noqa: E402

MAP_PATH = REPO_ROOT / "maps" / "datacenter.json"


# Per-kind defaults (mirrors maps/kinds.json + editor-kinds.js). Keep
# the script self-contained so it doesn't need to re-parse the JSON
# at populate-time. KIND_DEFAULTS[kind] = (width, height, blocks_movement).
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


def _id_seq(prefix: str) -> Any:
    counter = 0
    while True:
        counter += 1
        yield f"{prefix}-{counter}"


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
    """Build one MapObject dict with sensible defaults from KIND_DEFAULTS."""
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


# --- Per-room helpers -------------------------------------------------------


def furnish_reception(seq) -> list[dict[str, Any]]:
    """600x1100 entrance. Reception counter + decor; spawn at (300, 550)."""
    return [
        make(seq, "desk_large", 200, 280),  # reception counter
        make(seq, "chair_desk", 200, 360),
        make(seq, "monitor", 200, 240),
        make(seq, "keyboard", 200, 290),
        make(seq, "picture_frame", 100, 60),
        make(seq, "picture_frame", 480, 60),
        make(seq, "plant_cactus", 100, 1020),
        make(seq, "plant_cactus", 520, 1020),
    ]


def furnish_noc(seq) -> list[dict[str, Any]]:
    """900x1100 monitoring centre. Two task anchors live here:
    - analyze_logs at (850, 600) → monitoring_panel + lights_out repair
    - repair_deployment at (1200, 800) → ci_console (a desk)
    Vent v_noc at (850, 400) — keep that strip clear.
    """
    out: list[dict[str, Any]] = []
    # Big back-wall monitoring panel — task anchor + lights_out repair
    out.append(
        make(
            seq,
            "monitoring_panel",
            850,
            600,
            task_id="analyze_logs",
            object_type="monitoring_panel",
            sabotage_repair_id="lights_out",
        )
    )
    # CI desk — repair_deployment binding
    out.append(
        make(
            seq,
            "desk",
            1200,
            800,
            task_id="repair_deployment",
            object_type="ci_console",
        )
    )
    out.append(make(seq, "chair_desk", 1200, 870))
    out.append(make(seq, "monitor", 1200, 750))
    out.append(make(seq, "keyboard", 1200, 805))
    # Two ops-cluster desks (left + right of the room)
    for cx in (700, 1300):
        out.append(make(seq, "desk", cx, 200))
        out.append(make(seq, "chair_desk", cx, 270))
        out.append(make(seq, "monitor", cx, 150))
    out.append(make(seq, "cabinet", 720, 1050))
    out.append(make(seq, "cabinet", 1280, 1050))
    out.append(make(seq, "plant_cactus", 1450, 1050))
    return out


def furnish_meeting_room(seq) -> list[dict[str, Any]]:
    """700x1100 meeting room. reduce_scope anchor at (1850, 600).
    Spawn at (1700, 550) and (1850, 350) — keep room walkable around them.
    """
    out: list[dict[str, Any]] = []
    out.append(
        make(
            seq,
            "presentation_screen",
            1850,
            150,
            task_id="reduce_scope",
            object_type="meeting_screen",
        )
    )
    out.append(make(seq, "meeting_table", 1850, 700, width=320, height=120))
    for offset in (-120, 0, 120):
        out.append(make(seq, "chair_meeting", 1850 + offset, 620))
        out.append(make(seq, "chair_meeting", 1850 + offset, 780))
    out.append(make(seq, "plant_cactus", 1560, 1020))
    out.append(make(seq, "plant_cactus", 2140, 1020))
    return out


def furnish_break_room(seq) -> list[dict[str, Any]]:
    """700x1100 kitchen. refill_coffee at (2550, 600). Tile floor."""
    out: list[dict[str, Any]] = []
    # L-shaped kitchen counter along the back wall
    out.append(make(seq, "kitchen_counter", 2400, 100))
    out.append(make(seq, "kitchen_corner", 2700, 100))
    out.append(make(seq, "kitchen_counter", 2820, 220, rotation=90))
    out.append(make(seq, "kitchen_sink", 2440, 200))
    out.append(make(seq, "fridge", 2280, 220))
    # Coffee machine — task anchor pin
    out.append(
        make(
            seq,
            "coffee_machine",
            2550,
            600,
            task_id="refill_coffee",
            object_type="coffee_machine",
        )
    )
    # Standing-table cluster
    out.append(make(seq, "meeting_table", 2550, 950, width=240, height=100))
    out.append(make(seq, "chair_stool", 2440, 900))
    out.append(make(seq, "chair_stool", 2550, 900))
    out.append(make(seq, "chair_stool", 2660, 900))
    out.append(make(seq, "plant_cactus", 2230, 1040))
    return out


def furnish_tape_archive(seq) -> list[dict[str, Any]]:
    """700x1100 legacy storage. calm_legacy_service at (3250, 600).
    Vent v_archive at (3250, 400). Legacy floor (olive carpet)."""
    out: list[dict[str, Any]] = []
    out.append(
        make(
            seq,
            "old_workstation",
            3250,
            700,
            task_id="calm_legacy_service",
            object_type="legacy_terminal",
        )
    )
    out.append(make(seq, "chair_desk", 3250, 770))
    out.append(make(seq, "monitor", 3250, 650))
    # Stacked crates along walls
    for cx in (2980, 3050):
        out.append(make(seq, "crate", cx, 980))
    for cx in (3450, 3520):
        out.append(make(seq, "crate", cx, 980))
    out.append(make(seq, "cabinet", 2980, 200))
    out.append(make(seq, "cabinet", 3520, 200))
    return out


def furnish_loading_bay(seq) -> list[dict[str, Any]]:
    """1200x1100 industrial loading area. No tasks. Spawns at (4000, 550)
    and (4200, 750) — keep crates off those spots."""
    out: list[dict[str, Any]] = []
    # Stacked crates in two corners (avoid spawn coords)
    for cx, cy in [
        (3700, 200),
        (3770, 200),
        (3700, 270),
        (4700, 200),
        (4630, 200),
        (4700, 270),
        (3700, 950),
        (3770, 950),
        (4700, 950),
        (4630, 950),
    ]:
        out.append(make(seq, "crate", cx, cy))
    out.append(make(seq, "cabinet", 3700, 530))
    out.append(make(seq, "cabinet", 4700, 530))
    return out


def furnish_corridor(seq) -> list[dict[str, Any]]:
    """4800x600 central spine. Decor only — must stay walkable."""
    return [
        make(seq, "rug", 800, 1400, width=300, height=180),
        make(seq, "rug", 2400, 1400, width=300, height=180),
        make(seq, "rug", 4000, 1400, width=300, height=180),
        make(seq, "plant_cactus", 200, 1180),
        make(seq, "plant_cactus", 200, 1620),
        make(seq, "plant_cactus", 4600, 1180),
        make(seq, "plant_cactus", 4600, 1620),
        make(seq, "picture_frame", 1400, 1130),
        make(seq, "picture_frame", 3400, 1130),
    ]


def furnish_cooling_plant(seq) -> list[dict[str, Any]]:
    """1200x1500 cooling support room. Lots of server-rack-style
    machinery (CRAC units feel like racks)."""
    out: list[dict[str, Any]] = []
    # Two columns of cooling units along the side walls
    for cy in (1900, 2100, 2300, 2500, 2700, 2900):
        out.append(make(seq, "server_rack", 100, cy))
        out.append(make(seq, "server_rack", 1100, cy))
    # Central monitoring + cabinets
    out.append(make(seq, "monitoring_panel", 600, 1900))
    out.append(make(seq, "cabinet", 600, 3100))
    out.append(make(seq, "plant_cactus", 200, 3120))
    out.append(make(seq, "plant_cactus", 1000, 3120))
    return out


def furnish_server_hall_a(seq) -> list[dict[str, Any]]:
    """1600x1500 first server hall. write_release_notes anchor at (2000, 2400).
    comms_outage repair co-located. Lots of server racks in rows."""
    out: list[dict[str, Any]] = []
    # Release-console / comms_outage repair pin
    out.append(
        make(
            seq,
            "desk_large",
            2000,
            2400,
            task_id="write_release_notes",
            object_type="release_console",
            sabotage_repair_id="comms_outage",
        )
    )
    out.append(make(seq, "chair_desk", 2000, 2480))
    out.append(make(seq, "monitor", 1950, 2350))
    out.append(make(seq, "monitor", 2050, 2350))
    # Two rack rows flanking the back of the hall (away from the desk)
    for cy in (1850, 2000):
        for cx in (1300, 1450, 1600, 1750, 2250, 2400, 2550, 2700):
            out.append(make(seq, "server_rack", cx, cy))
    # Front utilities
    out.append(make(seq, "monitoring_panel", 1800, 3100))
    out.append(make(seq, "cabinet", 2750, 3100))
    return out


def furnish_server_hall_b(seq) -> list[dict[str, Any]]:
    """2000x1500 second server hall. fix_unit_tests at (3500, 2200) and
    review_pr at (4400, 2700). Two task pins → two sub-clusters of racks."""
    out: list[dict[str, Any]] = []
    # QA workstation + dev workstation
    out.append(
        make(
            seq,
            "desk",
            3500,
            2200,
            task_id="fix_unit_tests",
            object_type="qa_terminal",
        )
    )
    out.append(make(seq, "chair_desk", 3500, 2270))
    out.append(make(seq, "monitor", 3500, 2150))
    out.append(make(seq, "keyboard", 3500, 2205))
    out.append(
        make(
            seq,
            "desk",
            4400,
            2700,
            task_id="review_pr",
            object_type="git_terminal",
        )
    )
    out.append(make(seq, "chair_desk", 4400, 2770))
    out.append(make(seq, "monitor", 4400, 2650))
    out.append(make(seq, "keyboard", 4400, 2705))
    # Rack rows along the room edges (avoid the two desks + the central vent v_servers)
    for cy in (1850, 2000):
        for cx in (2900, 3050, 3200, 4150, 4300, 4500, 4650):
            out.append(make(seq, "server_rack", cx, cy))
    for cy in (3050, 3150):
        for cx in (2900, 3050, 3200, 3700, 3850, 4000):
            out.append(make(seq, "server_rack", cx, cy))
    out.append(make(seq, "cabinet", 2900, 2900))
    out.append(make(seq, "cabinet", 4750, 3100))
    return out


# --- Main -------------------------------------------------------------------


def main() -> None:
    raw = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    seq = _id_seq("dc")
    raw["mapObjects"] = []
    raw["mapObjects"].extend(furnish_reception(seq))
    raw["mapObjects"].extend(furnish_noc(seq))
    raw["mapObjects"].extend(furnish_meeting_room(seq))
    raw["mapObjects"].extend(furnish_break_room(seq))
    raw["mapObjects"].extend(furnish_tape_archive(seq))
    raw["mapObjects"].extend(furnish_loading_bay(seq))
    raw["mapObjects"].extend(furnish_corridor(seq))
    raw["mapObjects"].extend(furnish_cooling_plant(seq))
    raw["mapObjects"].extend(furnish_server_hall_a(seq))
    raw["mapObjects"].extend(furnish_server_hall_b(seq))

    parsed = save_map("datacenter", raw)
    print(f"datacenter.json updated: {len(parsed.map_objects)} mapObjects")
    print(f"  rooms={len(parsed.rooms)} doors={len(parsed.doors)}")
    print(f"  taskAnchors={len(parsed.task_anchors)} sabotagePanels={len(parsed.sabotage_panels)}")


if __name__ == "__main__":
    main()
