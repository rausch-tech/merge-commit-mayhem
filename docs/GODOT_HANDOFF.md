# Godot Client — Tier 4 Handoff

Onboarding-Dokument für den Godot-Entwickler, der den MCM Tier-4-Client baut.
Voraussetzung: solide Godot-4-Erfahrung. MCM-Vorwissen brauchst du keins —
diese Doku liefert Kontext, Architektur, Protokoll, vorhandenen Spike und
einen konkreten Slice-Plan.

- **Live-Backend:** https://game.prod-is-lava.dev (auto-deploy von `main`)
- **Repo:** https://github.com/rausch-tech/merge-commit-mayhem
- **Stand 2026-04-27:** Tier 0–3.7 ist live, Editor-Redesign abgeschlossen,
  Godot-Spike (`origin/slice/godot-spike`) wird gerade in `main` gemerged.

---

## Wie diese Doku zu lesen ist

Lies §1–§3 sequenziell — Kontext, Architektur, vorhandener Spike. Danach
nutzt du §4–§7 als Referenz, während du gegen den Code arbeitest. §8 ist
der konkrete Slice-Plan für Tier 4. §9 fasst Stolperfallen zusammen, die
beim Spike aufgefallen sind — bitte vor dem ersten F5 lesen.

Verlinkte Repository-Doku, die diese Datei nicht dupliziert:

- [`AGENTS.md`](../AGENTS.md) — repo-weiter Onboarding-Guide (Stack, Commands, CI-Gates).
- [`docs/ROADMAP.md`](ROADMAP.md) — vollständige Tier-Roadmap inkl. Tier 4.
- [`docs/PROTOCOL.md`](PROTOCOL.md) — vollständige WebSocket-Contract-Liste.
- [`docs/maps.md`](maps.md) — Map-JSON-Schema inkl. KayKit-Asset-Mapping.
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — Backend-Layout (FastAPI, Pydantic).
- [`docs/GAME_OVERVIEW.md`](GAME_OVERVIEW.md) — Spielprinzip, Rollen, Win-Conditions.

---

## 1. Was ist MCM?

### 1.1 Das Spiel

**Merge Conflict Mayhem** ist ein Social-Deduction-Multiplayer-Spiel für
Tech-Teams: Release-Team gegen geheime Chaos-Agenten in einem
DevOps-themen Office-Setting. 5–12 Spieler, ~10 Minuten pro Runde,
gedacht für die gemeinsame Mittagspause im Team.

- **Karten-Größe:** 4800×3200 px Office-Map mit Räumen wie Open Space,
  Kitchen, Server Room, Meeting Room, War Room, Legacy Basement.
- **Rollen:** 5 Release-Team-Rollen (Dev, Ops, QA, Product, Manager) +
  3 Chaos-Agent-Rollen, alle mit eigenen Tasks, Sabotagen, Active Abilities.
- **Win-Conditions** (first-to-fire):
  - Pipeline-Stability ≤ 0 → **Chaos gewinnt**
  - Alle Chaos-Agents rausgevotet → **Release gewinnt**
  - Release-Progress = 100% → **Release gewinnt**
  - 15-Minuten-Timer → **Chaos gewinnt**

Volle Spielmechanik in [`docs/GAME_OVERVIEW.md`](GAME_OVERVIEW.md).

### 1.2 Architektur-Nordstern (nicht-verhandelbar)

> **Python entscheidet. Der Client zeigt nur an.**

Daraus folgt jede Designentscheidung:

- **Backend (FastAPI + Pydantic v2 + WebSockets) ist autoritativ** für
  _allen_ State. Tickrate 20 Hz. Alle Positionen, Tasks, Sabotagen,
  Win-Conditions — Server entscheidet.
- **Clients senden nur Input, rendern Snapshots.** Keine Bewegungs-Prediction,
  keine Spiellogik im Client. Wenn Server sagt "Spieler ist auf (200, 150)",
  rendert der Client (200, 150) — Punkt.
- **WebSocket-Protokoll JSON, camelCase auf der Wire.** Pydantic erledigt
  snake_case ↔ camelCase aliasing automatisch via `alias_generator=to_camel`.
- **Public State leakt nie geheime Infos.** Roles werden ausschließlich an
  den Owner geschickt (`private_role`), nie broadcastet. Same für
  Per-Player-Coffee-Energy.

Wenn ein Feature dich verlocken würde Spiellogik in Godot zu schieben —
zurückschieben. Es bricht.

### 1.3 Aktueller Stand (Tier 0–3.7)

Was schon shipped ist und vom Godot-Client unterstützt werden muss:

- **Map** mit auto-derived walls (Slice 3, Wand-Modell C — siehe §6.4).
- **5+3 Rollen**, je mit Sabotagen, Tasks, Abilities, Coffee-Profil.
- **8 personal Tasks** pro Spieler (2 strength-matched + 1 random für
  Release; 3 fake Tasks für Chaos). 5 davon haben Mini-Games.
- **8 Sabotagen** mit object-binding (Tier 2.7) — z.B. `comms_outage`
  triggert nur wenn der Chaos am Console-Object steht.
- **Among-Us-Features:** Force-Reboot (Take-Down), Body-Discovery,
  Report, Emergency Meeting, Voting, Spectator-Mode, Vents (Chaos-Teleport).
- **Coffee-Energy** mit Decay, Refill, Splash, Speed/Task-Bonus.
- **Role-Intro-Modal, Personal-Task-Panel, Coffee-Meter, Ability-Button,
  Meeting-Context, Endscreen** mit Awards + AI-Postmortem.
- **Map-Editor** unter `/editor` für Map-Authoring.
- **591 Backend-Tests** (pytest) + **109 Frontend-Tests** (vitest), beides
  CI-Gate. Coverage-Floor: 88% auf `app/game/`.

Volle Tier-Liste mit Status: [`docs/ROADMAP.md`](ROADMAP.md).

---

## 2. Tier-4-Scope aus der Roadmap

### 2.1 Vor Godot (~1 Woche Asset-Decisions)

