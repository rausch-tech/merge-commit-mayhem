# Godot Client — Tier 4 Handoff

Onboarding-Dokument für den Godot-Entwickler, der den MCM Tier-4-Client baut.
Voraussetzung: solide Godot-4-Erfahrung. MCM-Vorwissen brauchst du keins —
diese Doku liefert Kontext, Architektur, Protokoll, vorhandene 3D-Demo und
einen konkreten Slice-Plan ab dem Punkt, an dem die Demo aufhört.

- **Live-Backend:** https://prod-is-lava.dev (auto-deploy von `main`)
- **Repo:** https://github.com/rausch-tech/merge-commit-mayhem
- **Stand 2026-04-27:** Tier 0–3.7 ist live; 3D-Demo (Tier-4-Prototyp) liegt
  unter `godot-3d/` direkt in `main`. Sie deckt die Architektur (Lobby,
  World-Stream, Character, HUD, Pause-Menü) ab und validiert Protokoll +
  Snapshot-Pipeline. Die Demo ist explizit **Spike-Qualität, kein finales
  Tier-4-Release** — Map-Wände rendern z.B. nicht gegen den aktuellen Server
  (siehe §3.6).

---

## Wie diese Doku zu lesen ist

Lies §1–§3 sequenziell — Spielkontext, Architektur, vorhandene 3D-Demo. §3.6
ist der wichtigste neue Abschnitt: er beschreibt den einen bekannten
Schema-Drift, den du bei der ersten echten Server-Session hitten wirst.
Danach nutzt du §4–§7 als Referenz, während du gegen den Code arbeitest. §8
fasst CI-Gates und Konventionen zusammen. §9 ist Stolperfallen-Sammlung —
bitte vor dem ersten F5 lesen. §10 ist der konkrete Slice-Plan. §11 sind
die ersten Schritte für dich.

Verlinkte Repository-Doku, die diese Datei nicht dupliziert:

- [`AGENTS.md`](../AGENTS.md) — repo-weiter Onboarding-Guide (Stack, Commands, CI-Gates).
- [`docs/ROADMAP.md`](ROADMAP.md) — vollständige Tier-Roadmap inkl. Tier 4.
- [`docs/PROTOCOL.md`](PROTOCOL.md) — vollständige WebSocket-Contract-Liste.
- [`docs/maps.md`](maps.md) — Map-JSON-Schema inkl. KayKit-Asset-Mapping.
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — Backend-Layout (FastAPI, Pydantic).
- [`docs/GAME_OVERVIEW.md`](GAME_OVERVIEW.md) — Spielprinzip, Rollen, Win-Conditions.
- [`ASSET_LICENSE.md`](../ASSET_LICENSE.md) — Asset-Lizenzlage für Tier 4.

---

## 1. Was ist MCM?

### 1.1 Das Spiel

**Merge Conflict Mayhem** ist ein Social-Deduction-Multiplayer-Spiel für
Tech-Teams: Release-Team gegen geheime Chaos-Agenten in einem
DevOps-themen Office-Setting. 5–12 Spieler, ~10 Minuten pro Runde,
gedacht für die gemeinsame Mittagspause im Team.

- **Karten-Größe:** 4800×3200 px Office-Map mit Räumen wie Open Space,
  Kitchen, Server Room, Meeting Room, War Room, Legacy Basement. Eine
  größere `office-complex` Map (5600×3200 mit Korridor) liegt ebenfalls
  vor.
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
  Per-Player-Coffee-Energy (`private_state`).

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
4.1–4.5 laufen, blockieren erst Tier 4.10 (Polish + Animations). Das
3D-Demo benutzt eine Übergangs-Asset-Auswahl (Kenney Mini + KayKit), die
für die finalen Slices ggf. ersetzt wird; siehe §6.6 + `ASSET_LICENSE.md`.

### 2.2 Godot-Sprint (~4–6 Wochen)

| #    | Slice                                                                                 | Effort | Demo-Stand                                                                                                 |
| ---- | ------------------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| 4.1  | Godot-4-Setup, Web-Export-Config, WebSocketPeer-Binding                               | 1 Tag  | OK in `godot-3d/`                                                                                          |
| 4.2  | Lobby-Scene (UI, Room-Code-Input, Player-Liste, Map-Selection, Start)                 | 1–2 Tg | OK `main.gd`                                                                                               |
| 4.3  | Map-Loader: JSON → 3D-Geometrie (Floors, Walls, Doors, Spawns, TaskAnchors)           | 2 Tage | TEILWEISE — §3.6 Schema-Drift                                                                              |
| 4.4  | Character-Scene: Mesh + Idle/Walk-Anim + Movement-Interpolation                       | 2–3 Tg | OK `character.gd`                                                                                          |
| 4.5  | HUD + Stat-Pills + Role + Timer (Tween-Animationen)                                   | 1 Tag  | OK `hud.gd`                                                                                                |
| 4.6  | Task-Interaction (Mini-Game-Modals via Tier-3-API + Progress-Ring + Completion-VFX)   | 2 Tage | TODO                                                                                                       |
| 4.7  | Sabotage-Buttons mit Cooldown-Display                                                 | 1 Tag  | TODO                                                                                                       |
| 4.8  | Voting-Overlay + Result-Toast (Slide-Animationen)                                     | 1 Tag  | TODO                                                                                                       |
| 4.9  | Endscreen mit Role-Reveal + Stats + Confetti-Particles                                | 1 Tag  | TODO                                                                                                       |
| 4.10 | Among-Us-Features: Vents (anim+sfx), Body+Report, Take-Down, Lights/Comms-VFX, Ghosts | 5–8 Tg | nur Ghost-Alpha vorhanden                                                                                  |
| 4.11 | Sound-Integration (Footsteps, UI-SFX, BGM)                                            | 1 Tag  | TEILWEISE (siehe §3)                                                                                       |
| 4.12 | Polish + Bugfixes                                                                     | 3–5 Tg | TODO                                                                                                       |
| 4.13 | Web-Export-Deploy zur selben EC2                                                      | 0.5 Tg | 🟡 lokal builbar via `scripts/godot-web-export.sh`, FastAPI mountet `/godot/`, EC2-Tarball-Inclusion offen |

Die Demo-Stand-Spalte ist **als Architektur-Referenz** gemeint, nicht als
"Slice-merged-DoD". Die Demo kompiliert und läuft lokal gegen Backend, ist
aber Spike-Qualität: keine Tests, kein Web-Export, ein Schema-Drift in §3.6,
und nicht alle Tier-4.4-Animationen sind durchgespielt.

**Tier 4 ist erst "done" wenn ein Live-Test mit echten Spielern erfolgreich
ist.** Live-Tests sind in MCM die Tier-Übergangs-Validierung.

---

## 3. Vorhandene 3D-Demo (`godot-3d/`)

Direkt in `main` gemerged (Branch `slice/tier4-3d-demo`, c568386 + d731528).
Dies ist die Architektur-Referenz: alles was Lobby/World/Character/HUD/Pause
betrifft, hat eine konkrete GDScript-Implementation, gegen die du
inkrementell weiterbauen kannst.

