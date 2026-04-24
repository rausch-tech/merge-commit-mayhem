# Vertical Slice: Lobby + Movement

**Projekt:** Merge Conflict Mayhem — Lunch Break Edition
**Datum:** 2026-04-24
**Status:** Design approved, Spec für Review
**Scope:** Erster Schnitt von Sprint 1 (siehe `merge_conflict_mayhem_project/docs/09_first_sprint_plan.md`)

---

## 1. Ziel

Eine lauffähige Ende-zu-Ende-Pipeline zwischen Python-Backend und Browser-Client, die die Architektur-Annahme *„Python entscheidet, der Client zeigt nur an"* beweist — ohne Game-Loop-Mechanik (Tasks, Sabotagen, Win/Lose). Wenn dieser Schnitt steht, bauen alle folgenden Features darauf auf.

## 2. Definition of Done

Drei Browser-Tabs (jeweils ein Spieler) können:

1. denselben Raumcode joinen und sich gegenseitig in der Lobby sehen,
2. warten, bis der Host die Runde startet,
3. ihre eigene Rolle privat angezeigt bekommen (genau einer bekommt `vibe_coder`, die anderen `developer`),
4. sich mit WASD auf einer Top-Down-Map mit sechs Räumen bewegen und die Bewegung der anderen live sehen,
5. einen runterzählenden Timer (600 s) im HUD beobachten.

Die pytest-Suite läuft grün; ein README erklärt `uv run uvicorn app.main:app --reload` und `http://localhost:8000` öffnen.

## 3. Explizit nicht Teil dieser Slice

- Tasks (Hold-Tasks, Fortschrittsbalken, Rewards)
- Sabotagen (CI/CD Rot, Kaffee leer, Mandatory Meeting)
- Globale Spielwerte jenseits des Timers (kein Release Progress, keine Pipeline Stability, kein Coffee, keine Incidents)
- Win/Lose-Logik, Endscreen
- Emergency Meetings, Voting
- Docker-Compose
- Finales Art/UI, Sound, Animationen
- JSON-Config-Loading (`rooms.json`, `tasks.json`, …) — kommt in Sprint 4

## 4. Tech-Stack

| Layer | Wahl | Begründung |
|---|---|---|
| Python | 3.12 | Doc 02 fordert 3.12+ |
| Package-Manager | `uv` | Modern, schnell, kein venv-Dance |
| Web-Framework | FastAPI | in Doc 02 festgelegt |
| WebSocket | FastAPI-native (Starlette) | kein extra Paket nötig |
| Validierung | Pydantic v2 | in Doc 02 festgelegt |
| Frontend | Plain HTML + Canvas + ES-Module JS | Slice braucht keinen Build-Step; Rendering-Primitives sind Rechtecke und Kreise |
| Frontend-Hosting | FastAPI `StaticFiles` | Ein Prozess, eine URL |
| Tests | pytest | in Doc 02 festgelegt |

Bewusst **nicht** in der Slice: Vite, npm, Phaser, isometrische Projektion, Docker-Compose.

## 5. Repo-Struktur

```text
/home/sven-rausch/se/mcm/
  pyproject.toml
  README.md
  .gitignore
  app/
    __init__.py
    main.py
    ws.py
    protocol.py
    game/
      __init__.py
      models.py
      room_code.py
      game_room.py
      rooms.py
      roles.py
  static/
    index.html
    main.js
    ws.js
    render.js
    input.js
    hud.js
    styles.css
  tests/
    __init__.py
    test_room_code.py
    test_roles.py
    test_game_room.py
    test_ws_protocol.py
  docs/
    superpowers/specs/
      2026-04-24-vertical-slice-lobby-movement-design.md
  merge_conflict_mayhem_project/   # Design-Dokumente, bleiben liegen
```

Keine `frontend/`-Ebene: statisches Frontend lebt direkt in `static/`. Wenn später Phaser oder Vite dazukommen, wird `frontend/` als eigenes Subprojekt angelegt.

## 6. Architekturprinzip

Das Backend ist autoritativ (Doc 02, §1). Für diese Slice heißt das konkret:

