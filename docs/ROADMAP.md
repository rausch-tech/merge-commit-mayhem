# Merge Conflict Mayhem — Roadmap

> **Vision:** Ein Among-Us-artiges Social-Deduction-Game für Tech-Teams. Statt einer Raumstation: ein Software-Büro mitten im Release. Statt Crewmates und Imposter: Release-Team und Chaos-Agenten. Mit der Mechanik-Klarheit von Among Us und der Insider-Komik eines Engineering-Teams in der Krise.

Dieses Dokument ist der **eine** Plan. Es ist die Wahrheit über den Stand und die Reihenfolge. Andere Docs erklären Sub-Themen (Map-Schema, Contributing, Architektur), aber Roadmap und Status leben hier.

---

## Stand (2026-04-27)

|                         |                                                                                                                                                                                                                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Repo**                | https://github.com/rausch-tech/merge-commit-mayhem                                                                                                                                                                                                                                                                    |
| **Live (Test-Server)**  | https://game.prod-is-lava.dev                                                                                                                                                                                                                                                                                         |
| **Backend-Tests**       | 471 grün (`uv run pytest`)                                                                                                                                                                                                                                                                                            |
| **Frontend-Tests**      | 37 grün (`npx vitest run`)                                                                                                                                                                                                                                                                                            |
| **Stack**               | Python 3.12 + FastAPI + Pydantic v2 + WebSockets, Vanilla JS + Canvas, Map als JSON-Daten, Vitest + happy-dom für Frontend-Smoke                                                                                                                                                                                      |
| **Geshippte Tier 0–3.5/3.6/3.7** | Foundation cleanup, Mechanik-Komplettierung, Among-Us-Features, Mini-Game-Framework, Persona-Layer (Rollen + persönliche Tasks + Coffee-Energy), Object-Bound-Sabotage, Endscreen-Story — auf Live deployt                                                                                                |
| **Geshippte Slice-IDs** | … → mobile-drawers-minimap → cable-pairing → coffee-pour → log-filter → sprint-trim → protocol-audit → sabotage-console (verworfen) → sabotage-object-binding → roles-and-personal-tasks → coffee-energy-and-abilities → meeting-context → endscreen-story → ai-flavor → lobby-role-preference                         |

**Was funktioniert (Live, Stand 2026-04-26):**

- 4–12 Spieler joinen einen Raum (Multi-Map-Auswahl in Lobby, Map-Editor unter `/editor`).
- 4800×3200-Map mit Räumen, Wänden, Türen, Vents, Sabotage-Panels. Camera scrollt am Spieler.
- Rollen werden privat verteilt (vibe_coder/developer, mehrere Chaos ab 7 Spielern).
- Hold-E auf 7 von 8 Tasks; `fix_unit_tests` startet das Mini-Game „Test-Suite reparieren" (klick 5 Tests in numerischer Reihenfolge).
- 7 Sabotagen: ci_cd_red, coffee_outage, mandatory_meeting, merge_conflict_storm, fake_customer_request, flaky_tests, lights_out (Vignette + Repair am Panel im Server-Room), comms_outage (Slack-Down: Tasks + andere Sabotagen blockiert, Repair am Panel im War-Room).
- Take-Down + Body-Discovery + Report-Trigger; Spectator-Mode für Geister (können noch Tasks erledigen).
- Vents: Chaos-only Teleport-Netzwerk, V-Taste cycelt durch Verbindungen.
- Voting + Endscreen mit Rollen-Reveal; In-Game-Menü via ESC mit Lobby verlassen / Runde beenden / Audio.
- Eventfeed rechts neben Canvas; konsistente HUD-Stats (Release, Pipeline, Coffee, Incidents, Timer, Rolle).
- Auto-Deploy auf jedem main-Push via GitHub Actions; CI gates pytest + vitest + ruff (lint+format) + prettier.

**Offen vor dem Godot-Sprint:**

- Asset-Pipeline-Entscheidung (Tier 4.0.x) bevor Tier 4 startet.

---

## Architektur (high-level)

> **Python entscheidet. Der Client zeigt nur an.**

