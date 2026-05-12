"""
Map-Loader und Pydantic-Modelle fuer die Spielkarte.

Die Karte definiert: Raeume (Rechtecke), Tueren (zwischen adjacenten Raum-
Paaren), Spawn-Punkte, Task-Anker, Vents, Sabotage-Panels, MapObjects, und
welcher Raum der War Room ist. Waende werden NICHT explizit gespeichert —
sie ergeben sich automatisch aus den Raum-Kanten: jede gemeinsame Kante
zweier Raeume ist eine Wand, abzueglich aller Tueren auf dieser Kante.
Map-Aussenkanten werden nicht gewallt (Player-Clamp im MovementController).

Slice-3-Schema-Bruch (2026-04-27): das alte ``wallLines`` ist entfernt.
Maps mit dem alten Feld werfen Pydantic-Validation-Errors; Migration via
``scripts/migrate_walls_to_doors.py`` ist die einmalige Konversion.

Mehrere Karten liegen unter /maps/*.json. ``discover_maps`` scannt das
Verzeichnis; ``MAP_REGISTRY`` ist die lazy gefuellte module-globale
Map-Map. Der Editor erzeugt das gleiche Format.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from app.game.kinds_registry import get_kinds_registry, is_known_kind, known_kinds
from app.game.walls import DOOR_WIDTH_DEFAULT, WALL_THICKNESS


def _camel() -> ConfigDict:
    return ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class Door(BaseModel):
    """A door is a gap in the auto-derived wall between two adjacent rooms.

    ``position`` is a coordinate along the shared edge: y for vertical
    shared edges (rooms side-by-side), x for horizontal shared edges
    (rooms top/bottom). ``width`` is the gap size, defaults to 240.
    ``door_kind`` is a client-side asset hint (browser ignores it; Godot
    maps it to a PackedScene like ``office_door`` or ``glass_panel``).
    """

    model_config = _camel()
    id: str
    between_room_a: str
    between_room_b: str
    position: int
    width: int = DOOR_WIDTH_DEFAULT
    door_kind: str = "office_door"


# Allowed values for the optional Godot-flavour fields on ``Room``.
_FLOOR_MATERIALS: Final[tuple[str, ...]] = ("office", "kitchen", "server", "legacy")
_LIGHTING_PROFILES: Final[tuple[str, ...]] = ("neutral", "warm", "cold", "dim")


class Room(BaseModel):
    """Axis-aligned rectangle. Room boundaries become walls automatically
    where they aren't shared with another room (and aren't on the map edge)
    or carved by a Door.

    Tier-4 / Godot-flavour fields are all optional with sensible defaults
    so the browser-only flow is unaffected; the Godot client uses them to
    pick floor materials, ceiling height, ambient lighting, and per-room
    sound zones."""

    model_config = _camel()
    id: str
    title: str
    x: int
    y: int
    width: int
    height: int
    color: str  # hex — used by 2D browser render
    # Godot-flavour (optional, ignored by browser):
    floor_material: str = "office"
    wall_height_m: float = 2.6
    lighting_profile: str = "neutral"
    ambient_sound: str | None = None


class MapSize(BaseModel):
    model_config = _camel()
    width: int
    height: int


class TaskAnchor(BaseModel):
    """Spatial anchor for a task. ``object_type`` (e.g. ``ci_console``,
    ``git_terminal``, ``coffee_machine``) lets sabotages bind to the same
    physical spot — chaos triggers a sabotage *at* the anchor that release-team
    uses for the matching task, so observers can't tell sabotage from task work.
    Maps without ``object_type`` keep the legacy "trigger from anywhere" path.
    """

    model_config = _camel()
    task_id: str
    x: float
    y: float
    object_type: str | None = None


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


class MapObject(BaseModel):
    """Tier 4 prop on the map — desks, server racks, kitchen counters,
    plants. Bounding box for server-side collision plus a logical ``kind``
    that each client maps to its own visual asset (browser: coloured
    rectangle with label, Godot: PackedScene from a kind→.gltf table).

    Optional bindings let one MapObject replace the legacy standalone
    ``TaskAnchor`` / ``SabotagePanel`` so a single physical desk can be a
    release-team task spot AND a sabotage trigger AND a repair panel.

    Rotation is axis-aligned only (0/90/180/270 in 90deg steps). 90 and
    270 swap width and height for collision; visual rotation is the
    client's responsibility.
    """

    model_config = _camel()
    id: str
    x: float
    y: float
    width: float
    height: float
    kind: str
    rotation: Literal[0, 90, 180, 270] = 0
    blocks_movement: bool = True
    # Optional gameplay bindings:
    task_id: str | None = None
    sabotage_repair_id: str | None = None
    object_type: str | None = None  # Tier 2.7 sabotage trigger binding

    @model_validator(mode="before")
    @classmethod
    def _default_blocks_movement_from_registry(cls, data: Any) -> Any:
        """Wenn weder ``blocks_movement`` noch ``blocksMovement`` im Map-JSON
        gesetzt sind, fuelle den Wert aus ``maps/kinds.json``. Damit wird die
        Registry zur Default-Source: einzelne Map-JSONs muessen das Feld nur
        explizit setzen, wenn sie das Kind-Default ueberschreiben wollen.
        Verhindert die Drift-Klasse, in der ein Map-JSON-Eintrag fuer einen
        Tisch ``blocksMovement: false`` haelt obwohl die Registry True sagt.
        Pydantic-Default ``True`` bleibt als Last-Resort-Fallback fuer Kinds
        ohne Registry-Eintrag (was der ``kind``-Validator separat ablehnt).
        """
        if (
            isinstance(data, dict)
            and "blocks_movement" not in data
            and "blocksMovement" not in data
        ):
            kind = data.get("kind")
            if kind:
                kdef = get_kinds_registry().get(kind)
                if isinstance(kdef, dict) and "blocks_movement" in kdef:
                    data["blocks_movement"] = kdef["blocks_movement"]
        return data

    @field_validator("kind")
    @classmethod
    def _kind_must_be_registered(cls, value: str) -> str:
        """Reject any kind that isn't in maps/kinds.json.

        Same severity as ``extra=forbid`` on the map level: a kind that
        no consumer knows about cannot render correctly anywhere, so we
        catch it at load-time rather than letting it ship to clients.
        """
        if not is_known_kind(value):
            known = ", ".join(sorted(known_kinds())) or "(registry empty)"
            raise ValueError(
                f"Unknown MapObject kind {value!r}: not in maps/kinds.json. "
                f"Add it to the registry first. Known kinds: {known}"
            )
        return value


class GameMap(BaseModel):
    model_config = _camel()
    name: str
    size: MapSize
    rooms: list[Room]
    # Slice-3 (Tier 4 prep): doors live as a top-level list, each door
    # references two adjacent rooms by id. Walls are auto-derived from
    # adjacent room edges (see ``compute_walls``); no separate
    # ``wallLines`` storage anymore. Migration via
    # scripts/migrate_walls_to_doors.py.
    doors: list[Door] = Field(default_factory=list)
    spawn_points: list[SpawnPoint] = Field(default_factory=list)
    task_anchors: list[TaskAnchor] = Field(default_factory=list)
    sabotage_panels: list[SabotagePanel] = Field(default_factory=list)
    vents: list[Vent] = Field(default_factory=list)
    # Tier 4: optional list of props (furniture, server racks, decor).
    map_objects: list[MapObject] = Field(default_factory=list)
    war_room_id: str


def load_map(path: Path) -> GameMap:
    """Load and validate a map JSON. Raises on invalid data."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return GameMap.model_validate(raw)