- **Positionen** werden serverseitig gehalten und berechnet. Der Client schickt nur Input-State und rendert die empfangenen Positionen.
- **Phase-Wechsel** (Lobby → Playing) geschieht ausschließlich serverseitig.
- **Rollen** werden serverseitig verteilt, pro Spieler privat übermittelt und nie im öffentlichen `game_state` erwähnt.
- **Timer** läuft auf dem Server; der Client rendert den empfangenen Wert ohne eigene Interpolation.

Der Client darf:

- letzten `game_state`-Snapshot + UI-Flags (eigene `playerId`, `isHost`, eigene Rolle) halten,
- Canvas zeichnen, HUD aktualisieren, Inputs einlesen.

Kein Client-Side Prediction, keine lokale Timer-Logik, kein lokaler State für andere Spieler.

## 7. WebSocket-Protokoll (Slice-Subset)

Format: `{"type": string, "payload": object}`, UTF-8 JSON. Feldnamen auf der Wire sind camelCase (kongruent zu Doc 03); Python-seitig snake_case mit Pydantic-Aliassen.

### Client → Server

| Type | Payload |
|---|---|
| `join_room` | `{roomCode: string, playerName: string}` |
| `start_game` | `{}` |
| `player_input` | `{up: bool, down: bool, left: bool, right: bool}` |

### Server → Client

| Type | Payload | Adressat |
|---|---|---|
| `room_joined` | `{roomCode, playerId, isHost}` | joinender Spieler |
| `lobby_state` | `{roomCode, players: [{id, name, color, isHost}]}` | alle im Raum |
| `private_role` | `{role, team, description}` | jeweiliger Spieler (einmal beim Spielstart) |
| `game_state` | `{phase, remainingSeconds, players: [{id, name, x, y, color}]}` | alle im Raum, 20 Hz während `playing` |
| `error` | `{code, message}` | individuell |

### Regeln

- `player_input` ist **State, nicht Event**. Der Server speichert den letzten Zustand pro Spieler; Tick-Loop wendet ihn an. Kein Ausdrücken von „Keyup/Keydown".
- Der öffentliche `game_state` enthält niemals `role` oder `team`.
- Bei WebSocket-Close wird der Spieler aus dem Raum entfernt; das `lobby_state`- oder `game_state`-Broadcast folgt sofort. Wenn der Host geht, wird der älteste verbliebene Spieler neuer Host. Leerer Raum wird aus der Registry entfernt.
- Reconnect im Client: bei Close 3 s warten, neu verbinden. Session wird nicht wiederhergestellt — der Spieler muss neu joinen. Akzeptabel für die Slice.

### Welt-Koordinaten

- Origin oben-links.
- Map 900 × 400 px (3 Räume × 300 px breit × 2 Reihen à 200 px hoch).
- Player-Radius 12 px, Bewegungsgeschwindigkeit 120 px/s → 6 px pro Tick.
- Raum-Layout in `app/game/rooms.py` als Konstante (Wechsel auf JSON-Config in Sprint 4 laut Roadmap).

### Fehlercodes (minimal)

| Code | Bedingung |
|---|---|
| `ROOM_FULL` | Join bei > 6 Spielern im Raum |
| `NAME_TAKEN` | Name ist bereits in diesem Raum vergeben |
| `NOT_HOST` | `start_game` von Non-Host |
| `WRONG_PHASE` | z. B. `start_game` während `playing` |
| `NOT_ENOUGH_PLAYERS` | `start_game` mit < 2 Spielern |

## 8. Backend-Komponenten

### `app/main.py`

- FastAPI-App mit `lifespan`-Contextmanager, der den 20-Hz-Tick-Task startet/stoppt.
- WebSocket-Route `/ws`. Wichtig: **vor** dem StaticFiles-Mount registriert, damit Routing nicht kollidiert.
- `StaticFiles(directory="static", html=True)` auf `/`.
- Globale `GameRegistry` (dict `room_code → GameRoom`).

### `app/ws.py` — `ConnectionManager`

