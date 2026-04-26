# Godot-Client Bootstrapping-Spike — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Roadmap-Update 2026-04-27:** Tier 3 heißt jetzt „Mini-Games (Task-Tiefe)", die Godot-Migration
> ist auf **Tier 4** gewandert. Tier-Referenzen unten beziehen sich auf den Stand bei Plan-Erstellung
> (2026-04-26). Aktuelle Nummerierung in `docs/ROADMAP.md` und in den Resume-Notes.
> Der Plan wurde inline implementiert und ist abgeschlossen — siehe Resume-Notes für Status.

**Goal:** Schmaler Godot-4.3-Client gegen den existierenden FastAPI-Backend, der das WS-Protokoll real validiert, `docs/CLIENT.md` mit gemessenen Werten füllt und ein Skelett für Tier 3 hinterlässt.

**Architecture:** Mono-Repo Sub-Folder `godot/`. Server bleibt unverändert. Godot rendert empfangene Snapshots, sendet Inputs, simuliert nichts. Vier inkrementelle Schritte (Connect → Map-Render → Player-Boxen → Input+Interpolation).

**Tech Stack:** Godot 4.3 LTS, GDScript, WebSocketPeer. Backend: FastAPI + Pydantic v2 (existiert). Browser-Client (`static/`) bleibt als Reference-Implementation und wird nicht modifiziert.

**Spec:** `docs/superpowers/specs/2026-04-26-godot-spike-design.md`

---

## Vorbemerkung: Test-Strategie

Der Spike testet **manuell visuell**, nicht via GUT-Framework. Begründung steht in der Spec (§7). Pro Task gibt es eine *Manual Acceptance*-Sektion mit konkreten Schritten und beobachtbarem Erwartungsergebnis. Keine Task gilt als done, bevor die Acceptance grün ist.

Lokales Backend muss laufen für jede Acceptance:

```bash
cd /home/sr/se/mcm
uv run uvicorn app.main:app --reload
```

Server hört dann auf `http://localhost:8000`, WebSocket auf `ws://localhost:8000/ws`. Browser-Tab unter `http://localhost:8000/` ist der Vergleichsclient.

---

## Phase 0 — Worktree und Projekt-Skelett

### Task 1: Worktree und Branch anlegen

**Files:**
- Modify: working tree wechselt zu `.worktrees/godot-spike/`

- [ ] **Step 1: Worktree erstellen**

```bash
cd /home/sr/se/mcm
git worktree add -b slice/godot-spike .worktrees/godot-spike
```

Erwartung: neuer Worktree unter `.worktrees/godot-spike/` mit Branch `slice/godot-spike` (vom aktuellen `main` ausgehend).

- [ ] **Step 2: In Worktree wechseln**

```bash
cd /home/sr/se/mcm/.worktrees/godot-spike
git status
```

Erwartung: `On branch slice/godot-spike`, working tree clean.

- [ ] **Step 3: Verifizieren dass Backend läuft**

In separatem Terminal:

```bash
cd /home/sr/se/mcm
uv run uvicorn app.main:app --reload
```

Browser-Tab: `http://localhost:8000/` öffnen, prüfen dass die Lobby-Maske erscheint. Wenn ja: Spike kann beginnen.

---

### Task 2: Godot-Projekt-Skelett anlegen

**Files:**
- Create: `godot/project.godot`
- Create: `godot/icon.svg`
- Create: `godot/scenes/.gitkeep`
- Create: `godot/scripts/.gitkeep`

- [ ] **Step 1: `godot/project.godot` erstellen**

Datei `godot/project.godot`:

```ini
; Engine configuration file.
; Auto-generated, do NOT edit manually beyond what's documented here.
; Spike-Konfiguration, kommt mit dem Spike — Tier 3 wird die Konfiguration erweitern.

config_version=5

[application]

config/name="Merge Conflict Mayhem (Godot Spike)"
config/version="0.0.1-spike"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.3", "GL Compatibility")
config/icon="res://icon.svg"

[display]

window/size/viewport_width=1280
window/size/viewport_height=720
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
```

Erläuterung: `gl_compatibility` ist Web-Export-tauglich (Tier 3.13). `canvas_items` Stretch-Mode ist der Godot-Default für 2D-UI mit Fenster-Resize.

- [ ] **Step 2: Default-Icon erstellen**

Datei `godot/icon.svg` (minimaler Platzhalter):

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect x="0" y="0" width="64" height="64" fill="#1a1d29"/>
  <text x="32" y="40" font-family="monospace" font-size="32" fill="#4ade80" text-anchor="middle">M</text>
</svg>
```

- [ ] **Step 3: Verzeichnisse anlegen**

```bash
mkdir -p godot/scenes godot/scripts
touch godot/scenes/.gitkeep godot/scripts/.gitkeep
```

- [ ] **Step 4: Godot 4.3 Editor öffnen, Projekt importieren**

Im Godot-4.3-Project-Manager: "Import" → `/home/sr/se/mcm/.worktrees/godot-spike/godot/project.godot` wählen → "Import & Edit". Editor öffnet ohne Fehler.

Erwartung: Editor zeigt leeres FileSystem (außer `.gitkeep`-Files), keine roten Fehler im Output-Panel.

- [ ] **Step 5: Editor wieder schließen**

Damit `.godot/`-Cache geschrieben wird (das ist gewollt, der gehört in .gitignore).

---

### Task 3: `.gitignore` erweitern

**Files:**
- Modify: `/home/sr/se/mcm/.gitignore`

- [ ] **Step 1: Top-Level `.gitignore` ergänzen**

Am Ende von `/home/sr/se/mcm/.gitignore` anhängen:

```
# Godot
godot/.godot/
godot/exports/
```

**Wichtig:** `*.import`-Files werden NICHT ignoriert. Sie enthalten persistente UID-Referenzen, die committet werden müssen.

- [ ] **Step 2: Verify .godot/ ist nicht versioniert**

```bash
cd /home/sr/se/mcm/.worktrees/godot-spike
git status godot/
```

Erwartung: `godot/.godot/` taucht NICHT in untracked auf. Falls doch: `.gitignore` Pfad-Match prüfen.

- [ ] **Step 3: Commit Phase 0**

```bash
git add .gitignore godot/
git commit -m "chore(godot): scaffold Godot 4.3 project skeleton

Mono-repo sub-folder under godot/, gl_compatibility renderer for
later Web-Export, default 1280x720 viewport.

Spec: docs/superpowers/specs/2026-04-26-godot-spike-design.md"
```

---

## Phase 1 — `docs/CLIENT.md` Initial Draft

### Task 4: `docs/CLIENT.md` mit Initial-Werten anlegen

**Files:**
- Create: `docs/CLIENT.md`

- [ ] **Step 1: CLIENT.md schreiben**

Datei `docs/CLIENT.md`:

```markdown
# Client Expectations

> Server-seitige Erwartungen an *jeden* Client (Browser jetzt, Godot ab Tier 3).
> Diese Doku ist normativ. Wenn Client-Verhalten widerspricht, ist eines von beiden
> falsch — wir entscheiden bewusst, welches angepasst wird.
>
> Diese Datei wird durch den Godot-Spike (siehe `docs/superpowers/specs/2026-04-26-godot-spike-design.md`)
> mit *real gemessenen* Werten gefüllt. Sektionen mit `[VERIFY:Step-X]` werden im Spike validiert.

## 1. Koordinaten- und Skalierungs-Konvention