### 3.1 Project Layout

```
godot-3d/
├── project.godot                          # Godot 4.6, mobile renderer, 1280×720
├── export_presets.cfg                     # Web-Export-Preset konfiguriert (threading + cross-origin-isolation)
├── maps/
│   ├── default.json                       # 6-room office (4800×3200) — LEGACY wallLines schema!
│   └── office_complex.json                # 9-room (5600×3200) mit Korridor — LEGACY wallLines
├── assets/
│   ├── audio/{footsteps,sting,ui}/        # 5 Carpet-Footsteps, 4 Stings, 2 UI-Klicks (Kenney CC0)
│   ├── character/kenney_mini/             # 6 Charakter-Meshes (Kenney Mini Characters CC0)
│   ├── floor/floor_kitchen.gltf           # 1 KayKit-Floor-Tile (aktuell ungenutzt im map_builder)
│   └── furniture/{desk,chair_desk_A,monitor}.gltf  # 3 KayKit-Möbelstücke
├── scenes/
│   ├── main.tscn                          # Entry: programmatic Lobby-UI
│   ├── world.tscn                         # 3D-Welt, gestartet beim phase=playing
│   ├── character.tscn                     # Single-Player-Mesh
│   ├── hud.tscn                           # CanvasLayer-HUD
│   ├── pause_menu.tscn                    # ESC-Overlay
│   ├── demo_world.tscn                    # Headless-Demo gegen Mock-State (aerial cam)
│   ├── demo_world_followcam.tscn          # Headless-Demo mit Follow-Cam
│   └── test_world.tscn                    # leftover, broken (siehe §3.4)
└── scripts/
    ├── main.gd                            # 535 LoC — Lobby-UI + Connect + Phase-Switch
    ├── world.gd                           # 313 LoC — World-Owner, Camera-Follow, Player-Sync
    ├── character.gd                       # 302 LoC — Mesh, Animation, Footsteps, Nameplate
    ├── map_builder.gd                     # 352 LoC — JSON → 3D Floors/Walls/Spawns/Furniture
    ├── hud.gd                             # 340 LoC — Stat-Pills, Timer, Role-Chip, Roster
    ├── pause_menu.gd                      # 146 LoC — ESC-Overlay
    ├── ws_client.gd                       #  72 LoC — WebSocketPeer-Wrapper, Signals
    ├── input_sender.gd                    #  41 LoC — WASD-Capture, 20 Hz Throttle
    ├── protocol.gd                        #  45 LoC — Konstanten, server_to_world() Helper
    ├── demo_world.gd                      #  87 LoC — Headless-Mock-Entry (aerial)
    ├── demo_world_followcam.gd            #  54 LoC — Headless-Mock-Entry (follow-cam)
    └── test_world.gd                      #  85 LoC — alter Spike, lädt fehlendes Dummy.glb
```

`project.godot` hat seit 2026-04-27 ein konfiguriertes Web-Export-Preset
(Tier 4.13). Build via `scripts/godot-web-export.sh` (release oder
`-d` fuer debug); Output landet unter `godot-3d/exports/index.html` (samt
`.wasm`/`.pck`/Audio-Worklets). FastAPI mountet `/godot/` auf das exports-
Verzeichnis und setzt COOP/COEP-Response-Headers, sodass der WASM-Build im
Browser SharedArrayBuffer nutzen kann. Lokaler Smoke:
`scripts/godot-web-export.sh --serve`, dann `http://localhost:8000/godot/`.
Production-Deploy auf EC2 ist noch nicht im Tarball-Step verdrahtet.

### 3.2 Was die Demo kann (verifiziert)

**Lobby (`main.gd`):**

- Programmatische UI: Connect-Card (URL/Raumcode/Spielername),
  Lobby-Card (Spielerliste, Demo-Mode-Checkbox für Host, Start-Button,
  Verlassen-Button), Log-Bereich am unteren Rand.
- WebSocket-Connect, `join_room` mit `roomCode`+`playerName`,
  `room_joined` lesen, `lobby_state` für Player-Liste, `start_game` mit
  `demo: bool` schicken.
- Phase-Detection: bei `game_state.phase == "playing"` (oder `"meeting"`)
  → `world.tscn` instanziieren, WSClient an die World übergeben,
  `main.tscn` queue-freen.
- Re-Entry-Sicherheit: `_transitioning`-Guard verhindert dass weitere
  20 Hz-Ticks während des Scene-Switches eine zweite World instanziieren.

**Welt (`world.gd` + `map_builder.gd`):**

- Map-JSON → `Node3D` mit Sub-Tree für Environment, Floors (per Room
  ein `PlaneMesh`), Walls, Perimeter, Spawn-Points (`Marker3D`),
  Task-Anchors (gelbe pulsierende Diamanten), Furniture-Heuristik pro Room.
- Lighting: ein DirectionalLight als Sun (mit Shadow-Map), ein zweites
  als Fill, ambient `Environment` mit gedämpftem Blau-Anteil.
- Camera: 2 Modi via `aerial_demo_camera` Bool-Export.
  - `false` (Default im Live-Spiel): Perspective-Cam mit 55° FOV,
    `CAMERA_OFFSET = Vector3(0, 10, 8)` und Pitch ~51°. Lerpt mit
    `CAMERA_LERP_SPEED=6` zum lokalen Spieler.
  - `true` (Demo-Screenshots): Orthographic top-down, am Map-Center geparkt,
    Map-Höhe = Cam-Size, schaut gerade nach unten.
- 20 Hz Snapshot-Apply: pro `game_state` Tick werden Player gespawned,
  bewegt (`push_target` + Lerp), oder despawned. Death-Detection via
  `isAlive`-Transition triggert Sting.
- Phase-Stings: `meeting` → Meeting-Sound, Death-Transition → Kill-Sound,
  `private_role` → Role-Reveal-Sound (einmalig).
- ESC öffnet/schließt Pause-Menü.

**Character (`character.gd`):**

- Wählt eines von 6 Kenney-Mini-Meshes basierend auf `player.color` —
  gespiegelt zu `static/render.js:COLOR_TO_CHAR_INDEX` und
  `app/game/game_room.py:_COLOR_PALETTE`. Spielers 7+ fallen auf Index 0.
- Position-Lerp mit `POSITION_LERP_SPEED=14` jedes Frame zum letzten
  `push_target(server_x, server_y)` (umgerechnet via
  `Protocol.server_to_world` — siehe §5.1).
- Walk/Idle-Animation-Switch via Movement-Detection (Deadzone-Schwelle).
  Kenney's `loop_mode=none` wird per `_force_loop` auf `LOOP_LINEAR`
  gehoben, sonst freezed der Clip nach einem Cycle.
- Footstep-Sounds: zufällig aus 5 Carpet-Variants, alle `FOOTSTEP_INTERVAL=0.38s`,
  `AudioStreamPlayer3D` mit `max_distance=12`. Pitch wird pro Step
  variiert für Natürlichkeit. Tote Spieler triggern keine Steps.
- Visuelle Identitätsmarker: Player-Color-Disc (TorusMesh, emissiv) am
  Boden + (nur lokaler Spieler) zusätzliches grünes Self-Ring mit
  Pulse-Animation. Nameplate als `Label3D` mit Billboard.