- **Server** (FastAPI + WebSocket) ist autoritativ für **allen** State. 20-Hz-Tick-Loop berechnet Positionen, Task-Progress, Sabotage-Cooldowns, Win-Conditions.
- **Client** (Browser via Vanilla JS, später Godot) sendet nur Inputs, rendert empfangene Snapshots. Keine Spiellogik im Frontend.
- **Map als JSON** in `maps/default.json`. Server lädt + validiert beim Start, schickt Karte beim Join an den Client. Single Source of Truth, mod-tauglich, Editor-fähig.
- **WS-Protokoll** ist client-agnostisch. Browser-Client und Godot-Client werden parallel gegen denselben Server laufen.

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
| 1.9 | **In-Game-Menü** — ESC-Overlay mit Lobby verlassen (alle), Runde beenden (host-only), Audio-Controls reingezogen, Rolle/Aufgaben-Recap                   | ~1 Tag  |

**Done-Kriterium:** Browser-Client deckt das gesamte Master-Doc-MVP ab plus Eventfeed plus Map-Editor plus In-Game-Menü. Mit 8 Leuten testbar. Multi-Map-Auswahl in der Lobby. Spieler können die Runde jederzeit verlassen, Host kann sie beenden.

### Tier 2 — Among-Us-Features

**Ziel:** Die Mechaniken, die Among Us spielenswert machen, in unserer Tech-Office-Variante. Hier wird das Spiel von „funktional MVP" zu „echtes Game".

**Aufwand:** ~2 Wochen.

| #   | Was                                                                                                                                                                                                                     | Status  | Naming-Idee                                           |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ----------------------------------------------------- |
| 2.1 | **Take-Down-Mechanik** — Chaos kann Spieler im Proximity-Radius außer Gefecht setzen. Cooldown ~25 s. Kein Take-Down im War Room (Sicherheitszone).                                                                     | ✅ done | „Force-Reboot", „Captcha-Loop", „LinkedIn-Spam-Blast" |
| 2.2 | **Body-Discovery + Report** — eliminierte Spieler bleiben als „Body" sichtbar bis entdeckt. Lebende Spieler in Proximity können Report-Button drücken → triggert Meeting.                                               | ✅ done | „Stale-Process-Found", Ghost = „Coredumped Engineer"  |
| 2.3 | **Vents** — Chaos kann zwischen vorab-definierten Punkten teleportieren. Map-JSON kriegt `vents: [...]`-Feld. Animation + Sound.                                                                                        | ✅ done | „SSH-Tunnel", „Internal-Pipeline"                     |
| 2.4 | **Lights-Sabotage** — Sichtbarkeits-Reduktion: Viewport bekommt Vignette, Spieler sehen nur ~150 px Radius um sich herum. Repariert durch Interact mit „Electrical Panel" (im Server Room).                             | ✅ done | „PagerDuty-Storm" / „Production-Outage"               |
| 2.5 | **Comms-Sabotage** — Tasks-Sidebar wird leer (kann nicht erfüllt werden), Sabotage-Buttons disabled. Repariert durch Interact mit „Comms Panel" (im War Room).                                                          | ✅ done | „Slack-Down", „Confluence-Outage"                     |
| 2.6 | **Spectator-Mode für Geister** — Tote Spieler können sich frei durch die Map bewegen, andere Geister sehen, Lebende sehen sie nicht. Tasks erfüllen können sie weiter (helfen Release-Team), aber nicht mehr abstimmen. | ✅ done | „Coredumped"                                          |
| 2.7 | **Sabotagen an Themen-Objekte binden** — jede Sabotage triggert nur in 60-px-Reichweite eines Task-Anchors mit passendem `objectType` (CI-Konsole, Git-Terminal, Kaffeemaschine, Monitoring-Panel etc.). Same Anchor wie Release-Tasks → outsider sehen nicht, ob da gearbeitet oder sabotiert wird. Per-Sabotage Hint + Button-Disable wenn ausser Reichweite. Erste Iteration mit dedizierter Console wurde verworfen (zu offensichtlich).                                | ✅ done | „Sabotage-Object-Binding"                             |

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
| 3.5 | **„Logs analysieren"** (für `analyze_logs`) — 8 Log-Zeilen mit gemischtem Severity, Multi-Select aller ERROR-Zeilen, Click auf WARN/INFO ist Soft-Reset.                                  | ✅ done |
| 3.6 | **„Scope reduzieren"** (für `reduce_scope`) — 6 Sprint-Tickets mit Story-Points, entferne Tickets bis Restsumme <= Budget; Priority-Tickets duerfen NICHT entfernt werden (Soft-Reset).   | ✅ done |

