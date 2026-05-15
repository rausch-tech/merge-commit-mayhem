# Changelog

Tier-by-Tier History für Merge Conflict Mayhem. Detail-Commits sind im git log;
dieser File listet die größeren Meilensteine, die ein Außenstehender mit dem
aktuellen Repo-Stand verbinden sollte. Format lose an
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) angelehnt.

## [Unreleased]

### Polish nach Public-Flip (2026-05-15)

- README mit Cover-Hero, 5 Badges (CI, License, Python, Godot, Live-URL), Stack-Tabelle
- Doku-Refactor: Tier-Klammern aus HOW-TOs und Schema-Docs entfernt, ROADMAP komprimiert (433 → 160 Zeilen mit `<details>`-Block für Done-Tiers)
- OG-Meta-Tags + Twitter-Card in `landing.html`, `spielprinzip.html`, `index.html` für Social-Sharing
- GitHub-Topics, custom Labels (`godot`, `backend`, `frontend`, `maps`, `ai-bots`), Pinned Welcome-Issue
- Branch Protection auf `main` mit 6 required checks und PR-Workflow
- 10 Dependabot-Bumps gemergt (actions/checkout, setup-node, download-/upload-artifact, setup-uv, cache, mypy 1→2, pytest-cov, hypothesis, happy-dom, vitest 2→4, pydantic 2.13.4)

## [2026-05-15] — Public Release

- Repository als public sichtbar unter https://github.com/rausch-tech/merge-commit-mayhem
- `LICENSE` (MIT) + `ASSET_LICENSE.md` + `SECURITY.md` + `CODE_OF_CONDUCT.md` + `CONTRIBUTING.md`
- Issue-Templates (Bug, Feature-Request), PR-Template, Dependabot-Config
- Gitleaks-Scan über 271 Commits clean; dokumentierter False-Positive im diff_review Mini-Game

## [Tier 4 — Godot-3D-Client] — 2026-04-28

Vollständige Feature-Parität zum Browser-Client im Godot-3D-Client erreicht.
Web-Export läuft auf https://prod-is-lava.dev/godot/ als WebAssembly-Build.

### Added

- **Lobby:** Map-Auswahl-Dropdown, Rollen-Präferenz, AI-NPC-Buttons (890b8e2)
- **Map-Render:** 3D-Geometrie via `compute_walls`-Port, KayKit-Meshes für alle 25 Kinds (f04662a)
- **Character-Movement:** Lerp-Speed 35 + Snap-on-Pushback bei Wall-Clamp/Idle-Stuck (f7e30b7, cfef514)
- **HUD:** Personal-Task-Panel mit ★, Coffee-Bar mit Pulse <15, Active-Ability-Button, Eventfeed, Role-Intro-Modal (b6ffb66, a069e53)
- **Mini-Games:** Alle 8 Tasks mit Modal-Plugins (sprint_trim, test_suite_repair, cable_pairing, coffee_pour, log_filter, diff_review, stability_balance, release_notes) (2cd619c, 170daf0, a4a8b88)
- **Sabotage-Strip:** 8 Icons, Cooldown-Ring, Object-Binding-Range-Check (5d13462)
- **Meeting + Voting:** Modal mit Context-Block, Voting-Buttons, Result-Toast mit Last-Words (b324722)
- **Endscreen:** Awards-Liste, Per-Player-Stats, AI-Postmortem, Confetti (72f279d)
- **Among-Us-Features:** Take-Down + Body-Report + Vents (8a8c078), Lights-Vignette + Comms-Disable (8a0f6b4), Ghost-Banner für Spectator (8ab8591)
- **Polish:** Camera-Shake bei Kill, Timer-Pulse <60s, Phase-Transition-Banner + Confetti, 3D-Body-Marker, Kill-Flash, Vent-VFX (f9fbe1a, f68a6bc, e1f0e3a)
- **Auto-Reconnect:** `playerId`-Persist in `user://player.json` + REJOIN-Fallback bei WS-Disconnect (71ab9c4)
- **Web-Export-Deploy:** GHA-Job `web-export` + EC2-Tarball-Integration, FastAPI mountet `/godot/` mit COOP/COEP-Headern (880bf7c)