| #     | Task                                                           |
| ----- | -------------------------------------------------------------- |
| 4.0.1 | Asset-Pipeline-Decision (Pixel-Art-Pack vs. AI-DevOps-Sprites) |
| 4.0.2 | Asset-Pack sourcing (itch.io / Humble + Lizenzen)              |
| 4.0.3 | DevOps-Theme Sprite-Generation oder Commission                 |

Diese drei Punkte sind Sven's Entscheidung — können parallel zu Tier
4.1–4.5 laufen, blockieren erst Tier 4.10 (Polish + Animations).

### 2.2 Godot-Sprint (~4–6 Wochen)

| #    | Slice                                                                                 | Effort |
| ---- | ------------------------------------------------------------------------------------- | ------ |
| 4.1  | Godot-4-Setup, Web-Export-Config, WebSocketPeer-Binding                               | 1 Tag  |
| 4.2  | Lobby-Scene (UI, Room-Code-Input, Player-Liste, Map-Selection, Start)                 | 1–2 Tg |
| 4.3  | Map-Loader: JSON → Tilemap-Layer dynamisch                                            | 2 Tage |
| 4.4  | Character-Scene: Sprites + 4-direction Idle/Walk-Anim + Movement-Interpolation        | 2–3 Tg |
| 4.5  | HUD + Stat-Pills + Role + Timer (Tween-Animationen)                                   | 1 Tag  |
| 4.6  | Task-Interaction (Mini-Game-Modals via Tier-3-API + Progress-Ring + Completion-VFX)   | 2 Tage |
| 4.7  | Sabotage-Buttons mit Cooldown-Display                                                 | 1 Tag  |
| 4.8  | Voting-Overlay + Result-Toast (Slide-Animationen)                                     | 1 Tag  |
| 4.9  | Endscreen mit Role-Reveal + Stats + Confetti-Particles                                | 1 Tag  |
| 4.10 | Among-Us-Features: Vents (anim+sfx), Body+Report, Take-Down, Lights/Comms-VFX, Ghosts | 5–8 Tg |
| 4.11 | Sound-Integration (Footsteps, UI-SFX, BGM)                                            | 1 Tag  |
| 4.12 | Polish + Bugfixes                                                                     | 3–5 Tg |
| 4.13 | Web-Export-Deploy zur selben EC2                                                      | 0.5 Tg |

**Tier 4 ist erst "done" wenn ein Live-Test mit echten Spielern erfolgreich
ist.** Live-Tests sind in MCM die Tier-Übergangs-Validierung.

---

## 3. Vorhandener Godot-Spike

Branch: `origin/slice/godot-spike`. Funktional ein lauffähiger Bootstrap,
der Protokoll, Koordinaten und Tick-Modell validiert hat. Tier 4.1–4.4
wachsen daraus organisch.

### 3.1 Project Layout

```
godot/
├── project.godot              # Godot 4.6 config
├── README.md                  # Quickstart (Windows+WSL2 setup)
├── scenes/
│   ├── main.tscn              # Entry: Connect-UI + Lobby-Log
│   └── debug_world.tscn       # Map-Debug-Render + Camera2D
├── scripts/
│   ├── main.gd                # UI-Driver, Message-Router, World-Switch
│   ├── ws_client.gd           # WebSocketPeer-Wrapper mit Signals
│   ├── protocol.gd            # Konstanten, Message-Type-Strings
│   ├── debug_renderer.gd      # _draw() für Map + Players
│   └── input_sender.gd        # Keyboard-Capture, 20 Hz Throttle
```

Plus `scripts/godot-check.sh` für headless GDScript-Parse-Checks (CI-Job
`godot-check` läuft auf jedem Push auf dem Spike-Branch).

### 3.2 Was der Spike kann (verifiziert)

- WebSocket-Connect, `join_room`, `room_joined`, `lobby_state` lesen
- Map als Debug-Linien rendern (Räume, Wände, Spawns, Task-Anker)
- `game_state.players` als farbige Boxen mit Namen + Self-Highlight
- `player_input` mit 20-Hz-Throttle senden
- Snapshot-Interpolation für smoothes Movement (verifiziert flüssig)

### 3.3 Was der Spike NICHT kann

- Tasks halten, Sabotagen triggern, Voting, Endscreen, Mini-Games
- Sprites, Animationen, Tilemaps
- Sound
- Web-Export-Build
- Auto-Reconnect

### 3.4 Bekannter Stale-State im Spike (wichtig!)

Der Spike wurde **vor Slice 3 (Wand-Modell C, 2026-04-27)** geschrieben.
Damals waren Walls als top-level `wallLines: [{axis, position, doors}]`
gespeichert. Heute werden Wände **aus Room-Edges + Türen abgeleitet**
(siehe §6.4). Konkret:

- `debug_renderer.gd:_draw_wall_lines()` liest `_map.get("wallLines", [])`.
  Auf aktuellen Maps ist dieses Feld leer/inexistent → Spike rendert keine
  Wände mehr.
- **Fix-Aufgabe in Tier 4.3:** Wall-Auto-Derive-Algorithmus aus
  `app/game/game_map.compute_walls()` in GDScript portieren. Algorithmus
  in §6.4 vollständig dokumentiert.

Außer dieser einen Stelle hält der Spike weiterhin gegen current-main.

### 3.5 Vollständiger Spike-Code (zum Mitlesen)

#### `scripts/protocol.gd` — Konstanten

```gdscript
class_name Protocol
extends RefCounted

const TICK_HZ: int = 20
const TICK_INTERVAL_MS: int = 50
const PLAYER_COLLISION_RADIUS: float = 20.0
const TASK_INTERACTION_RADIUS: float = 40.0

const TYPE_JOIN_ROOM: String = "join_room"
const TYPE_REJOIN: String = "rejoin"
const TYPE_PLAYER_INPUT: String = "player_input"

const TYPE_ROOM_JOINED: String = "room_joined"
const TYPE_LOBBY_STATE: String = "lobby_state"
const TYPE_GAME_STATE: String = "game_state"
const TYPE_PRIVATE_ROLE: String = "private_role"
const TYPE_PRIVATE_STATE: String = "private_state"
const TYPE_ERROR: String = "error"

static func envelope(type_: String, payload: Dictionary) -> String:
    return JSON.stringify({"type": type_, "payload": payload})
```

#### `scripts/ws_client.gd` — WebSocket-Wrapper

