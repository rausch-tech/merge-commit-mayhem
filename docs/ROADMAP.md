# Merge Conflict Mayhem — Roadmap

> **Vision:** Ein Among-Us-artiges Social-Deduction-Game für Tech-Teams. Statt einer Raumstation: ein Software-Büro mitten im Release. Statt Crewmates und Imposter: Release-Team und Chaos-Agenten. Mit der Mechanik-Klarheit von Among Us und der Insider-Komik eines Engineering-Teams in der Krise.

Dieses Dokument ist der **eine** Plan. Es ist die Wahrheit über den Stand und die Reihenfolge. Andere Docs erklären Sub-Themen (Map-Schema, Contributing, Architektur), aber Roadmap und Status leben hier.

---

## Stand (2026-05-15)

|              |                                                                                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Repo**     | https://github.com/rausch-tech/merge-commit-mayhem (public seit 2026-05-15)                                                                            |
| **Live**     | https://prod-is-lava.dev — Browser-Client unter `/`, Godot-3D-Web-Client unter `/godot/`                                                               |
| **Tests**    | 717 backend + 109 frontend grün, 92 % coverage auf `app/game/`, 22 GDScript-Parse-Checks                                                               |
| **Stack**    | Python 3.12 + FastAPI + Pydantic v2 + WebSockets, Vanilla JS + Canvas, Three.js (Editor-3D), Godot 4.6 + GDScript, KayKit-Assets (CC0)                 |
| **CI-Gates** | pytest+coverage 88 %, ruff (lint+format), mypy, prettier 3.3.3, vitest, godot-check, godot web-export — auto-deploy auf jedem main-Push                |
| **Phase**    | Tier 0–4 abgeschlossen (Done-Block unten). Beide Clients feature-vollständig auf Live. Nächste Phasen: Live-Test-Sweep, Tier 5 (Polish), Tier 6 (Mod). |

**Was Live spielbar ist:** 4–12 Spieler, vier Maps, 5+3 Rollen mit Personal-Tasks und Coffee-Energy, 8 Mini-Games pro Task, 8 Sabotagen mit Object-Binding, Among-Us-Features (Take-Down, Body-Discovery, Vents, Lights/Comms-Sabotage, Spectator), AI-NPC-Bots als Lobby-Filler (heuristisch oder LLM), Meeting-Kontext + AI-Flavor + AI-Postmortem, Endscreen mit Awards. Browser-Client und Godot-3D-Client laufen parallel gegen denselben FastAPI-Backend.

---

## Architektur (high-level)

> **Python entscheidet. Der Client zeigt nur an.**