- **Server-Welt:** 4800×3200 Pixel (`maps/default.json` → `size`).
- **Origin:** oben-links (0,0). X wächst nach rechts, Y wächst nach unten.
- **Godot-Default:** identisch — Origin oben-links, Y nach unten. Keine Y-Flip nötig.
- **Render-Strategie (Spike):** `Camera2D` mit Zoom-Faktor, 1 Server-Pixel = 1 Godot-Pixel. Keine Tilemap.
- **Default-Zoom-Faktor (Spike, Viewport 1280×720):** `Vector2(0.225, 0.225)` zeigt die ganze Map zentriert. `[VERIFY:Task-12]`
- **Player-Kollisions-Radius:** 20 px (siehe `app/game/walls.py:PLAYER_COLLISION_RADIUS`).
- **Task-Interaction-Radius:** 40 px (siehe `app/game/tasks.py:TASK_INTERACTION_RADIUS`).
- **Tilemap-Cell-Size:** offen, kommt mit Tier 3.3.

## 2. Tick- und Interpolations-Modell

- **Server-Tick:** 20 Hz → ein `game_state` alle ~50 ms (`app/main.py:TICK_HZ`).
- **Client-Regel:** Bewegung NICHT simulieren. Server ist autoritativ.
- **Render-Strategie:** Snapshot-Buffer (letzte 2 Frames) + lerp über die 50-ms-Lücke. `[VERIFY:Task-17]`
- **`player_input` Throttle:** max. 20 Hz (alle 50 ms). Senden bei Input-Change ODER spätestens jeden 50-ms-Tick. `[VERIFY:Task-16]`

## 3. Reconnect-Verhalten

- **Server-Verhalten:** behält Spieler-Identität 30 s nach Disconnect (Slice 0.10).
- **Client-API:**
  - **Erst-Join:** `join_room` mit `roomCode` + `playerName`.
  - **Reconnect:** `rejoin` mit `roomCode` + `playerId` (NICHT erneutes `join_room`). `[VERIFY:Task-19]`
- **Reconnect-Antwort:** `room_joined` mit derselben `playerId`, danach normaler `lobby_state`/`game_state`-Fluss.
- **Verhalten nach 30+ s:** offen, wird im Spike beobachtet. `[VERIFY:Task-19]`

## 4. Bewusst ausgeklammert (eigene Slices)

- **Asset-Mapping** (Sprites/Animations pro Spieler/Task/Sabotage) → Tier 3.0.1–3.0.3.
- **Sound-Trigger-Liste** (welches Server-Event triggert welchen SFX) → Tier 3.11.

## 5. Backend-Doku-Lücken (vom Spike entdeckt)

Pre-Spike wurden bereits folgende Lücken in `docs/PROTOCOL.md` und `docs/maps.md` geschlossen (Commits `<protocol-fix-sha>` und `<maps-fix-sha>`):

- Map-Größe in `docs/maps.md` korrigiert (4800×3200 statt 2400×1600).
- `rejoin`-Message in `docs/PROTOCOL.md §4` ergänzt.
- `lobby_state` Schema um `availableMaps`/`selectedMapId`/`map` erweitert.
- `game_state` um `incidents`, `events`, `bodies`, `players.isConnected` erweitert.
- `private_state`-Message neu dokumentiert.
- `REJOIN_NOT_AVAILABLE` in der Error-Code-Tabelle ergänzt.

Weitere Lücken, die der Spike *neu* entdeckt, werden hier aufgelistet (Task 14 füllt das nach Spike-Ende).
```

- [ ] **Step 2: Commit**

```bash
git add docs/CLIENT.md
git commit -m "docs(client): add CLIENT.md initial draft for Godot spike

Three sections (coordinates, tick/interpolation, reconnect) with
[VERIFY:Task-N] markers — values are filled in once the spike has
measured them.

Initial backend-doku-gap list based on spec recherche."
```

---

## Phase 2 — Schritt 1: Connect + Lobby (Konsole-only)

### Task 5: `protocol.gd` — Konstanten und Message-Types

**Files:**
- Create: `godot/scripts/protocol.gd`

- [ ] **Step 1: protocol.gd schreiben**

Datei `godot/scripts/protocol.gd`:

```gdscript
class_name Protocol
extends RefCounted

# Mirror der wichtigsten Werte aus app/protocol.py und docs/PROTOCOL.md.
# Halten wir kurz — der Spike braucht nicht alle Felder.

const TICK_HZ: int = 20
const TICK_INTERVAL_MS: int = 50  # 1000 / TICK_HZ
const PLAYER_COLLISION_RADIUS: float = 20.0
const TASK_INTERACTION_RADIUS: float = 40.0

# Outgoing message types (Client -> Server)
const TYPE_JOIN_ROOM: String = "join_room"
const TYPE_REJOIN: String = "rejoin"
const TYPE_PLAYER_INPUT: String = "player_input"

# Incoming message types (Server -> Client)
const TYPE_ROOM_JOINED: String = "room_joined"
const TYPE_LOBBY_STATE: String = "lobby_state"
const TYPE_GAME_STATE: String = "game_state"
const TYPE_PRIVATE_ROLE: String = "private_role"
const TYPE_ERROR: String = "error"

static func envelope(type_: String, payload: Dictionary) -> String:
    return JSON.stringify({"type": type_, "payload": payload})
```

- [ ] **Step 2: Syntax-Check im Editor**

Godot-Editor öffnen, `scripts/protocol.gd` aufmachen. Erwartung: keine roten Fehler-Marker am Rand. Output-Panel zeigt nichts.

- [ ] **Step 3: Commit**

```bash
git add godot/scripts/protocol.gd
git commit -m "feat(godot): add protocol constants and message-type names"
```

---

### Task 6: `ws_client.gd` — WebSocket-Wrapper

**Files:**
- Create: `godot/scripts/ws_client.gd`

- [ ] **Step 1: ws_client.gd schreiben**

Datei `godot/scripts/ws_client.gd`:

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
    var frame := Protocol.envelope(type_, payload)
    _socket.send_text(frame)

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
    var payload: Dictionary = parsed.get("payload", {}) if typeof(parsed.get("payload")) == TYPE_DICTIONARY else {}
    if type_ == "":
        push_warning("WSClient: packet without type — %s" % raw)
        return
    message_received.emit(type_, payload)
```

- [ ] **Step 2: Syntax-Check**

Editor öffnet `ws_client.gd`. Keine roten Marker. Speichern (Ctrl+S).

- [ ] **Step 3: Commit**

```bash
git add godot/scripts/ws_client.gd
git commit -m "feat(godot): add WebSocketPeer wrapper with connection signals"
```

---

### Task 7: `main.tscn` und `main.gd` — Connect-UI

**Files:**
- Create: `godot/scenes/main.tscn`
- Create: `godot/scripts/main.gd`

- [ ] **Step 1: main.gd schreiben**

Datei `godot/scripts/main.gd`:

```gdscript
extends Control

@onready var _url_field: LineEdit = $Panel/VBox/UrlField
@onready var _room_field: LineEdit = $Panel/VBox/RoomField
@onready var _name_field: LineEdit = $Panel/VBox/NameField
@onready var _connect_btn: Button = $Panel/VBox/ConnectBtn
@onready var _log: TextEdit = $Panel/VBox/Log

var _ws: WSClient
var _player_id: String = ""
var _map: Dictionary = {}

func _ready() -> void:
    _ws = WSClient.new()
    add_child(_ws)
    _ws.connected.connect(_on_connected)
    _ws.disconnected.connect(_on_disconnected)
    _ws.connection_error.connect(_on_error)
    _ws.message_received.connect(_on_message)
    _connect_btn.pressed.connect(_on_connect_pressed)

func _on_connect_pressed() -> void:
    var url := _url_field.text.strip_edges()
    var room := _room_field.text.strip_edges()
    var name_ := _name_field.text.strip_edges()
    if url == "" or room == "" or name_ == "":
        _append_log("[input] please fill all three fields")
        return
    _append_log("[ws] connecting to %s" % url)
    _ws.connect_to_server(url)
    set_meta("pending_room", room)
    set_meta("pending_name", name_)

func _on_connected() -> void:
    _append_log("[ws] connected")
    var room := str(get_meta("pending_room"))
    var name_ := str(get_meta("pending_name"))
    _ws.send(Protocol.TYPE_JOIN_ROOM, {"roomCode": room, "playerName": name_})
    _append_log("[ws] sent join_room room=%s name=%s" % [room, name_])

func _on_disconnected() -> void:
    _append_log("[ws] disconnected")

func _on_error(reason: String) -> void:
    _append_log("[ws] error: %s" % reason)

func _on_message(type_: String, payload: Dictionary) -> void:
    match type_:
        Protocol.TYPE_ROOM_JOINED:
            _player_id = str(payload.get("playerId", ""))
            _map = payload.get("map", {})
            var is_host := bool(payload.get("isHost", false))
            _append_log("[room_joined] playerId=%s isHost=%s mapName=%s" % [
                _player_id, is_host, _map.get("name", "?")
            ])
        Protocol.TYPE_LOBBY_STATE:
            var players: Array = payload.get("players", [])
            var names := players.map(func(p): return str(p.get("name", "?")))
            _append_log("[lobby_state] players=[%s]" % ", ".join(names))
        Protocol.TYPE_ERROR:
            _append_log("[server_error] code=%s message=%s" % [
                payload.get("code", "?"), payload.get("message", "?")
            ])
        _:
            _append_log("[%s] %s" % [type_, JSON.stringify(payload)])

func _append_log(line: String) -> void:
    _log.text += line + "\n"
    _log.scroll_vertical = _log.get_line_count()
```

- [ ] **Step 2: main.tscn als Text-Datei schreiben**

Datei `godot/scenes/main.tscn`:

```tscn
[gd_scene load_steps=2 format=3 uid="uid://b8spike0main00"]

[ext_resource type="Script" path="res://scripts/main.gd" id="1_main"]

[node name="Main" type="Control"]
anchor_right = 1.0
anchor_bottom = 1.0
script = ExtResource("1_main")

[node name="Panel" type="Panel" parent="."]
anchor_right = 1.0
anchor_bottom = 1.0

[node name="VBox" type="VBoxContainer" parent="Panel"]
anchor_left = 0.5
anchor_top = 0.5
anchor_right = 0.5
anchor_bottom = 0.5
offset_left = -300.0
offset_top = -240.0
offset_right = 300.0
offset_bottom = 240.0

[node name="Title" type="Label" parent="Panel/VBox"]
text = "MCM Godot Spike — Connect"

[node name="UrlLabel" type="Label" parent="Panel/VBox"]
text = "WebSocket URL:"

[node name="UrlField" type="LineEdit" parent="Panel/VBox"]
text = "ws://localhost:8000/ws"
placeholder_text = "ws://localhost:8000/ws"

[node name="RoomLabel" type="Label" parent="Panel/VBox"]
text = "Room Code:"

[node name="RoomField" type="LineEdit" parent="Panel/VBox"]
text = "ABCD"
placeholder_text = "4 letters"

[node name="NameLabel" type="Label" parent="Panel/VBox"]
text = "Player Name:"

[node name="NameField" type="LineEdit" parent="Panel/VBox"]
text = "Godot"
placeholder_text = "Your name"

[node name="ConnectBtn" type="Button" parent="Panel/VBox"]
text = "Connect"

[node name="LogLabel" type="Label" parent="Panel/VBox"]
text = "Log:"

[node name="Log" type="TextEdit" parent="Panel/VBox"]
custom_minimum_size = Vector2(0, 280)
editable = false
```

- [ ] **Step 3: Editor neu öffnen, Scene importieren**

Falls Editor offen war: einmal schließen + neu öffnen, damit `main.tscn` als FileSystem-Resource auftaucht.

- [ ] **Step 4: Manual Acceptance — Connect-Test**

Voraussetzungen:
- Backend läuft: `uv run uvicorn app.main:app --reload`
- Browser-Tab offen: `http://localhost:8000/`, Browser-Lobby mit Name "Browser" + Room "ABCD" gejoined.

Im Godot-Editor: F5 (Run Project) drücken. Spike-Fenster öffnet sich.

- URL = `ws://localhost:8000/ws` (default)
- Room Code = `ABCD`
- Player Name = `Godot`
- "Connect" klicken

**Erwartete Log-Ausgabe (ungefähre Reihenfolge):**

```
[ws] connecting to ws://localhost:8000/ws
[ws] connected
[ws] sent join_room room=ABCD name=Godot
[room_joined] playerId=<irgendwas> isHost=false mapName=default-office
[lobby_state] players=[Browser, Godot]
```

**Erwartung im Browser-Tab:** Spielerliste zeigt jetzt zwei Einträge: "Browser" (Host) und "Godot".

Wenn beide passen: Acceptance grün.

Wenn `[lobby_state]` `availableMaps`/`selectedMapId` enthält und das nicht im Log auftaucht (weil unser Handler sie ignoriert): das ist OK für Schritt 1, wir nehmen sie in Schritt 2 dazu.

- [ ] **Step 5: Spike beenden, Commit**

Spike-Fenster schließen.

```bash
git add godot/scenes/main.tscn godot/scripts/main.gd
git commit -m "feat(godot): wire connect-flow with join_room and lobby logging

Spike Schritt 1: WebSocket-Verbindung steht, join_room/room_joined/
lobby_state laufen durch. Reines Log-UI, kein Render."
```

---

## Phase 3 — Schritt 2: Map-Debug-Render

### Task 8: `debug_renderer.gd` — Map als Linien zeichnen

**Files:**
- Create: `godot/scripts/debug_renderer.gd`

- [ ] **Step 1: debug_renderer.gd schreiben**

Datei `godot/scripts/debug_renderer.gd`:

```gdscript
class_name DebugRenderer
extends Node2D

const COLOR_ROOM_OUTLINE: Color = Color(0.9, 0.9, 0.95, 0.6)
const COLOR_ROOM_FILL: Color = Color(0.2, 0.2, 0.28, 0.4)
const COLOR_WALL: Color = Color(0.95, 0.3, 0.3, 0.85)
const COLOR_DOOR: Color = Color(0.3, 0.7, 0.95, 0.9)
const COLOR_SPAWN: Color = Color(0.3, 0.95, 0.4, 0.9)
const COLOR_TASK: Color = Color(0.95, 0.85, 0.2, 0.9)

var _map: Dictionary = {}

func set_map(map: Dictionary) -> void:
    _map = map
    queue_redraw()

func _draw() -> void:
    if _map.is_empty():
        return
    _draw_rooms()
    _draw_wall_lines()
    _draw_spawns()
    _draw_task_anchors()

func _draw_rooms() -> void:
    var rooms: Array = _map.get("rooms", [])
    for room in rooms:
        var rect := Rect2(
            float(room.get("x", 0)), float(room.get("y", 0)),
            float(room.get("width", 0)), float(room.get("height", 0))
        )
        var fill := COLOR_ROOM_FILL
        var hex := str(room.get("color", ""))
        if hex.begins_with("#") and hex.length() == 7:
            fill = Color(hex)
            fill.a = 0.35
        draw_rect(rect, fill, true)
        draw_rect(rect, COLOR_ROOM_OUTLINE, false, 2.0)
        var label := str(room.get("title", room.get("id", "?")))
        var label_pos := rect.position + Vector2(12, 32)
        draw_string(ThemeDB.fallback_font, label_pos, label, HORIZONTAL_ALIGNMENT_LEFT, -1, 28, COLOR_ROOM_OUTLINE)

func _draw_wall_lines() -> void:
    var size: Dictionary = _map.get("size", {})
    var map_w := float(size.get("width", 4800))
    var map_h := float(size.get("height", 3200))
    var lines: Array = _map.get("wallLines", [])
    for line in lines:
        var axis := str(line.get("axis", "x"))
        var pos := float(line.get("position", 0))
        var doors: Array = line.get("doors", [])
        if axis == "x":
            draw_line(Vector2(pos, 0), Vector2(pos, map_h), COLOR_WALL, 4.0)
            for door in doors:
                var c := float(door.get("center", 0))
                var w := float(door.get("width", 120))
                draw_circle(Vector2(pos, c), w * 0.5, COLOR_DOOR)
        elif axis == "y":
            draw_line(Vector2(0, pos), Vector2(map_w, pos), COLOR_WALL, 4.0)
            for door in doors:
                var c := float(door.get("center", 0))
                var w := float(door.get("width", 120))
                draw_circle(Vector2(c, pos), w * 0.5, COLOR_DOOR)

func _draw_spawns() -> void:
    var spawns: Array = _map.get("spawnPoints", [])
    for sp in spawns:
        var p := Vector2(float(sp.get("x", 0)), float(sp.get("y", 0)))
        draw_line(p + Vector2(-12, -12), p + Vector2(12, 12), COLOR_SPAWN, 3.0)
        draw_line(p + Vector2(-12, 12), p + Vector2(12, -12), COLOR_SPAWN, 3.0)

func _draw_task_anchors() -> void:
    var tasks: Array = _map.get("taskAnchors", [])
    for ta in tasks:
        var p := Vector2(float(ta.get("x", 0)), float(ta.get("y", 0)))
        draw_circle(p, 16.0, COLOR_TASK)
        draw_string(ThemeDB.fallback_font, p + Vector2(20, 6), str(ta.get("taskId", "?")), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, COLOR_TASK)
```

Anmerkung: Doors werden als Kreise statt als Cutouts gezeichnet — der Spike validiert Koordinaten, nicht den Wall-Computation-Algorithmus. Browser-Vergleich: gleiche Position, andere Visualisierung.

- [ ] **Step 2: Syntax-Check**

Editor öffnet die Datei. Keine roten Marker.

- [ ] **Step 3: Commit**

```bash
git add godot/scripts/debug_renderer.gd
git commit -m "feat(godot): add Node2D debug renderer for rooms/walls/spawns/tasks"
```

---

### Task 9: `debug_world.tscn` — Scene mit Camera und Renderer

**Files:**
- Create: `godot/scenes/debug_world.tscn`

- [ ] **Step 1: debug_world.tscn schreiben**

Datei `godot/scenes/debug_world.tscn`:

```tscn
[gd_scene load_steps=2 format=3 uid="uid://b8spike0world0"]

[ext_resource type="Script" path="res://scripts/debug_renderer.gd" id="1_renderer"]

[node name="DebugWorld" type="Node2D"]

[node name="Renderer" type="Node2D" parent="."]
script = ExtResource("1_renderer")

[node name="Camera" type="Camera2D" parent="."]
position = Vector2(2400, 1600)
zoom = Vector2(0.225, 0.225)
```

Begründung Zoom: Map-Mitte ist (2400, 1600). Viewport 1280×720, Map 4800×3200. Zoom = min(1280/4800, 720/3200) = min(0.267, 0.225) = 0.225. Mit Faktor 0.225 ist die Map vertikal voll, horizontal mit etwas Margin.

- [ ] **Step 2: main.gd erweitern: World-Wechsel nach room_joined**

In `godot/scripts/main.gd` den `_on_message`-Handler für `TYPE_ROOM_JOINED` ergänzen, sodass nach dem Logging die World-Scene geladen wird. Ersetze den `TYPE_ROOM_JOINED`-Match-Block durch:

```gdscript
        Protocol.TYPE_ROOM_JOINED:
            _player_id = str(payload.get("playerId", ""))
            _map = payload.get("map", {})
            var is_host := bool(payload.get("isHost", false))
            _append_log("[room_joined] playerId=%s isHost=%s mapName=%s" % [
                _player_id, is_host, _map.get("name", "?")
            ])
            _switch_to_world()
```

Und unten in `main.gd` die neue Methode anfügen:

```gdscript
func _switch_to_world() -> void:
    var world_scene := load("res://scenes/debug_world.tscn") as PackedScene
    if world_scene == null:
        _append_log("[error] debug_world.tscn not found")
        return
    var world := world_scene.instantiate()
    get_tree().root.add_child(world)
    var renderer := world.get_node("Renderer") as DebugRenderer
    renderer.set_map(_map)
    # Connect-UI ausblenden
    visible = false
    # WSClient an die neue Scene umhängen, damit weiter Messages verarbeitet werden
    _ws.reparent(world)
    # Renderer für spätere Player-Updates merken
    set_meta("renderer", renderer)
```

Erläuterung: Wir behalten `WSClient` (zugewiesen an `world`), `Main` selbst wird nur ausgeblendet — so können wir später bei Disconnect drauf zurückgreifen.

- [ ] **Step 3: Manual Acceptance — Map-Render**

Voraussetzungen wie bei Task 7. Backend läuft, Browser im Raum.

Im Godot-Editor: F5. Connect-Flow durchgehen. Erwartung:

- Connect-UI verschwindet.
- Es erscheint ein 2D-View mit:
  - 6 farbigen Rechtecken (Räume): Open Space (oben-links blaugrau), Meeting Room (oben-mitte violett), Kitchen (oben-rechts braun), Server Room (unten-links blau), War Room (unten-mitte teal), Legacy Basement (unten-rechts grün).
  - Roten Linien zwischen den Räumen (Wände).
  - Blauen Kreisen auf den Wänden (Doors).
  - Grünen Kreuzen in Open Space (Spawn Points).
  - Gelben Kreisen mit Labels in den Räumen (Task Anchors).
- Map ist zentriert und (fast) vollständig im Fenster sichtbar.

**Browser-Vergleich:** Browser-Tab öffnen, in der Lobby (oder im Spiel) das Map-Layout anschauen. Die Räume müssen an gleichen relativen Positionen liegen, gleiche Aspect-Ratio. Wenn die Wände im Godot-Spike z.B. genau dort sind, wo im Browser die Wand-Cutout-Kanten sind: Koordinaten-Mapping korrekt.

**Wenn schief:** Camera2D-Position und Zoom in `debug_world.tscn` justieren; danach nochmal testen.

- [ ] **Step 4: Wenn Acceptance grün, Commit**

```bash
git add godot/scenes/debug_world.tscn godot/scripts/main.gd
git commit -m "feat(godot): render map as debug lines/rectangles after room_joined

Spike Schritt 2: rooms, wall lines, spawn points, task anchors als
2D-Primitives. Camera2D zoom 0.225 zeigt Map zentriert."
```

---

## Phase 4 — Schritt 3: Player-Boxen (kein Movement)

### Task 10: Player aus `game_state` als farbige Boxen rendern

**Files:**
- Modify: `godot/scripts/debug_renderer.gd`
- Modify: `godot/scripts/main.gd`

- [ ] **Step 1: `debug_renderer.gd` um Player-Render erweitern**

In `godot/scripts/debug_renderer.gd` die folgenden Properties oben hinzufügen (direkt nach den COLOR-Konstanten):