- `connect(ws, player_id, room_code)` — akzeptiert die Verbindung, merkt sich Mapping.
- `disconnect(ws)` — findet `(player_id, room_code)`, delegiert an `GameRoom.remove_player`.
- `send_to_player(player_id, msg)` — JSON-Serialisierung via Pydantic `model_dump_json(by_alias=True)`.
- `broadcast(room_code, msg)` — parallel an alle Verbindungen im Raum.

### `app/protocol.py` — Pydantic-Modelle v2

- `IncomingMessage` als `Annotated[Union[...], Discriminator("type")]` über `JoinRoom | StartGame | PlayerInput`.
- Outgoing-Modelle: `RoomJoined | LobbyState | PrivateRole | GameState | Error`.
- Alle Modelle nutzen `alias_generator=to_camel`, `populate_by_name=True` für snake↔camel-Mapping.

### `app/game/models.py` — Domain

```python
class Phase(str, Enum):
    LOBBY = "lobby"
    PLAYING = "playing"

class InputState(BaseModel):
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False

class Player(BaseModel):
    id: str
    name: str
    color: str
    is_host: bool = False
    role: str | None = None
    team: str | None = None
    x: float = 0.0
    y: float = 0.0
    input_state: InputState = InputState()
    joined_at: float  # monotonic, für Host-Transfer
```

### `app/game/room_code.py`

- Alphabet `A–Z` ohne `I`, `O` (Verwechslungsgefahr mit `1`, `0`).
- 4 Zeichen, reiner `random.choices`.
- `generate_unique(existing: set[str]) -> str` — versucht max. 32 mal, sonst `RuntimeError` (bei 24^4 ≈ 330 k möglichen Codes realistisch nie erreicht).

### `app/game/game_room.py` — `GameRoom`

- `code: str`, `phase: Phase`, `players: dict[player_id, Player]`, `remaining_seconds: float`, `started_at: float | None`.
- `add_player(name) -> Player` — prüft auf vollen Raum und doppelten Namen; wenn Raum leer → neuer Spieler wird Host; Farbe aus fester 6er-Palette, erste freie.
- `remove_player(player_id)` — entfernt Spieler; wenn Host ging, ältester verbliebener wird Host (via `joined_at`).
- `start()` — nur wenn Host triggert, Phase `LOBBY`, min. 2 Spieler; weist Rollen via `roles.assign` zu; setzt Spieler-Startpositionen auf eine einfache Grid-Verteilung im Open Space; Phase → `PLAYING`; `remaining_seconds = 600`.
- `apply_input(player_id, input_state)` — aktualisiert `Player.input_state`, kein sofortiger Effekt.
- `tick(dt: float)` — nur wenn Phase `PLAYING`:
  - Für jeden Spieler: Geschwindigkeitsvektor aus Input-State, Position-Delta `v * dt`, Clamping an `0..900 × 0..400`.
  - `remaining_seconds -= dt` (Floor beim Broadcasten).
- `public_state() -> GameStateMsg` — ohne `role`/`team`/`input_state`.
- `private_role_for(player_id) -> PrivateRoleMsg` — aus `Player.role`/`Player.team`.

### `app/game/rooms.py`

Konstante `ROOM_LAYOUT` mit 6 Einträgen, jeweils `{id, title, x, y, width, height, color}`. Farben aus Doc 07 (Open Space neutral-blau, Server Room blau, Meeting Room lila, Kitchen orange, Legacy Basement giftgrün, War Room cyan). Wird beim `lobby_state`- oder `game_state`-Broadcast **nicht** mitgesendet — der Client hat die gleiche Konstante. Im Sprint 4 wandert das Layout nach `rooms.json` und wird geschickt.

### `app/game/roles.py`

```python
def assign(
    player_ids: list[str],
    rng: random.Random | None = None,
) -> dict[str, tuple[str, str, str]]:
    """
    Gibt für jeden player_id ein (role, team, description)-Tupel zurück.
    Für die Slice: genau ein vibe_coder, Rest developer.
    Funktioniert für 2..6 Spieler.
    rng optional injizierbar für deterministische Tests.
    """
```

Zufall via `rng.shuffle` (Default: `random.SystemRandom()`). Rollen-Descriptions für die Slice hardcoded; in Sprint 3/4 aus `roles.json`.

### Tick-Loop