```gdscript
class_name WSClient
extends Node

signal connected
signal disconnected
signal message_received(type: String, payload: Dictionary)
signal connection_error(reason: String)

var _socket: WebSocketPeer = WebSocketPeer.new()
var _state: int = WebSocketPeer.STATE_CLOSED
var _previous_state: int = WebSocketPeer.STATE_CLOSED

func connect_to_server(url: String) -> void:
    var err := _socket.connect_to_url(url)
    if err != OK:
        connection_error.emit("connect_to_url returned error %d" % err)

func send(type_: String, payload: Dictionary = {}) -> void:
    if _state != WebSocketPeer.STATE_OPEN:
        push_warning("WSClient.send while not OPEN — drop %s" % type_)
        return
    _socket.send_text(Protocol.envelope(type_, payload))

func close() -> void:
    _socket.close()

func _process(_delta: float) -> void:
    _socket.poll()
    var current := _socket.get_ready_state()
    if current != _state:
        _previous_state = _state
        _state = current
        _on_state_change(current)
    while _state == WebSocketPeer.STATE_OPEN and _socket.get_available_packet_count() > 0:
        var raw := _socket.get_packet().get_string_from_utf8()
        _handle_packet(raw)

func _on_state_change(new_state: int) -> void:
    match new_state:
        WebSocketPeer.STATE_OPEN:
            connected.emit()
        WebSocketPeer.STATE_CLOSED:
            if _previous_state == WebSocketPeer.STATE_OPEN:
                disconnected.emit()
            else:
                var code := _socket.get_close_code()
                connection_error.emit("connection closed (code=%d)" % code)

func _handle_packet(raw: String) -> void:
    var parsed = JSON.parse_string(raw)
    if typeof(parsed) != TYPE_DICTIONARY:
        push_warning("WSClient: non-dict packet — %s" % raw)
        return
    var type_ := str(parsed.get("type", ""))
    var payload_raw = parsed.get("payload", {})
    var payload: Dictionary = payload_raw if typeof(payload_raw) == TYPE_DICTIONARY else {}
    if type_ == "":
        push_warning("WSClient: packet without type — %s" % raw)
        return
    message_received.emit(type_, payload)
```

#### `scripts/input_sender.gd` — Keyboard-Capture mit 20Hz-Throttle

```gdscript
class_name InputSender
extends Node

const SEND_INTERVAL: float = 0.05  # 50 ms = 20 Hz

var _ws: WSClient = null
var _accum: float = 0.0
var _last_state: Dictionary = {"up": false, "down": false, "left": false, "right": false}
var _dirty: bool = true

func attach(ws: WSClient) -> void:
    _ws = ws

func _process(delta: float) -> void:
    if _ws == null:
        return
    var current := {
        "up": Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP),
        "down": Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN),
        "left": Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT),
        "right": Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT),
    }
    if current.hash() != _last_state.hash():
        _dirty = true
        _last_state = current
    _accum += delta
    if _dirty and _accum >= SEND_INTERVAL:
        _ws.send(Protocol.TYPE_PLAYER_INPUT, current)
        _accum = 0.0
        _dirty = false
```

`main.gd` und `debug_renderer.gd` sind länger — direkt im Branch ansehen.
Wichtige Stellen:

- `main.gd:_on_message()` — Match-Statement das auf Message-Type
  routet. Der Tier-4-Client wird das deutlich erweitern.
- `debug_renderer.gd:push_snapshot()` — speichert prev/curr Snapshot mit
  Timestamps; `_process()` interpoliert. Übernehmen wir 1:1 in Tier 4.4.
- `debug_renderer.gd:_fit_camera_to_map()` — Camera-Zoom-Berechnung,
  wichtig wegen `stretch_mode=viewport` (siehe §9.3).

---

## 4. WebSocket-Protokoll

JSON-Frames `{type: string, payload: object}`. Vollständige Pydantic-Models:
[`app/protocol.py`](../app/protocol.py). Vollständige Doku:
[`docs/PROTOCOL.md`](PROTOCOL.md). Hier die Übersicht für den Godot-Client.

### 4.1 Client → Server

| Message                  | Payload (camelCase)                | Wann                                         |
| ------------------------ | ---------------------------------- | -------------------------------------------- |
| `join_room`              | `{roomCode: str, playerName: str}` | Auf Connect                                  |
| `rejoin`                 | `{roomCode: str, playerId: str}`   | Auf Reconnect innerhalb 30 s                 |
| `player_input`           | `{up, down, left, right: bool}`    | Alle 50 ms oder bei Input-Änderung           |
| `task_hold_start`        | `{taskId: str}`                    | E halten am Task                             |
| `task_hold_stop`         | `{taskId: str}`                    | E loslassen                                  |
| `trigger_sabotage`       | `{sabotageId: str}`                | Chaos triggert Sabotage (object-bound, nahe) |
| `repair_sabotage`        | `{sabotageId: str}`                | F halten am Repair-Panel                     |
| `use_vent`               | `{}`                               | Chaos: V cyclet Vents, dann zum TP           |
| `trigger_takedown`       | `{targetPlayerId: str}`            | Chaos: Take-Down-Attack                      |
| `report_body`            | `{bodyPlayerId: str}`              | Body finden + reporten                       |
| `call_emergency_meeting` | `{}`                               | Im War-Room (oder via Standup-Ability)       |
| `cast_vote`              | `{targetPlayerId: str}`            | Im Meeting voten                             |
| `mini_game_input`        | `{taskId: str, action, ...}`       | Mini-Game-Input (Tier 3 API)                 |
| `start_game`             | `{demo: bool = false}`             | Host startet Runde                           |
| `return_to_lobby`        | `{}`                               | Zurück zur Lobby                             |
| `leave_room`             | `{}`                               | Komplett verlassen                           |

### 4.2 Server → Client