- Ghost-State: alive=false → Mesh-Transparenz auf 0.55 (visuell sichtbar,
  aber kein Spectator-Mode-Verhalten implementiert).

**HUD (`hud.gd`):**

- Top-Bar mit 4 Stat-Pills: Release-Progress, Pipeline-Stability,
  Coffee-Level, Incidents — jeder mit Wert + Fill-Bar (clamped 0-100).
  Quelle: `game_state.{releaseProgress, pipelineStability, coffeeLevel, incidents}`.
- Phase-Label + Timer (rechts): `phase` und `remainingSeconds` formatiert
  als `mm:ss`.
- Role-Chip (links unten): `private_role.role` + Team (gefärbt — Chaos
  rot, Release grün).
- Spieler-Roster (rechts): Color-Dot + Name, "(du)"-Suffix, dimmed wenn
  `isAlive=false`. Wird auf jedem Tick neu gebaut (cheap genug bei <12 Spielern).
- Map-Label (unten): aktueller Map-Name als sanftes Hint.

**Pause-Menü (`pause_menu.gd`):**

- ESC öffnet/schließt das Overlay (volle Backdrop, zentrale Card).
- Buttons: "WEITER", "RAUM VERLASSEN" (Danger-Style), zusätzlich "RUNDE
  BEENDEN (Host)" wenn `is_host`.
- Sounds: `switch.ogg` beim Öffnen, `click.ogg` pro Button-Press.
- "RUNDE BEENDEN" schickt `return_to_lobby` (nur Host).

**Demo-Modi (`demo_world.tscn` / `demo_world_followcam.tscn`):**

- Spawnen World direkt mit Mock-Players + Mock-State, ohne FastAPI-Backend.
- `demo_world.gd` lädt `office_complex.json` (9 Räume, Korridor); aerial
  cam für Screenshot-Reihen.
- `demo_world_followcam.gd` lädt `default.json` und nutzt die
  in-game Follow-Cam — schöner für lokale Visuals, kein Server nötig.

### 3.3 Was die Demo NICHT kann

- Keine Task-Interaktion (`task_hold_start` / `task_hold_stop`).
- Keine Sabotage-Trigger oder Repair-Panels.
- Kein Voting-Overlay (`cast_vote` / `skip_vote`).
- Kein Endscreen — `phase=ended` bounct die Welt zurück nach `main.tscn`.
- Keine Mini-Game-Modals (5 Mini-Games existieren server-/browser-seitig).
- Kein Vent-Use, Body-Report, Take-Down, Use-Ability.
- Kein Auto-Reconnect via `user://player.json` (siehe §9.5 / §10).
- Web-Export-Build laeuft lokal (`scripts/godot-web-export.sh`). EC2-Deploy noch nicht durchverdrahtet.
- `private_state` (Coffee-Energy, Cooldowns) wird empfangen aber nicht
  gerendert.
