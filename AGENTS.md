# AGENTS.md — Merge Conflict Mayhem

> Single source of truth for any AI agent (Claude Code, Cursor, Aider,
> Codex, Continue, Copilot agents …) working on this repo. Read this first.
> Claude Code users: see also `CLAUDE.md` for Claude-specific notes; everything
> here applies regardless of agent.

---

## 0. TL;DR

- **Was:** Multiplayer-Social-Deduction-Spiel für Tech-Teams. Among-Us im
  Software-Büro. Release-Team gegen geheime Chaos-Agenten. ~10 Min/Runde.
- **Stack:** Python 3.12 + FastAPI + Pydantic v2 + WebSockets · Vanilla
  HTML/CSS/JS + Canvas · keine Build-Pipeline · `uv` als Python-Runner.
- **Architektur-Nordstern:** **Python entscheidet, der Client zeigt nur an.**
  Backend ist autoritativ für ALLEN State. Client sendet Inputs, rendert
  Snapshots. Wenn eine Idee Spiellogik in den Client drückt → zurück.
- **Live-Server:** https://game.prod-is-lava.dev (auto-deployed auf jedem
  `main`-Push via GitHub Actions).
- **Repo:** https://github.com/rausch-tech/merge-commit-mayhem · `origin/main`.
- **Roadmap:** `docs/ROADMAP.md` ist DIE Wahrheit über Reihenfolge + Stand.

---

## 1. Repository Layout

```
.
├── AGENTS.md                # diese Datei
├── CLAUDE.md                # Claude-Code-spezifische Notizen
├── CONTRIBUTING.md          # Onboarding für Menschen
├── README.md                # Repo-Quickstart
├── pyproject.toml           # uv + ruff + pytest config
├── package.json             # nur fuer Vitest/Prettier (kein npm-Build)
├── app/                     # Backend (FastAPI + asyncio)
│   ├── main.py              #   Routes + WS-Dispatcher + Tick-Loop
│   ├── protocol.py          #   Pydantic-Modelle für Wire-Format
│   ├── ws.py                #   ConnectionManager
│   └── game/                #   Game-Logik (server-authoritative)
│       ├── game_room.py     #     Room-State, Tick, Tasks, Sabotage, Vote
│       ├── game_map.py      #     Map-Loader + Pydantic-Map-Modelle
│       ├── models.py        #     Player, Phase, InputState
│       ├── roles.py         #     RoleDefinition + assign() + Speed-Multipliers
│       ├── tasks.py         #     TaskDefinition + Konstanten (Radien)
│       ├── sabotages.py     #     SabotageDefinition + Object-Type-Mapping
│       ├── ai_flavor.py     #     LLM-styled Eventfeed-Texte + Postmortem
│       ├── voting.py        #     Tally + Skip-Resolution
│       ├── walls.py         #     Wand-Linien → Rechtecke + Kollision
│       ├── room_code.py     #     4-Buchstaben-Codes
│       └── minigames/       #     Plugin-Framework + 5 Mini-Games
├── static/                  # Frontend (vanilla, served by FastAPI)
│   ├── landing.html         #   /
│   ├── spielprinzip.html    #   /spielprinzip (lange Doku-Subpage)
│   ├── index.html           #   /play (eigentliches Spiel)
│   ├── editor/editor.html   #   /editor (Map-Editor)
│   ├── main.js              #   Game-Client-Entry
│   ├── render.js            #   Canvas-Renderer
│   ├── ws.js                #   WebSocket-Client
│   ├── hud.js · tasks.js · sabotages.js · meetings.js · endscreen.js · ...
│   ├── role_intro.js        #   Role-Intro-Modal (Tier 3.5)
│   ├── minigames/           #   Mini-Game-Plugins (1:1 zu Server-Plugins)
│   ├── images/screenshots/  #   Doku-Screenshots fuer /spielprinzip
│   └── styles.css · landing.css · spielprinzip.css
├── tests/                   # pytest (471 grün)
│   └── conftest.py          #   snap_to_object_for_sabotage Helper
├── tests-frontend/          # vitest (37 grün, happy-dom)
├── maps/                    # Map-JSONs (default.json + small.json)
├── docs/                    # Doku-Block (Single Source of Truth)
│   ├── ROADMAP.md           #   Tier 0–7 mit Status (LESEN!)
│   ├── PROTOCOL.md          #   vollstaendiger WS-Vertrag
│   ├── ARCHITECTURE.md      #   Backend high-level
│   ├── GAME_OVERVIEW.md     #   shareable Markdown-Tour
│   ├── GODOT_HANDOFF.md     #   Onboarding für externe Godot-Devs (Tier-4-Client)
│   ├── GODOT-DEV-WITH-CLAUDE.md  # Workflow-Quick-Ref für KI-Agenten am Godot-Client
│   ├── DEPLOY.md · DEV.md · maps.md · README.md
├── godot-3d/                # Godot 4.6 Client (Tier-4)
│   ├── project.godot        #   Mobile-Renderer + canvas_items stretch + MSAA 4x
│   ├── scripts/             #   GDScripts (character, world, hud, …)
│   ├── scenes/              #   .tscn-Files (mostly Root-Node + Script-Anhang)
│   ├── assets/              #   KayKit + Kenney CC0 (siehe ASSET_LICENSE.md)
│   └── maps/                #   Lokal-Kopien für Demo-Szenen ohne Backend
├── scripts/                 # deploy.sh + perf_baseline.py + godot-check.sh
├── .worktrees/              # Git-Worktrees (in .gitignore)
└── merge_conflict_mayhem_project/  # historisches Design-Paket + externes Feedback
```