- **Server** (FastAPI + WebSocket) ist autoritativ für **allen** State. 20-Hz-Tick-Loop berechnet Positionen, Task-Progress, Sabotage-Cooldowns, Win-Conditions.
- **Client** (Browser via Vanilla JS, später Godot) sendet nur Inputs, rendert empfangene Snapshots. Keine Spiellogik im Frontend.
- **Map als JSON** in `maps/*.json`. Server lädt + validiert beim Start, schickt Karte beim Join an den Client. `maps/kinds.json` ist Single Source of Truth für MapObject-Kinds inklusive Asset-Pfaden pro Client. Mod-tauglich, Editor-fähig.
- **WS-Protokoll** ist client-agnostisch. Browser-Client und Godot-Client laufen parallel gegen denselben Server.
- **Server entscheidet, später Client zeigt** — auch der Godot-Client zieht Map + Kinds-Registry zur Laufzeit per HTTP vom Backend (Option C, PR #36), damit es keine Drift zwischen den beiden Welten gibt.

Detail siehe `docs/maps.md` (Map-Schema), `docs/PROTOCOL.md` (vollständiger WS-Vertrag) und `docs/ARCHITECTURE.md` (Backend-Innenleben).

---

## Roadmap

Sieben Tier in Reihenfolge. Tier 0–4 sind abgeschlossen (Block unten zum Ausklappen — Detail-Pläne im git log und in den Tags). Tier 5–7 sind die offenen Phasen.

### Done (Tier 0–4)

<details>
<summary><b>Tier 0–4 abgeschlossen.</b> Vom Foundation-Cleanup bis zum vollständigen Godot-3D-Client mit Feature-Parität. Click to expand für die per-Tier-Highlights.</summary>

| Tier                         | Was wurde geliefert                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **0** Foundation Cleanup     | Lint+CI+Test-Gates, Doku-Block (`PROTOCOL.md`, `ARCHITECTURE.md`, `DEPLOY.md`, `DEV.md`), Deploy-Script, Reconnect (30 s grace), Auto-Deploy auf EC2.                                                                                                                                                                                                                                                                                                  |
| **1** Core-Mechaniken        | Map 4800×3200, Eventfeed, Incidents-Stat, 4 zusätzliche Tasks, 3 zusätzliche Sabotagen, 4–12 Spieler mit Multi-Chaos, Map-Editor (Phase 1), Multi-Map-Support, In-Game-ESC-Menü.                                                                                                                                                                                                                                                                       |
| **2** Among-Us-Features      | Take-Down (Force-Reboot), Body-Discovery+Report, Vents, Lights-Sabotage mit Vignette, Comms-Sabotage, Spectator-Mode, **Sabotage-Object-Binding** (jede Sabotage an Task-Anchor mit passendem `objectType`).                                                                                                                                                                                                                                           |
| **3** Mini-Games             | Mini-Game-Framework (Server-authoritative), 6 von 8 Tasks mit eigenen Plugins (Sequencing/Pairing/Timing/Filter/Subset, Test-Suite/Cables/Coffee/Logs/Scope).                                                                                                                                                                                                                                                                                          |
| **3.5** Persona-Layer        | 5 Release + 3 Chaos Rollen mit Stärken/Schwächen-Multipliern, Coffee-Energy pro Spieler mit Decay/Penalty/Bonus, persönliche Task-Backlogs (3 pro Spieler), aktive Abilities 1×/Runde, Role-Intro-Modal, Lobby-Rollen-Wunsch.                                                                                                                                                                                                                          |
| **3.6** Meeting + AI-Flavor  | Meeting-Kontext (Reporter, Body, RecentEvents), Object-Bound-Sabotage als Tier-2.7-rework (statt dedizierter Console), AI-Flavor-Pools für Eventfeed + Last-Words.                                                                                                                                                                                                                                                                                     |
| **3.7** Endscreen + Metriken | Endscreen-Story mit Awards + Per-Player-Stats, AI-Postmortem-Generator, restliche 3 Mini-Games (Diff-Review, Stability-Balance, Release-Notes), JSONL-Metrik-Export via `/api/metrics`.                                                                                                                                                                                                                                                                |
| **3.8** Map-Toolchain        | Browser-Editor mit 2D + Three.js-3D-Vorschau Side-by-Side, Server-Save-API, prozedurale Floor-Texturen, Door-Frames, **`maps/kinds.json` als Single Source of Truth** für MapObject-Kinds (alle 4 Konsumenten lesen dynamisch), zwei populierte Maps (office_complex 390 Objekte, datacenter 147), `ASSET_SPEC.md`.                                                                                                                                    |
| **3.9** AI-Integration       | LLM-Provider-Abstraction (Anthropic Cloud + Local OpenAI-kompatibel), AI-NPC-Bots als Lobby-Filler (Heuristik + LLM-Intent, ThreadPoolExecutor für non-blocking Calls), `LLMClient` Protocol mit 3 s Timeout und Fallback auf Heuristik.                                                                                                                                                                                                               |
| **4** Godot-3D-Client        | Vollständige Feature-Parität zum Browser-Client: Lobby (Map-Auswahl, Rollen-Präferenz, AI-NPC-Buttons), Map-Render mit KayKit-Meshes (25/25 Kinds), Character-Movement mit Lerp 35 + Snap-on-Pushback, alle 8 Mini-Games, Sabotage-Buttons, Meeting+Voting, Endscreen, Among-Us-Mechaniken (Vents, Take-Down, Body-Report, Lights/Comms-VFX, Spectator), Auto-Reconnect, Polish (Camera-Shake, Phase-Banner, Confetti). Web-Export live auf `/godot/`. |

**Bleibt offen aus Tier 3.9/4** (low-priority backlog, kein Blocker):

- AI-Postmortem mit echtem LLM (statt Templates), AI-Game-Master / Live-Commentary, AI-Meeting-Summary, smartere Chaos-Bots (Phase 2)
- DevOps-Theme-Spezial-Meshes als Flavor-Layer über die KayKit-Defaults
- Touch-Controls für Mobile (vertagt auf Tier 5.2), BGM mit Mute-Toggle (vertagt auf Tier 5.1), In-Game-Audio-Slider

</details>

### Tier 5 — Polish + Distribution

**Ziel:** „echt fertig"-Niveau. Was zwischen Beta und „würde ich öffentlich zeigen" liegt.

| #   | Was                                                                                                                                | Aufwand  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------- | -------- |
| 5.1 | **BGM** — kuratierte Tracks, Mute-Toggle, Volume-Slider                                                                            | 0.5 Tag  |
| 5.2 | **Mobile-Layout** (Tablet 1024px) + Touch-Controls (virtual joystick)                                                              | 1 Woche  |
| 5.3 | **Account-System** (light) — Profil mit Skin-Auswahl, Win-Stats                                                                    | 3–5 Tage |
| 5.4 | **Custom Skins** — neben Color auch Hat-/Pet-Variationen, kosmetisch                                                               | 2–3 Tage |
| 5.5 | **Bessere Animationen** — Reaction-Idles, Walking-Wackel, Death-Pose                                                               | ongoing  |
| 5.6 | **Lobby-Link-Sharing** — URL mit Raumcode, evtl. QR                                                                                | 0.5 Tag  |
| 5.7 | **Better Error-Handling** — Toast-System mit Severity-Levels                                                                       | 0.5 Tag  |
| 5.8 | **Settings-Menü** — Sound, Sprache, Tastenkonfiguration                                                                            | 1 Tag    |
| 5.9 | **Endscreen-Awards** — „Held der Kaffeemaschine", „Pipeline Whisperer", „Most Suspicious Innocent", basierend auf Per-Player-Stats | 1 Tag    |

**Done-Kriterium:** Spielt sich auf Desktop + Tablet flüssig. Sieht poliert aus. Es gibt Wiederspielwert (Awards, Skins, Stats).

### Tier 6 — Community + Mod-Support

**Ziel:** Anderer Devs in deinem Team können Inhalte beitragen ohne Code-Touch.

**Pattern (geblueprintet durch Tier 3.8.7):** JSON unter `maps/<thing>.json` als single source of truth → Pydantic-Registry-Modul (`app/game/<thing>_registry.py`) mit fail-loud loader → `GET /api/<thing>` Endpoint → Pydantic-field_validator gegen Registry + Frontend liest dynamisch. Tests lesen die produktive JSON von disk + seed via `_seedFromRegistryForTests`. Drift-resistant per Konstruktion.

| #   | Was                                                                                                                                                                                                                                             | Aufwand  |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| 6.1 | **Tasks aus JSON** (`maps/tasks.json` o.ä.) — Reward-Werte, Räume, Dauern, Mini-Game-Bindung. Folgt dem 3.8.7-Pattern.                                                                                                                          | 1 Tag    |
| 6.2 | **Sabotagen aus JSON** (`maps/sabotages.json`) — Cooldown, Effekte, allowed_trigger_object_types. Folgt dem 3.8.7-Pattern.                                                                                                                      | 1 Tag    |
| 6.3 | **Rollen aus JSON** (`maps/roles.json`) — Team, Description, available_sabotages, Spezial-Fähigkeiten, Stärken/Schwächen-Kategorien. Folgt dem 3.8.7-Pattern.                                                                                   | 1.5 Tage |
| 6.4 | **Eventtexte aus JSON** (`event_texts.json`) — Pool pro Event-Typ, zufällig                                                                                                                                                                     | 0.5 Tag  |
| 6.5 | **Map-Editor Phase 2** — durch Tier 3.8 vorgezogen: Live-Preview (Server-Save → sofort spielbar), Validation-Strip, 3D-Vorschau                                                                                                                 | ✅ done  |
| 6.6 | **Map-Browser** — `GET /api/maps` + Editor-Modal listet alle Karten + lädt direkt; Hot-Reload via Registry-Reload nach Save                                                                                                                     | ✅ done  |
| 6.7 | **Erweiterte Rollen** — Data Wizard, Consultant, Shadow Admin, Incident Commander, Caffeine Collector, Bug Squasher, Legacy Oracle, Scrum Master mit Spezial-Fähigkeiten (Auto-Fix Bot, Distract, Speed Boost, Coffee Run, Scan Logs, Rollback) | 2 Wochen |
| 6.8 | **Insider-Gags + Memes** — kuratiert von Sven + Team, im Pool                                                                                                                                                                                   | ongoing  |

**Done-Kriterium:** Person ohne Code-Wissen kann eine neue Sabotage via Pull-Request beitragen. `docs/CONTRIBUTING.md` reicht aus dafür.

### Tier 7 — Live-Service-Phase

**Ziel:** Das Game lebt. Wir oder Community erweitern es regelmäßig.

| #   | Was                                                                                  |
| --- | ------------------------------------------------------------------------------------ |
| 7.1 | **Stable Releases + Versioning** — Server hat Version, Client checkt Kompatibilität  |
| 7.2 | **Statistik-Backend** — Per-Player-Stats persistieren, Win-Rate, Lieblings-Rolle     |
| 7.3 | **Saisons / Events** — temporäre Maps, Theme-Roll-outs (Halloween, Christmas-Office) |
| 7.4 | **Translation-Support** — i18n für Eventtexte, UI                                    |
| 7.5 | **Public Release** — falls gewünscht: Itch-Page, Discord, etc.                       |

Diese Tier ist absichtlich vage — was hier passiert hängt davon ab wie das Game vom Team angenommen wird.

---

## Was als nächstes konkret zu tun ist

**Aktueller Stand (2026-05-15):** Tier 0–4 durch (siehe Done-Block oben). Repo seit 2026-05-15 public. Branch-Protection auf main mit 6 required Checks und PR-Workflow. Beide Clients feature-vollständig auf Live.

**Direkt als nächstes:**

- **Live-Test-Sweep** mit echten Spielern auf dem Godot-Client — Bug-Surface, Balance-Feedback, Vergleich zum Browser-Client.
- **Public-Repo-Polish** (ongoing): Social Preview Image, CHANGELOG.md mit Tier-Highlights, CodeQL aktivieren, evtl. Demo-GIF im README.

**Lower priority (anytime):**

- **Editor-QoL** — Keyboard-Shortcuts, Multi-Select, Duplicate. ~1–2 h.
- **`/api/metrics` Aggregations-Endpoint** für die JSONL-Files. Hilft beim Balancing. ~45 min.
- **DevOps-Theme-Spezial-Meshes** — Coffee-Maschine, Server-Rack, Bug-Trophy als Flavor-Layer über die KayKit-Defaults.
- **AI-Backlog** — AI-Postmortem mit echtem LLM, Live-Commentary, Meeting-Summary, Chaos-Bots Phase 2.

**Anschließend:** Tier 5 (Polish + Distribution), Tier 6 (Community + Mod-Support), Tier 7 (Live-Service-Phase) — siehe unten.

---

## Wie wir entscheiden

- **Slices** sind die Arbeitseinheit. Jede Slice hat ihren eigenen Branch (`slice/<kurztitel>`), Tests, Live-Server-Restart nach Merge.
- **Specs/Plans** schreiben wir nur für nicht-triviale Slices (>1 Tag Aufwand). Kleinere Slices fließen direkt in den Implementer-Prompt ein.
- **Live-Tests** validieren Tier-Übergänge — bevor wir ein Tier fertig erklären, mit echten Spielern testen.

---

## Verwandte Docs

- [`docs/maps.md`](maps.md) — Map-JSON-Schema (Referenz für Map-Bauer)
- [`docs/PROTOCOL.md`](PROTOCOL.md) — vollständiger WS-Vertrag
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — High-Level-Overview
- [`docs/DEPLOY.md`](DEPLOY.md) — Deploy-Workflow + AWS/EC2/Caddy-Setup
- [`docs/DEV.md`](DEV.md) — lokale Entwicklung
- [`docs/GAME_OVERVIEW.md`](GAME_OVERVIEW.md) — Spielmechanik, Rollen, Win-Conditions
- [`docs/GODOT_HANDOFF.md`](GODOT_HANDOFF.md) — Godot-Client Architektur-Referenz (Protokoll, Stolperfallen, Scripts-Layout)
- [`docs/HOWTO-SABOTAGE.md`](HOWTO-SABOTAGE.md), [`HOWTO-MINIGAME.md`](HOWTO-MINIGAME.md), [`HOWTO-ROLE.md`](HOWTO-ROLE.md) — Contributing-Guides für neue Inhalte
- [`AGENTS.md`](../AGENTS.md) — Repo-weiter Onboarding-Guide für AI-Agents (Stack, Commands, Conventions)
- `merge_conflict_mayhem_project/` — ursprüngliches Design-Paket von Sven, behalten als historische Inspirations-Quelle (Roadmap ersetzt es)