- Wand-Rendering gegen den **Live-Server** funktioniert nicht (siehe §3.6).
- BGM-Loop fehlt absichtlich (Kenney's "computer-noise" war zu nervig);
  nur Footsteps + Stings + UI-Klicks sind im Audio-Mix.

### 3.4 Bekannte Caveats im Code

- **`scripts/test_world.gd`** preloaded `res://assets/character/Dummy.glb`,
  das nicht mehr im Repo liegt (Kenney-Swap hat es ersetzt). Die Datei
  wird nicht aus `main.tscn` referenziert, parst aber bei Project-Reload
  als Error. Saubere Lösung: das Script + `test_world.tscn` löschen.
- **`map_builder.gd`** liest `wallLines` (Legacy-Schema). Siehe §3.6 für
  die Migrations-Aufgabe — das ist Tier-4.3-Hauptbaustelle.
- **`map_builder.gd`** rendert keine Türen (`doorKind` wird ignoriert).
  Für Slice-3-Schema hieß "Türen sind implizit als Cutouts in den
  WallSegments codiert"; für die neue Schema-Welt müsstest du Door-Frames
  als eigene Geometrie laden.
- **`map_builder.gd`** ignoriert `mapObjects` (Tier-4-Props mit
  `blocksMovement`, `taskId`, `objectType`). Im Browser werden diese
  bereits gerendert (`static/render.js`). Im Godot-Client ist das
  Tier-4.3-Followup.
- **`map_builder.gd::_decorate_rooms`** ist hartkodiert auf Room-IDs
  (`open_space`, `meeting_room`, …) der `default.json`. Bei
  `office_complex` (mit `open_space_east`, `corridor`, `reception`)
  bleiben Räume möbelfrei. Lösung: an `mapObjects` koppeln statt an
  Room-IDs.
- **`world.gd`** hört auf `ws_client.disconnected` und ruft sofort
  `_return_to_main` — ein Auto-Reconnect-Versuch fehlt komplett.

### 3.5 Code-Map (zum schnellen Auffinden)

| Datei                            | Wichtige Stellen                                                               |
| -------------------------------- | ------------------------------------------------------------------------------ |
| `protocol.gd`                    | `WORLD_SCALE=0.01`, `server_to_world()`, alle Message-Type-Konstanten + Phasen |
| `ws_client.gd`                   | `connect_to_server()` mit Reconnect-Reset, `_handle_packet()` JSON-Routing     |
| `input_sender.gd`                | WASD/Arrow-Polling, 50 ms Throttle, `set_enabled()` für Cutscene-Locking       |
| `main.gd:_on_message`            | Dispatch von Lobby-Messages, `_transition_to_world()` für Phase-Switch         |
| `main.gd:_build_ui`              | Kompletter Lobby-UI-Tree programmatisch (kein Editor-Authoring)                |
| `world.gd:_apply_state`          | 20 Hz Player-Spawn/Despawn/Move, Death-Detection, HUD-Forward                  |
| `world.gd:_setup_camera`         | Aerial- vs. Follow-Cam-Setup                                                   |
| `character.gd:setup`             | Player-Daten setzen + Mesh-Auswahl per Color-Index                             |
| `character.gd:_process`          | Position-Lerp, Walk/Idle-Switch, Footsteps                                     |
| `character.gd:_force_loop`       | Workaround für Kenney `loop_mode=none`                                         |
| `map_builder.gd:build`           | Map → 3D-Tree (Floors → Walls → Perimeter → Spawns → TaskAnchors → Furniture)  |
| `map_builder.gd:_build_walls`    | **legt `wallLines` an — Schema-Drift, siehe §3.6**                             |
| `map_builder.gd:_decorate_rooms` | Hartkodierte Room-IDs für Möbel-Heuristik                                      |
| `hud.gd:apply_game_state`        | Stat-Pills + Timer + Phase + Roster aus `game_state`                           |
| `hud.gd:set_role_info`           | Role-Chip + Team-Color aus `private_role`                                      |

### 3.6 wallLines-Schema-Drift (Tier 4.3 Hauptbaustelle)

**Problem:** `map_builder.gd:_build_walls()` liest aus dem Map-JSON ein
Feld `wallLines: [{axis, position, doors[{center, width}]}]`. Dieses
Feld existierte bis 2026-04-27 im Server-Schema, wurde aber in Slice 3
("Wand-Modell C") entfernt. Der heutige Server-Code in
`app/game/game_map.py:GameMap` hat **kein** `wall_lines`-Feld mehr;
gedumpt wird über `room.map.model_dump(by_alias=True)`. Auf der Wire
kommt also `doors[]` als Top-Level-Liste, aber **nie** `wallLines`.

**Beweis:**

```python
# app/game/game_map.py
class GameMap(BaseModel):
    model_config = _camel()
    name: str
    size: MapSize
    rooms: list[Room]
    # Slice-3 (Tier 4 prep): doors live as a top-level list, each door
    # references two adjacent rooms by id. Walls are auto-derived from
    # adjacent room edges (see ``compute_walls``); no separate
    # ``wallLines`` storage anymore.
    doors: list[Door] = Field(default_factory=list)
    spawn_points: list[SpawnPoint] = Field(default_factory=list)
    task_anchors: list[TaskAnchor] = Field(default_factory=list)
    sabotage_panels: list[SabotagePanel] = Field(default_factory=list)
    vents: list[Vent] = Field(default_factory=list)
    map_objects: list[MapObject] = Field(default_factory=list)
    war_room_id: str
```

Die mitgelieferten Demo-Maps in `godot-3d/maps/*.json` benutzen noch das
alte Schema (sie sind Kopien aus dem Spike-Stand vor Slice 3) und sind
deshalb nur für die Headless-Demos brauchbar. **Sobald du gegen den
echten Server connectest, kommt eine Map ohne `wallLines` an, und der
Wall-Loop in `_build_walls()` iteriert über eine leere Liste → keine
Wände auf dem Floor.**

**Fix-Aufgabe in Tier 4.3:**

1. Wall-Auto-Derive-Algorithmus aus `app/game/game_map.compute_walls()`
   (vollständig in §6.4 dokumentiert) in GDScript portieren. Eine
   Browser-Mirror-Implementation existiert in
   [`static/render.js:computeWallsClient()`](../static/render.js) als
   zweite Referenz.
2. `map_builder.gd:_build_walls(parent, lines, …)` durch
   `_build_walls_from_doors(parent, rooms, doors, mapObjects, mapSize)`
   ersetzen, der die abgeleiteten Wand-Rechtecke direkt produziert.
3. `doorKind` aus jeder `doors[]`-Entry verwenden, um Türrahmen-Geometrie
   zu setzen (z.B. unterschiedliche Materials für `office_door`,
   `glass_panel`, `vault`, `none`).
4. `mapObjects` mit `blocksMovement=true` als zusätzliche Wall-AABBs
   hinzufügen (`map_object_aabb`-Logik aus `game_map.py` mirrorn).
5. Die Demo-Maps in `godot-3d/maps/` parallel migrieren via
   [`scripts/migrate_walls_to_doors.py`](../scripts/migrate_walls_to_doors.py)
   — der gleiche Migrator, der die `maps/*.json` damals umgestellt hat.
   So bleibt `demo_world.tscn` funktional.

Sanity-Check nach dem Fix: `default.json` aus dem Live-Server reicht 7
Doors (`d1`–`d7`); aus 6 Räumen + 7 Cutouts müssen genau die Wand-Segmente
entstehen, die du im Browser unter `http://localhost:8000` siehst.

---

## 4. WebSocket-Protokoll

JSON-Frames `{type: string, payload: object}`. Vollständige Pydantic-Models:
[`app/protocol.py`](../app/protocol.py). Vollständige Doku:
[`docs/PROTOCOL.md`](PROTOCOL.md). Hier die Übersicht für den Godot-Client.

### 4.1 Client → Server

| Message                  | Payload (camelCase)                | Wann                                         | Demo benutzt?                   |
| ------------------------ | ---------------------------------- | -------------------------------------------- | ------------------------------- |
| `join_room`              | `{roomCode: str, playerName: str}` | Auf Connect                                  | ja, `main.gd`                   |
| `rejoin`                 | `{roomCode: str, playerId: str}`   | Auf Reconnect innerhalb 30 s                 | nein                            |
| `select_map`             | `{mapId: str}`                     | Host wählt Map vor `start_game`              | nein                            |
| `start_game`             | `{demo: bool = false}`             | Host startet Runde                           | ja, `main.gd`                   |
| `set_preferred_role`     | `{role: str}`                      | Lobby: Spieler wählt Wunsch-Rolle            | nein                            |
| `player_input`           | `{up, down, left, right: bool}`    | Alle 50 ms oder bei Input-Änderung           | ja, `input_sender.gd`           |
| `task_hold_start`        | `{taskId: str}`                    | E halten am Task                             | nein                            |
| `task_hold_stop`         | `{taskId: str}`                    | E loslassen                                  | nein                            |
| `mini_game_input`        | `{taskId, action, ...}`            | Mini-Game-Input (Tier 3 API)                 | nein                            |
| `trigger_sabotage`       | `{sabotageId: str}`                | Chaos triggert Sabotage (object-bound, nahe) | nein                            |
| `repair_sabotage`        | `{sabotageId: str}`                | F halten am Repair-Panel                     | nein                            |
| `use_vent`               | `{}`                               | Chaos: V cyclet Vents, dann zum TP           | nein                            |
| `use_ability`            | `{}`                               | Aktive Rollen-Fähigkeit auslösen             | nein                            |
| `trigger_takedown`       | `{targetPlayerId: str}`            | Chaos: Take-Down-Attack                      | nein                            |
| `report_body`            | `{bodyPlayerId: str}`              | Body finden + reporten                       | nein                            |
| `call_emergency_meeting` | `{}`                               | Im War-Room (oder via Standup-Ability)       | nein                            |
| `cast_vote`              | `{targetPlayerId: str}`            | Im Meeting voten                             | nein                            |
| `skip_vote`              | `{}`                               | Im Meeting Skip wählen                       | nein                            |
| `return_to_lobby`        | `{}`                               | Host: Spielende → Lobby                      | ja, `pause_menu.gd`             |
| `abort_round`            | `{}`                               | Host: laufende Runde abbrechen               | nein                            |
| `leave_room`             | `{}`                               | Komplett verlassen                           | nein (Demo schließt nur den WS) |

### 4.2 Server → Client

| Message               | Payload (camelCase)                             | Wann                                     | Demo verarbeitet?         |
| --------------------- | ----------------------------------------------- | ---------------------------------------- | ------------------------- |
| `room_joined`         | `{roomCode, playerId, isHost, map}`             | Nach join/rejoin; full map-JSON dabei    | ja, `main.gd`             |
| `lobby_state`         | `{roomCode, players[], availableMaps[], map}`   | Während Lobby (Spieler joinen)           | ja, Player-Liste          |
| `private_role`        | `{role, team, title, ability, ...}`             | Nach Start, owner-only, einmalig         | ja, HUD-Chip              |
| `private_state`       | `{coffeeEnergy, abilityUsed, takedownCooldown}` | Jeder Tick, owner-only (für HUD)         | nein, ignoriert           |
| `game_state`          | `{phase, players[], tasks[], sabotages[], ...}` | Jeder Tick (20 Hz), per-viewer gefiltert | ja, `world.gd` + `hud.gd` |
| `voting_result`       | `{removedPlayerId, wasChaoAgent, tie, skipped}` | Nach Voting, vor nächster Phase          | nein                      |
| `game_ended`          | `{winner, reason, players[], aiPostmortem}`     | Runde vorbei                             | nein (bouncet zur Main)   |
| `mini_game_started`   | `{taskId, miniGameId, title, view}`             | Task triggert Mini-Game                  | nein                      |
| `mini_game_state`     | `{taskId, view}`                                | Mini-Game-Tick-Update                    | nein                      |
| `mini_game_completed` | `{taskId, success, reason}`                     | Mini-Game fertig                         | nein                      |
| `error`               | `{code: str, message: str}`                     | Action abgelehnt (z.B. NOT_NEAR_OBJECT)  | teilweise (nur Lobby)     |

Vollständige Beispiele + alle Felder in `docs/PROTOCOL.md`. Bei
Diskrepanzen ist `app/protocol.py` die Wahrheit.

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
ein Stand-Up-Bug-Quelle gewesen. Empfehlung: Read-Wrapper in
`protocol.gd` mit konstantisierten Keys einführen, sobald du mehr als
nur die Demo-Felder konsumierst.

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
      "mapObjects": [...],
      "warRoomId": "war_room"
    }
  }
}
```

**Wichtig:** Im `map`-Objekt steht `doors[]` (Top-Level), nicht
`wallLines`. Siehe §3.6 + §6.3.

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

### 5.1 Welt-Größe + Achsen + WORLD_SCALE

- **Server-Welt:** 4800×3200 Server-Pixel (default-office). Origin
  top-left, Y nach unten. Größere Maps wie `office_complex` haben
  5600×3200 px.
- **Player-Collision-Radius:** 20 Server-Pixel
  (`PLAYER_COLLISION_RADIUS` in `protocol.gd`, mirror zum Server).
- **Task-Interaction-Radius:** 40 Server-Pixel (`TASK_INTERACTION_RADIUS`).
- **WORLD_SCALE = 0.01.** Die 3D-Demo skaliert Server-Pixel auf
  Godot-Welt-Units: 1 Server-Pixel = 0.01 Godot-Units. Eine 4800-Pixel-Map
  ist also 48 Godot-Einheiten breit, was perfekt zur Default-Camera-Range
  und Light-Distance passt.
- **Achsen-Mapping:** Server (x, y) → Godot (x · scale, 0, y · scale).
  Der Y-Down-Server wird auf Godots Z-Achse abgebildet (Tiefe), Höhe
  bleibt 0 außer für Geometrie wie Wände. Helper:

  ```gdscript
  # protocol.gd
  const WORLD_SCALE: float = 0.01

  static func server_to_world(server_x: float, server_y: float) -> Vector3:
      return Vector3(server_x * WORLD_SCALE, 0.0, server_y * WORLD_SCALE)
  ```

  Pro Multiplikation gilt: **immer durch `Protocol.server_to_world` —
  nie inline `* 0.01`**, sonst hast du eine schmerzhafte Suche bei einer
  Scale-Anpassung. `map_builder.gd` und `character.gd` halten diese Regel
  konsequent ein.

- **Wand-Höhe:** `MapBuilder.WALL_HEIGHT = 2.6` Godot-Units. `WALL_THICKNESS
= 0.12`. Die Map-JSON kann `wallHeightM` pro Room als Hint mitliefern;
  die Demo nutzt das (noch) nicht.

### 5.2 Tick-Rate + Interpolation

- Server tickt **20 Hz** → ein `game_state` alle ~50 ms.
- **Client darf NICHT predicten.** Server ist autoritativ.
- **Render-Strategie:** Position-Lerp jedes Frame zum letzten
  `push_target`. Die Demo lerpt mit `POSITION_LERP_SPEED=14` und kommt
  damit auf flüssige Bewegung. Eine gefederte Variante (tatsächliche
  Snapshot-Interpolation mit Prev/Curr-Buffer) ist möglich; die Demo
  hat das nicht ausgeschöpft.
- **`player_input` Throttle:** Bei Input-Change ODER alle 50 ms — was
  zuerst kommt. `input_sender.gd` benutzt einen `_accum`-Akkumulator
  (`SEND_INTERVAL = 0.05`). `_dirty` wird auf Hash-Vergleich des
  Bool-Quadrupels gesetzt.

### 5.3 Reconnect-Verhalten (Tier 4.12 TODO)

- **Server hält Session 30 s nach Disconnect.** Innerhalb dieser Zeit
  reconnecten → `rejoin` (nicht `join_room`) mit gleicher `playerId`.
  Server reaktiviert die Session.
- **Nach 30+ s:** Server antwortet `error` mit Code `REJOIN_NOT_AVAILABLE`
  → Client fällt auf `join_room` zurück.
- **`playerId` persistieren:** Empfohlen `user://player.json`. Nach jedem
  `room_joined` speichern; beim Boot lesen, falls present `rejoin`
  versuchen.