def map_object_aabb(obj: "MapObject") -> tuple[int, int, int, int]:
    """AABB (x1, y1, x2, y2) for a MapObject. The object's ``x``/``y`` is
    the CENTER; rotation 90/270 swaps width and height for collision."""
    half_w = obj.width / 2.0
    half_h = obj.height / 2.0
    if obj.rotation in (90, 270):
        half_w, half_h = half_h, half_w
    return (
        int(round(obj.x - half_w)),
        int(round(obj.y - half_h)),
        int(round(obj.x + half_w)),
        int(round(obj.y + half_h)),
    )


def _interval_subtract(
    start: int, end: int, cutouts: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Return ``[start, end]`` minus the union of ``cutouts``. Each cutout
    is ``(a, b)`` with ``a < b``. The result is a sorted list of intervals
    that together cover ``[start, end] \\ cutouts``. Cutouts outside the
    range are clipped; overlapping cutouts merge naturally."""
    if not cutouts:
        return [(start, end)] if start < end else []
    clipped: list[tuple[int, int]] = []
    for a, b in cutouts:
        sa = max(a, start)
        sb = min(b, end)
        if sa < sb:
            clipped.append((sa, sb))
    clipped.sort()
    out: list[tuple[int, int]] = []
    cursor = start
    for a, b in clipped:
        if a > cursor:
            out.append((cursor, a))
        cursor = max(cursor, b)
    if cursor < end:
        out.append((cursor, end))
    return out


def _edge_overlap(
    other: Room, axis: str, edge_pos: int, start: int, end: int
) -> tuple[int, int] | None:
    """If ``other`` has a room edge at ``(axis, edge_pos)`` overlapping the
    perpendicular range ``[start, end]``, return the overlap interval.
    Otherwise return None.

    ``axis="x"`` means a vertical edge at x=edge_pos; the perpendicular
    coordinate is y. ``axis="y"`` means a horizontal edge at y=edge_pos
    with perpendicular x.
    """
    if axis == "x":
        if other.x != edge_pos and other.x + other.width != edge_pos:
            return None
        a = max(start, other.y)
        b = min(end, other.y + other.height)
    else:
        if other.y != edge_pos and other.y + other.height != edge_pos:
            return None
        a = max(start, other.x)
        b = min(end, other.x + other.width)
    return (a, b) if a < b else None


def _wall_rect(axis: str, edge_pos: int, seg_start: int, seg_end: int) -> tuple[int, int, int, int]:
    """Wall rectangle ``(x1, y1, x2, y2)`` centered on the given edge."""
    if axis == "x":
        return (edge_pos - WALL_THICKNESS, seg_start, edge_pos + WALL_THICKNESS, seg_end)
    return (seg_start, edge_pos - WALL_THICKNESS, seg_end, edge_pos + WALL_THICKNESS)


def _is_map_edge(axis: str, edge_pos: int, map_size: MapSize) -> bool:
    """True if the given edge sits exactly on the outer map boundary —
    those are NOT walled (the MovementController clamps perimeter)."""
    if axis == "x":
        return edge_pos == 0 or edge_pos == map_size.width
    return edge_pos == 0 or edge_pos == map_size.height


def compute_walls(game_map: GameMap) -> list[tuple[int, int, int, int]]:
    """Concrete wall rectangles for the map. Computed once per map; pure.

    Slice-3 algorithm: walls are derived from adjacent room edges, with
    door cutouts. For each room edge:
      - Shared portions with another room → wall minus matching doors.
        Processed once per room pair (dedup via ``processed`` set).
      - Non-shared (perimeter-of-room) portions → wall, unless the edge
        sits on the map outer boundary.
    Plus blocking ``map_objects`` (Tier 4 props) get their AABBs added.
    """
    out: list[tuple[int, int, int, int]] = []
    rooms = list(game_map.rooms)

    # Each (axis, edge_pos, room_a_id, room_b_id, ovl_start, ovl_end) is
    # processed once; the second time we hit the same pair from the other
    # room's edge iteration, we skip it.
    processed: set[tuple[str, int, str, str, int, int]] = set()

    for room in rooms:
        edges = (
            ("y", room.y, room.x, room.x + room.width),  # top
            ("y", room.y + room.height, room.x, room.x + room.width),  # bottom
            ("x", room.x, room.y, room.y + room.height),  # left
            ("x", room.x + room.width, room.y, room.y + room.height),  # right
        )
        for axis, edge_pos, start, end in edges:
            shared: list[tuple[str, tuple[int, int]]] = []
            for other in rooms:
                if other.id == room.id:
                    continue
                ovl = _edge_overlap(other, axis, edge_pos, start, end)
                if ovl is not None:
                    shared.append((other.id, ovl))

            # Shared portions — emit walls (with door cutouts), one per pair.
            for other_id, (ovl_start, ovl_end) in shared:
                pair_key = tuple(sorted([room.id, other_id]))
                key = (axis, edge_pos, pair_key[0], pair_key[1], ovl_start, ovl_end)
                if key in processed:
                    continue
                processed.add(key)

                cutouts: list[tuple[int, int]] = []
                for door in game_map.doors:
                    door_pair = tuple(sorted([door.between_room_a, door.between_room_b]))
                    if door_pair != pair_key:
                        continue
                    if not (ovl_start <= door.position <= ovl_end):
                        continue
                    half = door.width // 2
                    cutouts.append((door.position - half, door.position + half))

                for seg_start, seg_end in _interval_subtract(ovl_start, ovl_end, cutouts):
                    out.append(_wall_rect(axis, edge_pos, seg_start, seg_end))

            # Perimeter portions — only if this edge isn't on the map boundary.
            if not _is_map_edge(axis, edge_pos, game_map.size):
                shared_cuts = [ovl for _, ovl in shared]
                for seg_start, seg_end in _interval_subtract(start, end, shared_cuts):
                    out.append(_wall_rect(axis, edge_pos, seg_start, seg_end))

    # Tier 4: blocking MapObjects.
    for obj in game_map.map_objects:
        if obj.blocks_movement:
            out.append(map_object_aabb(obj))
    return out


def war_room_bounds_for(game_map: GameMap) -> tuple[int, int, int, int]:
    """Find the room with id=war_room_id and return (x_min, y_min, x_max, y_max)."""
    room = next((r for r in game_map.rooms if r.id == game_map.war_room_id), None)
    if room is None:
        raise ValueError(f"war_room_id {game_map.war_room_id!r} not found in rooms")
    return (room.x, room.y, room.x + room.width, room.y + room.height)


def task_position_map(game_map: GameMap) -> dict[str, tuple[float, float]]:
    """Return ``{task_id: (x, y)}`` for every task anchored on the map.

    Both legacy ``task_anchors`` and Tier-4 ``map_objects`` with a
    ``task_id`` contribute. When the same task id appears in both, the
    MapObject wins because that's the newer system — but in practice,
    a map should pick one or the other.
    """
    out: dict[str, tuple[float, float]] = {a.task_id: (a.x, a.y) for a in game_map.task_anchors}
    for obj in game_map.map_objects:
        if obj.task_id:
            out[obj.task_id] = (obj.x, obj.y)
    return out


# Default map loaded at module import time. Tests can override.
_DEFAULT_MAP_PATH: Final[Path] = Path(__file__).parent.parent.parent / "maps" / "default.json"
DEFAULT_MAP: Final[GameMap] = load_map(_DEFAULT_MAP_PATH)


# --- map registry -----------------------------------------------------------

DEFAULT_MAP_ID: Final[str] = "default"

_MAPS_DIR: Final[Path] = Path(__file__).parent.parent.parent / "maps"
_log = logging.getLogger("mcm.maps")

# Files in the maps/ directory that aren't game maps. Currently just the
# kinds-registry (Tier 3.8.7) — the discovery loop skips these instead
# of trying to validate them as GameMap (and noisily logging the failure
# at every save_map / reload_map_registry call).
_NON_MAP_FILES: Final[frozenset[str]] = frozenset({"kinds.json"})

# Lazy-populated cache of {stem: GameMap}. Tests can call ``reload_map_registry``
# to force a re-scan; production code typically reads via ``get_map_registry``.
_MAP_REGISTRY_CACHE: dict[str, GameMap] | None = None


def discover_maps(maps_dir: Path | None = None) -> dict[str, GameMap]:
    """Scan ``maps_dir`` for *.json maps and return ``{stem: GameMap}``.

    ``maps_dir`` defaults to the module-level ``_MAPS_DIR`` looked up at
    call time so tests can monkey-patch it without rebinding default args.

    Files that fail to load are logged and skipped — one bad map should not
    poison the whole registry. Result keys are sorted alphabetically for
    deterministic ordering on the wire.
    """
    if maps_dir is None:
        maps_dir = _MAPS_DIR
    out: dict[str, GameMap] = {}
    if not maps_dir.exists():
        return out
    for path in sorted(maps_dir.glob("*.json")):
        if path.name in _NON_MAP_FILES:
            continue
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


# Map-id sanitisation. Editor-facing API accepts a slugified form so
# filenames stay shell-safe and free from path-traversal vectors.
_MAP_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def is_valid_map_id(map_id: str) -> bool:
    """True if ``map_id`` is a safe slug we'd accept as a filename stem."""
    return bool(_MAP_ID_PATTERN.fullmatch(map_id))


def save_map(map_id: str, raw: dict[str, Any], maps_dir: Path | None = None) -> GameMap:
    """Validate ``raw`` against the schema and write to ``maps_dir/{id}.json``.

    ``maps_dir`` defaults to the module-level ``_MAPS_DIR`` resolved at call
    time so tests can monkey-patch it. Raises ``ValueError`` for invalid
    ids and ``pydantic.ValidationError`` for invalid map content. Atomic
    write via tmp-file + rename so a crash half-way never leaves a corrupt
    JSON behind. Reloads the registry so the next room creation sees the
    new map.
    """
    if not is_valid_map_id(map_id):
        raise ValueError(f"Invalid map id {map_id!r}: must match [a-z0-9][a-z0-9_-]{{0,39}}")
    if maps_dir is None:
        maps_dir = _MAPS_DIR
    parsed = GameMap.model_validate(raw)
    maps_dir.mkdir(parents=True, exist_ok=True)
    target = maps_dir / f"{map_id}.json"
    tmp = target.with_suffix(".json.tmp")
    payload = json.dumps(parsed.model_dump(by_alias=True), indent=2, ensure_ascii=False)
    tmp.write_text(payload + "\n", encoding="utf-8")
    tmp.replace(target)
    reload_map_registry()
    return parsed


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
