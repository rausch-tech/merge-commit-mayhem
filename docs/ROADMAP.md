# Merge Conflict Mayhem — Roadmap

> **Vision:** Ein Among-Us-artiges Social-Deduction-Game für Tech-Teams. Statt einer Raumstation: ein Software-Büro mitten im Release. Statt Crewmates und Imposter: Release-Team und Chaos-Agenten. Mit der Mechanik-Klarheit von Among Us und der Insider-Komik eines Engineering-Teams in der Krise.

Dieses Dokument ist der **eine** Plan. Es ist die Wahrheit über den Stand und die Reihenfolge. Andere Docs erklären Sub-Themen (Map-Schema, Contributing, Architektur), aber Roadmap und Status leben hier.

---

## Stand (2026-04-28)

|                        |                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Repo**               | https://github.com/rausch-tech/merge-commit-mayhem                                                                                                                                                                                                                                                                                                                                                   |
| **Live (Test-Server)** | https://prod-is-lava.dev (Apex-Domain seit 2026-04-27)                                                                                                                                                                                                                                                                                                                                               |
| **Backend-Tests**      | ~714 grün (`uv run pytest`), Coverage-Floor 88 % auf `app/game/`                                                                                                                                                                                                                                                                                                                                     |
| **Frontend-Tests**     | ~109 grün (`npx vitest run`)                                                                                                                                                                                                                                                                                                                                                                         |
| **Stack**              | Python 3.12 + FastAPI + Pydantic v2 + WebSockets, Vanilla JS + Canvas, Three.js für Editor-3D-Vorschau, Godot 4.6 für den 3D-Client, Vitest + happy-dom                                                                                                                                                                                                                                              |
| **CI-Gates**           | pytest (+ coverage 88 %), ruff (lint + format), mypy, prettier 3.3.3, vitest, godot-check, godot web-export (auto-deploy auf jedem main-Push)                                                                                                                                                                                                                                                        |
| **Geshippte Tier**     | 0 (Foundation), 1 (Core-Mechaniken), 2 (Among-Us-Features), 3 (Mini-Games), 3.5 (Persona-Layer), 3.6 (Meeting-Kontext + AI-Flavor), 3.7 (Endscreen + Closing-Mini-Games + Metrik-Export), 3.8 (Map-Authoring-Toolchain), 3.9.1 (LLM-Provider-Abstraction), 3.9.2 (AI-NPCs Lobby-Filler), 3.9.2.1 (LLM-Async-Fix nach Live-Incident)                                                                  |
| **In Arbeit**          | Tier 3.9.3+ (AI-Postmortem real LLM, Game-Master, Meeting-Summary, Map-Generator) und Tier 4.x parallel (Godot-Client Feature-Parität + Asset-Pipeline)                                                                                                                                                                                                                                              |
| **Tier 4 Stand**       | 3D-Client (`godot-3d/`) auf main: Lobby + World + Character + HUD + Pause + 5 Mini-Games + Take-Down + Body-Report + Vents + Endscreen-Awards + Personal-Tasks + Coffee-Pulse + Ability-Btn + Sabotage-Strip + Eventfeed + Role-Intro-Modal. Map-Loader liest aktuelles Schema, fetcht `kinds.json` zur Laufzeit vom Backend (Option C, PR #36). KayKit-Asset-Pipeline durch (25/25 Kinds gestaged). |

**Was funktioniert (Live, Stand 2026-04-28):**

- 4–12 Spieler joinen einen Raum, vier Maps wählbar in der Lobby (`default` mit 44 MapObjects, `office_complex` mit **390 MapObjects** nach Wow-Effekt-Pass, `datacenter` mit 147 MapObjects, `small`).
- **AI-NPCs als Lobby-Filler** (Tier 3.9.2): Host kann „+ Bot hinzufügen", Bots laufen LLM-getrieben oder heuristisch durch die Map, completen Tasks, melden Bodies, voten in Meetings.
- Map-Editor unter `/editor` mit 2D-Canvas + Three.js-3D-Vorschau Side-by-Side: Pan/Zoom, Save-/Load-direkt-zum-Server (`/api/maps`), Undo/Redo, Validation-Strip, Layer-Toggles, Drag-to-Move, Door-Tool, prozedurale Floor-Texturen pro `floorMaterial` (Carpet/Tiles/Concrete/Legacy), Door-Frames als sichtbare Geometrie.
- **Single Source of Truth für MapObject-Kinds** in `maps/kinds.json` (25 Kinds + `_meta`-Block mit Schema-Doku). Pydantic-Validator auf `MapObject.kind` rejected unbekannte Kinds. Editor + Browser-Renderer + 3D-Preview + Godot-Client lesen alle dynamisch via `GET /api/kinds`.
- 5+3 Rollen mit persönlichen Tasks, Stärken/Schwächen, Coffee-Profil, aktiven Fähigkeiten.
- Alle 8 Tasks haben Mini-Games (sequencing / pairing / timing / filter-by-criterion / subset-by-constraint, plus Spot-the-Bug / Stability-Balance / Click-to-Cycle-Sort).
- 8 Sabotagen mit Object-Binding (Tier 2.7): chaos triggert nur in Reichweite eines Task-Anchors mit passendem `objectType`.
- Among-Us-Features: Take-Down + Body-Discovery + Report, Vents (Chaos-Teleport), Lights/Comms-Sabotage mit Repair-Panels, Spectator-Mode für Geister.
- Coffee-Energy mit Decay/Speed-Penalty/Task-Bonus, Aktive Abilities 1×/Runde.
- Meeting-Kontext + AI-Flavor in Eventfeed + Postmortem; Endscreen mit Awards + Per-Player-Stats + AI-Postmortem.
- Metrik-Export (JSONL pro Tag) für Balancing, lesbar via `GET /api/metrics?since=YYYY-MM-DD` (win-rates, mean duration, tasks-per-role, sabotage-totals).
- Voting-Result mit AI-flavored „last words"-Zitat des eliminated Spielers — pool nach Team unterschieden.
- Brand: Subtitle „PROD IS LAVA", transparenter Logo-PNG, Apex-Domain.

---

## Architektur (high-level)

> **Python entscheidet. Der Client zeigt nur an.**

- **Server** (FastAPI + WebSocket) ist autoritativ für **allen** State. 20-Hz-Tick-Loop berechnet Positionen, Task-Progress, Sabotage-Cooldowns, Win-Conditions.
- **Client** (Browser via Vanilla JS, später Godot) sendet nur Inputs, rendert empfangene Snapshots. Keine Spiellogik im Frontend.
- **Map als JSON** in `maps/*.json`. Server lädt + validiert beim Start, schickt Karte beim Join an den Client. `maps/kinds.json` ist Single Source of Truth für MapObject-Kinds inklusive Asset-Pfaden pro Client. Mod-tauglich, Editor-fähig.
- **WS-Protokoll** ist client-agnostisch. Browser-Client und Godot-Client laufen parallel gegen denselben Server.
- **Server entscheidet, später Client zeigt** — auch der Godot-Client zieht Map + Kinds-Registry zur Laufzeit per HTTP vom Backend (Option C, PR #36), damit es keine Drift zwischen den beiden Welten gibt.

Detail siehe `docs/maps.md` (Map-Schema) und das künftige `docs/PROTOCOL.md` (siehe Tier 0).

---

## Roadmap

Sechs Tier, in der Reihenfolge wie sie gebaut werden sollten. Jedes Tier hat ein klares Definition-of-Done; nichts springt ein Tier nach vorne, bis das vorherige zu ist.

### Tier 0 — Solide Basis (Foundation Cleanup)

**Ziel:** Die Codebase ist sauber, getestet, dokumentiert, deploybar — bereit für ernsthaftes Mit-Entwickeln.

**Aufwand:** ~2 Wochen.

| #    | Was                                                                                                 | Status    |
| ---- | --------------------------------------------------------------------------------------------------- | --------- |
| 0.1  | **Lint + Format** — `ruff` für Python, `prettier` für JS, pre-commit-Hook                           | ✅ done   |
| 0.2  | **CI auf GitHub Actions** — pytest + ruff + prettier bei jedem Push/PR                              | ✅ done   |
| 0.3  | **Frontend-Tests** — Vitest + happy-dom, Smoke-Coverage pro JS-Modul                                | ✅ done   |
| 0.4  | **`docs/PROTOCOL.md`** — vollständiger WebSocket-Vertrag                                            | ✅ done   |
| 0.5  | **`docs/ARCHITECTURE.md`** — high-level Overview                                                    | ✅ done   |
| 0.6  | **`docs/DEPLOY.md`** — Deploy-Workflow                                                              | ✅ done   |
| 0.7  | **`docs/DEV.md`** — lokale Entwicklung                                                              | ✅ done   |
| 0.8  | **Deploy-Script** — `scripts/deploy.sh`                                                             | ✅ done   |
| 0.9  | **Dead-Code raus** — `incidentCount` ohne Mechanik raus                                             | ✅ done   |
| 0.10 | **Reconnect** — Server bewahrt Spieler-Identität 30 s nach Disconnect                               | ✅ done   |
| 0.11 | **Edge-Cases** — Host-Disconnect mid-Meeting etc.                                                   | ✅ done   |
| 0.12 | **Auto-Deploy auf main** — GitHub-Actions baut Tarball, scp + ssh-restart auf EC2 (Test-Gate davor) | ✅ done\* |
| 0.13 | **Live-Test mit Team** — 3–5 Runden, Bugs surfacen + fixen                                          | ✅ done   |

\*Auto-Deploy steht; braucht zwei GitHub-Secrets (`EC2_SSH_KEY`, `EC2_HOST`) damit's tatsächlich pusht — siehe [`DEPLOY.md`](DEPLOY.md).

**Done-Kriterium:** Alle Tests grün in CI. Doku-Block existiert. Deploy-Script funktioniert. Reconnect funktioniert. Mit echten Leuten gespielt, keine Critical-Bugs offen.

### Tier 1 — Spiel komplettieren (Core-Mechaniken)

**Ziel:** Browser-Client hat alle Kern-Mechaniken die wir wollen, bevor wir die Among-Us-Schicht oder Godot bauen. Sonst Doppelarbeit beim Porten.

**Aufwand:** ~1.5 Wochen.

| #   | Was                                                                                                                                                      | Status  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 1.0 | **Canvas-Vollbild + Map 2× größer** — Canvas füllt das Browser-Fenster, Map skaliert von 2400×1600 auf 4800×3200, Timer 720s → 900s                      | ✅ done |
| 1.1 | **Eventfeed** — Live-Feed rechts neben Canvas: „Pipeline ist rot", „PR gemerged", „Carol wurde entfernt — war Chaos-Agent". Trigger durch Server-Events. | ✅ done |
| 1.2 | **Incidents-Mechanik** — drittes Stat im HUD. Tasks „Logs analysieren" + „Legacy-Service beruhigen" reduzieren. Eine zukünftige Sabotage erzeugt sie.    | ✅ done |
| 1.3 | **Mehr Tasks** — vier zusätzliche aus dem Master-Doc: Logs analysieren, Legacy-Service beruhigen, Scope reduzieren, Release Notes schreiben              | ✅ done |
| 1.4 | **Mehr Sabotagen** — Merge Conflict Storm, Fake Customer Request, Flaky Tests                                                                            | ✅ done |
| 1.5 | **Spielerzahl 4–12** — MAX_PLAYERS auf 12, Color-Palette erweitern, Multi-Chaos bei großen Lobbys (2 Chaos ab 7 Spielern)                                | ✅ done |
| 1.6 | **Mute-Toggle / Volume-Slider** — Audio-Hygiene                                                                                                          | ✅ done |
| 1.7 | **Map-Editor (Phase 1)** — Browser-Editor unter `/editor`: Räume rechtecken, Wand-Linien + Türen, Spawns, Task-Anker. JSON-Export.                       | ✅ done |
| 1.8 | **Multi-Map-Support** — Lobby-Dropdown, mehrere `maps/*.json`, Host wählt                                                                                | ✅ done |
| 1.9 | **In-Game-Menü** — ESC-Overlay mit Lobby verlassen (alle), Runde beenden (host-only), Audio-Controls reingezogen, Rolle/Aufgaben-Recap                   | ✅ done |

**Done-Kriterium:** Browser-Client deckt das gesamte Master-Doc-MVP ab plus Eventfeed plus Map-Editor plus In-Game-Menü. Mit 8 Leuten testbar. Multi-Map-Auswahl in der Lobby. Spieler können die Runde jederzeit verlassen, Host kann sie beenden.

### Tier 2 — Among-Us-Features

**Ziel:** Die Mechaniken, die Among Us spielenswert machen, in unserer Tech-Office-Variante. Hier wird das Spiel von „funktional MVP" zu „echtes Game".

**Aufwand:** ~2 Wochen.

| #   | Was                                                                                                                                                                                                                                                                                                                                                                                                                                          | Status  | Naming-Idee                                           |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ----------------------------------------------------- |
| 2.1 | **Take-Down-Mechanik** — Chaos kann Spieler im Proximity-Radius außer Gefecht setzen. Cooldown ~25 s. Kein Take-Down im War Room (Sicherheitszone).                                                                                                                                                                                                                                                                                          | ✅ done | „Force-Reboot", „Captcha-Loop", „LinkedIn-Spam-Blast" |
| 2.2 | **Body-Discovery + Report** — eliminierte Spieler bleiben als „Body" sichtbar bis entdeckt. Lebende Spieler in Proximity können Report-Button drücken → triggert Meeting.                                                                                                                                                                                                                                                                    | ✅ done | „Stale-Process-Found", Ghost = „Coredumped Engineer"  |
| 2.3 | **Vents** — Chaos kann zwischen vorab-definierten Punkten teleportieren. Map-JSON kriegt `vents: [...]`-Feld. Animation + Sound.                                                                                                                                                                                                                                                                                                             | ✅ done | „SSH-Tunnel", „Internal-Pipeline"                     |
| 2.4 | **Lights-Sabotage** — Sichtbarkeits-Reduktion: Viewport bekommt Vignette, Spieler sehen nur ~150 px Radius um sich herum. Repariert durch Interact mit „Electrical Panel" (im Server Room).                                                                                                                                                                                                                                                  | ✅ done | „PagerDuty-Storm" / „Production-Outage"               |
| 2.5 | **Comms-Sabotage** — Tasks-Sidebar wird leer (kann nicht erfüllt werden), Sabotage-Buttons disabled. Repariert durch Interact mit „Comms Panel" (im War Room).                                                                                                                                                                                                                                                                               | ✅ done | „Slack-Down", „Confluence-Outage"                     |
| 2.6 | **Spectator-Mode für Geister** — Tote Spieler können sich frei durch die Map bewegen, andere Geister sehen, Lebende sehen sie nicht. Tasks erfüllen können sie weiter (helfen Release-Team), aber nicht mehr abstimmen.                                                                                                                                                                                                                      | ✅ done | „Coredumped"                                          |
| 2.7 | **Sabotagen an Themen-Objekte binden** — jede Sabotage triggert nur in 60-px-Reichweite eines Task-Anchors mit passendem `objectType` (CI-Konsole, Git-Terminal, Kaffeemaschine, Monitoring-Panel etc.). Same Anchor wie Release-Tasks → outsider sehen nicht, ob da gearbeitet oder sabotiert wird. Per-Sabotage Hint + Button-Disable wenn ausser Reichweite. Erste Iteration mit dedizierter Console wurde verworfen (zu offensichtlich). | ✅ done | „Sabotage-Object-Binding"                             |

Naming-Prinzip: nerdig, dev-thematisch, „kill" wird vermieden zugunsten von harmlos-witzigen Tech-Bezeichnungen. Final-Naming entscheiden wir bei Implementation jeder Slice.

**Done-Kriterium:** Alle 6 Features implementiert + getestet. Game spielt sich „wie Among Us, aber dev-themed". Mit Live-Tests bestätigt.

### Tier 3 — Mini-Games (Task-Tiefe)

**Ziel:** Tasks fühlen sich nicht mehr wie „hinlaufen + E drücken" an. Jede Task wird zu einem kleinen Spiel — entscheidende Spannungsquelle, weil ein Spieler an einer Task „sichtbar beschäftigt" sein muss und Saboteure das ausnutzen können.

**Aufwand:** ~3 Tage (für Framework + Beispiel). Erweiterung auf alle Tasks erfolgt iterativ in folgenden Slices, sobald sich das Pattern bewährt hat.

**Reihenfolge:** kommt **vor** Godot, weil das Mini-Game-API die Godot-Migration prägt. Wird das API in Browser ausgereift festgelegt, spart Tier 4 (Godot) doppelte Arbeit.

| #   | Was                                                                                                                                                                                      | Status  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 3.1 | **Mini-Game-Framework** — Server: Task-Schema kriegt `mini_game: str`. WS: `mini_game_started` / `mini_game_input` / `mini_game_state` / `mini_game_completed`. Client: pluggable Modal. | ✅ done |
| 3.2 | **Beispiel: „Test-Suite reparieren"** (für `fix_unit_tests`) — Liste aus 5 fehlerhaften Tests, klick die Bugs in der richtigen Reihenfolge weg.                                          | ✅ done |
| 3.3 | **„Server-Racks neu verkabeln"** (für `repair_deployment`) — Among-Us-Cables im Re-Skin: 4 farbige Source-Stecker links, 4 Buchsen rechts geshufflt, Tap-Pairing, Mismatch = Soft-Reset. | ✅ done |
| 3.4 | **„Kaffee einschenken"** (für `refill_coffee`) — Tasse fuellt sich zyklisch, Tap STOP im Sweet-Spot 70-100 %, sonst Cycle-Reset. Server-authoritative Timing.                            | ✅ done |
| 3.5 | **„Logs analysieren"** (für `analyze_logs`) — 8 Log-Zeilen mit gemischtem Severity, Multi-Select aller ERROR-Zeilen, Click auf WARN/INFO ist Soft-Reset.                                 | ✅ done |
| 3.6 | **„Scope reduzieren"** (für `reduce_scope`) — 6 Sprint-Tickets mit Story-Points, entferne Tickets bis Restsumme <= Budget; Priority-Tickets duerfen NICHT entfernt werden (Soft-Reset).  | ✅ done |

**Done-Kriterium:** Eine Task läuft komplett über ein Mini-Game (Server-validiert), die anderen 7 bleiben Hold-E. Das Mini-Game-API ist dokumentiert und Live-getestet, sodass weitere Mini-Games als eigene Slices folgen können (Code-Review-Simulator, Logs-Filtern, Coffee-Pour-Timing usw.). Mit Tier 3.3-3.6 stehen jetzt fuenf Mechanik-Patterns (Sequencing, Pairing, Timing, Filter-by-Criterion, Subset-by-Constraint) als Vorlagen fuer kuenftige Tasks. Stand jetzt: 5 von 8 Tasks haben ein Mini-Game.

### Tier 3.5 — Rollen, persönliche Tasks & Kaffee-Energy (Persona Layer)

**Ziel:** Vom „alle teilen einen Task-Pool, eine Release-Rolle" zum „jeder ist ein Spezialist mit eigenem Backlog und eigener Ressource". Ist der grosse Architektur-Shift, der Social-Deduction-Diskussionen erst trägt: „Warum war der Scrum Master im Server Room?" / „Warum hatte DevOps keinen Kaffee mehr?".

**Quelle der Anforderungen:** `merge_conflict_mayhem_project/merge_conflict_mayhem_gesamtfeedback.md` (Teile A–E, P-Prompt).

**Aufwand:** ~2 Wochen, in einer Rutsch-Session am 2026-04-26 grundgelegt.

| #     | Was                                                                                                                                                                                                                                 | Status  |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 3.5.1 | **5 Release-Rollen** — Developer / DevOps Engineer / QA Lead / Scrum Master / Caffeine Collector. Jede mit Stärken (Task-Kategorien × 1.35), Schwächen (× 0.75), eigenem Kaffee-Profil (decay-modifier, max_coffee).                | ✅ done |
| 3.5.2 | **3 Chaos-Rollen** — Vibe Coder (AI/Code), Rogue Consultant (Process/Scope), Shadow Admin (Infra). Unterschiedliche `available_sabotages` pro Variante.                                                                             | ✅ done |
| 3.5.3 | **Persönliche Task-Backlogs** — jeder Spieler kriegt 3 Tasks (2 strength-passend + 1 random). Chaos kriegt 3 Fake-Tasks passend zur Tarn-Persona. UI markiert eigene Tasks mit ★ in der Sidebar.                                    | ✅ done |
| 3.5.4 | **Coffee-Energy pro Spieler** — `coffee_energy: 0..max_coffee`. Decay 1.4/s × Rolle-Modifier. <15 = Speed-Penalty, ≥80 = Task-Bonus. Eigene Pille im HUD, pulsiert rot wenn niedrig.                                                | ✅ done |
| 3.5.5 | **Aktive Fähigkeiten** — `use_ability` 1×/Runde: Rollback (DevOps +18 Pipeline), Coffee Run (CC bufft Nachbarn), Standup (Scrum Master ruft Meeting), Reproduce Bug (QA flagged Recent Action). Button im HUD.                      | ✅ done |
| 3.5.6 | **Lobby-Rollen-Präferenz** — Dropdown in der Lobby, Wunsch wird best-effort respektiert. Singleton-Rollen capped at 1. Chaos-Wunsch wird ignoriert (random).                                                                        | ✅ done |
| 3.5.7 | **Role-Intro-Modal** — beim Phase-Wechsel lobby→playing zeigt jeder Spieler eine Rollen-Karte: Titel, Blurb, Stärken, Fähigkeit, Aufgaben. Auto-dismiss nach 30 s.                                                                  | ✅ done |
| 3.5.8 | **Task-Speed-Modifier serverseitig** — `task_speed_multiplier(role, category, coffee)` läuft in `_tick_tasks` + `_complete_mini_game`-Reward-Pfad. Movement-Multiplier nur als Penalty bei niedrigem Coffee (Tests bleiben stabil). | ✅ done |

**Done-Kriterium:** Spieler erleben spürbar unterschiedliche Rollen, Persönliche Tasks lenken Bewegung, Kaffee ist eine echte Ressource. Live-Test mit ≥6 Personen.

### Tier 3.6 — Meeting-Kontext, Object-Bound-Sabotage & AI-Flavor

**Ziel:** Diskussionen kriegen Substanz (was war wo? wer war involviert?), Sabotage wird ambig statt offensichtlich (Tier 2.7 rework), AI-Flavor durchzieht Eventfeed + Postmortem.

**Aufwand:** ~1.5 Wochen, ebenfalls am 2026-04-26 in derselben Rutsch-Session.

| #     | Was                                                                                                                                                                                                                                       | Status    |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| 3.6.1 | **Sabotage-Object-Binding (Tier 2.7 rework)** — dedizierte Console rausgeworfen (zu offensichtlich), stattdessen jede Sabotage an Task-Anchor mit passendem `object_type` gebunden. Same Anchor wie Release-Task → Ambiguität.            | ✅ done   |
| 3.6.2 | **Meeting-Kontext** — `meeting.context = {reporterName, body? {victimName, room}, recentEvents[]}`. Snapshot zum Meeting-Start. UI zeigt Block über Voting-Liste. Hinweise, keine Beweise.                                                | ✅ done   |
| 3.6.3 | **AI-Flavor-Texte** — `app/game/ai_flavor.py` mit reichen LLM-styled Pools für Sabotage-Events („CI hatte einen Hallucinations-Anfall"), Repair, Body-Found, Vote-Kick. Vibe Coder bekommt AI-Sabotage-Themen.                            | ✅ done   |
| 3.6.4 | **Accusation-Tags / Voting-Polish** — Geschlossen (won't-fix). Original-Begründung: „bringt mit Voice-Chat den meisten Wert". Voice-Chat ist out-of-game (Teams nutzen TeamSpeak/Slack/Meet), Tags adden ohne Voice-Mehrwert nur UI-Last. | ❌ closed |
| 3.6.5 | **Voting-Result-Story** — `voting_result.lastWords` Flavor-Line aus zwei team-spezifischen Pools (`_LAST_WORDS_CHAOS` / `_LAST_WORDS_RELEASE` in `ai_flavor.py`). Browser zeigt als gedimmtes Zitat unter dem Verdict-Toast.              | ✅ done   |

**Done-Kriterium:** Meetings haben Substanz; Saboteure müssen sich physisch ans Object stellen (kein Verrats-Pattern); Eventfeed + Postmortem fühlen sich AI-generiert an.

### Tier 3.7 — Endscreen-Story, Closing Mini-Games & Metriken

**Ziel:** Nach jeder Runde gibt's Diskussionsstoff (Awards, Stats, AI-Postmortem). Verbleibende Hold-E-Tasks bekommen ihre Mini-Games. Server exportiert Metriken für Balancing.

**Aufwand:** ~1.5 Wochen.

| #     | Was                                                                                                                                                                                                                         | Status     |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 3.7.1 | **Endscreen-Story + Per-Player-Stats** — `final_summary` mit Per-Player (Tasks, Sabotagen, Coffee-final, Ability-used), Awards (Pipeline Whisperer, Vibe of the Round, Held der Kaffeemaschine, Most Suspicious Innocent).  | ✅ done    |
| 3.7.2 | **AI-Postmortem-Generator** — `generate_postmortem(summary)` produziert mehrzeiligen LLM-styled Text. Im Endscreen unter `<pre>` gerendert.                                                                                 | ✅ done    |
| 3.7.3 | **`review_pr` Mini-Game** — Diff-Review: 6 Code-Zeilen, 2 problematische markieren (hardcoded API key, leerer except, debug log, SQLi, …). Pattern: Multi-Select-by-Criterion (mirror of log_filter).                       | ✅ done    |
| 3.7.4 | **`calm_legacy_service` Mini-Game** — Stabilitäts-Balancing: CPU/Memory/Queue in grünem Band [40,60] halten, jede Korrektur drückt die nächste Metrik leicht weg (Rotation cpu→mem→queue→cpu).                              | ✅ done    |
| 3.7.5 | **`write_release_notes` Mini-Game** — Click-to-Cycle-Sort: 6 Commits in Feature/Bugfix/Breaking-Change/Don't-mention-publicly einordnen. Drag-and-Drop verworfen (Mobile-tricky).                                           | ✅ done    |
| 3.7.6 | **Metrik-Export (JSONL)** — pro Runde: Winner, Reason, Rundendauer, Meetings, Force-Reboots, Tasks/Rolle, Sabotagen, Repairs, Coffee-Avg. Eine `<YYYY-MM-DD>.jsonl` pro Tag unter `MCM_METRICS_DIR` (Env-Var, Tests no-op). | ✅ done    |
| 3.7.7 | **Heatmaps (optional, später)** — Movement, Kills, Body-Discovery, Sabotage-Trigger pro Map. Hilft Map-Balancing.                                                                                                           | 🔮 backlog |

**Done-Kriterium:** Endscreen erzählt die Runde, alle 8 Tasks haben Mini-Games, Server logged Balance-Metriken.

### Tier 3.8 — Map-Authoring-Toolchain

**Ziel:** Designer können Maps schnell iterieren, ohne git-Push-Zyklus pro Test, und sehen sofort wie die Karte später in 3D aussieht. Vorbereitung für reichhaltige Maps in Tier 4 + ongoing.

**Aufwand:** ~1 Woche, in Slices von 0.5–2 Tagen.

| #     | Was                                                                                                                                                                                                                                                                                                                                          | Status  |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 3.8.1 | **Editor-Slices 1–5** — vents/panels/objectType beim Save erhalten, Kind-Library + Drag-to-Move, Wand-Modell C (Doors top-level + `compute_walls`), Door-Tool + draggable doors, Undo/Redo + Validation-Strip + Layer-Toggles + Strg+S.                                                                                                      | ✅ done |
| 3.8.2 | **MapObjects-Schema** — 25 Kinds (Workstation, Server, Meeting, Kitchen, Decor, Legacy), Server validiert + rendert als Bounding-Boxes im Browser, Editor-Palette + Default-Sizes pro Kind, MapObject-Placement-Tool mit Drag.                                                                                                               | ✅ done |
| 3.8.3 | **3D-Preview-Pane (Three.js)** — Read-only WYSIWYG neben dem 2D-Canvas, lädt dieselben `.glb`-Files wie der Godot-Client (KayKit Furniture, Kenney Mini Characters), Live-Sync, OrbitControls, prozedurale Wand-Textur.                                                                                                                      | ✅ done |
| 3.8.4 | **Server-Save-API** — `GET /api/maps`, `GET /api/maps/{id}`, `PUT /api/maps/{id}` mit Pydantic-Validate + atomic write + Registry-Reload. Editor-UI: „In Spiel speichern" + „Vom Server laden"-Modal. Ephemer (überlebt Deploy nicht).                                                                                                       | ✅ done |
| 3.8.5 | **office_complex-Befüllung** — 140 thematische MapObjects per Generator-Skript (`scripts/populate_office_complex.py`) über alle 9 Räume, 8 Task-Anchors mit `objectType`-Bindings, Sabotage-Repairs platziert.                                                                                                                               | ✅ done |
| 3.8.6 | **Floor-Texturen + Door-Frames** — pro `floorMaterial` eine prozedurale Tile-Texture (Parquet/Fliesen/Beton/Carpet), Türen als sichtbare Lintel-Geometrie pro `doorKind`.                                                                                                                                                                    | ✅ done |
| 3.8.7 | **`maps/kinds.json` als Single Source of Truth** — neue Backend-Validation (`MapObject.kind` field_validator gegen Registry), `GET /api/kinds` endpoint, Frontend-Migration (editor-kinds.js + render.js + editor-preview-3d.js) lesen dynamisch, Godot-Client (godot-3d/scripts/map_builder.gd) konsumiert dieselbe Datei. Drift-resistant. | ✅ done |
| 3.8.8 | **`docs/ASSET_SPEC.md`** — Naming-Convention, Pivot/Polycount-Budget, kinds.json-Erweiterungs-Workflow für die Godot-Devs, damit Tier 4.0.x in einem definierten Format landet.                                                                                                                                                              | ✅ done |
| 3.8.9 | **datacenter-Befüllung** — `scripts/populate_datacenter.py` mit 147 MapObjects (54 Server-Racks dominate), 10 Räume, 8 Task-Anchors. Re-runbar wenn Tier 4.0.x finalere Kinds liefert.                                                                                                                                                       | ✅ done |

**Done-Kriterium:** Designer kann ohne git-Touch eine Karte komponieren, sofort live testen, im 3D-Preview sehen was Spieler später sehen werden, und neue Kinds ohne Drift-Risiko hinzufügen. Floor + Door visuell unterscheidbar pro Material.

### Tier 3.9 — AI-Integration (LLM)

**Ziel:** Echte LLMs eingebunden — Postmortem & Last-Words werden vom Modell geschrieben statt aus statischen Pools, AI-NPCs füllen halbleere Lobbies. MCM ist intern AI-Showcase eines KI-Unternehmens, das soll man dem Spiel ansehen.

**Provider-Strategie:** Dual-Provider hinter `LLMClient`-Protocol — Anthropic Claude Haiku (Cloud, Default) ODER OpenAI-kompatibler lokaler Server (Gemma 4 via Ollama, Sven hat lokal laufend). Auswahl per Env-Vars. Hard Timeout 3 s pro Call, Fallback auf bestehende Heuristik / Template-Pools, damit das Spiel auch ohne LLM funktioniert. Keine Spiellogik im LLM — Entscheidungen, die das Outcome bestimmen, bleiben deterministisch im Server.

**Aufwand:** ~1.5 Wochen für 3.9.1–3.9.2, der Rest ist Backlog.

| #       | Was                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Status     |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 3.9.1   | **LLM-Provider-Abstraction** — `app/game/llm.py` mit `LLMClient` Protocol, `AnthropicClient` (urllib + 3 s timeout, kein extra dep) und `LocalOpenAIClient` (HTTP `/v1/chat/completions` für Ollama/Gemma 4). Provider-Selektion via `ANTHROPIC_API_KEY` oder `LLM_LOCAL_BASE_URL`+`LLM_LOCAL_MODEL`. Fallback no-op (Tests + Prod ohne LLM laufen weiter).                                                                                                                                                                                                                                                                                                                                        | ✅ done    |
| 3.9.2   | **AI-NPCs (Lobby-Filler-Bots, Release-Team)** — `app/game/bots/` mit BotManager + Pathfinding (BFS über room-graph aus Türen). LLM-Call alle 5 s pro Bot für High-Level-Intent, reactive Overrides für Body-in-Sight (sofort melden) und Meeting-Vote (heuristisch). Hold-E-Tasks: Bots skippen Mini-Game und auto-completen nach 4–6 s. Lobby-UI: Host-Button „+ Bot hinzufügen" (curated Names: Bot-Promptly, Bot-Cursor-Sr., Bot-StackOverflow, Bot-Junior, …). Phase 1: nur Release-Team-Bots. **+ Stuck-Detection** (PR #37): wenn der Bot mit Input nicht vorankommt (typisch wenn der room+door-Pathfinder einen Task hinter einem Desk pickt), Intent verwerfen, Task für 8 s blacklisten. | ✅ done    |
| 3.9.2.1 | **LLM-Call non-blocking** (PR #38, nach Live-Incident 2026-04-28) — `urllib.urlopen` ist sync, blockierte den `_tick_loop` für 3 s pro Anthropic-Timeout, und das **alle Räume gleichzeitig**. Fix: `BotManager._llm_executor: ThreadPoolExecutor`, `maybe_consult_llm` non-blocking dreigeteilt (reap → apply → submit). Bot fällt sofort heuristisch durch wenn LLM denkt, Result kommt beim nächsten Intent-Pick. Regression-Test mit 10 s blocking Stub-LLM.                                                                                                                                                                                                                                   | ✅ done    |
| 3.9.3   | **AI-Postmortem (real LLM)** — Bestehender `generate_postmortem(summary)` ruft jetzt `LLMClient` mit dem Round-Summary-JSON, Fallback auf den existierenden Template-Generator wenn kein Provider verfügbar oder Timeout. Prompt cached via Anthropic-Prompt-Caching auf den System-Prompt-Anteil.                                                                                                                                                                                                                                                                                                                                                                                                 | 🔮 backlog |
| 3.9.4   | **AI-Game-Master (Live-Commentary)** — Nach jedem signifikanten Event (Body-Found, Meeting-Start, Sabotage, Win) generiert das LLM eine kurze 1–2-Satz-Commentary-Zeile, die als Toast-Overlay erscheint. Async, blockiert nichts. Off-by-default per Env-Var.                                                                                                                                                                                                                                                                                                                                                                                                                                     | 🔮 backlog |
| 3.9.5   | **AI-Meeting-Summary** — Wenn ein Meeting endet, generiert das LLM aus `meeting.context.recentEvents` + Voting-Outcome eine 2-Satz-Zusammenfassung („Max wurde rausgevotet, obwohl er gerade Tasks gemacht hat — die Pipeline-Sabotage bleibt ungeklärt"). Erscheint im Eventfeed.                                                                                                                                                                                                                                                                                                                                                                                                                 | 🔮 backlog |
| 3.9.6   | **Chaos-Bots + AI-Map-Generator** — Phase-2-Bots können Chaos-Agent-Rolle übernehmen (LLM entscheidet wann Sabotage / Take-Down sinnvoll ist). Optional: `POST /api/maps/generate` mit Prompt → LLM produziert MapObject-JSON nach kinds.json-Schema, durchläuft normale Validation.                                                                                                                                                                                                                                                                                                                                                                                                               | 🔮 backlog |

**Design-Cuts (Phase 1 — 3.9.2):**

- **Release-Team only.** Chaos-Bots brauchen Game-Sense (Timing, Alibi-Building), das ist eigene Iteration.
- **Bots skippen Mini-Games.** Hold-E → 4–6 s → Task done. Mini-Games sind UI-Code, kein Bot soll DOM-clicken müssen.
- **LLM nur für High-Level-Intent.** Pathing/Movement/Vote ist deterministisch im Server. LLM darf Tempo nicht diktieren.
- **3 s Timeout, Fallback auf Heuristik.** Spiel muss ohne LLM laufen — sonst killt es uns die CI + Live-Tests ohne API-Key.
- **Curated Bot-Names statt LLM-generated.** Spieler sollen Bots erkennen können, plus Branding („Bot-Promptly" als Vibe).

**Done-Kriterium 3.9.2:** Host kann in der Lobby Bots hinzufügen, Bots laufen sinnvoll durch die Map, machen Tasks, melden Bodies wenn sie welche sehen, voten in Meetings nach Heuristik. Ohne LLM-Provider läuft alles weiter (heuristic-only mode).

### Tier 4 — Godot-Migration

**Ziel:** Browser-Client bleibt als Web-Fallback und Reference-Implementation. Godot wird der polished primary client mit echten Charakter-Animationen, 3D-Tilemaps, Sound-Mixing und Particle-Effects.

**Aufwand:** ~5–7 Wochen ab Production-Sprint, plus 0.5 Wochen 3D-Demo-Spike (geshippt).

**Stand 2026-05-12:** Tier 4.0–4.12 + 4.13 sind durch — Asset-Pipeline mit 25/25 Kinds gestaged, Web-Export auf https://prod-is-lava.dev/godot/ live, **vollständige Feature-Parität zum 2D-JS-Client erreicht** (alle 8 Mini-Games, Sabotage-Buttons, Meeting+Voting, Endscreen, Among-Us-Features inkl. Vents/Take-Down/Body-Report/Lights/Comms/Spectator, Auto-Reconnect, Polish mit Camera-Shake/Phase-Banner/Confetti). Verbliebene Asks: BGM (auf Tier 5.1 vertagt), Touch-Controls für Mobile (auf Tier 5.2 vertagt), Tier 4.0.3 DevOps-Theme-Spezial-Meshes. Vollständige Onboarding-Doku unter [`docs/GODOT_HANDOFF.md`](GODOT_HANDOFF.md). Schema-Konsolidierung via `maps/kinds.json` ist durch (siehe Tier 3.8.7).

#### Feature-Parität-Matrix (JS-Client → Godot-Client, Stand 2026-05-12)

| Bereich                      | 2D-JS-Client (Referenz)                      | Godot-3D-Client                                                        | Status                                     |
| ---------------------------- | -------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------ |
| Lobby-Connect                | Form (Name+Code) + Auto-WS                   | Web auto-derive WSS, Native ws://127.0.0.1:8000/ws                     | ✅ done                                    |
| Lobby-Map-Auswahl            | Dropdown aus `availableMaps`                 | OptionButton bound an availableMaps, Host-only-Edit                    | ✅ done (4.2.1, 890b8e2)                   |
| Lobby-Rollen-Präferenz       | Dropdown 5 Release-Rollen                    | OptionButton mit 5 Rollen + Random                                     | ✅ done (4.2.2, 890b8e2)                   |
| Lobby-Bot-Buttons (Tier 3.9) | add_bot / remove_bot pro Klick               | Buttons im Host-Panel                                                  | ✅ done (4.2.3, 890b8e2)                   |
| Movement                     | WASD + 20 Hz-Throttle                        | WASD + Pfeiltasten + 20 Hz                                             | ✅ done                                    |
| Map-Render (Walls/Doors)     | Canvas, Slice-3-Schema                       | 3D-Geometrie via `compute_walls`-Port + Door-Frames                    | ✅ done                                    |
| Map-Render (MapObjects)      | 2D-Boxen mit Fill+Label                      | KayKit-Meshes pro Kind; Fallback-Box bei unknown                       | ✅ done                                    |
| MapObject-Collision          | Server-side `_walls` enforced                | Server enforced + Lerp 35 + Snap-on-Pushback bei Wall-Clamp/Idle-Stuck | ✅ done (4.3.1, f7e30b7 + cfef514)         |
| TaskAnchor-Marker            | Floating Title + Status                      | Sphere mit Emission                                                    | ✅ done                                    |
| Vents                        | Interactive Object + V-Key Cycle             | V-Key Cycle + VFX                                                      | ✅ done (4.10, 8a8c078)                    |
| Hold-to-Interact (E)         | E-Key, sendet `task_hold_*`                  | E-Key, sendet `task_hold_*` mit Proximity-Check                        | ✅ done                                    |
| Mini-Game-Framework          | Modal + Registry, 8 Spiele                   | Modal + Registry, **8 Spiele**                                         | ✅ done (4.6, 2cd619c + 170daf0 + a4a8b88) |
| Personal-Task-Panel ★        | Sidebar mit eigenen Tasks markiert           | Sidebar mit ★ + amber Border                                           | ✅ done (4.5.1, b6ffb66)                   |
| Sabotage-Buttons             | 8 Icons + Cooldown-Ring + Object-Binding     | 8 Icons + Cooldown-Ring + Range-Check                                  | ✅ done (4.7, 5d13462)                     |
| Take-Down (Force-Reboot)     | Proximity-Button + War-Room-Safe             | Proximity-Button + Kill-Flash                                          | ✅ done (4.10, 8a8c078)                    |
| Body-Discovery + Report      | Proximity-Button mit Trigger                 | Proximity-Button + 3D-Body-Marker                                      | ✅ done (4.10, 8a8c078 + e1f0e3a)          |
| Lights-Sabotage VFX          | Radial Vignette                              | Radial Vignette                                                        | ✅ done (4.10, 8a0f6b4)                    |
| Comms-Sabotage VFX           | Sidebar leer + Buttons disabled              | Sidebar-blank-State                                                    | ✅ done (4.10, 8a0f6b4)                    |
| Spectator-Mode (Geist)       | Free-Move + sieht andere Geister             | Ghost-Banner + nur-Ghosts-sichtbar                                     | ✅ done (4.10, 8ab8591)                    |
| Meeting-Modal mit Context    | Reporter+Body+RecentEvents                   | Modal mit Context-Block (Reporter, Body, RecentEvents)                 | ✅ done (4.8, b324722)                     |
| Voting-UI (cast/skip)        | Buttons pro Spieler + Skip                   | Buttons pro Spieler + Skip                                             | ✅ done (4.8, b324722)                     |
| Voting-Result + Last-Words   | Toast mit AI-Quote                           | Slide-In-Toast mit Last-Words-Quote                                    | ✅ done (4.8, b324722)                     |
| HUD-Stats-Pills (4)          | Release/Pipeline/Coffee/Incidents + Timer    | analoge Stat-Bars                                                      | ✅ done                                    |
| HUD-Coffee-Bar (privat)      | private_state-bound, pulsiert <15            | private_state-bound + rot+pulsing <15                                  | ✅ done (4.5.2, b6ffb66)                   |
| HUD-Ability-Button           | Per-Rolle, 1×/Runde                          | Per-Rolle, 1×/Runde, disabled wenn used                                | ✅ done (4.5.3, b6ffb66)                   |
| HUD-Eventfeed                | Live-Log rechts, AI-flavored                 | RichTextLabel mit Severity-Klassen + AI-Texte                          | ✅ done (4.5.4, a069e53)                   |
| Role-Intro-Modal             | Beim Phase-Wechsel, 30 s Auto-Dismiss        | Modal mit Team/Role/Strengths/Ability/Tasks                            | ✅ done (4.5.5, a069e53)                   |
| Endscreen                    | Awards + Per-Player-Stats + AI-Postmortem    | Awards-Liste + Per-Player-Stats + AI-Postmortem + Confetti             | ✅ done (4.9, 72f279d)                     |
| Audio (Stings)               | role-reveal/meeting/kill/task-complete       | 4 Stings vorhanden                                                     | ✅ done                                    |
| Audio (Footsteps)            | Optional, JS-Client hat keine                | 5 Carpet-Samples                                                       | ✅ done                                    |
| Audio (BGM)                  | Optional, mute-toggle                        | bewusst ausgelassen                                                    | 🔮 vertagt auf Tier 5.1                    |
| In-Game-ESC-Menü             | Lobby-verlassen, Runde-beenden, Audio-Slider | Lobby-verlassen, Runde-beenden, kein Audio                             | 🔮 Audio-Slider auf Tier 5.1               |
| Touch-Controls (Mobile)      | Virtual joystick + 4 Action-Buttons          | gar nicht                                                              | 🔮 vertagt auf Tier 5.2                    |
| Reconnect bei DC             | Server bewahrt Identität 30 s                | Auto-Reconnect mit playerId-Persist + REJOIN-Fallback                  | ✅ done (4.12, 71ab9c4)                    |
| AI-NPC-Bots in Lobby         | add_bot / remove_bot Buttons                 | add_bot / remove_bot Buttons                                           | ✅ done (4.2.3, 890b8e2)                   |

#### Vor-Godot-Block (Decisions + Asset-Pipeline)

| #     | Was                                                                                                                                                                                                                                                                               | Status                                        |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| 4.0.1 | **Asset-Pipeline-Entscheidung** — Sven hat KayKit-Bits + Eigenproduktion bestätigt; Godot-Devs bauen die Pipeline.                                                                                                                                                                | ✅ entschieden                                |
| 4.0.2 | **Asset-Pipeline aufbauen** — `scripts/import_kaykit_assets.py` (Pipeline-Skript), 22 KayKit-Meshes für die noch unstaged Kinds vendored unter `godot-3d/assets/{furniture,kitchen,server}/`, `IMPORT_MANIFEST.txt` als CC0-Audit-Trail. Folgt `docs/ASSET_SPEC.md` (Tier 3.8.8). | ✅ done (2026-04-27, KayKit-Default-Sweep)    |
| 4.0.3 | **DevOps-Theme-Spezial-Meshes** (Coffee-Maschine, Server-Rack, Bug-Trophy, etc.) — DevOps-Flavor-Layer über die KayKit-Defaults; per kinds.json-Replace registriert, GLTF-Asset im Repo unter `godot-3d/assets/`.                                                                 | ⛔ offen, Godot-Team kann auf 4.0.2 aufsetzen |

Übergangs-Stand (2026-04-27): Alle 25 von 25 Kinds haben jetzt ein `godot_asset` (KayKit-Default-Mesh). Editor-3D-Preview + Godot-Client picken die Meshes automatisch auf, statt farbige Box-Fallbacks zu rendern. Tier 4.0.3 ist darüber-Layer: einzelne Kinds können durch DevOps-getunte Custom-Meshes ersetzt werden, indem das `godot_asset` einer Kind-Definition auf einen neuen Pfad zeigt — die Pipeline bleibt dieselbe.

**Wichtig für die Godot-Devs:** `.gltf.import`-Sidecar-Files sind für die 22 neuen Meshes noch NICHT committed (Godot generiert sie beim ersten Project-Open). Sobald jemand das Godot-Projekt öffnet und reimportiert, kommt der `.import`-Drift in einen Folge-Commit. Der Browser-3D-Preview braucht keine `.import`-Sidecars und rendert die Meshes ab sofort.

#### Godot-Sprint (refined nach Audit 2026-04-28)

Slice-Reihenfolge optimiert auf "User-spürbarer Pain zuerst": Sven hatte zwei konkrete Bug-Reports nach erstem Live-Test der Web-Build (durch Tische laufen, keine Map/Rollen-Auswahl), die bekommen 4.2/4.3-Sub-Slices.

| #     | Paket                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Aufwand  | Status                                                                                                     |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------- |
| 4.1   | Godot 4.6 Projekt-Setup, WebSocketPeer-Anbindung                                                                                                                                                                                                                                                                                                                                                                                                                         | 1 Tag    | ✅ via 3D-Demo                                                                                             |
| 4.2   | Lobby-Scene Basis (Raumcode, Spielerliste, Start, Demo-Mode)                                                                                                                                                                                                                                                                                                                                                                                                             | 1 Tag    | ✅ via 3D-Demo                                                                                             |
| 4.2.1 | **Lobby — Map-Auswahl-Dropdown** ← Sven-Pain. `lobby_state.availableMaps` an OptionButton koppeln, Host-only-Edit, `select_map`-Send wie im JS-Client.                                                                                                                                                                                                                                                                                                                   | 0.5 Tag  | ✅ done (2026-04-28, 890b8e2)                                                                              |
| 4.2.2 | **Lobby — Rollen-Präferenz-Dropdown** ← Sven-Pain. 5 Release-Rollen + "Random" als OptionButton, `set_preferred_role`-Send. Chaos-Wunsch wird ignoriert (Server-side).                                                                                                                                                                                                                                                                                                   | 0.5 Tag  | ✅ done (2026-04-28, 890b8e2)                                                                              |
| 4.2.3 | **Lobby — AI-NPC-Buttons** (Tier-3.9-Bots) — `add_bot` / `remove_bot` für den Host, kuratierte Bot-Namen aus dem Server-Pool.                                                                                                                                                                                                                                                                                                                                            | 0.5 Tag  | ✅ done (2026-04-28, 890b8e2)                                                                              |
| 4.3   | Map-Loader: JSON → 3D-Geometrie (Floors, Walls, Doors, Spawns, TaskAnchors, MapObjects)                                                                                                                                                                                                                                                                                                                                                                                  | 2 Tage   | ✅ done (KayKit-Meshes via Tier 4.0.2)                                                                     |
| 4.3.1 | **Client-Smoothing für MapObject-Collision** ← Sven-Pain "läuft durch Tische". Server enforced collision korrekt (`_walls + map_object_aabb`), aber 14.0-Lerp im character.gd lässt den Char visuell ~100ms in den Tisch reinlaufen, bevor Server-Snap-Back greift. Optionen: (a) Lerp-Speed auf 25.0 hoch, (b) clientseitige AABB-Reject auf bekannten blocking MapObjects, (c) Server-Tickrate hoch (teurer). Empfehlung: (a) zuerst probieren, (b) wenn nicht reicht. | 0.5 Tag  | ✅ done (2026-04-28, f7e30b7 + cfef514 — Lerp 35 + Snap-on-Pushback + Idle-Stuck-Trigger)                  |
| 4.4   | Charakter-Scene: Mesh + Idle/Walk-Animation + Movement-Interpolation                                                                                                                                                                                                                                                                                                                                                                                                     | 2–3 Tage | ✅ via 3D-Demo                                                                                             |
| 4.5   | HUD-Stats-Pills + Rolle + Timer                                                                                                                                                                                                                                                                                                                                                                                                                                          | 1 Tag    | ✅ via 3D-Demo                                                                                             |
| 4.5.1 | **HUD — Personal-Task-Panel mit ★** — Sidebar listet alle Tasks (room, status, progress), eigene Tasks bekommen ★ + amber Border. Quelle: `private_role.assignedTasks[]`.                                                                                                                                                                                                                                                                                                | 0.5 Tag  | ✅ done (2026-04-28, b6ffb66)                                                                              |
| 4.5.2 | **HUD — Coffee-Bar Pulse < 15** — vorhandene Coffee-Bar bekommt rot+pulsing-Animation wenn `private_state.coffeeEnergy < 15` (Speed-Penalty-Threshold).                                                                                                                                                                                                                                                                                                                  | 0.25 Tag | ✅ done (2026-04-28, b6ffb66)                                                                              |
| 4.5.3 | **HUD — Active-Ability-Button** — Per-Rolle (Coffee Run, Rollback, Standup, Reproduce Bug), 1×/Runde, sendet `use_ability`. Disabled wenn `private_state.abilityUsed=true` oder phase!=playing.                                                                                                                                                                                                                                                                          | 0.5 Tag  | ✅ done (2026-04-28, b6ffb66)                                                                              |
| 4.5.4 | **HUD — Eventfeed** — RichTextLabel rechts, scrollt zu newest, Severity-Klassen (info/warn/error). Server-Events aus `game_state.events[]`. AI-flavored Texte (Tier 3.6/3.9).                                                                                                                                                                                                                                                                                            | 0.5 Tag  | ✅ done (2026-04-28, a069e53)                                                                              |
| 4.5.5 | **Role-Intro-Modal** — beim phase=playing-Wechsel: Modal mit Team-Color, Rolle, Description, Strengths, Ability, AssignedTasks. 30 s Auto-Dismiss oder Click-to-close. Dedupe wenn role_id unverändert.                                                                                                                                                                                                                                                                  | 0.5 Tag  | ✅ done (2026-04-28, a069e53)                                                                              |
| 4.6   | **Mini-Games-Sweep — 7 fehlende Spiele** — sprint_trim ist fertig. Portieren: test_suite_repair (sequencing), cable_pairing (drag-pair), coffee_pour (timing-stop), log_filter (multi-select), diff_review (filter-by-criterion), stability_balance (rotating-correction), release_notes (click-to-cycle-sort). Alle nutzen die existierende Modal+Registry-Architektur, nur die UI pro Spiel ist neu.                                                                   | 4–5 Tage | ✅ done (2026-04-28, 2cd619c + 170daf0 + a4a8b88 — 8/8 Mini-Games)                                         |
| 4.7   | **Sabotage-Buttons** — 8 Icons aus `images/sabotage_icons.png`, Cooldown-Ring + numeric, Object-Binding-Reichweiten-Check (60 px), Disabled-States (ghost, comms-down). Sendet `trigger_sabotage`.                                                                                                                                                                                                                                                                       | 1 Tag    | ✅ done (2026-04-28, 5d13462)                                                                              |
| 4.8   | **Meeting + Voting** — Meeting-Modal mit Context-Block (Reporter, Body+Room, RecentEvents-`<details>`), Voting-Buttons pro Spieler + Skip. `voting_result`-Toast mit Slide-In + Last-Words-Quote.                                                                                                                                                                                                                                                                        | 1.5 Tage | ✅ done (2026-04-28, b324722)                                                                              |
| 4.9   | **Endscreen** — finalSummary-bound: Awards-Liste, Per-Player-Stats (Tasks, Sabotagen, Coffee-final, Ability-used), AI-Postmortem `<pre>`-Block, Confetti-Particles. Reset-Button (host-only) sendet `return_to_lobby`.                                                                                                                                                                                                                                                   | 1 Tag    | ✅ done (2026-04-28, 72f279d)                                                                              |
| 4.10  | **Among-Us-Features** — Vents (V-Key + Animation + Sting), Take-Down (Proximity-Button + Cooldown), Body-Discovery + Report-Button, Lights-Vignette (radial alpha-overlay auf CanvasLayer), Comms-Disable (Sidebar-blank), Spectator-Mode (free-fly cam, only-ghosts-visible).                                                                                                                                                                                           | 5–8 Tage | ✅ done (2026-04-28, 8a8c078 + 8a0f6b4 + 8ab8591)                                                          |
| 4.11  | **Sound-Polish** — Footstep-Variants pro Floor-Material (kitchen-tile vs carpet vs concrete), BGM optional mit Mute-Toggle, mehr UI-Stings.                                                                                                                                                                                                                                                                                                                              | 1 Tag    | ✅ done (2026-04-28, f9fbe1a + f68a6bc — Camera-Shake + Phase-Banner + Confetti; BGM auf Tier 5.1 vertagt) |
| 4.12  | **Polish-Sweep** — Touch-Controls für Mobile (virtual joystick + Action-Buttons), Auto-Reconnect (rejoin-Message bei WS-DC), In-Game-ESC-Menü Audio-Slider, Bug-Fixes aus Live-Tests, FPS-Counter optional.                                                                                                                                                                                                                                                              | 3–5 Tage | ✅ done (2026-04-28, 71ab9c4 — Auto-Reconnect; Touch-Controls auf Tier 5.2 vertagt)                        |
| 4.13  | Web-Export-Deploy auf EC2 — `scripts/godot-web-export.sh`, GHA-Job `web-export` baut + Artifact, Deploy-Job zieht ins Tarball, FastAPI mountet `/godot/` mit COOP/COEP. Live unter https://prod-is-lava.dev/godot/.                                                                                                                                                                                                                                                      | 0.5 Tag  | ✅ done (2026-04-28)                                                                                       |

**Done-Kriterium:** Godot-Web-Build läuft auf prod-is-lava.dev, fühlt sich „wie Among Us, dev-themed" an, hat mindestens dieselbe Featuredecke wie Browser-Client, plus Animationen + Sound + Particles. Live-Test mit echten Spielern bestätigt das Tier-Übergang.

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

**Aktueller Stand (2026-05-12):** Tier 0–3.8.7 + Tier 4 (Godot-Sprint) durch. Browser-Client komplett. Editor mit 2D + 3D-Vorschau, Server-Save, Floor-Texturen, Door-Frames. **Kinds-Registry konsolidiert** (3.8.7) — alle 4 Konsumenten (Backend, Editor, Browser, Godot) lesen `maps/kinds.json`. **Godot-Client production-ready** — alle 8 Mini-Games, Sabotage-Buttons, Meeting/Voting, Endscreen, Among-Us-Features (Vents, Take-Down, Body-Report, Lights/Comms-VFX, Spectator), Auto-Reconnect, Polish (Camera-Shake, Phase-Banner, Confetti). Web-Export läuft auf https://prod-is-lava.dev/godot/. Public-Prep-Pass durch (LICENSE, SECURITY, CoC, Issue-Templates, Dependabot — Commit `d9c6cac` #42).

**Direkt als nächstes (Public-Flip-Phase):**

- **Dependabot-Welle triagieren** (#43–#52, alle vom 28.04.) — major bumps prüfen, mergen oder schließen, bevor das Repo public geht.
- **Visibility-Flip auf public** — `gh repo edit --visibility public` (manueller Step nach Triage).
- **Live-Test-Sweep** mit echten Spielern auf dem Godot-Client — Bug-Surface, Balance-Feedback, Vergleich zum Browser-Client. Tier-4-Übergangs-Validierung laut Done-Kriterium.

**Lower priority (anytime):**

- **Editor-QoL** — Keyboard-Shortcuts, Multi-Select, Duplicate. ~1–2 h.
- **`/api/metrics`** — Aggregations-Endpoint für die JSONL-Files aus Tier 3.7.6. Hilft beim Balancing nach Live-Tests. ~45 min.
- **Tier 3.8.8 — `docs/ASSET_SPEC.md`** schreiben. Naming-Convention, Pivot/Polycount, kinds.json-Erweiterungs-Workflow. ~30 min.
- **Tier 3.8.9 — `datacenter`-Map befüllen** mit ~100 MapObjects via Generator-Skript (analog `populate_office_complex.py`). ~1 h.
- **Tier 4.0.3 DevOps-Theme-Spezial-Meshes** — Coffee-Maschine, Server-Rack, Bug-Trophy als DevOps-Flavor-Layer über die KayKit-Defaults.

**Anschließend:** Tier 5 (Polish + Distribution) als ongoing Slices — BGM, Mobile/Touch-Controls, Skins, Awards. Tier 6 (Community + Mod-Support), Tier 7 (Live-Service).

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
- [`docs/GODOT_HANDOFF.md`](GODOT_HANDOFF.md) — Tier-4-Onboarding für den externen Godot-Entwickler
- [`docs/HOWTO-SABOTAGE.md`](HOWTO-SABOTAGE.md), [`HOWTO-MINIGAME.md`](HOWTO-MINIGAME.md), [`HOWTO-ROLE.md`](HOWTO-ROLE.md) — Contributing-Guides für neue Inhalte
- [`AGENTS.md`](../AGENTS.md) — Repo-weiter Onboarding-Guide für AI-Agents (Stack, Commands, Conventions)
- `merge_conflict_mayhem_project/` — ursprüngliches Design-Paket von Sven, behalten als historische Inspirations-Quelle (Roadmap ersetzt es)