---

## 2. Tooling & Commands

**Verbindlich.** Nicht durch `pip`, `poetry`, `venv`, `npm install` etc. ersetzen.

```bash
# Run dev server (hot reload, Port 8000)
uv run uvicorn app.main:app --reload

# Backend tests
uv run pytest                             # alle 471
uv run pytest tests/test_sabotages.py     # einzelne Datei
uv run pytest -k "personal_task"          # by name match

# Frontend tests
npx vitest run                            # alle 37 (happy-dom)
npx vitest                                # watch mode

# Lint + Format (Backend)
uv run ruff check .
uv run ruff check . --fix
uv run ruff format .
uv run ruff format --check .

# Lint + Format (Frontend) — VERSION GENAU SO PINNEN, CI nutzt 3.3.3
npx --yes prettier@3.3.3 --check 'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md' 'CONTRIBUTING.md' 'README.md'
npx --yes prettier@3.3.3 --write  'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md' 'CONTRIBUTING.md' 'README.md'

# Performance baseline
PYTHONPATH=. uv run python scripts/perf_baseline.py

# Deploy lokal triggern (CI macht das automatisch auf main-Push)
bash scripts/deploy.sh

# Godot-Client (Tier 4)
scripts/godot-check.sh                    # GDScript-Parse-Check (auch in CI)
godot --headless --path godot-3d --import # Asset-Import nach Pull

# Headless-Render einer Demo-Szene (für Visual-Tests)
xvfb-run --auto-servernum --server-args="-screen 0 1280x720x24" \
  godot --path godot-3d --rendering-driver opengl3 \
  --scene res://scenes/demo_world_followcam.tscn \
  --write-movie /tmp/godot-shots/frame.png \
  --quit-after 60 --fixed-fps 20
# Frame ansehen: Read /tmp/godot-shots/frame00000050.png
# Vollständiger Workflow-Guide: docs/GODOT-DEV-WITH-CLAUDE.md
```

**Stand der Tests** (2026-04-27): **471 Backend** + **37 Frontend** grün.
Wenn dein Patch das ändert, fix die Tests im selben Commit.

---

## 3. CI Gates (`.github/workflows/`)

Sechs Jobs laufen parallel auf jedem Push/PR:

1. **`pytest (+ coverage gate)`** — `uv run pytest -q --cov=app/game --cov-fail-under=88`.
   Muss grün sein. Coverage-Threshold ist Slice 6 von v1-Hardening; aktueller
   Stand 92 % auf `app/game/`, 88 % als CI-Floor.
