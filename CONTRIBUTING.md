# Contributing

Hi 👋 — Merge Conflict Mayhem ist ein internes Multiplayer-Game für Tech-Teams, in aktiver Entwicklung. Beiträge sind willkommen.

## Vor dem ersten PR

1. Repo clonen, `uv sync`, `uv run pytest` läuft grün
2. Lokal starten: `uv run uvicorn app.main:app --reload`, http://localhost:8000 öffnen
3. Drei Browser-Tabs joinen denselben Raumcode → das Spiel testen

## Was du beitragen kannst

### Klein (gut für Erst-Beitrag)

| Was | Wo | Hinweis |
|---|---|---|
| **Neuer Eventtext** | (kommt mit Tier 5.4) `event_texts.json` — aktuell hardcoded in Code, sammeln wir aber schon im Roadmap | Witzig, kurz, Tech-Insider-tauglich |
| **Bug-Report** | GitHub Issues | Schritte zur Reproduktion, was erwartet, was gesehen |
| **Doku-Verbesserung** | `docs/*.md` | Tippfehler, unklare Stellen, fehlende Beispiele |
| **Neue Task-Idee** | GitHub Issue mit Label `task-idea` | Titel, Raum, Reward-Vorschlag, lustige Beschreibung |
| **Neue Sabotage-Idee** | GitHub Issue mit Label `sabotage-idea` | Effekt, Cooldown, Repair-Mechanik, lustige Beschreibung |

### Mittel

| Was | Hinweis |
|---|---|
| **Neue Task implementieren** | Definition in `app/game/tasks.py`, Position in `maps/default.json` (`taskAnchors`), Icon-Mapping in `static/sprites.js` |
| **Neue Sabotage implementieren** | Definition in `app/game/sabotages.py`, Effekt-Branch in `GameRoom.apply_sabotage`, Icon in `static/sprites.js` |
| **Neue Map** | `maps/<name>.json` — Schema siehe `docs/maps.md`. Validieren mit `uv run python -c "from app.game.game_map import load_map; print(load_map('maps/<name>.json').name)"` |

### Groß

Größere Features sollten erst als GitHub Issue diskutiert werden — meistens haben wir Meinungen zu Architektur und passendem Tier in der Roadmap.

## Architektur-Leitplanken (nicht-verhandelbar)

- **Backend autoritativ.** Alle Spiellogik in Python. Frontend rendert nur empfangene Snapshots. Kein Game-State im Browser.
- **WebSocket-Protokoll Godot-kompatibel.** JSON, camelCase auf der Wire, keine JS-spezifischen Annahmen.
- **Öffentlicher `game_state` enthält keine Rollen.** Rolle nur via privaten `private_role`-Event an den jeweiligen Spieler.

Wenn dein Beitrag das verletzen würde, lass uns vorher reden.

## Coding-Konventionen

- **Python:** PEP 8 + `ruff` (kommt mit Tier 0.1). Type-Hints überall. Pydantic v2 für Datenmodelle.
- **JavaScript:** Plain ES-Module, `prettier`-Format (kommt mit Tier 0.1). Vermeide externe Frameworks für die aktuelle Slice (kein React, Vue etc.); Godot-Sprint ist die Bühne für mehr Tooling.
- **Tests:** Backend pytest in `tests/`. Frontend-Tests kommen mit Tier 0.3.
- **Branch-Namen:** `slice/<kurztitel>` für ganze Sprint-Schnitte, `feat/<kurz>` für einzelne Features, `fix/<kurz>` für Bugs.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).

## Pull-Request-Flow

1. Issue erstellen oder existierendes finden
2. Branch von `main`: `git checkout -b feat/dein-feature`
3. Code + Tests + ggf. Doku
4. `uv run pytest` muss grün sein
5. PR erstellen, im Body verlinken auf Issue
6. Review-Feedback einarbeiten
7. Merge erfolgt squash, damit `main`-History sauber bleibt

## Wo finde ich was?

```text
app/
├── main.py                 # FastAPI app + WS endpoint + handlers
├── protocol.py             # Pydantic message models (request/response shapes)
├── ws.py                   # ConnectionManager
└── game/
    ├── game_map.py         # Map loading + Pydantic models
    ├── game_room.py        # Per-room state machine + tick + voting
    ├── models.py           # Phase + Player domain types
    ├── room_code.py        # 4-char ABCD generator
    ├── roles.py            # Role assignment
    ├── sabotages.py        # Sabotage definitions + speed constants
    ├── tasks.py            # Task definitions (positions in map JSON)
    ├── voting.py           # Vote tally + chaos-eliminated check
    └── walls.py            # Wall geometry helpers + collision

static/
├── index.html              # Lobby + game screen + endscreen + meeting overlay
├── styles.css              # Dark theme
├── main.js                 # State router, WS handlers
├── ws.js                   # WebSocket wrapper
├── input.js                # Keyboard input
├── render.js               # Canvas, camera, walls, tasks, players
├── hud.js                  # Stat pills + role
├── tasks.js                # Sidebar task list
├── sabotages.js            # Bottom-right chaos buttons
├── meetings.js             # Emergency button + voting overlay + result toast
├── endscreen.js            # End overlay with role reveal
├── audio.js                # Click + task-complete sounds
└── sprites.js              # Spritesheet metadata + drawSprite helper

maps/
└── default.json            # Map data (rooms, walls, doors, spawns, task anchors)

tests/                      # pytest, currently 207 tests
docs/                       # Documentation — start with docs/ROADMAP.md
```

## Fragen?

GitHub Issue mit Label `question` aufmachen, oder direkt Sven (sr@rausch.se) kontaktieren.
