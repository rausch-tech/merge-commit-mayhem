# Map JSON Schema

A map is a single JSON file describing the physical layout that the game engine
interprets. The default map lives at `/maps/default.json`. New maps can be added
by dropping further JSON files in that directory and (later) selecting them from
the lobby; for now only the default is loaded.

Maps können auch im Browser-Editor unter `/editor` erstellt werden. Der Editor
ist ein rein clientseitiges Tool: er erzeugt JSON-Dateien in genau diesem
Schema, modifiziert keinen Server-State und kann bestehende Maps zur Bearbeitung
laden.

## Top-level

```jsonc
{
  "name": "default-office",
  "size": { "width": 4800, "height": 3200 },
  "rooms":          [ ... ],
  "doors":          [ ... ],   // Slice-3 (Wand-Modell C): top-level
  "spawnPoints":    [ ... ],
  "taskAnchors":    [ ... ],
  "sabotagePanels": [ ... ],
  "vents":          [ ... ],
  "mapObjects":     [ ... ],   // Tier 4 props (optional, defaults to [])
  "warRoomId":      "war_room"
}
```

## Rooms

Each room is an axis-aligned rectangle. Optional Tier-4 / Godot fields
let the 3D client pick floor materials, ceiling height, ambient lighting,
and per-room sound zones — the browser ignores them.

```jsonc
{
  "id": "open_space",
  "title": "Open Space",
  "x": 0,
  "y": 0,
  "width": 800,
  "height": 800,
  "color": "#3a4560",

  // Tier-4 / Godot extras (all optional, sensible defaults):
  "floorMaterial": "office", // office | kitchen | server | legacy
  "wallHeightM": 2.6,
  "lightingProfile": "neutral", // neutral | warm | cold | dim
  "ambientSound": null, // e.g. "kitchen_hum", "server_fans"
}
```

## Walls and doors

**Walls are not stored.** They are auto-derived at runtime from the room
rectangles minus any doors. For each pair of adjacent rooms the shared
edge becomes a wall (with door cutouts); for each room edge that is
neither shared with another room nor on the map outer boundary, that
edge becomes a perimeter wall. Map-perimeter edges are NOT walled —
the server's MovementController clamps the player to the map bounds.

This means: to "open" a passage between two adjacent rooms, you add a
door referencing both room ids. To remove a wall section, you either
add a door there or move/resize the rooms so the edge isn't shared and
isn't a perimeter.

### Doors

A door is a gap on the shared edge between two rooms.

```jsonc
{
  "id": "d1",
  "betweenRoomA": "open_space",
  "betweenRoomB": "meeting_room",
  "position": 800, // coordinate along the shared edge (y for vertical, x for horizontal)
  "width": 240, // optional, default 240
  "doorKind": "office_door", // optional, default "office_door". Godot uses this as a sprite/scene key.
}
```

`betweenRoomA` and `betweenRoomB` are room ids; the order doesn't matter
(the algorithm sorts internally for dedup). `position` is interpreted
along the perpendicular axis of the shared edge:

- For a **vertical** shared edge (rooms side-by-side, edge at some
  `x=N`), `position` is a y-coordinate.
- For a **horizontal** shared edge (rooms top/bottom, edge at some
  `y=N`), `position` is an x-coordinate.

`doorKind` is a free-form string used by the Godot client to pick a 3D
door scene (`office_door`, `glass_panel`, `vault`, `none`). The browser
client ignores it.

### Pre-Slice-3 schema (deprecated)

Maps written before 2026-04-27 used `wallLines: [{axis, position, doors}]`
to define walls explicitly. That field is gone — use the one-shot
migration script:

```bash
uv run python scripts/migrate_walls_to_doors.py
```

The script reads each `maps/*.json` file in place, drops `wallLines`,
and emits the equivalent top-level `doors` list. Output is committed.
Maps that still contain `wallLines` after migration will fail Pydantic
validation at server startup with a clear `extra_forbidden` error.

## Spawn points + task anchors + war room

`spawnPoints` is a list of `{ "x": ..., "y": ... }` points where players are
placed at round start (in join order).

`taskAnchors` connects logical task ids (defined in `app/game/tasks.py`) to
coordinates on this map. Each entry is `{ "taskId": "...", "x": ..., "y": ... }`.
The server uses this at GameRoom-init time; the client receives task positions
via the `game_state` message.