2. **`vitest`** — `npx vitest run`. Muss grün sein.
3. **`ruff (lint + format)`** — `uv run ruff check .` + `uv run ruff format --check .`.
4. **`mypy`** — `uv run mypy`. Läuft gegen `app/` (siehe `[tool.mypy]` in
   `pyproject.toml`). Moderate Konfiguration: `strict_optional`,
   `warn_unreachable`, `warn_unused_ignores`. Mini-Game-Plugins sind dict-shape-
   heavy und haben einen eigenen Override mit gelockerten Codes.
5. **`prettier`** — `npx --yes prettier@3.3.3 ...`. **Version-Pin ist kritisch** —
   Prettier 3.3 vs 4.0 formatieren Markdown-Tabellen unterschiedlich. Lokal
   wenn du Prettier hast, immer mit `prettier@3.3.3` aufrufen, sonst CI rot.
6. **`deploy to EC2`** — läuft nur auf `main`-Push, _nachdem_ die anderen
   Gates grün sind. Tarball + scp + ssh-restart auf `t4g.nano` in
   eu-central-1. Braucht GitHub-Secrets `EC2_SSH_KEY` und `EC2_HOST`.

Nach dem Deploy ist der neue Build live unter https://game.prod-is-lava.dev.

---

## 4. Architecture-Cheat-Sheet

### Server-authoritative Pattern

- **Alles** läuft serverseitig: Movement, Task-Progress, Coffee-Decay,
  Sabotage-Cooldowns, Win-Conditions, Voting, Mini-Game-State.
- Client schickt `player_input`, `task_hold_start`, `trigger_sabotage`,
  `cast_vote`, `mini_game_input` etc. → Server validiert → Server tickt → Server
  broadcastet `game_state`.
- Client rendert nur den letzten Snapshot. Keine Prediction.
- Tick-Frequenz: **20 Hz** (50 ms). p99 Tick-Compute = 0.6 ms bei 12 Spielern.

### WebSocket-Wire-Format

- JSON, **camelCase** auf der Wire. Pydantic mappt snake_case ↔ camelCase via
  `alias_generator=to_camel`.
- Frame: `{ "type": "<msg_type>", "payload": { ... } }`.
- Validierung: Pydantic `_IncomingEnvelope` mit Discriminator. Unbekannte Typen
  → `error`-Frame mit `BAD_MESSAGE`.
- **Per-Viewer-Broadcasts** (`public_state_for(viewer_id)`):
  - Alive viewers sehen nur alive players (Spectator-Mode hidden).
  - Geister sehen alle.
  - **`private_role` und `private_state`** gehen NUR an den Owner — leaken
    sonst Rollen. NEVER public-broadcast.

### Map-Datenmodell

- Maps liegen als JSON unter `maps/*.json`, Pydantic validiert beim Server-
  Start. Default-Map: `maps/default.json` (4800×3200 px, 6 Räume).
- Rooms · WallLines (mit Door-Cuts) · SpawnPoints · TaskAnchors (mit
  `objectType` für Tier 2.7) · SabotagePanels · Vents · `warRoomId`.
- Editor unter `/editor` produziert dasselbe JSON-Schema (siehe `docs/maps.md`).

### Mini-Game-Framework (Tier 3)

- Plugin-Pattern: `init_state(seed)` · `handle_input(state, action, params)` ·
  `is_complete(state)` · `public_view(state)`. Server-side
  `app/game/minigames/`, Client-side `static/minigames/`. **Beide müssen
  übereinstimmen** — der Server ist Master, Client darf nicht „cheaten".
- Aktuell 5 Mechanik-Patterns: Sequencing, Pairing, Timing,
  Filter-by-Criterion, Subset-by-Constraint.
- 5 von 8 Tasks haben Mini-Games. Die anderen 3 (`review_pr`,
  `calm_legacy_service`, `write_release_notes`) laufen über Hold-E (Tier 3.7
  offen).

---

## 5. Game-Mechanics-Cheat-Sheet

### Phasen

`LOBBY → PLAYING → MEETING → PLAYING → … → ENDED → LOBBY` (via Host).

### Rollen (Tier 3.5)

**Release-Team (5):** Developer, DevOps Engineer, QA Lead, Scrum Master,
Caffeine Collector. Jede mit `strength_categories`, `weak_categories`,
Coffee-Profil und meist einer aktiven Fähigkeit (1×/Runde).