**Done-Kriterium:** Eine Task läuft komplett über ein Mini-Game (Server-validiert), die anderen 7 bleiben Hold-E. Das Mini-Game-API ist dokumentiert und Live-getestet, sodass weitere Mini-Games als eigene Slices folgen können (Code-Review-Simulator, Logs-Filtern, Coffee-Pour-Timing usw.). Mit Tier 3.3-3.6 stehen jetzt fuenf Mechanik-Patterns (Sequencing, Pairing, Timing, Filter-by-Criterion, Subset-by-Constraint) als Vorlagen fuer kuenftige Tasks. Stand jetzt: 5 von 8 Tasks haben ein Mini-Game.

### Tier 3.5 — Rollen, persönliche Tasks & Kaffee-Energy (Persona Layer)

**Ziel:** Vom „alle teilen einen Task-Pool, eine Release-Rolle" zum „jeder ist ein Spezialist mit eigenem Backlog und eigener Ressource". Ist der grosse Architektur-Shift, der Social-Deduction-Diskussionen erst trägt: „Warum war der Scrum Master im Server Room?" / „Warum hatte DevOps keinen Kaffee mehr?".

**Quelle der Anforderungen:** `merge_conflict_mayhem_project/merge_conflict_mayhem_gesamtfeedback.md` (Teile A–E, P-Prompt).

**Aufwand:** ~2 Wochen, in einer Rutsch-Session am 2026-04-26 grundgelegt.

| #   | Was                                                                                                                                                                                                                          | Status  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 3.5.1 | **5 Release-Rollen** — Developer / DevOps Engineer / QA Lead / Scrum Master / Caffeine Collector. Jede mit Stärken (Task-Kategorien × 1.35), Schwächen (× 0.75), eigenem Kaffee-Profil (decay-modifier, max_coffee).            | ✅ done |
| 3.5.2 | **3 Chaos-Rollen** — Vibe Coder (AI/Code), Rogue Consultant (Process/Scope), Shadow Admin (Infra). Unterschiedliche `available_sabotages` pro Variante.                                                                       | ✅ done |
| 3.5.3 | **Persönliche Task-Backlogs** — jeder Spieler kriegt 3 Tasks (2 strength-passend + 1 random). Chaos kriegt 3 Fake-Tasks passend zur Tarn-Persona. UI markiert eigene Tasks mit ★ in der Sidebar.                              | ✅ done |
| 3.5.4 | **Coffee-Energy pro Spieler** — `coffee_energy: 0..max_coffee`. Decay 1.4/s × Rolle-Modifier. <15 = Speed-Penalty, ≥80 = Task-Bonus. Eigene Pille im HUD, pulsiert rot wenn niedrig.                                          | ✅ done |
| 3.5.5 | **Aktive Fähigkeiten** — `use_ability` 1×/Runde: Rollback (DevOps +18 Pipeline), Coffee Run (CC bufft Nachbarn), Standup (Scrum Master ruft Meeting), Reproduce Bug (QA flagged Recent Action). Button im HUD.               | ✅ done |
| 3.5.6 | **Lobby-Rollen-Präferenz** — Dropdown in der Lobby, Wunsch wird best-effort respektiert. Singleton-Rollen capped at 1. Chaos-Wunsch wird ignoriert (random).                                                                  | ✅ done |
| 3.5.7 | **Role-Intro-Modal** — beim Phase-Wechsel lobby→playing zeigt jeder Spieler eine Rollen-Karte: Titel, Blurb, Stärken, Fähigkeit, Aufgaben. Auto-dismiss nach 30 s.                                                            | ✅ done |
| 3.5.8 | **Task-Speed-Modifier serverseitig** — `task_speed_multiplier(role, category, coffee)` läuft in `_tick_tasks` + `_complete_mini_game`-Reward-Pfad. Movement-Multiplier nur als Penalty bei niedrigem Coffee (Tests bleiben stabil). | ✅ done |

