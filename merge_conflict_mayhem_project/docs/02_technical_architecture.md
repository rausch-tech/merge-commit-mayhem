# 02 – Technical Architecture

## Ziel

Das Spiel soll schnell als Browser-Prototyp spielbar sein, aber später ohne kompletten Rewrite auf einen Godot-Client wechseln können.

Daher gilt:

> Python entscheidet. Der Client zeigt nur an.

---

# 1. Architekturprinzip

Das Backend ist autoritativ.

Der Server verwaltet:

- Räume
- Spieler
- Rollen
- Game State
- Timer
- Tasks
- Sabotagen
- Meetings
- Voting
- Win/Lose-Logik

Der Client verwaltet:

- Rendering
- Eingaben
- UI-Anzeige
- Animationen
- lokale Sounds

Der Client darf nicht final entscheiden:

- ob ein Task abgeschlossen wurde
- ob eine Sabotage gültig war
- ob ein Spieler gewonnen hat
- welche Rolle ein Spieler hat
- ob ein Spieler entfernt wird

---

# 2. Zielarchitektur

```text
                 ┌────────────────────────────┐
                 │        Python Backend       │
                 │ FastAPI / WebSockets        │
                 │                            │
                 │ - Lobby                     │
                 │ - Rollenverteilung          │
                 │ - Game State                │
                 │ - Tasks                     │
                 │ - Sabotagen                 │
                 │ - Voting                    │
                 │ - Win/Lose                  │
                 └─────────────┬──────────────┘
                               │
                 WebSocket JSON Protocol
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                             │
┌───────▼────────┐                           ┌────────▼────────┐
│ Browser Client │                           │   Godot Client   │
│ JS / Phaser    │                           │ GDScript         │
│ MVP / Intranet │                           │ schöner Client   │
└────────────────┘                           └─────────────────┘
```

---

# 3. Stack

## Backend

- Python 3.12+
- FastAPI
- WebSockets
- Pydantic
- Uvicorn
- pytest

## MVP-Client

- Vite
- Plain JavaScript
- Phaser oder Canvas
- HTML/CSS

## Späterer Client

- Godot
- GDScript
- WebSocketPeer
- gleiches JSON-Protokoll

## Deployment

- Docker Compose
- Backend-Service
- Frontend als statischer Build
- optional Reverse Proxy im Intranet

---

# 4. Repository-Struktur

```text
merge-conflict-mayhem/
  README.md
  docker-compose.yml
  .gitignore

  docs/
    game-design.md
    protocol.md
    roadmap.md
    contribution-guide.md

  backend/
    pyproject.toml
    app/
      main.py
      websocket.py
      game/
        models.py
        game_room.py
        game_state.py
        roles.py
        tasks.py
        sabotages.py
        voting.py
        tick_loop.py
      config/
        rooms.json
        tasks.json
        roles.json
        sabotages.json
        event_texts.json
      tests/
        test_roles.py
        test_tasks.py
        test_sabotages.py
        test_win_conditions.py

  frontend/
    package.json
    index.html
    src/
      main.js
      websocket.js
      game/
        scene.js
        renderer.js
        input.js
        ui.js
      styles.css
```

---

# 5. Backend-Komponenten

## GameRoom

Verwaltet eine einzelne Spielrunde:

- room_code
- players
- phase
- game_state
- tasks
- sabotages
- votes
- timer

## GameState

Zentraler serialisierbarer Zustand.

## Tick Loop

Läuft z. B. 10–20 Mal pro Sekunde.

Aufgaben:

- Inputs anwenden
- Positionen aktualisieren
- Task-Fortschritt berechnen
- Sabotageeffekte verwalten
- Timer reduzieren
- Win Conditions prüfen
- GameState broadcasten

## WebSocket Manager

Verwaltet:

- Verbindungen
- Join/Leave
- Nachrichtenrouting
- Broadcasts
- private Nachrichten pro Spieler

---

# 6. Datenmodelle

## Player

```python
class Player(BaseModel):
    id: str
    name: str
    color: str
    role: str | None = None
    team: str | None = None
    is_alive: bool = True
    x: float
    y: float
    current_room: str | None = None
    emergency_meetings_left: int = 1
    completed_tasks: int = 0
    triggered_sabotages: int = 0
```

## GameState

```python
class GameState(BaseModel):
    room_code: str
    phase: Literal["lobby", "playing", "meeting", "voting", "ended"]
    players: list[Player]
    tasks: list[Task]
    release_progress: int = 0
    pipeline_stability: int = 100
    incident_count: int = 0
    coffee_level: int = 100
    remaining_seconds: int = 600
    winner: str | None = None
    events: list[str] = []
```

## Task

```python
class Task(BaseModel):
    id: str
    title: str
    room: str
    type: Literal["hold", "sequence", "choice"]
    progress: float = 0
    required_seconds: int = 5
    is_completed: bool = False
    release_progress_reward: int = 0
    pipeline_stability_reward: int = 0
    incident_delta: int = 0
```

## Sabotage

```python
class Sabotage(BaseModel):
    id: str
    title: str
    room: str
    effect: str
    cooldown_seconds: int
    is_active: bool = False
```

---

# 7. Godot-Migration

Die spätere Migration zu Godot ist kein Neustart, wenn folgende Regeln gelten:

- Das Protokoll bleibt stabil.
- Der Server bleibt autoritativ.
- Keine zentrale Logik liegt nur im Browser.
- Der Browser-Client ist nur Referenzclient.
- Godot implementiert dieselben WebSocket-Events.

Was bleibt gleich:

- Backend
- GameState
- Rollenlogik
- Tasks
- Sabotagen
- Voting
- Win Conditions
- Config-Dateien

Was sich ändert:

- Rendering
- Animationen
- Sound
- UI
- Map-Darstellung

---

# 8. Config-Driven Design

Möglichst viele Inhalte sollten aus JSON/YAML kommen:

- rooms.json
- tasks.json
- roles.json
- sabotages.json
- event_texts.json

Das macht Pull Requests für Mitarbeitende einfach.

---

# 9. Beispiel rooms.json

```json
[
  {
    "id": "open_space",
    "title": "Open Space",
    "x": 0,
    "y": 0,
    "width": 300,
    "height": 200
  },
  {
    "id": "server_room",
    "title": "Serverraum",
    "x": 0,
    "y": 200,
    "width": 300,
    "height": 200
  }
]
```

---

# 10. Beispiel tasks.json

```json
[
  {
    "id": "fix_unit_tests",
    "title": "Unit Tests fixen",
    "room": "open_space",
    "type": "hold",
    "requiredSeconds": 5,
    "releaseProgressReward": 10
  },
  {
    "id": "refill_coffee",
    "title": "Kaffee auffüllen",
    "room": "kitchen",
    "type": "hold",
    "requiredSeconds": 4,
    "effect": {
      "coffeeLevel": 100
    }
  }
]
```