```gdscript
const PLAYER_BOX_SIZE: Vector2 = Vector2(40, 40)
const COLOR_SELF_OUTLINE: Color = Color(1, 1, 1, 1)

var _players: Array = []
var _self_player_id: String = ""

func set_self_player_id(id: String) -> void:
    _self_player_id = id

func set_players(players: Array) -> void:
    _players = players
    queue_redraw()
```

Dann den `_draw()`-Block am Ende um einen Aufruf erweitern:

```gdscript
func _draw() -> void:
    if _map.is_empty():
        return
    _draw_rooms()
    _draw_wall_lines()
    _draw_spawns()
    _draw_task_anchors()
    _draw_players()
```

Und unten die Methode anhängen:

```gdscript
func _draw_players() -> void:
    for p in _players:
        var pos := Vector2(float(p.get("x", 0)), float(p.get("y", 0)))
        var hex := str(p.get("color", "#888888"))
        var col := Color(hex) if hex.begins_with("#") and hex.length() == 7 else Color(0.5, 0.5, 0.5)
        if not bool(p.get("isAlive", true)):
            col.a = 0.3
        var rect := Rect2(pos - PLAYER_BOX_SIZE * 0.5, PLAYER_BOX_SIZE)
        draw_rect(rect, col, true)
        if str(p.get("id", "")) == _self_player_id:
            draw_rect(rect, COLOR_SELF_OUTLINE, false, 4.0)
        var name_ := str(p.get("name", "?"))
        draw_string(ThemeDB.fallback_font, pos + Vector2(-30, -28), name_, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(1, 1, 1, 0.95))
```

- [ ] **Step 2: `main.gd` — `game_state` an den Renderer leiten**

In `godot/scripts/main.gd` einen weiteren `match`-Arm in `_on_message` einbauen — direkt nach dem `TYPE_LOBBY_STATE`-Block:

```gdscript
        Protocol.TYPE_GAME_STATE:
            var renderer := get_meta("renderer", null) as DebugRenderer
            if renderer != null:
                renderer.set_self_player_id(_player_id)
                renderer.set_players(payload.get("players", []))
```

Außerdem direkt nach `_switch_to_world()` den `set_self_player_id` einmalig setzen:

In `_switch_to_world()` ans Ende anfügen:

```gdscript
    renderer.set_self_player_id(_player_id)
```

- [ ] **Step 3: Manual Acceptance — Player-Render**

Voraussetzungen:
- Backend läuft.
- Browser-Tab: Browser-Spieler joint Raum "ABCD", Host. Klick "Demo-Mode starten" (oder Browser-zu-Browser falls 2 Tabs offen, dann "Spiel starten" im Host-Tab).
- Wichtig: Solange das Spiel in `LOBBY` ist, kommt kein `game_state`. Demo-Mode oder echter Start sind nötig.

Godot-Spike: F5 → Connect mit Name "Godot" → join_room → Map-Render.

Browser-Host: "Spiel starten" klicken (mit aktiviertem Demo-Mode falls nur 1 menschlicher Spieler).

**Erwartung im Godot-Spike:** auf der Map erscheinen jetzt 1+ farbige Boxen mit Namen darüber (Browser-Spieler + Godot-Spieler). Die Box mit dem Namen "Godot" hat einen weißen Outline (Self-Highlight).

**Browser-Vergleich:** Im Browser bewegt sich der Browser-Spieler (z.B. mit WASD im Browser-Tab). Im Godot-Spike springt die Browser-Box am gleichen visuellen Ort hin (ohne Smoothing — das kommt in Task 17). Eigene Box (Godot) bewegt sich nicht, weil wir noch keinen Input senden.

Wenn Boxen an grob richtigen Stellen erscheinen + Self-Highlight am richtigen Spieler: grün.

- [ ] **Step 4: Commit**

```bash
git add godot/scripts/debug_renderer.gd godot/scripts/main.gd
git commit -m "feat(godot): render game_state players as colored boxes with self highlight"
```

---

## Phase 5 — Schritt 4: Input + Interpolation

### Task 11: Input-Capture mit 20-Hz-Throttle

**Files:**
- Create: `godot/scripts/input_sender.gd`
- Modify: `godot/scripts/main.gd`
- Modify: `godot/scenes/debug_world.tscn`

- [ ] **Step 1: input_sender.gd schreiben**

Datei `godot/scripts/input_sender.gd`:

```gdscript
class_name InputSender
extends Node

const SEND_INTERVAL: float = 0.05  # 50 ms = 20 Hz

var _ws: WSClient
var _accum: float = 0.0
var _last_state: Dictionary = {"up": false, "down": false, "left": false, "right": false}
var _dirty: bool = true  # send once at start to register initial all-false

func _ready() -> void:
    set_process(true)

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

Begründung: Sende-Bedingung ist (Input geändert) UND (mind. 50 ms seit letztem Send). Bei stillem Input: kein Spam. Bei Input-Change: schicker Reaktion innerhalb maximal 50 ms.

- [ ] **Step 2: debug_world.tscn um InputSender-Node erweitern**

Datei `godot/scenes/debug_world.tscn` ersetzen durch:

```tscn
[gd_scene load_steps=3 format=3 uid="uid://b8spike0world0"]

[ext_resource type="Script" path="res://scripts/debug_renderer.gd" id="1_renderer"]
[ext_resource type="Script" path="res://scripts/input_sender.gd" id="2_input"]

[node name="DebugWorld" type="Node2D"]

[node name="Renderer" type="Node2D" parent="."]
script = ExtResource("1_renderer")

[node name="Camera" type="Camera2D" parent="."]
position = Vector2(2400, 1600)
zoom = Vector2(0.225, 0.225)

[node name="InputSender" type="Node" parent="."]
script = ExtResource("2_input")
```

- [ ] **Step 3: main.gd — InputSender mit ws verbinden**

In `_switch_to_world()` ans Ende anfügen (nach dem `set_self_player_id`-Call):

```gdscript
    var sender := world.get_node("InputSender") as InputSender
    sender.attach(_ws)
```

- [ ] **Step 4: Manual Acceptance — Input ohne Smoothing**

Voraussetzungen wie Task 10 (Backend, Browser im Raum, Spielstart).

Godot-Spike: F5 → Connect → Spiel ist gestartet → Map mit Player-Boxen sichtbar.

**Test:** WASD oder Pfeiltasten im Spike-Fenster gedrückt halten.

**Erwartung:** Die "Godot"-Box (mit weißem Outline) bewegt sich in Pfeilrichtung. **Aber ruckelig** — sie springt alle 50 ms ein Stück, weil wir noch nicht interpolieren.

**Browser-Vergleich:** Im Browser-Tab sieht man die "Godot"-Box smooth laufen (Browser interpoliert ja schon). Wir wollen den Bug-Marker visuell sehen, dass Godot ohne Interpolation hakelig ist.

Wenn Bewegung passiert + Richtung stimmt + ruckelig: grün, ist Erwartung.

- [ ] **Step 5: Commit**

```bash
git add godot/scripts/input_sender.gd godot/scripts/main.gd godot/scenes/debug_world.tscn
git commit -m "feat(godot): send player_input at 20 Hz (no interpolation yet)

Spike Schritt 4 — Teil 1: Input-Capture + Throttling. Bewegung
ist absichtlich ruckelig, Smoothing kommt im nächsten Commit."
```

---

### Task 12: Snapshot-Buffer + Interpolation

**Files:**
- Modify: `godot/scripts/debug_renderer.gd`
- Modify: `godot/scripts/main.gd`

- [ ] **Step 1: `debug_renderer.gd` um Snapshot-Buffer erweitern**

In `debug_renderer.gd` Properties (nach den existierenden `_players` / `_self_player_id`):

```gdscript
var _snap_prev: Dictionary = {}     # playerId -> {x, y, color, name, isAlive, id}
var _snap_curr: Dictionary = {}     # playerId -> {...}
var _snap_prev_t: float = 0.0
var _snap_curr_t: float = 0.0
var _interp_render: Array = []      # ersetzt _players im Draw