| Message               | Payload (camelCase)                             | Wann                                     |
| --------------------- | ----------------------------------------------- | ---------------------------------------- |
| `room_joined`         | `{roomCode, playerId, isHost, map}`             | Nach join/rejoin; full map-JSON dabei    |
| `lobby_state`         | `{roomCode, players[], availableMaps[], map}`   | Während Lobby (Spieler joinen)           |
| `private_role`        | `{role, team, title, ability, ...}`             | Nach Start, owner-only, einmalig         |
| `private_state`       | `{coffeeEnergy, abilityUsed, takedownCooldown}` | Jeder Tick, owner-only (für HUD)         |
| `game_state`          | `{phase, players[], tasks[], sabotages[], ...}` | Jeder Tick (20 Hz), per-viewer gefiltert |
| `voting_result`       | `{removedPlayerId, wasChaoAgent, tie, skipped}` | Nach Voting, vor nächster Phase          |
| `game_ended`          | `{winner, reason, players[]}`                   | Runde vorbei                             |
| `mini_game_started`   | `{taskId, miniGameId, title, view}`             | Task triggert Mini-Game                  |
| `mini_game_state`     | `{taskId, view}`                                | Mini-Game-Tick-Update                    |
| `mini_game_completed` | `{taskId, success, reason}`                     | Mini-Game fertig                         |
| `error`               | `{code: str, message: str}`                     | Action abgelehnt (z.B. NOT_NEAR_OBJECT)  |

### 4.3 Pydantic ↔ Wire (camelCase)

Backend-Code in `app/protocol.py` benutzt snake_case, auf der Wire steht
camelCase. Pydantic erledigt das via `alias_generator=to_camel`:

```python
class GameStateMsg(BaseModel):
    model_config = _camel_config()
    phase: str
    remaining_seconds: int
    release_progress: int = 0
    pipeline_stability: int = 100
    coffee_level: int = 100
    incidents: int = 0
    players: list[dict[str, Any]]
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    sabotages: list[dict[str, Any]] = Field(default_factory=list)
    meeting: dict[str, Any] | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    bodies: list[dict[str, Any]] = Field(default_factory=list)

class PrivateRoleMsg(BaseModel):
    model_config = _camel_config()
    role: str
    team: str
    description: str
    title: str = ""
    short_blurb: str = ""
    available_sabotages: list[str] = Field(default_factory=list)
    strength_categories: list[str] = Field(default_factory=list)
    weak_categories: list[str] = Field(default_factory=list)
    ability_id: str | None = None
    ability_label: str = ""
    ability_hint: str = ""
    max_coffee: float = 100.0
    assigned_task_ids: list[str] = Field(default_factory=list)
    assigned_tasks: list[dict[str, Any]] = Field(default_factory=list)
```

**Konsequenz für GDScript:** Dictionary-Keys sind case-sensitive.
`game_state["coffee_energy"]` ist falsch, korrekt ist
`game_state["coffeeEnergy"]`. Tippfehler scheitern silent — schon einmal
ein Stand-Up-Bug-Quelle gewesen.

### 4.4 Beispiel-Frames (Wire-Format)

**Client → Server:**

```json
{ "type": "join_room", "payload": { "roomCode": "ABCD", "playerName": "Alice" } }
```

**Server → Client (`room_joined`):**

```json
{
  "type": "room_joined",
  "payload": {
    "roomCode": "ABCD",
    "playerId": "player-uuid-123",
    "isHost": true,
    "map": {
      "name": "default-office",
      "size": { "width": 4800, "height": 3200 },
      "rooms": [...],
      "doors": [...],
      "spawnPoints": [...],
      "taskAnchors": [...],
      "vents": [...],
      "warRoomId": "war_room"
    }
  }
}
```

**Server → Client (`game_state`, alle 50 ms):**

```json
{
  "type": "game_state",
  "payload": {
    "phase": "playing",
    "remainingSeconds": 720,
    "releaseProgress": 35,
    "pipelineStability": 75,
    "coffeeLevel": 60,
    "incidents": 2,
    "players": [
      {
        "id": "player-uuid-123",
        "name": "Alice",
        "x": 400.5,
        "y": 300.2,
        "color": "#ff6b6b",
        "isAlive": true,
        "isConnected": true
      }
    ],
    "tasks": [
      {
        "id": "task-uuid-1",
        "taskId": "fix_unit_tests",
        "playerId": "player-uuid-123",
        "x": 600,
        "y": 500,
        "progress": 0.5,
        "objectType": "qa_terminal",
        "category": "code"
      }
    ],
    "sabotages": [],
    "events": [],
    "bodies": []
  }
}
```

---

## 5. Koordinaten + Tick-Modell

### 5.1 Welt-Größe + Achsen

- Server-Welt: **4800×3200 px**. Origin top-left, Y nach unten.
  **Godot-Default matched das — kein Y-Flip nötig.**
- Player-Collision-Radius: **20 px** (`PLAYER_COLLISION_RADIUS` in `protocol.gd`).
- Task-Interaction-Radius: **40 px** (`TASK_INTERACTION_RADIUS`).
- Spike rendert 1 Server-Pixel = 1 Godot-Pixel. **Tier 4.3 wechselt auf
  Tilemap** — Cell-Size noch offen (z.B. 32 px → 150×100 Cells für 4800×3200).

### 5.2 Tick-Rate + Interpolation

- Server tickt **20 Hz** → ein `game_state` alle ~50 ms.
- **Client darf NICHT predicten.** Server ist autoritativ.
- **Render-Strategie:** Letzte 2 Snapshots + Timestamps buffern.
  Position via `lerp(prev_pos, curr_pos, alpha)` mit
  `alpha = clamp((now - curr_time) / 50ms + 1.0, 0, 1)`. Im Spike
  validiert; Movement ist flüssig.
- **`player_input` Throttle:** Bei Input-Change ODER alle 50 ms — was
  zuerst kommt. Spike benutzt einen `_accum`-Akkumulator (`SEND_INTERVAL = 0.05`).

### 5.3 Reconnect-Verhalten

- **Server hält Session 30 s nach Disconnect.** Innerhalb dieser Zeit
  reconnecten → `rejoin` (nicht `join_room`) mit gleicher `playerId`.
  Server reaktiviert die Session.
- **Nach 30+ s:** Server antwortet `error` mit Code `REJOIN_NOT_AVAILABLE`
  → Client fällt auf `join_room` zurück.
- **`playerId` persistieren:** Empfohlen `user://player.json`. Nach jedem
  `room_joined` speichern; beim Boot lesen, falls present `rejoin`
  versuchen.

---