- **Demo-Stand:** `world.gd:_on_disconnected` ruft direkt `_return_to_main`,
  ohne Reconnect-Versuch. `main.gd` zeigt nur "Verbindung verloren". Das
  ist Tier-4.12-Followup.

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

`wallLines` taucht **nicht** im Server-Output auf. Siehe §3.6.

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

Browser ignoriert diese Felder. Die 3D-Demo benutzt nur `color` (Floor-
Tint); die anderen Felder sind ungenutzte Reserven für Tier 4.6+.

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

Browser ignoriert `doorKind`. Godot kann es für eine 3D-Door-Scene
verwenden (Tier 4.3).

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
als Referenz beim Portieren nach GDScript. Migration der Demo-Maps via
[`scripts/migrate_walls_to_doors.py`](../scripts/migrate_walls_to_doors.py).

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

### 6.6 Kind-Catalogue → Asset-Mapping

Server-seitig sind **25 Kinds** definiert (Source of truth:
[`docs/maps.md`](maps.md) + [`static/editor/editor-kinds.js`](../static/editor/editor-kinds.js)).
Die 3D-Demo hat davon nur **drei** als 3D-Mesh gestaged — der Rest ist
Tier-4-Asset-Sourcing-Backlog.

**Aktuell in `godot-3d/assets/` (Tier 4 Übergangs-Stand):**