**Chaos-Agenten (3):** Vibe Coder (AI/Code), Rogue Consultant (Process/Scope),
Shadow Admin (Infra). Unterscheiden sich nur in `available_sabotages`.

**Singleton-Caps:** DevOps, QA, Scrum Master, Caffeine Collector — max. 1×
pro Runde. Lobby-Wunschrolle wird best-effort respektiert; Chaos-Wunsch
wird silently ignoriert (Geheimhaltung).

### Persönliche Tasks (Tier 3.5)

- Jeder Spieler kriegt **3 Tasks** beim Rundenstart in `assigned_task_ids`.
- Release: 2 strength-passend + 1 random. Chaos: 3 plausible Fake-Tasks.
- Server validiert NICHT, ob du nur eigene Tasks machst — andere Tasks gehen
  auch, nur langsamer (kein Hard Sackgassen-Lock).

### Coffee-Energy (Tier 3.5)

- Jeder Spieler hat eigene `coffee_energy` (0..max). Decay 1.4/s ×
  `role.coffee_decay_modifier`.
- < 15 → Speed-Penalty + Movement-Slowdown. ≥ 80 → Task-Bonus.
- Refill: `refill_coffee`-Task (eigene + Splash für Nachbarn) · Coffee-Run-
  Ability (Caffeine Collector) · `coffee_outage`-Sabotage halbiert alle.
- Globaler `coffee_level` ist davon unabhängig — Team-Indicator + Sabotage-
  Trigger für Slack-Down-blockiert-State.

### Sabotagen (Tier 2.7 rework)

8 Sabotagen, jede mit `trigger_object_types`-Tuple. Chaos triggert nur an
einem Task-Anchor mit passendem `object_type` (60 px Radius). Same Anchor wie
Release-Task → Beobachter sehen nur „X arbeitet am Terminal", nicht ob das
Repair, Task oder Sabotage ist.

| Sabotage              | Object-Type                          | Trigger-Ort (Default-Map)            |
| --------------------- | ------------------------------------ | ------------------------------------ |
| ci_cd_red             | `ci_console`                         | Server Room (an `repair_deployment`) |
| flaky_tests           | `qa_terminal`                        | Open Space (an `fix_unit_tests`)     |
| merge_conflict_storm  | `git_terminal`                       | Open Space (an `review_pr`)          |
| coffee_outage         | `coffee_machine`                     | Kitchen (an `refill_coffee`)         |
| mandatory_meeting     | `meeting_screen`                     | Meeting Room (an `reduce_scope`)     |
| fake_customer_request | `release_console` / `meeting_screen` | Meeting Room                         |
| lights_out            | `monitoring_panel`                   | Server Room (an `analyze_logs`)      |
| comms_outage          | `monitoring_panel` / `ci_console`    | Server Room                          |

`lights_out` und `comms_outage` haben zusätzlich Repair-Panels (50 px).

### Force-Reboot, Vents, Bodies, Voting

- **Force-Reboot:** Chaos in 40 px → Target `is_alive=false`, Body bleibt,
  Cooldown 25 s. War-Room ist Sicherheitszone (kein Force-Reboot).
- **Vents:** Chaos-only Teleport, V-Taste cycelt Verbindungen. 50 px Reach.
- **Body-Discovery:** Lebender in 40 px → Report-Button → Meeting.
- **Meeting:** 60 s, Reporter + Body-Ort + letzte 6 Events im Context-Block.
  Eine Stimme pro Lebendem (re-vote überschreibt). Skip möglich. Geister voten
  nicht.

### Endscreen (Tier 3.7)

`final_summary` mit `perPlayer` (Tasks, Sabotagen, Coffee-Final, Ability-
Used, Alive), `awards` (Pipeline Whisperer, Vibe of the Round, Held der
Kaffeemaschine, Most Suspicious Innocent), `postmortem` (LLM-styled Text aus
`ai_flavor.generate_postmortem`).

---

## 6. Conventions (verbindlich)

### Sprache

- **Kommunikation Deutsch**, knapp. Multiple-Choice-Fragen wenn das die
  Antwort beschleunigt.