```python
async def tick_loop(registry, manager):
    dt = 0.05
    while True:
        await asyncio.sleep(dt)
        for room in list(registry.active_rooms()):
            if room.phase == Phase.PLAYING:
                room.tick(dt)
                await manager.broadcast(room.code, room.public_state())
                # Win-Conditions kommen in späterem Sprint
```

Broadcast passiert jeden Tick, auch ohne State-Change. Bei 3 Spielern × 20 Hz × ~400 Byte = ~24 KB/s total — irrelevant. Delta-Broadcasting kommt, wenn nötig.

## 9. Frontend-Komponenten

### `static/index.html`

Zwei Screens im selben Dokument, per CSS-Klasse `hidden` ein/aus:

- `#lobby-screen`: Input `playerName`, Input `roomCode`, `Join`-Button, Spielerliste, `Start`-Button (nur sichtbar wenn `isHost`).
- `#game-screen`: `<canvas id="game-canvas" width="900" height="400">`, HUD-Leiste oben.

### `static/ws.js`

- `connect()` öffnet `new WebSocket(\`ws://${location.host}/ws\`)`.
- `send(type, payload)` wrapt auf `{type, payload}` und `JSON.stringify`.
- `onmessage` dispatched via registrierte Handler `handlers[type] = fn(payload)`.
- Bei Close: 3 s warten, neu verbinden. Session-Restore nicht implementiert.

### `static/main.js`

- Hält `clientState = {phase, playerId, isHost, ownRole, roomCode, players: []}`.
- Handler für `room_joined`, `lobby_state`, `private_role`, `game_state`, `error`.
- Bei `phase === "playing"` zum ersten Mal: Lobby ausblenden, Game-Screen einblenden, Render-Loop starten.

### `static/input.js`

- `keydown`/`keyup` für W/A/S/D → lokaler `inputState`.
- Sendet `player_input` **edge-triggered** (nur bei Änderung).
- `window.blur` → alle Keys `false` und einmal senden.

### `static/render.js`

- `requestAnimationFrame`-Loop, ~60 FPS.
- Zeichnet Räume aus einer clientseitigen `ROOM_LAYOUT`-Konstante, die das Backend-Layout 1:1 spiegelt (gleiche IDs, Koordinaten, Farben). Solange das Layout im Backend eine Konstante ist, synchronisiert „manuell halten" genügt; sobald es in Sprint 4 nach `rooms.json` wandert, wird es im Protokoll mitgeschickt.
- Zeichnet alle Spieler aus `clientState.lastGameState.players` als farbige Kreise + Name darüber.
- Eigener Spieler bekommt einen extra Outline-Ring, damit man sich findet.
- Keine Extrapolation/Interpolation zwischen Snapshots.

### `static/hud.js`

- Timer (`remainingSeconds` → `mm:ss`).
- Eigene Rolle (aus `private_role`, einmal nach Start gesetzt).
- Spielerliste mit farbigen Punkten.

### `static/styles.css`

Dark Navy Background (`#14182a`), Canvas mittig, HUD als Flex-Row darüber. ~100 Zeilen, kein Framework.

## 10. Test-Plan

Datei-Mapping:

| Datei | Fälle |
|---|---|
| `tests/test_room_code.py` | Generator produziert 4-Zeichen-Code aus erlaubtem Alphabet; `generate_unique` meidet Kollisionen; Alphabet enthält weder `I` noch `O` |
| `tests/test_roles.py` | Für N ∈ {2,3,4,5,6}: genau ein `vibe_coder`, Rest `developer`; Rollen→Team-Mapping (`vibe_coder`→`chaos_agents`, `developer`→`release_team`); Seed-Stabilität bei festem Seed |
| `tests/test_game_room.py` | `add_player` setzt ersten als Host, weitere nicht; `NAME_TAKEN` bei Duplikat; `remove_player(host)` → ältester Nicht-Host wird Host; Input → Position-Delta nach einem Tick; Clamping an Map-Grenzen; Timer zählt korrekt runter; `start()` nur bei min. 2 Spielern und nur vom Host |
| `tests/test_ws_protocol.py` | `TestClient`-Roundtrip: zwei Verbindungen joinen denselben Raumcode; beide bekommen `lobby_state` mit beiden Spielern; `start_game` vom Non-Host → `Error{code: NOT_HOST}`; vom Host → beide bekommen `private_role` + beide beginnen `game_state` mit `phase=playing` zu empfangen |

