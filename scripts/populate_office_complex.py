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


# --- Per-room helpers -------------------------------------------------------

# Layout style per room is intentionally distinct so designers can scan the
# 3D-Vorschau and immediately tell "that's the kitchen" / "that's legacy".


def furnish_reception(seq) -> list[dict[str, Any]]:
    """800x1200 entrance. Big counter near the door, decor away from spawn."""
    return [
        make(seq, "desk_large", 240, 320, rotation=0),  # Reception counter
        make(seq, "chair_desk", 240, 410),
        make(seq, "monitor", 240, 280),
        make(seq, "picture_frame", 100, 60),
        make(seq, "picture_frame", 700, 60),
        make(seq, "rug", 400, 720),
        make(seq, "plant_cactus", 720, 1080),
        make(seq, "plant_cactus", 80, 1080),
    ]


def furnish_open_space_west(seq) -> list[dict[str, Any]]:
    """1600x1200 open-plan. fix_unit_tests anchor at (1200, 400). Vent
    v_open at (1600, 600) — keep that spot clear."""
    out: list[dict[str, Any]] = []
    # Task anchor desk — qa_terminal binding
    out.append(
        make(
            seq,
            "desk",
            1200,
            400,
            task_id="fix_unit_tests",
            object_type="qa_terminal",
        )
    )
    out.append(make(seq, "chair_desk", 1200, 470))
    out.append(make(seq, "monitor", 1200, 350))
    out.append(make(seq, "keyboard", 1200, 405))
    # Two more desk clusters (top-left + bottom-left). Avoid (1600, 600) vent.
    for cx, cy in [(950, 200), (950, 1000), (2200, 200), (2200, 1000)]:
        out.append(make(seq, "desk", cx, cy))
        out.append(make(seq, "chair_desk", cx, cy + 70 if cy < 600 else cy - 70))
        out.append(make(seq, "monitor", cx, cy - 50))
    # Decor
    out.append(make(seq, "rug", 1600, 850))  # under the bottom corridor
    out.append(make(seq, "plant_cactus", 850, 50))
    out.append(make(seq, "plant_cactus", 2300, 50))
    out.append(make(seq, "cabinet", 2350, 1130))
    return out


def furnish_open_space_east(seq) -> list[dict[str, Any]]:
    """1600x1200 sister floor. review_pr anchor at (3200, 400)."""
    out: list[dict[str, Any]] = []
    out.append(
        make(
            seq,
            "desk",
            3200,
            400,
            task_id="review_pr",
            object_type="git_terminal",
        )
    )
    out.append(make(seq, "chair_desk", 3200, 470))
    out.append(make(seq, "monitor", 3200, 350))
    out.append(make(seq, "keyboard", 3200, 405))
    # Mirror layout
    for cx, cy in [(2600, 200), (2600, 1000), (3800, 200), (3800, 1000)]:
        out.append(make(seq, "desk", cx, cy))
        out.append(make(seq, "chair_desk", cx, cy + 70 if cy < 600 else cy - 70))
        out.append(make(seq, "monitor", cx, cy - 50))
    out.append(make(seq, "rug", 3200, 850))
    out.append(make(seq, "plant_cactus", 2500, 50))
    out.append(make(seq, "plant_cactus", 3900, 50))
    out.append(make(seq, "cabinet", 2500, 1130))
    return out


def furnish_meeting_room(seq) -> list[dict[str, Any]]:
    """1600x1200. reduce_scope anchor at (4800, 600). Big meeting table +
    chairs + presentation screen."""
    out: list[dict[str, Any]] = []
    # Meeting table centered on room center (4800, 600). Width 480 horizontal.
    out.append(make(seq, "meeting_table", 4800, 600))
    # Chairs along both long sides.
    for offset in (-200, -100, 0, 100, 200):
        out.append(make(seq, "chair_meeting", 4800 + offset, 510))
        out.append(make(seq, "chair_meeting", 4800 + offset, 690))
    # Presentation screen at the wall — task anchor pin
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
    # Decor — corner plants + rug under the table
    out.append(make(seq, "rug", 4800, 600, width=520, height=180))
    out.append(make(seq, "plant_cactus", 4080, 80))
    out.append(make(seq, "plant_cactus", 5520, 80))
    out.append(make(seq, "plant_cactus", 4080, 1120))
    out.append(make(seq, "plant_cactus", 5520, 1120))
    return out


def furnish_corridor(seq) -> list[dict[str, Any]]:
    """5600x800 central spine. Keep traffic-friendly — only decor."""
    return [
        make(seq, "rug", 800, 1600, width=300, height=180),
        make(seq, "rug", 2800, 1600, width=300, height=180),
        make(seq, "rug", 4800, 1600, width=300, height=180),
        make(seq, "plant_cactus", 200, 1280),
        make(seq, "plant_cactus", 200, 1900),
        make(seq, "plant_cactus", 5400, 1280),
        make(seq, "plant_cactus", 5400, 1900),
        make(seq, "picture_frame", 1400, 1230),
        make(seq, "picture_frame", 3000, 1230),
        make(seq, "picture_frame", 4500, 1230),
    ]


