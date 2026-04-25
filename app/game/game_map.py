"""
Map-Loader und Pydantic-Modelle fuer die Spielkarte.

Die Karte definiert: Raeume, Wand-Linien (mit Tuer-Cutouts), Spawn-Punkte,
Task-Anker und welcher Raum der War Room ist. Wand-Rechtecke werden zur
Lade-Zeit aus den Wand-Linien + Tuerenberechnet (siehe walls.py).

Eine einzelne Standard-Karte liegt unter /maps/default.json. Der Editor
(spaeter) erzeugt das gleiche Format.
"""

import json
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


class GameMap(BaseModel):
    model_config = _camel()
    name: str
    size: MapSize
    rooms: list[Room]
    wall_lines: list[WallLine] = Field(default_factory=list)
    spawn_points: list[SpawnPoint] = Field(default_factory=list)
    task_anchors: list[TaskAnchor] = Field(default_factory=list)
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