## 6. Map-JSON-Schema

Volle Doku in [`docs/maps.md`](maps.md). Was Godot wissen muss:

### 6.1 Top-Level

```jsonc
{
  "name": "default-office",
  "size": { "width": 4800, "height": 3200 },
  "rooms":          [ ... ],
  "doors":          [ ... ],   // top-level seit Slice 3 (Wand-Modell C)
  "spawnPoints":    [ ... ],
  "taskAnchors":    [ ... ],
  "sabotagePanels": [ ... ],
  "vents":          [ ... ],
  "mapObjects":     [ ... ],   // Tier 4 props (optional)
  "warRoomId":      "war_room"
}
```

### 6.2 Rooms (mit Godot-Extras)

Räume sind axis-aligned Rectangles. Optionale Tier-4-Felder erlauben
Material-/Höhe-/Lighting-Hints für Godot:

```jsonc
{
  "id": "open_space",
  "title": "Open Space",
  "x": 0,
  "y": 0,
  "width": 800,
  "height": 800,
  "color": "#3a4560",

  // Tier-4 Godot-Extras (alle optional):
  "floorMaterial": "office", // office | kitchen | server | legacy
  "wallHeightM": 2.6, // Wandhöhe in Metern (für 3D)
  "lightingProfile": "neutral", // neutral | warm | cold | dim
  "ambientSound": null, // z.B. "kitchen_hum", "server_fans"
}
```

Browser ignoriert diese Felder. Godot kann sie für 3D-Tilemap-Layer und
Ambient-Audio nutzen.

### 6.3 Doors (Wall-Cutouts)

**Walls werden NICHT gespeichert.** Sie werden zur Laufzeit aus
Room-Adjazenzen + Door-Cutouts abgeleitet (Slice 3, "Wand-Modell C"):

```jsonc
{
  "id": "d1",
  "betweenRoomA": "open_space",
  "betweenRoomB": "meeting_room",
  "position": 800, // Koordinate entlang shared edge (y bei vertical, x bei horizontal)
  "width": 240, // Gap-Breite (default 240)
  "doorKind": "office_door", // Godot-Scene-Key (office_door / glass_panel / vault / none)
}
```

Browser ignoriert `doorKind`. Godot nutzt es für die 3D-Door-Scene.

### 6.4 Wall-Auto-Derivation (must-port to GDScript)

Algorithmus aus `app/game/game_map.compute_walls()`. Für jeden Room und
jede seiner 4 Edges:

1. **Geteilte Portion mit Nachbarraum** → Wand-Segment, minus Door-Cutouts.
   Pro Room-Pair einmal verarbeiten (Dedup).
2. **Perimeter-Portion (kein Nachbarraum)** → Wand, außer wenn die Edge
   auf dem Map-Outer-Boundary liegt.
3. **Blocking MapObjects (Tier 4 Props)** → ihre AABBs werden zur
   Wall-Liste addiert (`map_object_aabb()`).

`WALL_THICKNESS = 24` (Server-Pixel), zentriert auf der Edge. Doors stanzen
**width**-breite Gaps.

```python
# Vollständig in app/game/game_map.py:compute_walls()
def compute_walls(game_map: GameMap) -> list[tuple[int, int, int, int]]:
    out: list[tuple[int, int, int, int]] = []
    rooms = list(game_map.rooms)
    processed: set[tuple[str, int, str, str, int, int]] = set()

    for room in rooms:
        edges = (
            ("y", room.y, room.x, room.x + room.width),                      # top
            ("y", room.y + room.height, room.x, room.x + room.width),        # bottom
            ("x", room.x, room.y, room.y + room.height),                     # left
            ("x", room.x + room.width, room.y, room.y + room.height),        # right
        )
        for axis, edge_pos, start, end in edges:
            shared: list[tuple[str, tuple[int, int]]] = []
            for other in rooms:
                if other.id == room.id:
                    continue
                ovl = _edge_overlap(other, axis, edge_pos, start, end)
                if ovl is not None:
                    shared.append((other.id, ovl))

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

            if not _is_map_edge(axis, edge_pos, game_map.size):
                shared_cuts = [ovl for _, ovl in shared]
                for seg_start, seg_end in _interval_subtract(start, end, shared_cuts):
                    out.append(_wall_rect(axis, edge_pos, seg_start, seg_end))

    for obj in game_map.map_objects:
        if obj.blocks_movement:
            out.append(map_object_aabb(obj))
    return out
```

Eine JS-Mirror-Implementation existiert in
[`static/render.js:computeWallsClient()`](../static/render.js) — nützlich
als Referenz beim Portieren nach GDScript.

### 6.5 MapObjects (Tier-4-Props)

```jsonc
{
  "id": "os-desk-qa",
  "x": 400,
  "y": 400, // CENTER (nicht top-left)
  "width": 110,
  "height": 60,
  "kind": "desk", // logischer Asset-Key
  "rotation": 0, // 0 / 90 / 180 / 270 only
  "blocksMovement": true, // true → AABB in Wall-Collision
  "taskId": "fix_unit_tests", // optional — task anchor
  "objectType": "qa_terminal", // optional — sabotage-trigger-binding (Tier 2.7)
  "sabotageRepairId": "lights_out", // optional — repair panel
}
```

**Rotation 90/270 swappen width ↔ height** für Collision. Dein Renderer
muss den selben Swap machen, damit das gezeichnete Rechteck = das physische.

### 6.6 Kind-Catalogue → KayKit-Asset-Mapping

25 Kinds aktuell. Volle Tabelle inkl. Default-Sizes und Browser-Farben in
[`docs/maps.md`](maps.md). Auszug:

| Kind                  | Default-Size | Blocks?  | KayKit-Asset (Godot)                        |
| --------------------- | ------------ | -------- | ------------------------------------------- |
| `desk`                | 110×60       | optional | Furniture/`desk.fbx`                        |
| `desk_large`          | 180×80       | yes      | Furniture/`desk_large.fbx`                  |
| `chair_desk`          | 50×50        | no       | Furniture/`chair_desk_A.fbx`                |
| `chair_meeting`       | 50×50        | no       | Furniture/`chair_A.fbx`                     |
| `monitor`             | 60×30        | no       | Furniture/`monitor.fbx`                     |
| `keyboard`            | 50×20        | no       | Furniture/`keyboard.fbx`                    |
| `server_rack`         | 80×100       | yes      | Space Base/`structure_tall.fbx` (proxy)     |
| `monitoring_panel`    | 200×60       | no       | Furniture/`pictureframe_large_A.fbx`        |
| `cabinet`             | 80×80        | yes      | Furniture/`cabinet_medium.fbx`              |
| `meeting_table`       | 480×140      | yes      | Furniture/`table_medium_long.fbx` (proxy)   |
| `presentation_screen` | 200×30       | no       | Furniture/`pictureframe_large_B.fbx`        |
| `kitchen_counter`     | 320×80       | yes      | Restaurant/`kitchencounter_straight_A.fbx`  |
| `kitchen_corner`      | 120×120      | yes      | Restaurant/`kitchencounter_innercorner.fbx` |
| `kitchen_sink`        | 120×80       | yes      | Restaurant/`kitchencounter_sink.fbx`        |
| `coffee_machine`      | 90×90        | no       | Restaurant/`icecream_machine.fbx` (proxy)   |
| `fridge`              | 100×130      | yes      | Restaurant/`fridge_A.fbx`                   |
| `plant_cactus`        | 60×60        | no       | Furniture/`cactus_medium_A.fbx`             |
| `picture_frame`       | 80×30        | no       | Furniture/`pictureframe_medium.fbx`         |
| `rug`                 | 200×120      | no       | Furniture/`rug_rectangle_A.fbx`             |
| `crate`               | 70×70        | yes      | Space Base/`cargo_A.fbx`                    |
| `old_workstation`     | 110×60       | optional | Furniture/`desk_decorated.fbx`              |

(siehe `docs/maps.md` für vollständige 25-Zeilen-Tabelle)

**Hinweise:**

- "(proxy)" bedeutet das Asset ist nur Platzhalter bis Tier 4.0.x
  finale Assets liefert.
- Unbekannte Kinds → Fallback: neutral grau + Kind-String als Label.
- Source of truth fürs Editor-Palette ist
  [`static/editor/editor-kinds.js`](../static/editor/editor-kinds.js).
  Wenn Godot neue Kinds einführt, bitte dort + in `docs/maps.md` +
  `static/render.js:MAP_OBJECT_STYLE` lockstep updaten.

---

## 7. Lokales Setup

### 7.1 Backend lokal starten

```bash
cd /path/to/mcm
uv sync                                          # Deps einmal installieren
uv run uvicorn app.main:app --reload             # Dev-Server, Port 8000
```

Browser auf http://localhost:8000 öffnen. WebSocket-Endpoint:
`ws://localhost:8000/ws` (oder `ws://127.0.0.1:8000/ws` wegen IPv6-Trap, §9.4).

### 7.2 Tests laufen lassen

```bash
# Backend (pytest): 591 Tests
uv run pytest                    # alle
uv run pytest tests/test_x.py    # einzeln
uv run pytest -k "name_pattern"  # gefiltert

# Frontend (vitest): 109 Tests
npx vitest run                   # alle
npx vitest                       # watch mode

# Coverage-Gate (CI): 88% auf app/game/
uv run pytest --cov=app/game --cov-fail-under=88
```

### 7.3 Lint + Format vor jedem Commit

```bash
uv run ruff check .              # Python lint
uv run ruff format .             # Python auto-format

# Frontend — MUSS v3.3.3 sein (CI enforced exact)
npx --yes prettier@3.3.3 --check 'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md'
npx --yes prettier@3.3.3 --write  'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md'
```

**Gotcha:** Prettier 3.3 vs 4.0 reformatten Markdown-Tabellen unterschiedlich.
**Lokal immer v3.3.3 benutzen** — sonst CI rot.

### 7.4 Setup auf Windows + WSL2

Bei Sven's Setup läuft das Backend in WSL und der Godot-Editor auf Windows:

1. Project öffnen via UNC-Pfad im Godot-Project-Manager:
   `\\wsl.localhost\<DISTRO>\home\<user>\se\mcm\godot\project.godot`
2. Distro-Name: `wsl -l` (Windows-PowerShell) oder `echo $WSL_DISTRO_NAME` (in WSL).
3. Backend-Connect: `localhost:8000` funktioniert nativ (WSL2 forwards). Falls
   nicht, WSL-IP nehmen: `ip addr show eth0` → `inet`-Zeile.

UNC-Pfade sind langsamer als nativer Windows-FS, aber für Editor-Workflow
OK. Bei Editor-Hängern: Repo zusätzlich nach `C:\` clonen, Backend bleibt
in WSL.

### 7.5 Headless-Parse-Check ohne Editor

`scripts/godot-check.sh` parsed alle GDScripts headless — schneller als
F5 und ohne Editor-Cache:

```bash
./scripts/godot-check.sh           # alle scripts
./scripts/godot-check.sh -v        # verbose
```

Setzt `godot` (Godot 4.6) im PATH voraus. Empfehlung: vor jedem
Commit + vor F5 wenn ungewohnte Editor-Caching-Probleme auftreten.

---

## 8. CI-Gates + Konventionen

### 8.1 CI-Jobs (`.github/workflows/ci.yml`)

Jeder Push und PR triggert sechs Jobs parallel. Alle müssen grün sein.

| Job             | Command                                               | Gate                 |
| --------------- | ----------------------------------------------------- | -------------------- |
| **pytest**      | `uv run pytest -q --cov=app/game --cov-fail-under=88` | Tests + 88% Coverage |
| **ruff lint**   | `uv run ruff check .`                                 | Python-Lint          |
| **ruff format** | `uv run ruff format --check .`                        | Python-Format        |
| **mypy**        | `uv run mypy`                                         | Type-Check (`app/`)  |
| **prettier**    | `npx --yes prettier@3.3.3 --check ...`                | **v3.3.3 exact**     |
| **vitest**      | `npx vitest run`                                      | Frontend-Smoke-Tests |

Plus Job **`deploy`** (only on main + alle 6 grün) — `scripts/deploy.sh`
zur EC2.

Auf dem Spike-Branch zusätzlich Job **`godot-check`** — headless
GDScript-Parse-Check. Ist noch nicht für Tier-4-Branch generalisiert; bei
Bedarf den Branch-Filter erweitern.

### 8.2 Konventionen aus AGENTS.md

- **Branches:** `slice/<kurzname>` für Roadmap-Slices, `feat/<kurz>` für
  Features. `main` ist live.
- **Worktrees:** Branch-Isolation via `.worktrees/<branch-basename>/` —
  ist per `.gitignore` ausgeschlossen.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`,
  `chore:`, `refactor:`). Multi-Line via heredoc. Co-Author-Trailer für
  Claude-Sessions.