| Demo-Asset                         | Quelle                     | Verwendet für                                                               |
| ---------------------------------- | -------------------------- | --------------------------------------------------------------------------- |
| `furniture/desk.gltf`              | KayKit Furniture Bits CC0  | Kind `desk`, Meeting-Tisch-Proxy                                            |
| `furniture/chair_desk_A.gltf`      | KayKit Furniture Bits CC0  | Kind `chair_desk` + Meeting-Stuhl                                           |
| `furniture/monitor.gltf`           | KayKit Furniture Bits CC0  | Kind `monitor`, Server-Rack-Proxy                                           |
| `floor/floor_kitchen.gltf`         | KayKit Furniture Bits CC0  | (geladen, aber von `map_builder.gd` ungenutzt — `test_world.gd` benutzt es) |
| `character/kenney_mini/*.glb` (×6) | Kenney Mini Characters CC0 | Player-Character pro Color (Index 0–5)                                      |
| `audio/footsteps/*.ogg` (×5)       | Kenney Impact Sounds CC0   | Carpet-Footsteps                                                            |
| `audio/sting/*.ogg` (×4)           | Kenney Sci-Fi Sounds CC0   | role-reveal, meeting, kill, task-complete                                   |
| `audio/ui/*.ogg` (×2)              | Kenney UI Audio CC0        | click, switch                                                               |

Volle Lizenzlage in [`ASSET_LICENSE.md`](../ASSET_LICENSE.md).

**Backlog Kinds (server-seitig spezifiziert, im 3D-Demo nicht
gestaged):**

| Kind                  | Default-Size | Blocks?  | Empfohlene Quelle (Vorschlag)                                           |
| --------------------- | ------------ | -------- | ----------------------------------------------------------------------- |
| `desk_large`          | 180×80       | yes      | KayKit `desk_large.fbx`                                                 |
| `chair_meeting`       | 50×50        | no       | KayKit `chair_A.fbx`                                                    |
| `keyboard`            | 50×20        | no       | KayKit `keyboard.fbx`                                                   |
| `server_rack`         | 80×100       | yes      | KayKit Space Base `structure_tall.fbx` (proxy) → ggf. Quaternius Sci-Fi |
| `monitoring_panel`    | 200×60       | no       | KayKit `pictureframe_large_A.fbx`                                       |
| `cabinet`             | 80×80        | yes      | KayKit `cabinet_medium.fbx`                                             |
| `meeting_table`       | 480×140      | yes      | KayKit `table_medium_long.fbx` (proxy bisher: 3× desk)                  |
| `presentation_screen` | 200×30       | no       | KayKit `pictureframe_large_B.fbx`                                       |
| `kitchen_counter`     | 320×80       | yes      | KayKit Restaurant `kitchencounter_straight_A.fbx`                       |
| `kitchen_corner`      | 120×120      | yes      | KayKit Restaurant `kitchencounter_innercorner.fbx`                      |
| `kitchen_sink`        | 120×80       | yes      | KayKit Restaurant `kitchencounter_sink.fbx`                             |
| `coffee_machine`      | 90×90        | no       | (Custom oder AI-Sprite — dedizierter MCM-Brand)                         |
| `fridge`              | 100×130      | yes      | KayKit Restaurant `fridge_A.fbx`                                        |
| `plant_cactus`        | 60×60        | no       | KayKit `cactus_medium_A.fbx`                                            |
| `picture_frame`       | 80×30        | no       | KayKit `pictureframe_medium.fbx`                                        |
| `rug`                 | 200×120      | no       | KayKit `rug_rectangle_A.fbx`                                            |
| `crate`               | 70×70        | yes      | KayKit Space Base `cargo_A.fbx`                                         |
| `old_workstation`     | 110×60       | optional | KayKit `desk_decorated.fbx`                                             |
| (… plus 4 weitere)    |              |          | siehe `docs/maps.md`                                                    |

**Hinweise:**

- "Vorschlag" ist nicht final — Sven entscheidet in Tier 4.0.x über
  die Asset-Pipeline. Die KayKit-Pfade sind die "leichten" CC0-Defaults
  während der Übergangsphase.
- Unbekannte Kinds → Fallback im Renderer: neutral grau + Kind-String
  als Label (so macht's der Browser auch).
- Sven hat sich bewusst gegen das KayKit-Dummy entschieden und die
  Kenney Mini Characters genommen, weil sie 6 unterscheidbare
  Mesh-Variants liefern und eigene Animationen mitbringen — siehe
  `ASSET_LICENSE.md`.
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
uv run mypy                      # Python type-check (CI gate)

# Frontend — MUSS v3.3.3 sein (CI enforced exact)
npx --yes prettier@3.3.3 --check 'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md'
npx --yes prettier@3.3.3 --write  'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md'
```

**Gotcha:** Prettier 3.3 vs 4.0 reformatten Markdown-Tabellen unterschiedlich.
**Lokal immer v3.3.3 benutzen** — sonst CI rot.

### 7.4 Setup auf Windows + WSL2

Bei Sven's Setup läuft das Backend in WSL und der Godot-Editor auf Windows:

1. Project öffnen via UNC-Pfad im Godot-Project-Manager:
   `\\wsl.localhost\<DISTRO>\home\<user>\se\mcm\godot-3d\project.godot`
2. Distro-Name: `wsl -l` (Windows-PowerShell) oder `echo $WSL_DISTRO_NAME` (in WSL).
3. Backend-Connect: `localhost:8000` funktioniert nativ (WSL2 forwards). Falls
   nicht, WSL-IP nehmen: `ip addr show eth0` → `inet`-Zeile.

UNC-Pfade sind langsamer als nativer Windows-FS, aber für Editor-Workflow
OK. Bei Editor-Hängern: Repo zusätzlich nach `C:\` clonen, Backend bleibt
in WSL.

### 7.5 Headless-Demo lokal screenshotten

Für Visuals ohne Backend:

```bash
# Aerial overview (gut für Architektur-Screenshots):
godot --path godot-3d --rendering-driver opengl3 \
    --main-scene res://scenes/demo_world.tscn --quit-after 200

# Follow-Cam (in-game-Perspektive):
godot --path godot-3d --rendering-driver opengl3 \
    --main-scene res://scenes/demo_world_followcam.tscn --quit-after 200
```

Beide laden ihre Map (`office_complex.json` bzw. `default.json`) **lokal
aus `godot-3d/maps/`** und benutzen daher das Legacy-`wallLines`-Schema
— Wände rendern hier korrekt, anders als im Live-Server-Connect (§3.6).

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

Es gibt aktuell **keinen** Godot-spezifischen CI-Job. Wenn du einen
Headless-Parse-Check oder Web-Export-Build im CI haben willst, müsstest
du den nachbauen (Godot-Headless-Container, `godot --check-only` o.ä.).
Der frühere `godot-check.sh` aus dem 2D-Spike existiert nicht mehr.

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

## 9. Stolperfallen aus der Demo-Implementation

### 9.1 Godot-Project-Konfiguration

Aktuelle Defaults in `godot-3d/project.godot`:

```ini
[application]
config/name="Merge Conflict Mayhem (Tier 4 Demo)"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.6", "Mobile")

[display]
window/size/viewport_width=1280
window/size/viewport_height=720
window/size/mode=2                          # Maximized
window/subwindows/embed_subwindows=false    # NICHT in den Editor embedden
window/stretch/mode="canvas_items"          # 1280×720 mit dynamischem stretch

[rendering]
renderer/rendering_method="mobile"
anti_aliasing/quality/msaa_3d=2
anti_aliasing/quality/screen_space_aa=1
```

`embed_subwindows=false` ist wichtig: Godot 4 Default embedded das
Run-Window in den Editor und bricht damit `stretch_mode`. Mit dem Setting
oben öffnet F5 ein eigenständiges OS-Fenster.

`renderer/rendering_method="mobile"` ist Absicht — die Forward+ Pipeline
ist in der HTML5-Web-Build noch nicht stabil genug, "mobile" deckt das
visuelle Niveau der Demo problemlos ab.

### 9.2 Kenney-Mini Animation-Loop-Mode

Die Kenney Mini Character `.glb`-Files importieren ihre AnimationPlayer
mit `loop_mode = NONE`. Ohne Workaround friert die Walk-Animation nach
einem Cycle ein. `character.gd:_force_loop()` setzt `loop_mode =
LOOP_LINEAR` zur Laufzeit:

```gdscript
func _force_loop(qualified_name: String) -> void:
    if qualified_name == "" or _anim_player == null:
        return
    var anim: Animation = _anim_player.get_animation(qualified_name)
    if anim != null:
        anim.loop_mode = Animation.LOOP_LINEAR
```

Wenn du eigene `.glb`/`.fbx`-Animationen einbringst und ein "Charakter
hängt fest" siehst, ist das fast immer das Loop-Mode-Problem.

### 9.3 GDScript-Caching

`class_name`-Änderungen, neue Klassen-Definitionen oder Method-Signature-
Changes brauchen einen **Project-Reload** (`Project → Reload Current
Project`) — Editor-Cache ist persistent und vergisst sonst die Änderung.

### 9.4 IPv6-Trap unter Windows

Windows resolved `localhost` zuerst nach `::1` (IPv6). uvicorn bindet per
Default nur IPv4. Godot's `WebSocketPeer` wartet ~50 s auf TCP-Timeout
bevor es auf IPv4 fällt → fühlt sich wie "Connect hängt" an.

**Workarounds:**

- `ws://127.0.0.1:8000/ws` statt `localhost` (Demo-Default in
  `main.gd:_url_field`).