func _ready() -> void:
    set_process(true)

func push_snapshot(players: Array, now_msec: float) -> void:
    var by_id := {}
    for p in players:
        by_id[str(p.get("id", ""))] = p
    _snap_prev = _snap_curr
    _snap_prev_t = _snap_curr_t
    _snap_curr = by_id
    _snap_curr_t = now_msec

func _process(_delta: float) -> void:
    if _snap_curr.is_empty():
        return
    var now := float(Time.get_ticks_msec())
    var dt := _snap_curr_t - _snap_prev_t
    var alpha: float = 1.0
    if dt > 0.0:
        alpha = clamp((now - _snap_curr_t) / dt + 1.0, 0.0, 1.0)
    var rendered: Array = []
    for id in _snap_curr.keys():
        var curr := _snap_curr[id] as Dictionary
        var p := curr.duplicate()
        if _snap_prev.has(id):
            var prev := _snap_prev[id] as Dictionary
            var px := lerp(float(prev.get("x", 0)), float(curr.get("x", 0)), alpha)
            var py := lerp(float(prev.get("y", 0)), float(curr.get("y", 0)), alpha)
            p["x"] = px
            p["y"] = py
        rendered.append(p)
    _interp_render = rendered
    queue_redraw()
```

**Wichtig:** die alte `set_players()`-Methode bleibt erhalten (für Lobby-Phase, wo es kein Tick gibt), wird aber von `main.gd` durch `push_snapshot` ersetzt.

In `_draw_players()` die Schleife auf `_interp_render` umstellen:

```gdscript
func _draw_players() -> void:
    var source: Array = _interp_render if not _interp_render.is_empty() else _players
    for p in source:
        var pos := Vector2(float(p.get("x", 0)), float(p.get("y", 0)))
        var hex := str(p.get("color", "#888888"))
        var col := Color(hex) if hex.begins_with("#") and hex.length() == 7 else Color(0.5, 0.5, 0.5)
        if not bool(p.get("isAlive", true)):
            col.a = 0.3
        var rect := Rect2(pos - PLAYER_BOX_SIZE * 0.5, PLAYER_BOX_SIZE)
        draw_rect(rect, col, true)
        if str(p.get("id", "")) == _self_player_id:
            draw_rect(rect, COLOR_SELF_OUTLINE, false, 4.0)
        var name_ := str(p.get("name", "?"))
        draw_string(ThemeDB.fallback_font, pos + Vector2(-30, -28), name_, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(1, 1, 1, 0.95))
```

Erläuterung der Alpha-Formel: `(now - curr_t) / dt + 1.0` — wir rendern mit einem Tick Verzögerung. Wenn `now == curr_t`, alpha = 1.0 (zeige curr). Wenn `now == curr_t + dt`, alpha hätte 2.0 (clamped auf 1.0 — wir extrapolieren nicht, sondern stehen einfach auf curr bis das nächste snapshot kommt). Klingt counterintuitiv aber: wir interpolieren *zwischen* prev und curr, mit der Annahme dass curr "jetzt" ist. Bei 50 ms Lücken zwischen Snapshots ist das sauber.

- [ ] **Step 2: `main.gd` — `set_players` durch `push_snapshot` ersetzen**

In `_on_message`-Match-Arm für `TYPE_GAME_STATE`:

```gdscript
        Protocol.TYPE_GAME_STATE:
            var renderer := get_meta("renderer", null) as DebugRenderer
            if renderer != null:
                renderer.push_snapshot(payload.get("players", []), float(Time.get_ticks_msec()))
```

(Die alte `set_players`-Aufruf kommt raus.)

- [ ] **Step 3: Manual Acceptance — smoothes Movement**

Voraussetzungen wie Task 11.

F5, Connect, Spielstart, WASD halten.

**Erwartung:**
- Eigene Box bewegt sich **smooth** (kein 50-ms-Ruckeln mehr).
- Browser-Spieler-Box im Spike bewegt sich auch **smooth**.
- Beide Browser-Tab und Spike zeigen identische Spieler-Positionen mit minimaler Latenz.

**Wenn die Bewegung wieder ruckelig wäre:** dann ist die `push_snapshot`-Logik nicht angekommen — `get_meta("renderer")` prüfen.

**Wenn die Bewegung "rückwärts springt":** dann ist die alpha-Formel falsch — Logging einbauen, debuggen.

- [ ] **Step 4: Commit**

```bash
git add godot/scripts/debug_renderer.gd godot/scripts/main.gd
git commit -m "feat(godot): interpolate game_state snapshots over 50ms ticks

Spike Schritt 4 — Teil 2: Snapshot-Buffer der letzten 2 Frames,
lerp zwischen ihnen. Bewegung wird smooth bei 20-Hz-Server-Tick."
```

---

## Phase 6 — Reconnect-Test, Doku finalisieren, README

### Task 13: Reconnect-Verhalten manuell testen und dokumentieren

**Files:**
- Modify: `docs/CLIENT.md` (nur Sektion 3)

- [ ] **Step 1: `rejoin`-Handler in main.gd vorbereiten**

Damit wir Reconnect testen können, müssen wir wissen, was `app/protocol.py:RejoinPayload` erwartet: `roomCode` + `playerId`. In `main.gd` eine Manual-Reconnect-Methode (für jetzt einfach: Spike neu starten und mit alter playerId rejoin'en — dafür müssen wir die playerId persistieren).

Einfachstes Vorgehen für den Test (kein Code-Change nötig):
1. Spike laufen lassen, mit Name "Godot" joinen.
2. Im Log `playerId=<X>` ablesen und notieren.
3. Spike-Fenster schließen (= simuliert Disconnect).
4. Innerhalb 30 s: Spike neu starten — und prüfen, ob `join_room` mit Name "Godot" wieder dieselbe `playerId` `<X>` zurückgibt **ODER** ob `rejoin` mit der notierten `<X>` dasselbe tut.

Also wir testen beide Pfade.

- [ ] **Step 2: Test A — `join_room` mit gleichem Namen innerhalb 30 s**

Backend läuft, Browser im Raum als Host, Spielstart (damit Spieler-Identität persistiert wird).

1. Spike F5 → Connect mit `Name=Godot`, `Room=ABCD`. `playerId` aus Log notieren.
2. Spike-Fenster schließen.
3. Sofort wieder F5 → Connect mit gleichem Namen + Room.
4. Im Log nachsehen: ist `playerId` gleich oder anders?

Beobachtung dokumentieren.

- [ ] **Step 3: Test B — `rejoin` mit notierter `playerId`**

In `main.gd` temporäre Test-Variante: ändere die `_on_connected`-Methode kurzfristig so, dass sie statt `join_room` ein `rejoin` mit hartcodierter `playerId` schickt. Beispiel:

```gdscript
func _on_connected() -> void:
    _append_log("[ws] connected")
    var room := str(get_meta("pending_room"))
    var pid := "REPLACE_WITH_NOTED_PLAYER_ID"  # aus Test A
    _ws.send(Protocol.TYPE_REJOIN, {"roomCode": room, "playerId": pid})
    _append_log("[ws] sent rejoin room=%s playerId=%s" % [room, pid])