- **Niemals ungefragt pushen.** Push = Live-Effect. Vorher mit Sven
  abklären.
- **Sprache:** Kommunikation mit Sven auf Deutsch, knapp,
  Multiple-Choice-Fragen wenn sinnvoll. **Code-Comments auf English**,
  Comment-the-WHY.
- **Keine Emojis** in Code, Docs, Commits — außer explizit angefragt.
- **Keine neuen `.md`-Files** ohne expliziten Auftrag — bestehende
  editen.

### 8.3 Wire-Format-Regeln

- **camelCase auf der Wire.** Snake_case ↔ camelCase macht Pydantic
  automatisch. GDScript-Dictionary-Access muss camelCase nutzen.
- **JSON only.** Keine binären Formate, kein Custom-Wire.
- **Server is authoritative.** Client entscheidet keine Spiellogik.

---

## 9. Stolperfallen aus dem Spike

### 9.1 Godot-Project-Konfiguration

Die richtigen Defaults in `project.godot`:

```ini
[display]
window/size/mode=2                 # Maximized
window/subwindows/embed_subwindows=false   # NICHT in den Editor embedden
window/stretch/mode="viewport"     # 1.5:1 aspect ratio matched die Map (4800×3200)
```

`embed_subwindows=false` ist wichtig: Godot 4 Default embedded das
Run-Window in den Editor und bricht damit `stretch_mode`. Mit dem Setting
oben öffnet F5 ein eigenständiges OS-Fenster.

Spike-Viewport: 1080×720 (1.5:1) → matched die 4800×3200-Map ohne
Black-Bars. Tier 4 mit Tilemap kann aber ein anderes Aspect haben (z.B.
16:9 mit HUD-Overlay).

### 9.2 GDScript-Caching

`class_name`-Änderungen, neue Klassen-Definitionen oder Method-Signature-
Changes brauchen einen **Project-Reload** (`Project → Reload Current
Project`) — Editor-Cache ist persistent und vergisst sonst die Änderung.

`scripts/godot-check.sh` umgeht den Cache → sehr nützlich beim Iterieren.

### 9.3 Camera2D + Viewport

Mit `stretch_mode=viewport`:

- `get_viewport_rect().size` ist die konfigurierte Viewport-Größe (z.B.
  1080×720), unabhängig von der OS-Window-Größe.
- Camera-Zoom-Formel: `zoom = min(viewport_w / map_w, viewport_h / map_h)`.
  Spike measured ~0.225 für 1080×720 / 4800×3200.

Mit `stretch_mode=canvas_items` müsstest du stattdessen `get_window().size`
nehmen. Pro Strategie konsistent bleiben — beides mischen führt zu
mysteriösen Off-by-Camera-Bugs.

### 9.4 IPv6-Trap unter Windows

Windows resolved `localhost` zuerst nach `::1` (IPv6). uvicorn bindet per
Default nur IPv4. Godot's `WebSocketPeer` wartet ~50 s auf TCP-Timeout
bevor es auf IPv4 fällt → fühlt sich wie "Connect hängt" an.

**Workarounds:**

- `ws://127.0.0.1:8000/ws` statt `localhost` (Spike-Default).
- Oder: `uv run uvicorn app.main:app --host :: --reload` (bindet beides).

### 9.5 Reconnect-Window

Server hält Session 30 s nach Disconnect. Innerhalb der Zeit:

```gdscript
# Pseudocode
if FileAccess.file_exists("user://player.json"):
    var saved = JSON.parse_string(FileAccess.open("user://player.json", FileAccess.READ).get_as_text())
    _ws.send(Protocol.TYPE_REJOIN, {"roomCode": saved.roomCode, "playerId": saved.playerId})
    # Server antwortet mit room_joined ODER error{code: REJOIN_NOT_AVAILABLE}
```

Bei `REJOIN_NOT_AVAILABLE` → fallback auf `join_room`.

### 9.6 Snapshot-Interpolation-Math

Validierte Formel aus dem Spike:

```
alpha = clamp((now - curr_snapshot_time) / 50ms + 1.0, 0, 1)
lerped_x = lerp(prev_x, curr_x, alpha)
lerped_y = lerp(prev_y, curr_y, alpha)
```

Liefert smoothes Movement zwischen 50-ms-Server-Snapshots. Wichtig:
**lerp zwischen Snapshots, nicht über sie hinaus** — keine Prediction.

### 9.7 camelCase-Falle

Server schickt `coffeeEnergy`, `releaseProgress`, `isAlive`, `playerId`,
etc. GDScript-Dict-Keys sind case-sensitive — `dict["coffee_energy"]`
liefert silent `null`/Default. Empfehlung: lese-Wrapper in `protocol.gd`
mit allen erwarteten Keys konstantisiert, damit Tippfehler beim
Compile/Parse auffallen, nicht erst zur Laufzeit.

---

## 10. Tier-4-Build-Order (konkrete Slices)

Aus `docs/ROADMAP.md`, leicht angereichert mit Spike-Erfahrungen.
Empfohlene Reihenfolge:

1. **Tier 4.1 (1 Tag) — Setup + Web-Export-Config**

   - Spike-Branch in main mergen (passiert gerade).
   - `project.godot`: HTML5-Export-Profile anlegen.
   - Connect-UI behalten, optional URL-Pre-Fill nach `wss://game.prod-is-lava.dev/ws`.
   - Test gegen lokales Backend + Live-Server.

2. **Tier 4.2 (1–2 Tage) — Lobby-Scene**

   - Player-Liste aus `lobby_state.players`.
   - Map-Selector (Server schickt `availableMaps[]`).
   - Start-Button (nur für Host — `lobby_state.isHost`).
   - Übergang Lobby → World ist im Spike schon angedeutet (`_switch_to_world()`).