`warRoomId` references the room id where Emergency Meetings can be called from.
The server derives the war-room AABB from the referenced room rectangle.

## Map objects (Tier 4 — props with collision)

`mapObjects` is an optional list of axis-aligned props on the map: desks,
server racks, kitchen counters, fridges, plants, decorative crates. Each
object has a center position, a bounding box (width × height), a logical
`kind` for client-side asset lookup, and optional gameplay bindings.

```jsonc
{
  "id": "os-desk-qa", // unique within the map
  "x": 400,
  "y": 400, // CENTER point (not top-left)
  "width": 110,
  "height": 60,
  "kind": "desk", // logical asset key (see catalogue below)
  "rotation": 0, // axis-aligned: 0 / 90 / 180 / 270 only
  "blocksMovement": true, // true (default) = added to wall collision
  "taskId": "fix_unit_tests", // optional — replaces standalone TaskAnchor
  "objectType": "qa_terminal", // optional — Tier 2.7 sabotage trigger binding
  "sabotageRepairId": "lights_out", // optional — replaces standalone SabotagePanel
}
```

**Collision.** Objects with `blocksMovement: true` contribute their AABB to
the server's wall list (see `compute_walls()`). Rotation 90/270 swaps width
and height for collision; the client's renderer mirrors the same swap so
the drawn rectangle matches the physical one exactly.

**Bindings.** A single MapObject can simultaneously be a release-team task
spot, a sabotage trigger, and a repair panel. The server picks up
`taskId`, `objectType`, and `sabotageRepairId` from MapObjects in addition
to the legacy standalone `taskAnchors` / `sabotagePanels` lists, so a
map can use either system or mix them during migration.

**Why MapObjects exist.** Two reasons.

1. _Physical realism._ The mockup (`images/ingame.png`) shows offices
   crammed with desks, server racks, kitchen counters — props that
   visually fill space and physically block the player. The wall-line
   abstraction can't represent free-standing furniture; MapObjects can.
2. _Client-agnostic asset wiring._ The browser renders each MapObject as
   a coloured rectangle with a `kind` label (placeholder; see
   `static/render.js:MAP_OBJECT_STYLE`). The Godot client maps the same
   `kind` to a real `.gltf` PackedScene from the KayKit Bits Bundle —
   one server payload, two visual treatments, no asset paths on the wire.

### Kind catalogue

**Source of truth: [`maps/kinds.json`](../maps/kinds.json).** Beim
Hinzufuegen eines Kinds **nur dort ergaenzen** — alle Konsumenten lesen die
Registry zur Laufzeit:

- **Backend-Validator** (`app/game/game_map.py`) — Pydantic `@field_validator`
  auf `MapObject.kind` rejected unbekannte Kinds beim Map-Load.
- **Browser-Frontend** (`static/kinds.js` + `static/render.js` via
  `kindBrowser2d()`) — fetcht `/api/kinds` beim Boot.
- **Editor-Palette** (`static/editor/editor-kinds.js`) — gleicher Fetch.
- **3D-Editor-Vorschau** (`static/editor/editor-preview-3d.js`) — gleicher Fetch.
- **Godot-3D-Client** (`godot-3d/scripts/kinds_loader.gd`) — `KindsLoader`
  fetcht `/api/kinds`, fällt auf `res://maps/kinds.json` zurück wenn der
  Backend offline ist.

Drift-frei garantiert. Die Tabelle unten ist eine human-readable Mirror der
JSON-Registry:

| Kind                  | Default size | Blocks?  | Mockup region              | Browser colour        | KayKit asset (Godot)                        |
| --------------------- | ------------ | -------- | -------------------------- | --------------------- | ------------------------------------------- |
| `desk`                | 110×60       | optional | Open Space, Meeting Room   | `#7c5a3a` brown       | Furniture/`desk.fbx`                        |
| `desk_large`          | 180×80       | yes      | Open Space (boss desk)     | `#7c5a3a` brown       | Furniture/`desk_large.fbx`                  |
| `desk_decorated`      | 110×60       | yes      | Legacy Basement            | `#7c5a3a` brown       | Furniture/`desk_decorated.fbx`              |
| `chair_desk`          | 50×50        | no       | Open Space (per desk)      | `#3f3128` dark brown  | Furniture/`chair_desk_A.fbx`                |
| `chair_meeting`       | 50×50        | no       | Meeting/War Room           | `#3f3128` dark brown  | Furniture/`chair_A.fbx`                     |
| `chair_stool`         | 50×50        | no       | Kitchen                    | `#3f3128` dark brown  | Furniture/`chair_stool.fbx`                 |
| `monitor`             | 60×30        | no       | On every desk              | `#1f2937` dark slate  | Furniture/`monitor.fbx`                     |
| `keyboard`            | 50×20        | no       | Decor on desk              | `#1f2937` slate       | Furniture/`keyboard.fbx`                    |
| `mug`                 | 20×20        | no       | Decor on desk              | `#a16207` amber       | Furniture/`mug_A.fbx`                       |
| `lamp_desk`           | 30×30        | no       | Decor                      | `#fbbf24` yellow      | Furniture/`lamp_desk.fbx`                   |
| `server_rack`         | 80×100       | yes      | Server Room                | `#1e293b` deep slate  | Space Base/`structure_tall.fbx` (proxy)     |
| `monitoring_panel`    | 200×60       | no       | Server Room (analyze_logs) | `#0ea5e9` sky         | Furniture/`pictureframe_large_A.fbx`        |
| `cabinet`             | 80×80        | yes      | Server Room, Legacy        | `#3f3f46` zinc        | Furniture/`cabinet_medium.fbx`              |
| `meeting_table`       | 480×140      | yes      | Meeting Room, War Room     | `#52525b` zinc        | Furniture/`table_medium_long.fbx` (proxy)   |
| `presentation_screen` | 200×30       | no       | Meeting/War Room walls     | `#1e1b4b` indigo      | Furniture/`pictureframe_large_B.fbx`        |
| `kitchen_counter`     | 320×80       | yes      | Kitchen                    | `#9ca3af` slate       | Restaurant/`kitchencounter_straight_A.fbx`  |
| `kitchen_corner`      | 120×120      | yes      | Kitchen                    | `#9ca3af` slate       | Restaurant/`kitchencounter_innercorner.fbx` |
| `kitchen_sink`        | 120×80       | yes      | Kitchen                    | `#94a3b8` slate       | Restaurant/`kitchencounter_sink.fbx`        |
| `coffee_machine`      | 90×90        | no       | Kitchen (refill_coffee)    | `#854d0e` sienna      | Restaurant/`icecream_machine.fbx` (proxy)   |
| `fridge`              | 100×130      | yes      | Kitchen                    | `#cbd5e1` light slate | Restaurant/`fridge_A.fbx`                   |
| `plant_cactus`        | 60×60        | no       | Decor                      | `#15803d` green       | Furniture/`cactus_medium_A.fbx`             |
| `picture_frame`       | 80×30        | no       | Wall decor                 | `#a78bfa` lavender    | Furniture/`pictureframe_medium.fbx`         |
| `rug`                 | 200×120      | no       | Decor                      | `#7e22ce` purple      | Furniture/`rug_rectangle_A.fbx`             |
| `crate`               | 70×70        | yes      | Legacy Basement            | `#78350f` rust        | Space Base/`cargo_A.fbx`                    |
| `old_workstation`     | 110×60       | optional | Legacy Basement            | `#44403c` stone       | Furniture/`desk_decorated.fbx`              |

Unknown kinds **fail loud** — the Pydantic validator rejects them at
map-load time with a clear error pointing to `maps/kinds.json`. So the
palette below is exhaustive: every kind that's in a `maps/*.json` is
listed here.

## Server behaviour

The map is loaded once at startup (`app/game/game_map.DEFAULT_MAP`) and sent
to each client inside the `room_joined` payload. The client renders rooms,
walls, and `mapObjects` directly from this data — no hardcoded layout in the
frontend.

Wall rectangles are computed server-side via `compute_walls()` (lines
plus blocking-MapObject AABBs) and also recomputed client-side in
`render.js:computeWallsClient()`. The browser renderer additionally
draws every `mapObject` as a colour-coded rectangle so props remain
visually distinct from walls; collision behaviour is identical in both
worlds because the same AABB derivation runs server- and client-side.