## [Tier 3.9 — AI-Integration] — 2026-04-28

### Added

- LLM-Provider-Abstraction (`app/game/llm.py`) mit `AnthropicClient` (Cloud) + `LocalOpenAIClient` (Ollama-compatible)
- AI-NPC-Bots als Lobby-Filler mit Heuristik-Fallback (b558a2e, PR #35)
- ThreadPoolExecutor für non-blocking LLM-Calls nach Live-Incident (PR #38)
- Hard-3s-Timeout pro Call, automatic fallback wenn Provider abwesend oder langsam
- Curated Bot-Namen (Bot-Promptly, Bot-Cursor-Sr., Bot-StackOverflow, Bot-Junior, …)

## [Tier 3.8 — Map-Authoring-Toolchain] — 2026-04-27

### Added

- Browser-Editor unter `/editor` mit 2D-Canvas + Three.js-3D-Vorschau side-by-side
- Server-Save-API (`GET/PUT /api/maps`) mit Pydantic-Validate + atomic write
- `maps/kinds.json` als Single Source of Truth für MapObject-Kinds (d3c0934, PRs #29/#30/#36)
- Pydantic-Validator auf `MapObject.kind` gegen Registry, alle 4 Konsumenten lesen dynamisch via `GET /api/kinds`
- KayKit-Asset-Pipeline + 22 KayKit-Meshes vendored unter `godot-3d/assets/` (f04662a)
- `office_complex` mit 390 MapObjects, `datacenter` mit 147 (24d1a6d, f8b7c5a)
- Prozedurale Floor-Texturen pro `floorMaterial`, Door-Frames als sichtbare Lintel-Geometrie
- `docs/ASSET_SPEC.md` als Konventions-Dokument für die Asset-Pipeline

## [Tier 3.7 — Endscreen-Story + Closing-Mini-Games + Metriken]

### Added

- Endscreen mit Awards (Pipeline Whisperer, Vibe of the Round, Held der Kaffeemaschine, Most Suspicious Innocent) + Per-Player-Stats
- AI-Postmortem-Generator (`ai_flavor.generate_postmortem`) als LLM-styled `<pre>`-Block
- Restliche 3 Mini-Games: `diff_review` (Multi-Select-by-Criterion), `stability_balance` (Rotating-Correction), `release_notes` (Click-to-Cycle-Sort)
- JSONL-Metrik-Export pro Tag (`MCM_METRICS_DIR`), `GET /api/metrics` Aggregations-Endpoint (PR #34)

## [Tier 3.6 — Meeting-Kontext + AI-Flavor]

### Added

- Meeting-Modal mit Context-Block (Reporter, Body+Room, RecentEvents-Snapshot)
- `app/game/ai_flavor.py` mit LLM-styled Pools für Sabotage-Events, Repair, Body-Found, Vote-Kick, Last-Words
- `voting_result.lastWords` Flavor-Line aus team-spezifischen Pools
- **Sabotage-Object-Binding als Tier-2.7-rework** — dedizierte Console rausgeworfen, stattdessen jede Sabotage an Task-Anchor mit passendem `objectType` gebunden (Ambiguität für Beobachter)

## [Tier 3.5 — Persona-Layer]

### Added

- 5 Release-Rollen (Developer, DevOps Engineer, QA Lead, Scrum Master, Caffeine Collector) mit Stärken/Schwächen-Multipliern und individuellen Coffee-Profilen
- 3 Chaos-Rollen (Vibe Coder, Rogue Consultant, Shadow Admin) mit unterschiedlichen `available_sabotages`
- **Coffee-Energy pro Spieler** mit Decay/Speed-Penalty (<15)/Task-Bonus (≥80)
- Persönliche Task-Backlogs (3 pro Spieler, 2 strength-passend + 1 random)
- Active Abilities 1×/Runde (Rollback +18 Pipeline, Coffee Run +35 Coffee an Nachbarn, Standup ruft Meeting, Reproduce Bug flagged Last-Activity)
- Role-Intro-Modal beim Phase-Wechsel lobby→playing mit 30s Auto-Dismiss
- Lobby-Rollen-Präferenz mit Singleton-Caps (best-effort respektiert)
- Task-Speed-Multiplier serverseitig (Movement-Penalty nur bei niedrigem Coffee, Tests bleiben stabil)

## [Tier 3 — Mini-Games (Task-Tiefe)]

### Added

- Mini-Game-Framework: Server-authoritative Plugin-Architektur (`app/game/minigames/`), WS-Messages (`mini_game_started`/`_input`/`_state`/`_completed`), Client-side pluggable Modal
- 6 von 8 Tasks mit eigenen Mini-Games: Sequencing (test_suite_repair), Pairing (cable_pairing), Timing (coffee_pour), Filter (log_filter), Subset-by-Constraint (reduce_scope)

## [Tier 2 — Among-Us-Features]

### Added

- Take-Down-Mechanik (Force-Reboot): Chaos kann Spieler im Proximity-Radius eliminieren, Cooldown ~25s, kein Take-Down im War Room
- Body-Discovery + Report: Bodies bleiben sichtbar bis entdeckt, Report-Button triggert Emergency Meeting
- Vents: Chaos kann zwischen vordefinierten Punkten teleportieren (Map-JSON `vents[]`)
- Lights-Sabotage mit radial-Vignette + Repair an Electrical Panel
- Comms-Sabotage (Sidebar-blank + Sabotage-Buttons disabled) + Repair an Comms Panel
- Spectator-Mode für eliminierte Spieler (frei beweglich, sehen andere Geister, helfen weiter mit Tasks aber kein Vote)
- **Sabotage-Object-Binding** — jede Sabotage triggert nur in 60px-Reichweite eines Task-Anchors mit passendem `objectType`

## [Tier 1 — Core-Mechaniken komplettieren]

### Added

- Canvas-Vollbild, Map 4800×3200 (vorher 2400×1600), Timer 720s → 900s
- Eventfeed (Live-Log rechts mit info/warn/error-Severity)
- Incidents-Stat im HUD + reducer-Tasks (Logs analysieren, Legacy-Service beruhigen)
- 4 zusätzliche Tasks (Logs analysieren, Legacy-Service beruhigen, Scope reduzieren, Release Notes schreiben)
- 3 zusätzliche Sabotagen (Merge Conflict Storm, Fake Customer Request, Flaky Tests)
- 4–12 Spieler mit Multi-Chaos ab 7
- Map-Editor (Phase 1) unter `/editor` mit Räumen/Wänden/Türen/Spawns/Task-Ankern, JSON-Export
- Multi-Map-Support mit Lobby-Dropdown
- In-Game-ESC-Menü (Lobby verlassen, Runde beenden, Audio-Slider, Rolle/Tasks-Recap)

## [Tier 0 — Foundation Cleanup]

### Added

- Lint + Format (ruff für Python, prettier für JS/MD) + pre-commit-Hook
- CI auf GitHub Actions (pytest + ruff + prettier + vitest + godot-check + godot web-export bei jedem Push/PR)
- Frontend-Tests via Vitest + happy-dom (~109 Tests)
- Doku-Block: `docs/PROTOCOL.md`, `ARCHITECTURE.md`, `DEPLOY.md`, `DEV.md`
- Deploy-Script (`scripts/deploy.sh`) + Auto-Deploy auf EC2 (GitHub-Actions baut Tarball, scp + ssh-restart auf t4g.nano in eu-central-1)
- Reconnect: Server bewahrt Spieler-Identität 30s nach Disconnect
- Live-Test-Validierung mit echten Spielern

---

[Unreleased]: https://github.com/rausch-tech/merge-commit-mayhem/compare/main...HEAD