- **Code-Comments + Docstrings Englisch** (Codebase ist gemischt — neue
  Dateien folgen dem Stil drumherum).

### Branches & Commits

- **Branches:** `slice/<kurz>` für Roadmap-Slices, `feat/<kurz>` für Features,
  `fix/<kurz>` für Bugfixes. `main` ist Live-Branch (auto-deploy).
- **Worktrees** unter `.worktrees/<branch-basename>/` — per `.gitignore`
  ausgeschlossen.
- **Commit-Style:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`,
  `test:`, `refactor:`). Body in Hereing per `git commit -m "$(cat <<'EOF' …)"`.
- **Co-author-Trailer:** Bei AI-generierten Commits  
  `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`  
  am Ende des Commit-Bodies.

### Push & Deploy

- **Niemals ungefragt pushen.** Auch nicht bei zuvor klar erteilter
  Zustimmung für andere Actions. Push ist Deploy → Live-Effekt → User
  bestätigt jedes Mal.
- Direkt auf `main` committen ist OK für Doku/Polish; größere Slices kriegen
  einen eigenen Branch + PR.

### Style-Regeln

- **Keine Emojis** in Code, Doku oder Commit-Messages, ausser explizit
  angefragt.
- **Keine neuen Markdown-Files** ohne expliziten Auftrag (kein
  spontanes `NOTES.md` etc.).
- **Default-write no comments**. Comments nur wenn das WHY non-obvious ist
  (Hidden Constraint, Workaround, surprise factor) — nicht für WHAT.
- **Existing files editen** statt neue zu erstellen.

### Testing

- **Test-Dateien für jedes neue Verhalten.** Wenn du Server-Logik anfasst,
  muss ein pytest-Test rein. Frontend-Visuals sind grenzwertig — Smoke-Coverage
  reicht oft.
- **Failing-Test-First** ist ideal aber nicht vorgeschrieben.
- **`tests/conftest.py`** hat `snap_to_object_for_sabotage(room, pid, sab_id)` —
  benutze das in jedem Test, der `apply_sabotage` aufruft, sonst NOT_NEAR_OBJECT.

---

## 7. Common Gotchas (gelernt durch Schmerz)

### `prettier@3.3.3` ist gepinnt

Lokal frisches `npx prettier` zieht v4 → reformat-diff bei Markdown-Tabellen
→ CI rot. **Immer mit `--yes prettier@3.3.3` aufrufen** (siehe Commands oben).

### `coffee_level` (global) vs. `coffee_energy` (per-Player)

Beide existieren parallel. `coffee_level` ist Team-Stat (HUD-Pille „Coffee
100 %", Slack-Down-Block-Trigger). `coffee_energy` ist per-Spieler (HUD-Pille
„Du 87", Speed-Modifier-Driver). Verwechseln → falscher Effekt.

### `private_role` / `private_state` LEAKEN sonst

Diese zwei Frame-Typen gehen NUR an den Owner. Jeder Code-Pfad, der `await
manager.broadcast(...)` mit RoleInfo aufruft, ist ein Bug. Es gibt
`manager.send_to_player(room, pid, ...)` für per-Owner-Sends.

### Sabotage-Console wurde **verworfen**

Tier 2.7 hatte erst dedizierte `SabotageConsole`-Anchors auf der Map. Verworfen
(too obvious — wer davorsteht, ist sofort verdächtig). **Aktuelles Modell:**
`object_type` auf Task-Anchors, Sabotage-Definition listet
`trigger_object_types`-Tuple. Code-Spuren der alten Console sind alle weg —
keine Rückfälle bauen.

### Test-Cascade beim Sabotage-Trigger

Vor Tier 2.7 waren `apply_sabotage`-Tests location-agnostisch. Jetzt müssen
sie den Chaos-Spieler an den passenden Anchor snappen. Helper:
`snap_to_object_for_sabotage(room, chaos_id, "ci_cd_red")`. Wer das vergisst
→ 33 Tests fallen kaskadiert mit `NOT_NEAR_OBJECT`. Nicht den Helper
auf-locken — wir wollen den Gate-Test grün halten.

### Map ohne `objectType` → Legacy-Path

Backwards-compat: Maps mit _zero_ typed Anchors fallen zur „from-anywhere"-
Sabotage zurück. Editor-Maps (im Browser gebaut) brechen also nicht.
`_map_has_typed_anchors()` ist die Gate-Funktion.

### Movement-Speed-Multiplier ist nur Penalty

`movement_speed_multiplier(role, coffee)` gibt **1.0 bei voller Coffee** zurück
— kein Movement-Bonus. Sonst kippten alle Speed-Tests. Task-Speed darf
boost-en (`task_speed_multiplier`), Movement nicht.

### `coffeeEnergy` ist Float, `coffee_level` ist Int

Pydantic-Modelle entsprechend. `Player.coffee_energy: float`, room-level
`coffee_level: int`. Beim Mischen passieren sonst Type-Errors in Tests.

### Mehrere Mini-Game-Sessions pro Spieler verboten

`active_mini_games[player_id]` ist `dict[str, MiniGameSession]` mit Single-
Owner. Wer ein zweites startet → `MINI_GAME_ALREADY_ACTIVE`-Error. Ist
Absicht — die Modal-UI wäre sonst overlapped.

---

## 8. WebSocket-Protocol-Quick-Ref

Vollständige Spec in `docs/PROTOCOL.md`. Hier das Wesentliche zum schnell-
Andocken:

### Incoming (Client → Server)

`join_room` · `rejoin` · `start_game` · `player_input` · `task_hold_start` ·
`task_hold_stop` · `trigger_sabotage` · `repair_sabotage` · `use_vent` ·
`trigger_takedown` · `report_body` · `call_emergency_meeting` · `cast_vote` ·
`skip_vote` · `select_map` · `return_to_lobby` · `leave_room` · `abort_round` ·
`mini_game_input` · `set_preferred_role` · `use_ability`

### Outgoing (Server → Client)

`room_joined` · `lobby_state` · `private_role` (Owner-only) · `private_state`
(Owner-only, jeden Tick) · `game_state` (per-Viewer-filtered) · `voting_result`
· `game_ended` · `mini_game_started` (Owner-only) · `mini_game_state` (Owner-
only) · `mini_game_completed` (Owner-only) · `error`

### Wichtige Felder im `game_state.payload`

- `phase` (`lobby`/`playing`/`meeting`/`ended`)
- `players[]` (per-Viewer gefiltert — Geister hidden für Lebende)
- `tasks[]` mit `objectType`, `category`
- `sabotages[]` mit `triggerObjectTypes`, `triggerAnchors`, `objectHint`
- `meeting.context` (Reporter, Body, Recent-Events) während MEETING
- `finalSummary` (Per-Player-Stats, Awards, Postmortem) während ENDED

### Error-Codes (subset)

`NOT_HOST` · `WRONG_PHASE` · `NOT_ENOUGH_PLAYERS` · `NOT_CHAOS_AGENT` ·
`NOT_NEAR_OBJECT` · `NOT_IN_WAR_ROOM` · `COMMS_DOWN` · `SABOTAGE_ON_COOLDOWN` ·
`PLAYER_ELIMINATED` · `NO_ABILITY` · `ABILITY_ALREADY_USED` ·
`MINI_GAME_ALREADY_ACTIVE` · `BAD_MESSAGE`

---

## 9. Workflow für neue Slices

1. **Roadmap lesen** (`docs/ROADMAP.md`). Welcher Slice ist next? Nichts
   eigenmächtig vorziehen.
2. **Branch:** `git checkout -b slice/<kurztitel>` (oder `feat/`).
3. **Worktree** unter `.worktrees/<branch>/` wenn parallel zu anderem Slice
   gearbeitet wird.
4. **Spec/Plan** nur für Slices > 1 Tag Aufwand. Kleinere → direkt los.
5. **Implementieren.** TDD wenn sinnvoll. Tests grün halten oder fixen.
6. **Lint + Format** lokal: `uv run ruff check . && uv run ruff format .` +
   `npx --yes prettier@3.3.3 --write …`.
7. **Tests:** `uv run pytest && npx vitest run`.
8. **Commit** mit conventional Prefix + Co-Author-Trailer wenn AI-generiert.
9. **Pause vor Push.** User fragen: "OK zum Push und Live-Deploy?".
10. **Nach Merge auf main:** Live-Smoke per `curl https://game.prod-is-lava.dev/`.
    Roadmap-Eintrag updaten (`✅ done`).