def furnish_server_room(seq) -> list[dict[str, Any]]:
    """1400x1200. server_room. Two task anchors here:
    - analyze_logs at (700, 2400) — monitoring_panel + lights_out repair
    - repair_deployment at (700, 2700) — ci_console
    Vent v_server also at (700, 2400) — sits on top of the panel.
    """
    out: list[dict[str, Any]] = []
    # Monitoring panel + lights_out repair on the back wall
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
    # CI console (a desk) — repair_deployment binding
    out.append(
        make(
            seq,
            "desk",
            700,
            2700,
            task_id="repair_deployment",
            object_type="ci_console",
        )
    )
    out.append(make(seq, "chair_desk", 700, 2770))
    out.append(make(seq, "monitor", 700, 2650))
    # Server racks lining the side walls — feels like a real server room
    for cy in (2100, 2300, 2500, 2700, 2900, 3100):
        out.append(make(seq, "server_rack", 100, cy))
        out.append(make(seq, "server_rack", 1300, cy))
    out.append(make(seq, "cabinet", 350, 3120))
    return out


def furnish_war_room(seq) -> list[dict[str, Any]]:
    """1400x1200. write_release_notes at (2100, 2400). comms_outage repair
    at (2100, 2400) too — same MapObject does both."""
    out: list[dict[str, Any]] = []
    # Release-console + comms_outage repair on the back wall
    out.append(
        make(
            seq,
            "desk_large",
            2100,
            2400,
            task_id="write_release_notes",
            object_type="release_console",
            sabotage_repair_id="comms_outage",
        )
    )
    out.append(make(seq, "chair_desk", 2100, 2480))
    out.append(make(seq, "monitor", 2050, 2350))
    out.append(make(seq, "monitor", 2150, 2350))
    # War-room meeting table closer to the front
    out.append(make(seq, "meeting_table", 2100, 2900, width=360, height=120))
    for offset in (-120, 0, 120):
        out.append(make(seq, "chair_meeting", 2100 + offset, 2820))
        out.append(make(seq, "chair_meeting", 2100 + offset, 2980))
    # Big screen
    out.append(make(seq, "presentation_screen", 2100, 2080))
    out.append(make(seq, "rug", 2100, 2900, width=400, height=180))
    out.append(make(seq, "plant_cactus", 1480, 3120))
    out.append(make(seq, "plant_cactus", 2720, 3120))
    return out


def furnish_kitchen(seq) -> list[dict[str, Any]]:
    """1400x1200. refill_coffee at (3500, 2700)."""
    out: list[dict[str, Any]] = []
    # L-shaped counter run along the back wall
    out.append(make(seq, "kitchen_counter", 2960, 2080))
    out.append(make(seq, "kitchen_counter", 3280, 2080))
    out.append(make(seq, "kitchen_counter", 3600, 2080))
    out.append(make(seq, "kitchen_corner", 3920, 2080))
    out.append(make(seq, "kitchen_counter", 4060, 2200, rotation=90))
    out.append(make(seq, "kitchen_sink", 3280, 2150))
    # Coffee machine — task anchor pin
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
    out.append(make(seq, "fridge", 4080, 2900))
    # Standing tables / stools
    out.append(make(seq, "meeting_table", 3500, 2950, width=320, height=110))
    out.append(make(seq, "chair_stool", 3380, 2900))
    out.append(make(seq, "chair_stool", 3500, 2900))
    out.append(make(seq, "chair_stool", 3620, 2900))
    out.append(make(seq, "chair_stool", 3380, 3000))
    out.append(make(seq, "chair_stool", 3500, 3000))
    out.append(make(seq, "chair_stool", 3620, 3000))
    out.append(make(seq, "plant_cactus", 2900, 3120))
    out.append(make(seq, "rug", 3500, 2900, width=380, height=160))
    return out


def furnish_legacy_basement(seq) -> list[dict[str, Any]]:
    """1400x1200. calm_legacy_service at (4900, 2700). Old crates +
    workstations — feels like the abandoned PHP corner."""
    out: list[dict[str, Any]] = []
    # Legacy terminal — task anchor
    out.append(
        make(
            seq,
            "old_workstation",
            4900,
            2700,
            task_id="calm_legacy_service",
            object_type="legacy_terminal",
        )
    )
    out.append(make(seq, "chair_desk", 4900, 2770))
    out.append(make(seq, "monitor", 4900, 2650))
    # A few more old workstations
    out.append(make(seq, "old_workstation", 4400, 2700))
    out.append(make(seq, "chair_desk", 4400, 2770))
    out.append(make(seq, "monitor", 4400, 2650))
    out.append(make(seq, "old_workstation", 5400, 2700))
    out.append(make(seq, "chair_desk", 5400, 2770))
    out.append(make(seq, "monitor", 5400, 2650))
    # Stacked crates + cabinet — the "junk corner"
    out.append(make(seq, "crate", 4290, 2090))
    out.append(make(seq, "crate", 4380, 2090))
    out.append(make(seq, "crate", 4290, 2180))
    out.append(make(seq, "crate", 5510, 2090))
    out.append(make(seq, "crate", 5400, 2090))
    out.append(make(seq, "cabinet", 5500, 3120))
    out.append(make(seq, "cabinet", 4310, 3120))
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