**Nicht getestet (manuell im Browser verifiziert):**

- Canvas-Zeichnen
- JS-WebSocket-Client
- Drei-Tab-Test (DoD-Verifikation)
- Tastatur-Focus-Loss-Verhalten

## 11. Konkrete Design-Entscheidungen

| Entscheidung | Wahl | Alternative | Begründung |
|---|---|---|---|
| Frontend-Rendering | Plain Canvas / Vanilla JS | Phaser, Iso-Projektion | Slice-Ziel ist Pipeline-Beweis, nicht Optik. Wechsel zu Phaser später = nur Renderer-Austausch. |
| Dev-Setup | Ein Prozess (FastAPI serviert Static) | Vite + Backend getrennt | Ohne Bundling-Bedarf ist Vite Overhead. |
| Tick-Frequenz | 20 Hz | 10 Hz, 60 Hz | 20 Hz ist WASD-smooth und für 3 Spieler irrelevante Last. |
| Input-Semantik | State | Event | Idempotent, kein Key-Sticking bei Packet-Loss. |
| Player-Kollisionen | Ignorieren | Kreis-Push | In der Slice egal; später als eigene Entscheidung. |
| Tick-Broadcast | Jeden Tick | Nur bei Change | ~24 KB/s bei 3 Spielern, nicht relevant. |
| Client-Side Prediction | Keine | Lokale Extrapolation | Fügen wir hinzu, wenn Lag sichtbar wird. |
| HUD-Werte | Nur was das Backend hat | Platzhalter-Balken | Ehrlich statt kosmetisch. |
| Min. Spieler zum Starten | 2 | 4 (Doc-MVP) | Slice-Test mit 2 Tabs möglich; 4 Spieler als Produkt-Gate kommt später. |
| Host-Transfer | Ältester verbliebener | Manuelle Wahl, Random | Einfach und intuitiv. |
| Farbpalette | Feste 6er aus Doc 07 | Dynamisch zufällig | Gute Unterscheidbarkeit; max. 6 Spieler matcht MVP-Zielzahl. |
| Raum-Layout | Konstante im Code | JSON-Config | Doc 08 sagt Sprint 4 für Config. |

## 12. Risiken

1. **WebSocket-Routing bei StaticFiles-Mount** — WebSocket-Route muss vor dem Mount registriert werden. Wird beim ersten `python -m uvicorn`-Smoke-Test verifiziert; Fallback ist ein Subpath-Mount für Static (`/app/`) + explizite `/`-Route.
2. **Pydantic-Camel-Alias-Roundtrip** — Doc 03 nutzt camelCase. Wir verifizieren in den Protokoll-Tests, dass ein-/ausgehende Nachrichten den camelCase-Vertrag einhalten.
3. **Browser-Tab-Sharing** — `playerId` wird serverseitig vergeben (UUID4), Client hält sie nur in Memory, damit drei Tabs drei Spieler sind.

## 13. Nächste Schritte nach dieser Slice

(Nur zur Orientierung, nicht Teil dieses Spec-Scopes.)

1. **Game-Loop-Mechanik**: Tasks (Hold-Task im passenden Raum, Fortschrittsbalken), Release-Progress-Berechnung.
2. **Sabotagen**: CI/CD Rot, Kaffee leer, Mandatory Meeting — sichtbar für alle, Cooldowns im Backend.
3. **Win/Lose + Endscreen**: `release_progress >= 100`, `pipeline_stability <= 0`, Timer 0.
4. **Voting (Sprint 2)**: Emergency Meeting im War Room, 60-s-Voting.
5. **Polish (Sprint 3)**: Eventfeed-Texte, Awards, Insider-Gags.
6. **Config-Driven (Sprint 4)**: Tasks/Sabotagen/Rollen/Räume aus JSON.
7. **Godot-Client (Sprint 5)**: gleiches WebSocket-Protokoll, nur Rendering-Layer tauschen.
