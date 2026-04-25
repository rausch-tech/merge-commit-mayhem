# Map JSON Schema

A map is a single JSON file describing the physical layout that the game engine
interprets. The default map lives at `/maps/default.json`. New maps can be added
by dropping further JSON files in that directory and (later) selecting them from
the lobby; for now only the default is loaded.

## Top-level

```jsonc
{
  "name": "default-office",
  "size": { "width": 2400, "height": 1600 },
  "rooms":         [ ... ],
  "wallLines":     [ ... ],
  "spawnPoints":   [ ... ],
  "taskAnchors":   [ ... ],
  "warRoomId":     "war_room"
}
```

## Rooms

Each room is an axis-aligned rectangle.

```jsonc
{ "id": "open_space", "title": "Open Space", "x": 0, "y": 0, "width": 800, "height": 800, "color": "#3a4560" }
```

## Wall lines + doors

A wall line runs across the map on one axis with optional door cutouts.

```jsonc
{
  "axis": "x",
  "position": 800,
  "doors": [{ "center": 400, "width": 120 }, { "center": 1200, "width": 120 }]
}
```

`axis: "x"` means a vertical wall line at x=position (runs the full height of the map).
`axis: "y"` means a horizontal wall line at y=position (runs the full width).

The engine computes concrete wall rectangles from these lines + door cutouts at
load time. A door `width` is optional and defaults to 120.

## Spawn points + task anchors + war room

`spawnPoints` is a list of `{ "x": ..., "y": ... }` points where players are
placed at round start (in join order).

`taskAnchors` connects logical task ids (defined in `app/game/tasks.py`) to
coordinates on this map. Each entry is `{ "taskId": "...", "x": ..., "y": ... }`.
The server uses this at GameRoom-init time; the client receives task positions
via the `game_state` message.

`warRoomId` references the room id where Emergency Meetings can be called from.
The server derives the war-room AABB from the referenced room rectangle.

## Server behaviour

The map is loaded once at startup (`app/game/game_map.DEFAULT_MAP`) and sent
to each client inside the `room_joined` payload. The client renders rooms and
walls directly from this data — no hardcoded layout in the frontend.

Wall rectangles are computed server-side via `compute_walls()` and also
recomputed client-side in `render.js:computeWallsClient()` using the same
algorithm, so both physics and visuals remain in sync without the server having
to send precomputed wall rectangles.