3. **Tier 4.3 (2 Tage) — Map-Loader: JSON → Tilemap**

   - Cell-Size wählen (32 px → 150×100 für 4800×3200 ist ein guter Start).
   - Wall-Auto-Derive aus `compute_walls` portieren (siehe §6.4 — der
     Spike's `_draw_wall_lines` ist obsolet seit Slice 3).
   - Doors als separate Tilemap-Layer mit `doorKind` als Variant.
   - Floor-Material aus `room.floorMaterial` → unterschiedliche Tilesets.

4. **Tier 4.4 (2–3 Tage) — Character Scene**

   - Sprites aus `images/figuren.png` (Browser benutzt das gleiche Sheet).
   - 4-direction Idle/Walk-Animation.
   - Position aus `game_state.players`, Snapshot-Interpolation aus dem
     Spike übernehmen (`debug_renderer.gd:push_snapshot`).
   - Self-Highlight wenn `id == playerId`.

5. **Tier 4.5 (1 Tag) — HUD**

   - Stat-Pills: Release-Progress, Pipeline-Stability, Coffee-Level, Incidents.
     Quelle: `game_state.{releaseProgress, pipelineStability, coffeeLevel, incidents}`.
   - Role-Label aus `private_role.title`.
   - Timer aus `game_state.remainingSeconds`.
   - Coffee-Bar aus `private_state.coffeeEnergy`.
   - Tween-Animationen für smooth changes.

6. **Tier 4.6 (2 Tage) — Task-Interaction + Mini-Game-Modals**

   - "Halten zum Bearbeiten" (E) → `task_hold_start` / `task_hold_stop`.
   - Server sendet `mini_game_started{taskId, miniGameId, view}` →
     Modal öffnen.
   - 5 Mini-Games existieren (sequencing / pairing / timing /
     filter-by-criterion / subset-by-constraint). Pluggable Modal-UI pro
     `miniGameId`. Browser-Implementation in `static/minigames/` als Referenz.
   - `mini_game_state` updates die UI, `mini_game_completed` schließt sie.

7. **Tier 4.7 (1 Tag) — Sabotage-Buttons**

   - Aus `private_role.availableSabotages` Liste rendern.
   - Cooldown-Display.
   - `trigger_sabotage` schicken — Server lehnt ab wenn nicht nahe an
     `objectType` (Tier 2.7 object-binding) → Error-Toast aus
     `error{code, message}`.

8. **Tier 4.8 (1 Tag) — Voting-Overlay**

   - `game_state.meeting` enthält Phase + Players.
   - Voting-Liste, Countdown, "Skip" Option.
   - `cast_vote{targetPlayerId}`.
   - `voting_result` → Toast mit Slide-In.

9. **Tier 4.9 (1 Tag) — Endscreen**

   - `game_ended.players` enthält Per-Player-Stats + Awards (Tier 3.7).
   - `game_ended.aiPostmortem` ist der KI-Text (optional anzeigen).
   - Confetti-Particles wenn Release-Team gewinnt, anders wenn Chaos.

10. **Tier 4.10 (5–8 Tage) — Among-Us-Features**

    - Vents: V cyclet durch verbundene `vents[].linkedVents`, Click TP.
    - Body-Discovery: tote Spieler haben `bodies[]` Eintrag.
    - Report-Button wenn nahe an Body.
    - Take-Down: Chaos-Animation (rot blinken, slow).
    - Lights/Comms-VFX: Vignette + UI-disable-States.
    - Spectator-Mode: alive=false → reduced opacity + see-through walls.

11. **Tier 4.11 (1 Tag) — Sound**

    - Footsteps abhängig von `room.floorMaterial`.
    - UI-SFX, BGM.
    - Audio-Bus für Mute/Volume (Tier 1 hatte das schon im Browser).

12. **Tier 4.12 (3–5 Tage) — Polish + Reconnect**

    - Settings-UI (Sound, Graphics, Keybinds).
    - Auto-Reconnect via `user://player.json` (siehe §9.5).
    - Edge-Cases: Sabotage während Meeting, Body-Discovery Race-Conditions, etc.

13. **Tier 4.13 (0.5 Tag) — Web-Export-Deploy**
    - Godot Web-Export bauen.
    - Auf `game.prod-is-lava.dev` unter `/godot/` deployen
      (Backend-`scripts/deploy.sh` erweitern).

**Tier 4 ist erst "done" wenn ein Live-Test mit echten Spielern läuft.**

---

## 11. Erste Schritte für dich

1. **Spike-Branch ausprobieren:**

   ```bash
   git checkout origin/slice/godot-spike
   cd godot && godot --editor .
   ```

   F5 → Connect-UI → `ws://127.0.0.1:8000/ws` (Backend muss laufen) →
   Room `ABCD` → Name `Godot`. Browser-Tab parallel auf
   `http://localhost:8000` mit gleichem Room-Code → ihr seht euch
   gegenseitig, Movement smooth. Wenn das klappt: Setup ist OK.

2. **`docs/PROTOCOL.md` lesen** für die volle Message-Liste mit allen
   Edge-Cases.

3. **`docs/maps.md` lesen** für das Map-Schema inkl. der vollständigen
   Kind-Catalogue-Tabelle (25 Einträge mit allen Browser-Farben +
   KayKit-Pfaden).

4. **§10 Build-Order durchgehen** — pro Slice eigener Branch unter
   `slice/godot-tier-4-N-<kurz>` und Worktree unter
   `.worktrees/godot-tier-4-N-<kurz>/`.

5. **Vor jedem Push fragen.** Push triggert CI, CI deployed live.

---

## Kontakt + Stand

- Sven Rausch ([sr@rausch.se](mailto:sr@rausch.se)) — Product/Architect.
- Repo: https://github.com/rausch-tech/merge-commit-mayhem
- Live: https://game.prod-is-lava.dev
- Stand dieser Doku: 2026-04-27, nach Editor-Slices 1–5 (Wand-Modell C +
  Editor-UX-Redesign abgeschlossen). Spike auf
  `origin/slice/godot-spike` wird gerade in main gemerged.
