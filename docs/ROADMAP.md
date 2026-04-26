# Merge Conflict Mayhem — Roadmap

> **Vision:** Ein Among-Us-artiges Social-Deduction-Game für Tech-Teams. Statt einer Raumstation: ein Software-Büro mitten im Release. Statt Crewmates und Imposter: Release-Team und Chaos-Agenten. Mit der Mechanik-Klarheit von Among Us und der Insider-Komik eines Engineering-Teams in der Krise.

Dieses Dokument ist der **eine** Plan. Es ist die Wahrheit über den Stand und die Reihenfolge. Andere Docs erklären Sub-Themen (Map-Schema, Contributing, Architektur), aber Roadmap und Status leben hier.

---

## Stand (2026-04-26)

|                         |                                                                                                                                                                                                                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Repo**                | https://github.com/rausch-tech/merge-commit-mayhem                                                                                                                                                                                                                                                                    |
| **Live (Test-Server)**  | https://game.prod-is-lava.dev                                                                                                                                                                                                                                                                                         |
| **Backend-Tests**       | 448 grün (`uv run pytest`)                                                                                                                                                                                                                                                                                            |
| **Frontend-Tests**      | 35 grün (`npx vitest run`)                                                                                                                                                                                                                                                                                            |
| **Stack**               | Python 3.12 + FastAPI + Pydantic v2 + WebSockets, Vanilla JS + Canvas, Map als JSON-Daten, Vitest + happy-dom für Frontend-Smoke                                                                                                                                                                                      |
| **Geshippte Tier 0–3**  | Foundation cleanup, Mechanik-Komplettierung, Among-Us-Features, Mini-Game-Framework — alles auf Live deployt                                                                                                                                                                                                          |
| **Geshippte Slice-IDs** | lobby-movement → game-loop → scrolling-camera → spritesheets → character-sprites → walls → voting → map-data → eventfeed → incidents → tasks-1.4 → sabotages-1.4 → multi-chaos → audio-mute → map-editor → multi-map → in-game-menu → take-down → spectator → lights-out → vents → comms-outage → minigames-framework → mobile-touch-quickhack → mobile-drawers-minimap → cable-pairing → coffee-pour |

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

**Done-Kriterium:** Eine Task läuft komplett über ein Mini-Game (Server-validiert), die anderen 7 bleiben Hold-E. Das Mini-Game-API ist dokumentiert und Live-getestet, sodass weitere Mini-Games als eigene Slices folgen können (Code-Review-Simulator, Logs-Filtern, Coffee-Pour-Timing usw.). Mit Tier 3.3 + 3.4 stehen jetzt drei Mechanik-Patterns (Sequencing, Pairing, Timing) als Vorlagen fuer kuenftige Tasks.

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