---

## 10. Doku-Index — wo was steht

| Datei                                                                   | Was drin steht                                            |
| ----------------------------------------------------------------------- | --------------------------------------------------------- |
| `AGENTS.md`                                                             | DIESE DATEI — Agent-Onboarding                            |
| `CLAUDE.md`                                                             | Claude-Code-spezifische Notizen, kürzer                   |
| `README.md` (root)                                                      | Repo-Quickstart für Menschen                              |
| `CONTRIBUTING.md` (root)                                                | Wie ein Mensch mitcodet                                   |
| `docs/ROADMAP.md`                                                       | Tier 0–7 mit Status, Slice-IDs, Stand                     |
| `docs/PROTOCOL.md`                                                      | Vollständiger WebSocket-Vertrag                           |
| `docs/ARCHITECTURE.md`                                                  | Backend-High-Level + Performance                          |
| `docs/GAME_OVERVIEW.md`                                                 | Shareable Markdown-Tour des Spiels                        |
| `docs/maps.md`                                                          | Map-JSON-Schema                                           |
| `docs/DEPLOY.md`                                                        | Deploy-Workflow + Secrets                                 |
| `docs/DEV.md`                                                           | Lokale Entwicklung                                        |
| `static/spielprinzip.html`                                              | Web-Variante der Game-Tour mit Screenshots                |
| `merge_conflict_mayhem_project/merge_conflict_mayhem_gesamtfeedback.md` | Externes Brainstorming-Feedback (Tier 3.5/3.6/3.7-Quelle) |
| `merge_conflict_mayhem_project/`                                        | Historisches Design-Paket — Inspiration, nicht aktuell    |