**Done-Kriterium:** Spieler erleben spürbar unterschiedliche Rollen, Persönliche Tasks lenken Bewegung, Kaffee ist eine echte Ressource. Live-Test mit ≥6 Personen.

### Tier 3.6 — Meeting-Kontext, Object-Bound-Sabotage & AI-Flavor

**Ziel:** Diskussionen kriegen Substanz (was war wo? wer war involviert?), Sabotage wird ambig statt offensichtlich (Tier 2.7 rework), AI-Flavor durchzieht Eventfeed + Postmortem.

**Aufwand:** ~1.5 Wochen, ebenfalls am 2026-04-26 in derselben Rutsch-Session.

| #   | Was                                                                                                                                                                                                                          | Status  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 3.6.1 | **Sabotage-Object-Binding (Tier 2.7 rework)** — dedizierte Console rausgeworfen (zu offensichtlich), stattdessen jede Sabotage an Task-Anchor mit passendem `object_type` gebunden. Same Anchor wie Release-Task → Ambiguität.  | ✅ done |
| 3.6.2 | **Meeting-Kontext** — `meeting.context = {reporterName, body? {victimName, room}, recentEvents[]}`. Snapshot zum Meeting-Start. UI zeigt Block über Voting-Liste. Hinweise, keine Beweise.                                    | ✅ done |
| 3.6.3 | **AI-Flavor-Texte** — `app/game/ai_flavor.py` mit reichen LLM-styled Pools für Sabotage-Events („CI hatte einen Hallucinations-Anfall"), Repair, Body-Found, Vote-Kick. Vibe Coder bekommt AI-Sabotage-Themen.                   | ✅ done |
| 3.6.4 | **Accusation-Tags / Voting-Polish** — Schritt nach hinten: Voting-UI bleibt erstmal wie sie ist, Tags sind ein eigener Slice (bringt mit Voice-Chat den meisten Wert).                                                         | ⏳ open |
| 3.6.5 | **Voting-Result-Story** — Roll-out kann später mit „last words" Flavor-Line erweitert werden.                                                                                                                                | ⏳ open |

**Done-Kriterium:** Meetings haben Substanz; Saboteure müssen sich physisch ans Object stellen (kein Verrats-Pattern); Eventfeed + Postmortem fühlen sich AI-generiert an.

### Tier 3.7 — Endscreen-Story, Closing Mini-Games & Metriken

**Ziel:** Nach jeder Runde gibt's Diskussionsstoff (Awards, Stats, AI-Postmortem). Verbleibende Hold-E-Tasks bekommen ihre Mini-Games. Server exportiert Metriken für Balancing.

**Aufwand:** ~1.5 Wochen.

| #   | Was                                                                                                                                                                                                                          | Status  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| 3.7.1 | **Endscreen-Story + Per-Player-Stats** — `final_summary` mit Per-Player (Tasks, Sabotagen, Coffee-final, Ability-used), Awards (Pipeline Whisperer, Vibe of the Round, Held der Kaffeemaschine, Most Suspicious Innocent).      | ✅ done |
| 3.7.2 | **AI-Postmortem-Generator** — `generate_postmortem(summary)` produziert mehrzeiligen LLM-styled Text. Im Endscreen unter `<pre>` gerendert.                                                                                  | ✅ done |
| 3.7.3 | **`review_pr` Mini-Game** — Diff-Review: 5–8 Code-Zeilen, 2 problematische markieren (hardcoded API key, `catch(Exception){}`, `console.log`, …). Pattern: Spot-the-Bug.                                                       | ⏳ open |
| 3.7.4 | **`calm_legacy_service` Mini-Game** — Stabilitäts-Balancing: CPU/Memory/Queue in grünem Bereich halten, jede Korrektur drückt einen anderen Wert leicht weg.                                                                  | ⏳ open |
| 3.7.5 | **`write_release_notes` Mini-Game** — Drag/Click-Sort: Commits in Feature/Bugfix/Breaking-Change/Should-Not-Be-Mentioned-Publicly einordnen.                                                                                  | ⏳ open |
| 3.7.6 | **Metrik-Export (JSONL)** — pro Runde: Winrate, Rundendauer, Meetings, Force-Reboots, Tasks/Rolle, Sabotagen, Repairs, Coffee-Avg. Datei pro Runde unter `data/playtest/`.                                                    | ⏳ open |
| 3.7.7 | **Heatmaps (optional, später)** — Movement, Kills, Body-Discovery, Sabotage-Trigger pro Map. Hilft Map-Balancing.                                                                                                            | 🔮 backlog |

**Done-Kriterium:** Endscreen erzählt die Runde, alle 8 Tasks haben Mini-Games, Server logged Balance-Metriken.

### Tier 4 — Godot-Migration

**Ziel:** Browser-Client bleibt als Web-Fallback und Reference-Implementation. Godot wird der polished primary client mit echten Charakter-Animationen, Tilemaps, Sound-Mixing und Particle-Effects.

**Aufwand:** ~5–7 Wochen.

Der Godot-Sprint kommt **nach** Tier 0–3, weil:

- Mit unfinishedem Browser doppelte Feature-Arbeit
- Ohne Foundation-Cleanup (Tier 0) keine Test-Sicherheit beim Porten
- Ohne Among-Us-Features im Browser (Tier 2) keine klare Spec für Godot
- Ohne Mini-Game-API im Browser (Tier 3) doppelte Mini-Game-Arbeit in Godot

#### Vor-Godot-Block (Decisions, ~1 Woche)

| #     | Was                                                                                                                    | Status           |
| ----- | ---------------------------------------------------------------------------------------------------------------------- | ---------------- |
| 4.0.1 | Asset-Pipeline-Entscheidung — Pixel-Art-Pack einkaufen + AI-generierte DevOps-Sprites (Coffee-Maschinen, Server-Racks) | Sven entscheidet |
| 4.0.2 | Asset-Pack-Beschaffung — itch.io / Humble / Synty research + Lizenz-Doku                                               | 1 Tag            |
| 4.0.3 | DevOps-Theme-Sprites generieren oder commission'en (Coffee, Server, Bug, etc.)                                         | 1–3 Tage         |

#### Godot-Sprint (~4–6 Wochen)

| #    | Paket                                                                                                                        | Aufwand  |
| ---- | ---------------------------------------------------------------------------------------------------------------------------- | -------- |
| 4.1  | Godot 4 Projekt-Setup, Web-Export-Config, WebSocketPeer-Anbindung                                                            | 1 Tag    |
| 4.2  | Lobby-Scene (UI, Raumcode-Input, Spielerliste, Map-Auswahl, Start)                                                           | 1–2 Tage |
| 4.3  | Map-Loader: Map-JSON → Tilemap-Layer dynamisch                                                                               | 2 Tage   |
| 4.4  | Charakter-Scene: Sprites + 4-Richtungs-Idle/Walk-Animation + Movement-Interpolation                                          | 2–3 Tage |
| 4.5  | HUD + Stat-Pills + Rolle + Timer mit Tween-Animationen                                                                       | 1 Tag    |
| 4.6  | Task-Interaktion (Mini-Game-Modals via Tier-3-API + Progress-Ring + Completion-VFX)                                          | 2 Tage   |
| 4.7  | Sabotage-Buttons mit Cooldown-Anzeige                                                                                        | 1 Tag    |
| 4.8  | Voting-Overlay + Result-Toast mit Slide-Animationen                                                                          | 1 Tag    |
| 4.9  | Endscreen mit Rollen-Reveal + Stats + Confetti-Particles                                                                     | 1 Tag    |
| 4.10 | Among-Us-Features: Vents (Animation + Sound), Body-Discovery + Report, Take-Down-Animation, Lights/Comms-VFX, Spectator-Mode | 5–8 Tage |
| 4.11 | Sound-Integration (Footsteps, UI-SFX, BGM)                                                                                   | 1 Tag    |
| 4.12 | Polish + Bug-Fixes                                                                                                           | 3–5 Tage |
| 4.13 | Web-Export-Deploy auf gleiche EC2                                                                                            | 0.5 Tag  |

**Done-Kriterium:** Godot-Web-Build läuft auf gleichem Server, fühlt sich „wie Among Us, dev-themed" an, hat mindestens dieselbe Featuredecke wie Browser-Client, plus Tier-2-Animationen + Sound + Particles.

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

| #   | Was                                                                                                                                                                                                                                             | Aufwand  |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| 6.1 | **Tasks aus JSON** (`tasks.json`) — Reward-Werte, Räume, Dauern. Code lädt validiert.                                                                                                                                                           | 1 Tag    |
| 6.2 | **Sabotagen aus JSON** (`sabotages.json`)                                                                                                                                                                                                       | 1 Tag    |
| 6.3 | **Rollen aus JSON** (`roles.json`) — Team, Description, available Sabotagen, Spezial-Fähigkeiten                                                                                                                                                | 1.5 Tage |
| 6.4 | **Eventtexte aus JSON** (`event_texts.json`) — Pool pro Event-Typ, zufällig                                                                                                                                                                     | 0.5 Tag  |
| 6.5 | **Map-Editor Phase 2** — Live-Preview (Map sofort spielen), Validierung visualisieren, mehrere Maps gleichzeitig                                                                                                                                | 2–3 Tage |
| 6.6 | **Map-Browser** — Liste aller `maps/*.json` mit Vorschau, Hot-Reload                                                                                                                                                                            | 1 Tag    |
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

**Aktueller Stand (2026-04-26):** Tier 0–3 sind durch. Browser-Client deckt das gesamte Among-Us-Feature-Set ab; drei Mini-Games (Sequencing/Pairing/Timing) decken bereits drei der acht Tasks ab.

**Als nächstes:** Asset-Pipeline-Entscheidung (Tier 4.0.x) anstossen — Pixel-Art-Pack einkaufen vs. AI-generierte DevOps-Sprites. Parallel weitere Mini-Games (Tier 3) fuer die restlichen 5 Tasks, wann immer eine als zu „flach" auf Live auffaellt.

**Vor Godot:** Asset-Pipeline-Entscheidung (Tier 4.0.x) — Pixel-Art-Pack einkaufen vs. AI-generierte DevOps-Sprites. Sven entscheidet.

**Wochen 1–7 ab Godot-Start:** Tier 4 (Godot-Migration mit Polish).

**Anschließend:** Tier 5–7 als ongoing Slices.

Mit Asset-Pack-Hilfe und ohne Mobile/Account: ~2 Monate ab Tier 4 bis „polished public-fähig".

---

## Wie wir entscheiden

- **Slices** sind die Arbeitseinheit. Jede Slice hat ihren eigenen Branch (`slice/<kurztitel>`), Tests, Live-Server-Restart nach Merge.
- **Specs/Plans** schreiben wir nur für nicht-triviale Slices (>1 Tag Aufwand). Kleinere Slices fließen direkt in den Implementer-Prompt ein.
- **Live-Tests** validieren Tier-Übergänge — bevor wir ein Tier fertig erklären, mit echten Spielern testen.

---

## Verwandte Docs

- `docs/maps.md` — Map-JSON-Schema (Referenz für Map-Bauer)
- `docs/CONTRIBUTING.md` — wie Mitarbeitende beitragen können (kommt mit Tier 6.0)
- `docs/PROTOCOL.md` — vollständiger WS-Vertrag (kommt mit Tier 0.4)
- `docs/ARCHITECTURE.md` — High-Level-Overview (kommt mit Tier 0.5)
- `docs/DEPLOY.md` — Deploy-Workflow (kommt mit Tier 0.6)
- `docs/DEV.md` — lokale Entwicklung (kommt mit Tier 0.7)
- `merge_conflict_mayhem_project/` — ursprüngliches Design-Paket von Sven, behalten als historische Inspirations-Quelle (Roadmap ersetzt es)