- Oder: `uv run uvicorn app.main:app --host :: --reload` (bindet beides).

### 9.5 Reconnect-Window (TODO in Demo)

Server hält Session 30 s nach Disconnect. Innerhalb der Zeit:

```gdscript
# Pseudocode — noch nicht in der Demo implementiert.
if FileAccess.file_exists("user://player.json"):
    var saved = JSON.parse_string(FileAccess.open("user://player.json", FileAccess.READ).get_as_text())
    _ws.send(Protocol.TYPE_REJOIN, {"roomCode": saved.roomCode, "playerId": saved.playerId})
    # Server antwortet mit room_joined ODER error{code: REJOIN_NOT_AVAILABLE}
```

Bei `REJOIN_NOT_AVAILABLE` → fallback auf `join_room`.

### 9.6 Snapshot-Position-Lerp vs. echte Interpolation

Die Demo lerpt jedes Frame gegen das letzte `push_target` mit
`POSITION_LERP_SPEED=14`. Das ist visuell smooth genug für den Spike,
ist aber **kein** Snapshot-Interpolation im strengen Sinne — eine
gespeicherte Prev/Curr-Kette mit Timestamps + alpha-basiertem `lerp`
würde gegen Server-Hiccups deterministischer sein. Für Tier 4.4-Polish
ist das ein Refactor-Kandidat. Validierte Formel aus dem 2D-Spike
(damals fluid):

```
alpha = clamp((now - curr_snapshot_time) / 50ms + 1.0, 0, 1)
lerped_x = lerp(prev_x, curr_x, alpha)
lerped_y = lerp(prev_y, curr_y, alpha)
```

Wichtig: **lerp zwischen Snapshots, nicht über sie hinaus** — keine
Prediction.

### 9.7 camelCase-Falle

Server schickt `coffeeEnergy`, `releaseProgress`, `isAlive`, `playerId`,
etc. GDScript-Dict-Keys sind case-sensitive — `dict["coffee_energy"]`
liefert silent `null`/Default. Empfehlung: lese-Wrapper in `protocol.gd`
mit allen erwarteten Keys konstantisiert, damit Tippfehler beim
Compile/Parse auffallen, nicht erst zur Laufzeit. Die Demo macht das nur
für Message-Type- und Phase-Strings (`Protocol.TYPE_*`, `Protocol.PHASE_*`).

### 9.8 Pause-Menü process_mode

`pause_menu.gd` setzt `process_mode = Node.PROCESS_MODE_ALWAYS`, sodass
es ESC auch dann verarbeitet, wenn die World später mal pausiert wird.
Im Moment pausieren wir die World gar nicht — falls du `get_tree().paused`
einführst, ist das Verhalten schon vorbereitet.

### 9.9 WSClient-Reparenting beim Phase-Switch

`main.gd:_transition_to_world()` reparented den `WSClient` von der
`Main`-Scene zur frisch instanzierten `World`-Scene. Das passiert in
zwei Schritten: (a) `add_child.call_deferred(world)`, (b) nach
`await get_tree().process_frame` → `remove_child(_ws)` und
`world.add_child(_ws)`. Vor (b) wird das `message_received`-Signal
disconnected, damit Lobby-Code nicht mehr antwortet.

Wenn du die Phase-Logik ausweitest (z.B. World pausieren statt neu
instanziieren), achte darauf den Reparent-Zyklus zu verstehen, sonst
verlierst du Messages oder bekommst doppelte Listeners.

---

## 10. Tier-4-Build-Order (konkrete Slices)

Aus `docs/ROADMAP.md`, leicht angereichert mit Demo-Erfahrungen.
Empfohlene Reihenfolge:

**Bereits durch die 3D-Demo abgedeckt (Architektur, nicht final):**

- **Tier 4.1 (Setup)** — `project.godot` läuft, WS-Connect funktioniert
  lokal, Web-Export-Profile gefüllt + Build-Skript da
  (`scripts/godot-web-export.sh`). Open: EC2-Deploy-Step für den Web-Build
  (Tier 4.13).
- **Tier 4.2 (Lobby)** — `main.gd` deckt Connect, Lobby, Player-Liste,
  Demo-Mode-Checkbox, Start-Button ab. Open: Map-Selection-UI an
  `lobby_state.availableMaps` koppeln + `select_map`-Message verschicken.
- **Tier 4.4 (Character)** — `character.gd` mit Mesh-per-Color, Walk/Idle,
  Footsteps. Open: dezidierte Snapshot-Buffer-Interpolation (siehe §9.6),
  Dead-Spectator-View statt nur Alpha.
- **Tier 4.5 (HUD)** — `hud.gd` mit allen Stats, Timer, Role-Chip,
  Roster. Open: Tween-Animationen bei Stat-Changes, Coffee-Bar aus
  `private_state` (aktuell wird `coffeeLevel` aus `game_state` benutzt
  — das ist Map-weite Stability, nicht Per-Player-Coffee).

**Tier 4.3 (Map-Loader) — partiell, eine echte Aufgabe:**

- Schema-Drift fixen (siehe §3.6): `compute_walls`-Logik portieren,
  Doors aus `doors[]` lesen, MapObjects mit `blocksMovement` als Walls.
