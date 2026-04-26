"""
Map-Loader und Pydantic-Modelle fuer die Spielkarte.

Die Karte definiert: Raeume, Wand-Linien (mit Tuer-Cutouts), Spawn-Punkte,
Task-Anker und welcher Raum der War Room ist. Wand-Rechtecke werden zur
Lade-Zeit aus den Wand-Linien + Tuerenberechnet (siehe walls.py).

Mehrere Karten liegen unter /maps/*.json. ``discover_maps`` scannt das
Verzeichnis; ``MAP_REGISTRY`` ist die lazy gefuellte module-globale Map-Map.
Der Editor (spaeter) erzeugt das gleiche Format.
"""

import json
import logging
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.game.walls import (
    DOOR_WIDTH_DEFAULT,
    horizontal_wall_segments,
    vertical_wall_segments,
)


def _camel() -> ConfigDict:
    return ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class WallDoor(BaseModel):
    model_config = _camel()
    center: int
    width: int = DOOR_WIDTH_DEFAULT


class WallLine(BaseModel):
    model_config = _camel()
    axis: Literal["x", "y"]
    position: int
    doors: list[WallDoor] = Field(default_factory=list)


class Room(BaseModel):
    model_config = _camel()
    id: str
    title: str
    x: int
    y: int
    width: int
    height: int
    color: str  # hex


class MapSize(BaseModel):
    model_config = _camel()
    width: int
    height: int


class TaskAnchor(BaseModel):
    model_config = _camel()
    task_id: str
    x: float
    y: float


class SpawnPoint(BaseModel):
    model_config = _camel()
    x: float
    y: float


class SabotagePanel(BaseModel):
    """Spatial anchor where a sabotage can be repaired (Tier 2.4+).

    Players have to reach this point to clear the corresponding sabotage.
    `sabotage_id` matches a SabotageDefinition.id.
    """

    model_config = _camel()
    sabotage_id: str
    x: float
    y: float


class Vent(BaseModel):
    """Tier 2.3: a vent through which chaos agents can teleport.

    `connected_to` is a list of vent ids reachable from this one. Edges should
    be symmetric (if A lists B, B should list A) but the server treats the
    field literally — so a one-way vent is technically representable.
    """

    model_config = _camel()
    id: str
    x: float
    y: float
    connected_to: list[str] = Field(default_factory=list)


class GameMap(BaseModel):
    model_config = _camel()
    name: str
    size: MapSize
    rooms: list[Room]
    wall_lines: list[WallLine] = Field(default_factory=list)
    spawn_points: list[SpawnPoint] = Field(default_factory=list)
    task_anchors: list[TaskAnchor] = Field(default_factory=list)
    sabotage_panels: list[SabotagePanel] = Field(default_factory=list)
    vents: list[Vent] = Field(default_factory=list)
    war_room_id: str


def load_map(path: Path) -> GameMap:
    """Load and validate a map JSON. Raises on invalid data."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return GameMap.model_validate(raw)


def compute_walls(game_map: GameMap) -> list[tuple[int, int, int, int]]:
    """Concrete wall rectangles for the map. Computed once per map; pure."""
    out: list[tuple[int, int, int, int]] = []
    for line in game_map.wall_lines:
        doors_pairs = [(d.center, d.width) for d in line.doors]
        if line.axis == "x":
            out.extend(vertical_wall_segments(line.position, doors_pairs, game_map.size.height))
        else:
            out.extend(horizontal_wall_segments(line.position, doors_pairs, game_map.size.width))
    return out


def war_room_bounds_for(game_map: GameMap) -> tuple[int, int, int, int]:
    """Find the room with id=war_room_id and return (x_min, y_min, x_max, y_max)."""
    room = next((r for r in game_map.rooms if r.id == game_map.war_room_id), None)
    if room is None:
        raise ValueError(f"war_room_id {game_map.war_room_id!r} not found in rooms")
    return (room.x, room.y, room.x + room.width, room.y + room.height)


def task_position_map(game_map: GameMap) -> dict[str, tuple[float, float]]:
    """Return {task_id: (x, y)} from the map's task_anchors."""
    return {a.task_id: (a.x, a.y) for a in game_map.task_anchors}


# Default map loaded at module import time. Tests can override.
_DEFAULT_MAP_PATH: Final[Path] = Path(__file__).parent.parent.parent / "maps" / "default.json"
DEFAULT_MAP: Final[GameMap] = load_map(_DEFAULT_MAP_PATH)


# --- map registry -----------------------------------------------------------

DEFAULT_MAP_ID: Final[str] = "default"

_MAPS_DIR: Final[Path] = Path(__file__).parent.parent.parent / "maps"
_log = logging.getLogger("mcm.maps")

# Lazy-populated cache of {stem: GameMap}. Tests can call ``reload_map_registry``
# to force a re-scan; production code typically reads via ``get_map_registry``.
_MAP_REGISTRY_CACHE: dict[str, GameMap] | None = None


def discover_maps(maps_dir: Path = _MAPS_DIR) -> dict[str, GameMap]:
    """Scan ``maps_dir`` for *.json maps and return ``{stem: GameMap}``.

    Files that fail to load are logged and skipped — one bad map should not
    poison the whole registry. Result keys are sorted alphabetically for
    deterministic ordering on the wire.
    """
    out: dict[str, GameMap] = {}
    if not maps_dir.exists():
        return out
    for path in sorted(maps_dir.glob("*.json")):
        try:
            out[path.stem] = load_map(path)
        except Exception:
            _log.exception("Skipping invalid map file %s", path)
    return out


def reload_map_registry() -> dict[str, GameMap]:
    """Force a re-scan of the maps directory and return the fresh registry."""
    global _MAP_REGISTRY_CACHE
    _MAP_REGISTRY_CACHE = discover_maps()
    return _MAP_REGISTRY_CACHE


def get_map_registry() -> dict[str, GameMap]:
    """Return the lazily-populated registry of available maps."""
    global _MAP_REGISTRY_CACHE
    if _MAP_REGISTRY_CACHE is None:
        _MAP_REGISTRY_CACHE = discover_maps()
    return _MAP_REGISTRY_CACHE


def resolve_default_map_id(registry: dict[str, GameMap] | None = None) -> str:
    """Return ``DEFAULT_MAP_ID`` if present in the registry, else the first
    sorted id (registry guarantees alphabetic ordering). Falls back to the
    constant if the registry is empty so the wire field is never blank."""
    reg = registry if registry is not None else get_map_registry()
    if DEFAULT_MAP_ID in reg:
        return DEFAULT_MAP_ID
    if reg:
        return next(iter(sorted(reg.keys())))
    return DEFAULT_MAP_ID