```

(Diese Änderung ist für den Test temporär. Nach Test A laufen, Test B laufen, danach revertieren.)

1. Erst Test A komplett (siehe Step 2).
2. `playerId` aus dem Log notieren.
3. main.gd temporär auf rejoin umstellen, `pid` einsetzen.
4. Spike-Fenster schließen + sofort F5.
5. Log beobachten — `room_joined` mit gleicher `playerId`?

Beobachtung dokumentieren.

- [ ] **Step 4: Test C — Reconnect nach 30+ s**

1. main.gd revertieren (zurück auf `join_room`).
2. Spike F5 → Connect mit `Name=Godot`. `playerId` notieren.
3. Spike-Fenster schließen.
4. **35 Sekunden warten.**
5. Spike F5 → Connect mit gleichem Namen.
6. Log: `playerId` gleich oder anders? Server-Verhalten beobachten.

- [ ] **Step 5: `docs/CLIENT.md` Sektion 3 aktualisieren**

In `docs/CLIENT.md` Sektion 3 (Reconnect-Verhalten) ersetzen durch die *gemessenen* Werte. Beispiel-Vorlage (die echten Werte hängen vom Test ab):

```markdown
## 3. Reconnect-Verhalten

- **Server-Verhalten:** behält Spieler-Identität 30 s nach Disconnect (Slice 0.10).
- **Client-API:**
  - **Erst-Join:** `join_room` mit `roomCode` + `playerName`.
  - **Reconnect via `join_room`:** [GETESTET in Spike: <Ergebnis Test A>]
  - **Reconnect via `rejoin`:** `rejoin` mit `roomCode` + `playerId`. [GETESTET in Spike: <Ergebnis Test B>]
- **Verhalten nach 30+ s Disconnect:** [GETESTET in Spike: <Ergebnis Test C>]
- **Empfehlung für Tier 3:** [Ableitung aus den Tests, z.B. "Godot-Client speichert `playerId` nach `room_joined` lokal, schickt bei Reconnect `rejoin`. Wenn `rejoin` mit `error` kommt (z.B. Session abgelaufen), Fallback auf `join_room`."]
```

- [ ] **Step 6: main.gd auf join_room reverten (falls noch auf rejoin)**

Sicherstellen dass `main.gd` wieder den ursprünglichen `_on_connected`-Code hat.

- [ ] **Step 7: Commit**

```bash
git add docs/CLIENT.md
git commit -m "docs(client): document measured reconnect behaviour from spike

Tested join_room re-join, rejoin with stored playerId, and
post-30s disconnect recovery."
```

---

### Task 14: `docs/CLIENT.md` mit gemessenen Werten + Doku-Lücken finalisieren

**Files:**
- Modify: `docs/CLIENT.md`

- [ ] **Step 1: Sektion 1 (Koordinaten) `[VERIFY:Task-12]` ersetzen**

In `docs/CLIENT.md` Sektion 1 den Punkt "Default-Zoom-Faktor" ersetzen durch den tatsächlich verwendeten Wert (aus `debug_world.tscn` — sollte `Vector2(0.225, 0.225)` sein, falls nicht justiert). Beispiel:

```markdown
- **Default-Zoom-Faktor (Spike, Viewport 1280×720):** `Vector2(0.225, 0.225)`. Begründung: `min(viewport_w/map_w, viewport_h/map_h) = min(1280/4800, 720/3200) = 0.225`. Map ist vertikal voll im Viewport, horizontal mit ~120px Margin.
```

- [ ] **Step 2: Sektion 2 (Tick) `[VERIFY:Task-16]` und `[VERIFY:Task-17]` ersetzen**

Sektion 2 ersetzen durch:

```markdown
## 2. Tick- und Interpolations-Modell

- **Server-Tick:** 20 Hz → ein `game_state` alle ~50 ms (`app/main.py:TICK_HZ`).
- **Client-Regel:** Bewegung NICHT simulieren. Server ist autoritativ.
- **Render-Strategie (validiert im Spike):** Snapshot-Buffer (letzte 2 Frames) + lerp zwischen prev und curr mit `alpha = clamp((now - curr_t) / dt + 1.0, 0, 1)`. Bei 20-Hz-Server liefert das visuell smoothe Bewegung. Siehe `godot/scripts/debug_renderer.gd::_process()`.
- **`player_input` Throttle (validiert im Spike):** Sende-Bedingung ist `(input geändert) UND (>= 50 ms seit letztem Send)`. Bei stillem Input: kein Spam. Bei Input-Change: max. 50 ms Latenz. Siehe `godot/scripts/input_sender.gd::SEND_INTERVAL`.
```

- [ ] **Step 3: Sektion 5 (Doku-Lücken) erweitern**

Während des Spikes haben wir vermutlich weitere Lücken entdeckt. In Sektion 5 alle gefundenen Lücken eintragen — Beispiel-Vorlage:

```markdown
## 5. Backend-Doku-Lücken (vom Spike entdeckt)

Pre-Spike sind die im initialen Plan identifizierten Lücken bereits in `docs/PROTOCOL.md` und `docs/maps.md` geschlossen:

- Map-Größe: 4800×3200 (`docs/maps.md`).
- `rejoin`-Message und `REJOIN_NOT_AVAILABLE`-Error: in `docs/PROTOCOL.md §4` und §6.
- `lobby_state`-Multi-Map-Felder (`availableMaps`, `selectedMapId`, `map`): in §5.
- `game_state`-Erweiterungen (`incidents`, `events`, `bodies`, `players.isConnected`): in §5.
- `private_state`-Message: in §5 ergänzt.

**Vom Spike NEU entdeckte Lücken** (während Tasks 7-12 + Reconnect-Test):

[TODO: Task 14 füllt nach Spike-Ende. Beispielsweise: Wall-Computation-Algorithmus an Map-Rändern, `compute_walls()`-Verhalten, Edge-Cases bei Reconnect mid-Meeting, ...]
```

- [ ] **Step 4: Commit**

```bash
git add docs/CLIENT.md
git commit -m "docs(client): finalize CLIENT.md with measured spike values

All [VERIFY:Task-N] markers replaced with real values.
Backend-doku-gap list compiled for follow-up slices."
```

---

### Task 15: `godot/README.md` und finaler Commit

**Files:**
- Create: `godot/README.md`

- [ ] **Step 1: README schreiben**

Datei `godot/README.md`:

```markdown
# MCM Godot Spike

Bootstrapping-Spike für den späteren Tier-3-Godot-Client.

## Was das ist

Schmaler Godot-4.3-Client, der gegen den existierenden FastAPI-Backend
WebSocket spricht. Validiert Protokoll-Erwartungen, kein Gameplay.

Vollständige Doku: `../docs/superpowers/specs/2026-04-26-godot-spike-design.md`
und `../docs/CLIENT.md`.

## Voraussetzungen