- 3D-Door-Frames pro `doorKind` rendern.
- `mapObjects` rendern (Kind-Catalogue, siehe §6.6).
- `_decorate_rooms` ablösen — Möbel kommen aus `mapObjects`, nicht
  aus hartkodierten Room-IDs.

**Neue Slices (von 0):**

1. **Tier 4.6 (2 Tage) — Task-Interaction + Mini-Game-Modals**

   - "Halten zum Bearbeiten" (E) am `taskAnchors[]`-Marker → `task_hold_start` /
     `task_hold_stop`.
   - Server sendet `mini_game_started{taskId, miniGameId, view}` →
     Modal öffnen.
   - 5 Mini-Games existieren (sequencing / pairing / timing /
     filter-by-criterion / subset-by-constraint). Pluggable Modal-UI pro
     `miniGameId`. Browser-Implementation in `static/minigames/` als Referenz.
   - `mini_game_state` updates die UI, `mini_game_completed` schließt sie.
   - Progress-Ring auf dem Char, Completion-VFX.

2. **Tier 4.7 (1 Tag) — Sabotage-Buttons**

   - Aus `private_role.availableSabotages` Liste rendern.
   - Cooldown-Display (Quelle: `private_state.takedownCooldown` /
     analoge Felder).
   - `trigger_sabotage` schicken — Server lehnt ab wenn nicht nahe an
     `objectType` (Tier 2.7 object-binding) → Error-Toast aus
     `error{code, message}`.
   - Repair-Panels für Release: `repair_sabotage` mit F-Hold.

3. **Tier 4.8 (1 Tag) — Voting-Overlay**

   - `game_state.meeting` enthält Phase + Players.
   - Voting-Liste, Countdown, "Skip" Option.
   - `cast_vote{targetPlayerId}` bzw. `skip_vote`.
   - `voting_result` → Toast mit Slide-In.

4. **Tier 4.9 (1 Tag) — Endscreen**

   - `game_ended.players` enthält Per-Player-Stats + Awards (Tier 3.7).
   - `game_ended.aiPostmortem` ist der KI-Text (optional anzeigen).
   - Confetti-Particles wenn Release-Team gewinnt, anders wenn Chaos.
   - Aktuell bouncet die Demo bei `phase=ended` direkt zu `main.tscn` —
     das ist die zu ersetzende Stelle in `world.gd:_apply_state`.

5. **Tier 4.10 (5–8 Tage) — Among-Us-Features**

   - Vents: V cyclet durch verbundene `vents[].connectedTo`, Click TP.
   - Body-Discovery: tote Spieler haben `bodies[]` Eintrag.
   - Report-Button wenn nahe an Body → `report_body{bodyPlayerId}`.
   - Take-Down: Chaos-Animation (rot blinken, slow). `trigger_takedown`.
   - Lights/Comms-VFX: Vignette + UI-disable-States.
   - Spectator-Mode: alive=false → reduced opacity (bereits in Demo) +
     see-through walls + Cam-Modus-Flag.
   - `use_ability` für aktive Rollen.

6. **Tier 4.11 (1 Tag) — Sound-Polish**

   - Footsteps abhängig von `room.floorMaterial` (aktuell: nur Carpet).
   - UI-SFX-Abdeckung (Toast, Slide-In, Stat-Blink).
   - BGM-Auswahl für Lobby + Match (optional, BGM bewusst aus dem Demo
     gelassen).
   - Audio-Bus für Mute/Volume (Tier 1 hatte das schon im Browser).

7. **Tier 4.12 (3–5 Tage) — Polish + Reconnect**

   - Settings-UI (Sound, Graphics, Keybinds).
   - Auto-Reconnect via `user://player.json` (siehe §5.3 / §9.5).
   - Edge-Cases: Sabotage während Meeting, Body-Discovery Race-Conditions,
     Phase-Switch während Modal offen, etc.
   - `test_world.gd` + `test_world.tscn` cleanen (siehe §3.4).

8. **Tier 4.13 (0.5 Tag) — Web-Export-Deploy**
   - Godot Web-Export bauen.
   - Auf `prod-is-lava.dev` unter `/godot/` deployen
     (Backend-`scripts/deploy.sh` erweitern).
   - HTTPS/WSS-Endpoint testen — der Live-Server hat bereits ein
     valides Cert.

**Tier 4 ist erst "done" wenn ein Live-Test mit echten Spielern läuft.**

---

## 11. Erste Schritte für dich

1. **Demo lokal ausprobieren:**

   ```bash
   git clone git@github.com:rausch-tech/merge-commit-mayhem.git
   cd merge-commit-mayhem
   uv sync && uv run uvicorn app.main:app --reload   # Backend in Terminal A
   godot --editor godot-3d                            # Editor in Terminal B
   ```

   F5 → Connect-UI → `ws://127.0.0.1:8000/ws` → Raumcode `DEMO` →
   irgendein Name → "VERBINDEN". Browser-Tab parallel auf
   `http://localhost:8000` mit gleichem Raumcode `DEMO` → ihr seht
   euch gegenseitig in beiden Clients. Movement smooth. Wenn das klappt:
   Setup ist OK.

   **Erwartung:** Die Wände rendern in der 3D-Welt **nicht** (Schema-
   Drift, §3.6). Charaktere, Floors, Furniture, Camera-Follow
   funktionieren.

2. **Headless-Demo screenshotten** (kein Backend nötig):

   ```bash
   godot --path godot-3d --rendering-driver opengl3 \
       --main-scene res://scenes/demo_world_followcam.tscn
   ```

   Hier rendern die Wände **wohl** (Demo-Map ist Legacy-Schema).

3. **§3.6 lesen + fixen.** Die `compute_walls`-Portierung ist die erste
   Slice. Eigener Branch `slice/godot-tier-4-3-walls` unter
   `.worktrees/godot-tier-4-3-walls/`. Migration der lokalen Demo-Maps
   via `scripts/migrate_walls_to_doors.py` parallel.

4. **`docs/PROTOCOL.md` lesen** für die volle Message-Liste mit allen
   Edge-Cases.

5. **`docs/maps.md` lesen** für das Map-Schema inkl. der vollständigen
   Kind-Catalogue-Tabelle (25 Einträge mit Browser-Farben + KayKit-Pfaden).

6. **§10 Build-Order durchgehen** — pro Slice eigener Branch unter
   `slice/godot-tier-4-N-<kurz>` und Worktree unter
   `.worktrees/godot-tier-4-N-<kurz>/`.

7. **Vor jedem Push fragen.** Push triggert CI, CI deployed live.

---

## Kontakt + Stand

- **Repo:** https://github.com/rausch-tech/merge-commit-mayhem
- **Live:** https://prod-is-lava.dev
- **Fragen / Diskussion:** GitHub Issues mit Label `godot` oder `question`.
- Stand dieser Doku: 2026-04-27, nach `slice/tier4-3d-demo`-Merge in
  main (Tier-4-Prototyp) und Editor-Slices 1–5 (Wand-Modell C +
  Editor-UX-Redesign abgeschlossen). Diese v2 ersetzt die v1
  (PR #18) und reflektiert die Realität von `godot-3d/`.