---

## 11. Anti-Patterns (don't)

- **Spiellogik in den Client legen.** Wenn der Renderer entscheidet ob ein
  Take-Down erlaubt ist → Bug. Server gates everything.
- **Globalen Game-State im Client mutieren.** `state.players` ist read-only
  Snapshot. Bei Bedarf Server-Action senden.
- **Public-broadcast von `private_role`/`private_state`.** Leak.
- **Map-Anchors hardcoden.** Positions kommen IMMER aus `maps/*.json` via
  `task_position_map`. Editor muss den Code mitführen können.
- **Feature-Flags / Backwards-Compat-Shims für eigenes Code-Aging.** Wenn ein
  Field unused ist, weg damit. Keine `// removed`-Comments hinterlassen.
- **Specs/Plans für triviale Slices schreiben.** Roadmap reicht; Spec/Plan
  nur > 1 Tag Aufwand und nur in `docs/superpowers/specs/` (vom Brainstorming-
  Skill produziert).
- **Eigenmächtig pushen.** Auch nicht bei vorheriger Zustimmung. Jedes Push =
  jedes Mal nachfragen.
- **`pip` / `poetry` / venv.** Wir benutzen `uv`. Punkt.
- **Emojis im Output / Code / Doku.** Ausser explizit angefragt.

---

## 12. Quick-Sanity-Check beim Onboarden

Wenn du diesen Repo zum ersten Mal anfasst, lauf:

```bash
uv run pytest                # 471 grün?
npx vitest run               # 37 grün?
uv run ruff check .          # All checks passed?
npx --yes prettier@3.3.3 --check 'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md' 'CONTRIBUTING.md' 'README.md'
                             # All matched files use Prettier code style?
```

Wenn alle vier grün sind, bist du synchron. Sonst — _das_ zuerst fixen, nicht
einen Patch oben drauf.

---

**Stand: 2026-04-27 · Tier 0–3.7 deployed · v8 chaos roles (Vibe Coder, Rogue
Consultant, Shadow Admin) · 5 release roles · 8 Sabotagen object-bound · 5/8
Tasks mit Mini-Game · Live: https://game.prod-is-lava.dev**