- **Godot 4.3 LTS** ([Download](https://godotengine.org/download))
- **MCM-Backend** läuft lokal: `cd .. && uv run uvicorn app.main:app --reload`

## Projekt öffnen

1. Godot 4.3 starten.
2. Project Manager → "Import" → `godot/project.godot` wählen.
3. "Import & Edit".

## Spike starten

Im Editor: F5 (Run Project). Es öffnet sich ein Fenster mit Connect-UI.

- **WebSocket URL:** `ws://localhost:8000/ws` (default; oder `wss://game.prod-is-lava.dev/ws` für Live-Smoke).
- **Room Code:** vier Buchstaben, z.B. `ABCD`.
- **Player Name:** beliebig.
- **Connect** klicken.

Browser-Tab parallel öffnen unter `http://localhost:8000/`, mit gleichem
Room Code joinen — beide Clients sehen sich gegenseitig.

## Tasten-Bindings (im Spiel)

- **WASD** oder **Pfeiltasten:** Bewegung.

## Was der Spike kann

- WebSocket-Connect, `join_room`, `room_joined`, `lobby_state` lesen.
- Map als Debug-Linien rendern (Räume, Wände, Spawns, Task-Anker).
- `game_state.players` als farbige Boxen mit Namen rendern.
- `player_input` mit 20-Hz-Throttle senden.
- Snapshot-Interpolation für smoothes Movement.

## Was der Spike NICHT kann

- Tasks halten, Sabotagen triggern, Voting, Endscreen.
- Sprites, Animationen, Tilemaps.
- Sound.
- Web-Export-Build.
- Tilemap-basiertes Rendering (kommt mit Tier 3.3).

## Code-Struktur

- `scenes/main.tscn` — Connect-UI (Entry-Point).
- `scenes/debug_world.tscn` — World mit Camera2D, Renderer, Input-Sender.
- `scripts/protocol.gd` — Konstanten und Message-Type-Strings.
- `scripts/ws_client.gd` — WebSocketPeer-Wrapper mit Signals.
- `scripts/main.gd` — Connect-UI-Driver, Message-Routing.
- `scripts/debug_renderer.gd` — `_draw()` für Map und Spieler, Snapshot-Buffer.
- `scripts/input_sender.gd` — Tastatur-Capture mit 20-Hz-Throttle.

## Nächste Schritte (Tier 3)

Siehe `../docs/ROADMAP.md` Tier 3. Der Spike ist die Basis — Tier 3.1
übernimmt Connect+Lobby aus diesem Skelett, Tier 3.3 ersetzt den
DebugRenderer durch Tilemap, Tier 3.4 ersetzt Player-Boxen durch Sprites.
```

- [ ] **Step 2: Commit**

```bash
git add godot/README.md
git commit -m "docs(godot): add README explaining spike scope and how to run"
```

---

### Task 16: ROADMAP-Update und finale Übersicht

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: ROADMAP.md um Spike-Erkenntnisse-Sektion erweitern**

In `docs/ROADMAP.md` direkt **vor** "### Tier 3 — Godot-Migration" eine neue Sub-Sektion einfügen:

```markdown
### Pre-Tier-3 — Godot-Bootstrapping-Spike (done)

**Ziel:** Protokoll-Annahmen vor dem Tier-3-Sprint real validieren, Doku-Lücken aufdecken, Skelett-Repo-Struktur etablieren.

**Aufwand (real):** [TODO: nach Spike-Ende eintragen]

| #     | Was                                                                                                         | Status      |
| ----- | ----------------------------------------------------------------------------------------------------------- | ----------- |
| P3.0  | `godot/`-Subfolder, `project.godot`, Branch `slice/godot-spike`, `.gitignore`                              | done        |
| P3.1  | `docs/CLIENT.md` mit Koordinaten/Tick/Reconnect-Sektionen, validiert + gemessen                            | done        |
| P3.2  | Spike Schritt 1: Connect + Lobby, `join_room` → `room_joined` → `lobby_state`                              | done        |
| P3.3  | Spike Schritt 2: Map-Debug-Render (Räume, Walls, Spawns, Task-Anchors)                                     | done        |
| P3.4  | Spike Schritt 3: Player-Boxen mit Self-Highlight                                                           | done        |
| P3.5  | Spike Schritt 4: Input + Snapshot-Interpolation                                                            | done        |
| P3.6  | Reconnect-Tests dokumentiert in `docs/CLIENT.md` Sektion 3                                                 | done        |
| P3.7  | Backend-Doku-Lücken-Liste in `docs/CLIENT.md` Sektion 5 — werden vor Tier 3 als eigene Slices abgearbeitet | done (Liste) |

Spec: `docs/superpowers/specs/2026-04-26-godot-spike-design.md`. Plan: `docs/superpowers/plans/2026-04-26-godot-spike.md`.

**Pre-Spike erledigte Doku-Fixes** (auf `main`, vor dem Spike-Worktree):

- `docs/maps.md` — Map-Größe auf 4800×3200 korrigiert
- `docs/PROTOCOL.md` — `rejoin`, `private_state`, Multi-Map-`lobby_state`, erweitertes `game_state`, `REJOIN_NOT_AVAILABLE` ergänzt

**Folge-Slices vor Tier 3** (kommen aus Task 14, falls der Spike weitere Lücken aufdeckt) — werden hier nach Spike-Ende eingetragen.
```

- [ ] **Step 2: Commit**

```bash
git add docs/ROADMAP.md
git commit -m "docs(roadmap): document Pre-Tier-3 Godot bootstrapping spike

Spike has shipped — adds the seven sub-tasks completed plus the
follow-up doc-fix slices that fell out of the gap analysis."
```

---

## Done-Verifikation

Am Ende des Plans nochmal alle Done-Kriterien (Spec §9) durchgehen:

- [ ] **Editor-Run-Sanity:** `cd godot && godot --editor .` (oder Editor-Project-Manager) öffnet das Projekt, F5 startet den Spike ohne Fehler.
- [ ] **Two-Client-Sanity:** Browser-Tab + Godot-Spike sehen sich, Bewegung beider Spieler ist smooth in beiden Clients sichtbar.
- [ ] **`docs/CLIENT.md` Real-Werte:** Keine `[VERIFY:Task-N]`-Marker mehr. Sektion 5 hat eine echte, abarbeitbare Lückenliste.
- [ ] **`docs/ROADMAP.md` Pre-Tier-3-Sektion** existiert mit Status `done` und Folge-Slice-Liste.
- [ ] **`godot/README.md`** existiert, fünfzeilen-tauglich.
- [ ] **Branch `slice/godot-spike`** hat ~12+ kohärente Commits, alle conventional, kein Merge zu `main` ohne extra User-Approval.
- [ ] **Backend unverändert:** `git diff main..slice/godot-spike -- app/ tests/ static/` ist leer.

Wenn alle Checks grün: User pingen mit "Spike ist fertig, ready für Review + Merge-Entscheidung". User entscheidet, ob nach `main` mergen oder erst die Pre-Tier-3-Doku-Slices oben drauf.

**KEIN Merge zu `main` ohne explizite User-Zustimmung.** (Per CLAUDE.md.)

---

## Plan Self-Review Notes

- **Spec coverage:** Alle Sektionen der Spec haben mindestens eine Task. §4 (Repo-Layout) → Tasks 1-3. §5 (CLIENT.md) → Tasks 4, 13, 14. §6 (Schritte 1-4) → Tasks 5-12. §7 (Test-Setup) → in jeder Acceptance-Sektion verlinkt. §8 (Output) → Tasks 14, 15. §9 (Done) → Done-Verifikation am Ende. §10 (Folge-Arbeit) → Task 16. §11 (Risiken) → werden in CLIENT.md §5 + ROADMAP-Folge-Slices verarbeitet.
- **Type consistency:** `DebugRenderer` referenziert in `main.gd` und `debug_renderer.gd` mit `class_name DebugRenderer`. `WSClient` referenziert in `main.gd`, `input_sender.gd`, `ws_client.gd`. `Protocol` als Konstanten-Klasse durchgängig. Method-Namen `set_map`, `set_self_player_id`, `set_players`, `push_snapshot`, `attach` werden alle definiert und genauso aufgerufen.
- **Placeholders:** Keine TBD/TODO im Code. Die `[VERIFY:Task-N]`-Marker in CLIENT.md sind absichtliche Platzhalter, die explizit in Tasks 13-14 ersetzt werden — das ist Teil des Plans, nicht ein Plan-Fehler.
