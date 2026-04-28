# Contributing

Hi — Merge Conflict Mayhem ist ein Multiplayer-Game für Tech-Teams, in aktiver Entwicklung. Beiträge sind willkommen.

Bevor du loslegst:

- Du solltest mit dem [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) einverstanden sein.
- Sicherheitslücken bitte **nicht** als public Issue, sondern privat über [`SECURITY.md`](SECURITY.md).

## Vor dem ersten PR

1. Repo clonen, `uv sync`, `uv run pytest` läuft grün
2. Lokal starten: `uv run uvicorn app.main:app --reload`, http://localhost:8000 öffnen
3. Drei Browser-Tabs joinen denselben Raumcode → das Spiel testen

## Was du beitragen kannst

### Klein (gut für Erst-Beitrag)

| Was                    | Wo                                            | Hinweis                                                             |
| ---------------------- | --------------------------------------------- | ------------------------------------------------------------------- |
| **Bug-Report**         | GitHub Issues                                 | Schritte zur Reproduktion, was erwartet, was gesehen                |
| **Doku-Verbesserung**  | `docs/*.md`                                   | Tippfehler, unklare Stellen, fehlende Beispiele                     |
| **Neue Task-Idee**     | GitHub Issue mit Label `task-idea`            | Titel, Raum, Reward-Vorschlag, lustige Beschreibung                 |
| **Neue Sabotage-Idee** | GitHub Issue mit Label `sabotage-idea`        | Effekt, Cooldown, Repair-Mechanik, lustige Beschreibung             |
| **Neue Map**           | `maps/<name>.json` — Schema in `docs/maps.md` | Im Browser-Editor (`/editor`) erstellen + speichern, dann committen |

### Mittel

| Was                              | Hinweis                                                                                                                                                                                                                          |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Neue Task implementieren**     | Schritt-für-Schritt in [`docs/HOWTO-MINIGAME.md`](docs/HOWTO-MINIGAME.md) (wenn die Task ein Mini-Game braucht) — Definition in `app/game/tasks.py`, Position als MapObject im Map-JSON, Mini-Game-Plugin server- + clientseitig |
| **Neue Sabotage implementieren** | Schritt-für-Schritt in [`docs/HOWTO-SABOTAGE.md`](docs/HOWTO-SABOTAGE.md) — Definition in `app/game/sabotages.py`, `object_type`-Binding, Effekt im Controller                                                                   |
| **Neue Rolle**                   | Schritt-für-Schritt in [`docs/HOWTO-ROLE.md`](docs/HOWTO-ROLE.md) — `RoleDefinition`, Coffee-Profil, optional Ability + Singleton-Cap                                                                                            |
| **Beitrag zum Godot-3D-Client**  | Onboarding in [`docs/GODOT_HANDOFF.md`](docs/GODOT_HANDOFF.md) — Stack, Architektur, Asset-Pipeline. Code unter `godot-3d/`                                                                                                      |

### Groß

Größere Features sollten erst als GitHub Issue diskutiert werden — meistens haben wir Meinungen zu Architektur und passendem Tier in der Roadmap.

## Architektur-Leitplanken (nicht-verhandelbar)

- **Backend autoritativ.** Alle Spiellogik in Python. Frontend (Browser oder Godot) rendert nur empfangene Snapshots. Kein Game-State im Client.
- **WebSocket-Protokoll client-agnostisch.** JSON, camelCase auf der Wire. Browser- und Godot-Client teilen sich denselben Server.
- **Öffentlicher `game_state` enthält keine Rollen.** Rolle nur via privaten `private_role`-Event an den jeweiligen Spieler.

Wenn dein Beitrag das verletzen würde, lass uns vorher reden.

## Coding-Konventionen

- **Python:** PEP 8 + `ruff` (lint + format). Type-Hints überall. Pydantic v2 für Datenmodelle. mypy als CI-Gate.
- **JavaScript:** Plain ES-Module, `prettier@3.3.3`-Format. Vermeide externe Frameworks (kein React, Vue etc.); der Browser-Client soll lesbar bleiben ohne Build-Pipeline.
- **GDScript (Godot):** Stand der Konventionen siehe [`docs/GODOT_HANDOFF.md`](docs/GODOT_HANDOFF.md). `scripts/godot-check.sh` parsed alle GDScripts headless als CI-Gate.
- **Tests:** Backend pytest in `tests/` (~714). Frontend vitest in `tests-frontend/` (~109). Beide CI-Gates.
- **Branch-Namen:** `slice/<kurztitel>` für Sprint-Schnitte, `feat/<kurz>` für Features, `fix/<kurz>` für Bugs.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).

## Pull-Request-Flow

1. Issue erstellen oder existierendes finden
2. Branch von `main`: `git checkout -b feat/dein-feature`
3. Code + Tests + ggf. Doku
4. `uv run pytest && npx vitest run` muss grün sein
5. PR erstellen, im Body verlinken auf Issue
6. Review-Feedback einarbeiten
7. Merge erfolgt squash, damit `main`-History sauber bleibt

## Wo finde ich was?

Vollständiges Repo-Layout in [`AGENTS.md`](AGENTS.md) Section 1. Kurz-Pointer:

```text
app/                # Backend (FastAPI + asyncio)
├── main.py · protocol.py · ws.py
└── game/
    ├── game_room.py · runtime.py · models.py
    ├── controllers/   # tasks · sabotages · meeting · mini_game · movement
    ├── bots/          # AI-NPCs (manager + pathfinding + decision)
    ├── llm.py         # LLMClient Protocol (Anthropic + Local-OpenAI)
    ├── minigames/     # 8 Mini-Game-Plugins (server-side)
    └── …

static/             # Browser-Frontend (vanilla, served by FastAPI)
├── index.html · main.js · render.js · ws.js · …
├── editor/         # Map-Editor (2D-Canvas + Three.js-3D-Vorschau)
└── minigames/      # 8 Mini-Game-Plugins (client-side)

godot-3d/           # Godot-3D-Client (Tier 4)
├── scripts/        # GDScripts
└── scenes/         # .tscn-Files

maps/               # Map-JSONs + kinds.json (Single Source of Truth)
tests/              # pytest
tests-frontend/     # vitest
docs/               # Doku — start mit docs/ROADMAP.md
```

## Lizenz für Beiträge

By contributing to this project, you agree that your contributions are licensed
under the same license as the part of the project you contribute to:

- **Code contributions** are licensed under the MIT License (see [`LICENSE`](LICENSE)).
- **Asset contributions** (artwork, sprites, audio, branding) are subject to the
  Asset License (see [`ASSET_LICENSE.md`](ASSET_LICENSE.md)) unless otherwise
  agreed in writing.

## Fragen?

GitHub Issue mit Label `question` aufmachen.
