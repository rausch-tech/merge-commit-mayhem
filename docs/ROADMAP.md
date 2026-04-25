# Merge Conflict Mayhem — Roadmap

> **Vision:** Ein Among-Us-artiges Social-Deduction-Game für Tech-Teams. Statt einer Raumstation: ein Software-Büro mitten im Release. Statt Crewmates und Imposter: Release-Team und Chaos-Agenten. Mit der Mechanik-Klarheit von Among Us und der Insider-Komik eines Engineering-Teams in der Krise.

Dieses Dokument ist der **eine** Plan. Es ist die Wahrheit über den Stand und die Reihenfolge. Andere Docs erklären Sub-Themen (Map-Schema, Contributing, Architektur), aber Roadmap und Status leben hier.

---

## Stand (2026-04-25)

| | |
|---|---|
| **Repo** | https://github.com/rausch-tech/merge-commit-mayhem |
| **Live (Test-Server)** | https://mcm.3-78-184-97.sslip.io |
| **Backend-Tests** | 207 grün (`uv run pytest`) |
| **Stack** | Python 3.12 + FastAPI + Pydantic v2 + WebSockets, Vanilla JS + Canvas, Map als JSON-Daten |
| **Geshippt** | 8 getaggte Slices: lobby-movement → game-loop → scrolling-camera → spritesheets → character-sprites → walls → voting → map-data |

Was funktioniert: drei Browser-Tabs joinen einen Raum, Host startet, Rollen werden privat verteilt, Spieler bewegen sich mit WASD durch eine 2400×1600-Karte mit Räumen + Wänden + Türen, machen Tasks, Chaos sabotiert, Voting im War Room kann Spieler eliminieren, Endscreen mit Rollen-Reveal. Demo-Mode für Solo-Test.

Was noch nicht: vents, killable players + body discovery, lights/comms-Sabotage, eventfeed, take-down-Mechanik. Außerdem: Code-Hygiene (kein Lint, keine CI, keine Frontend-Tests), Doku unvollständig (kein protocol.md, kein contributing.md), 4 Tasks und 3 Sabotagen sind nach 5 min repetitiv.

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

| # | Was | Aufwand |
|---|---|---|
| 0.1 | **Lint + Format** — `ruff` für Python, `prettier` für JS, pre-commit-Hook | 0.5 Tag |
| 0.2 | **CI auf GitHub Actions** — pytest + ruff + prettier bei jedem Push/PR, Status-Badge im README | 0.5 Tag |
| 0.3 | **Frontend-Tests** — Vitest + happy-dom, Smoke-Coverage pro JS-Modul | 1 Tag |
| 0.4 | **`docs/PROTOCOL.md`** — vollständiger WebSocket-Vertrag (alle Messages mit Schema, Phase-Übergänge, Error-Codes, Beispiel-Sequenzen) | 0.5 Tag |
| 0.5 | **`docs/ARCHITECTURE.md`** — high-level Overview, Tick-Loop-Topologie, Map-Daten-Flow | 0.5 Tag |
| 0.6 | **`docs/DEPLOY.md`** — Deploy-Workflow (Tarball, EC2, Caddy, sslip.io, Stop/Start) | 0.5 Tag |
| 0.7 | **`docs/DEV.md`** — lokale Entwicklung, Branch-Konventionen, Worktrees, Commit-Style | 0.25 Tag |
| 0.8 | **Deploy-Script** — `scripts/deploy.sh` für one-command Tarball + scp + restart | 0.5 Tag |
| 0.9 | **Dead-Code raus** — `incidentCount` ohne Mechanik raus, ungenutzte Spritesheets dokumentieren oder ausräumen | 0.5 Tag |
| 0.10 | **Reconnect** — Server bewahrt Spieler-Identität 30 s nach Disconnect; Client kann mit selber Identität rejoin | 1 Tag |
| 0.11 | **Edge-Cases** — Host-Disconnect mid-Meeting, letzter Spieler in ENDED, gleichzeitige Joins, Memory-Smoke | 0.5–1 Tag |
| 0.12 | **Live-Test mit Team** — 3–5 Runden, Bugs surfacen + fixen | 1 Termin + Bug-Block |

**Done-Kriterium:** Alle Tests grün in CI. Doku-Block existiert. Deploy-Script funktioniert. Reconnect funktioniert. Mit echten Leuten gespielt, keine Critical-Bugs offen.

### Tier 1 — Spiel komplettieren (Core-Mechaniken)

**Ziel:** Browser-Client hat alle Kern-Mechaniken die wir wollen, bevor wir die Among-Us-Schicht oder Godot bauen. Sonst Doppelarbeit beim Porten.

**Aufwand:** ~1.5 Wochen.

| # | Was | Aufwand |
|---|---|---|
| 1.1 | **Eventfeed** — Live-Feed rechts neben Canvas: „Pipeline ist rot", „PR gemerged", „Carol wurde entfernt — war Chaos-Agent". Trigger durch Server-Events. | 1 Tag |
| 1.2 | **Incidents-Mechanik** — drittes Stat im HUD. Tasks „Logs analysieren" + „Legacy-Service beruhigen" reduzieren. Eine zukünftige Sabotage erzeugt sie. | 1 Tag |
| 1.3 | **Mehr Tasks** — vier zusätzliche aus dem Master-Doc: Logs analysieren, Legacy-Service beruhigen, Scope reduzieren, Release Notes schreiben | 0.5 Tag |
| 1.4 | **Mehr Sabotagen** — Merge Conflict Storm, Fake Customer Request, Flaky Tests | 1 Tag |
| 1.5 | **Spielerzahl 4–12** — MAX_PLAYERS auf 12, Color-Palette erweitern, Multi-Chaos bei großen Lobbys (2 Chaos ab 7 Spielern) | 1 Tag |
| 1.6 | **Mute-Toggle / Volume-Slider** — Audio-Hygiene | 0.25 Tag |
| 1.7 | **Map-Editor (Phase 1)** — Browser-Editor unter `/editor`: Räume rechtecken, Wand-Linien + Türen, Spawns, Task-Anker. JSON-Export. | 2–3 Tage |
| 1.8 | **Multi-Map-Support** — Lobby-Dropdown, mehrere `maps/*.json`, Host wählt | 0.5 Tag |

**Done-Kriterium:** Browser-Client deckt das gesamte Master-Doc-MVP ab plus Eventfeed plus Map-Editor. Mit 8 Leuten testbar. Multi-Map-Auswahl in der Lobby.

### Tier 2 — Among-Us-Features

**Ziel:** Die Mechaniken, die Among Us spielenswert machen, in unserer Tech-Office-Variante. Hier wird das Spiel von „funktional MVP" zu „echtes Game".

**Aufwand:** ~2 Wochen.

| # | Was | Aufwand | Naming-Idee |
|---|---|---|---|
| 2.1 | **Take-Down-Mechanik** — Chaos kann Spieler im Proximity-Radius außer Gefecht setzen. Cooldown ~25 s. Kein Take-Down im War Room (Sicherheitszone). | 1 Tag | „Force-Reboot", „Captcha-Loop", „LinkedIn-Spam-Blast" |
| 2.2 | **Body-Discovery + Report** — eliminierte Spieler bleiben als „Body" sichtbar bis entdeckt. Lebende Spieler in Proximity können Report-Button drücken → triggert Meeting. | 1.5 Tage | „Stale-Process-Found", Ghost = „Coredumped Engineer" |
| 2.3 | **Vents** — Chaos kann zwischen vorab-definierten Punkten teleportieren. Map-JSON kriegt `vents: [...]`-Feld. Animation + Sound. | 1.5 Tage | „SSH-Tunnel", „Internal-Pipeline" |
| 2.4 | **Lights-Sabotage** — Sichtbarkeits-Reduktion: Viewport bekommt Vignette, Spieler sehen nur ~150 px Radius um sich herum. Repariert durch Interact mit „Electrical Panel" (im Server Room). | 1 Tag | „PagerDuty-Storm" / „Production-Outage" |
| 2.5 | **Comms-Sabotage** — Tasks-Sidebar wird leer (kann nicht erfüllt werden), Sabotage-Buttons disabled. Repariert durch Interact mit „Comms Panel" (im War Room). | 1 Tag | „Slack-Down", „Confluence-Outage" |
| 2.6 | **Spectator-Mode für Geister** — Tote Spieler können sich frei durch die Map bewegen, andere Geister sehen, Lebende sehen sie nicht. Tasks erfüllen können sie weiter (helfen Release-Team), aber nicht mehr abstimmen. | 1 Tag | „Coredumped" |

Naming-Prinzip: nerdig, dev-thematisch, „kill" wird vermieden zugunsten von harmlos-witzigen Tech-Bezeichnungen. Final-Naming entscheiden wir bei Implementation jeder Slice.

**Done-Kriterium:** Alle 6 Features implementiert + getestet. Game spielt sich „wie Among Us, aber dev-themed". Mit Live-Tests bestätigt.

### Tier 3 — Godot-Migration

**Ziel:** Browser-Client bleibt als Web-Fallback und Reference-Implementation. Godot wird der polished primary client mit echten Charakter-Animationen, Tilemaps, Sound-Mixing und Particle-Effects.

**Aufwand:** ~5–7 Wochen.

Der Godot-Sprint kommt **nach** Tier 0–2, weil:
- Mit unfinishedem Browser doppelte Feature-Arbeit
- Ohne Foundation-Cleanup (Tier 0) keine Test-Sicherheit beim Porten
- Without Among-Us-Features im Browser (Tier 2) keine klare Spec für Godot

#### Vor-Godot-Block (Decisions, ~1 Woche)

| # | Was | Status |
|---|---|---|
| 3.0.1 | Asset-Pipeline-Entscheidung — Pixel-Art-Pack einkaufen + AI-generierte DevOps-Sprites (Coffee-Maschinen, Server-Racks) | Sven entscheidet |
| 3.0.2 | Asset-Pack-Beschaffung — itch.io / Humble / Synty research + Lizenz-Doku | 1 Tag |
| 3.0.3 | DevOps-Theme-Sprites generieren oder commission'en (Coffee, Server, Bug, etc.) | 1–3 Tage |

#### Godot-Sprint (~4–6 Wochen)

| # | Paket | Aufwand |
|---|---|---|
| 3.1 | Godot 4 Projekt-Setup, Web-Export-Config, WebSocketPeer-Anbindung | 1 Tag |
| 3.2 | Lobby-Scene (UI, Raumcode-Input, Spielerliste, Map-Auswahl, Start) | 1–2 Tage |
| 3.3 | Map-Loader: Map-JSON → Tilemap-Layer dynamisch | 2 Tage |
| 3.4 | Charakter-Scene: Sprites + 4-Richtungs-Idle/Walk-Animation + Movement-Interpolation | 2–3 Tage |
| 3.5 | HUD + Stat-Pills + Rolle + Timer mit Tween-Animationen | 1 Tag |
| 3.6 | Task-Interaktion (Hold-E + Progress-Ring + Completion-VFX) | 1 Tag |
| 3.7 | Sabotage-Buttons mit Cooldown-Anzeige | 1 Tag |
| 3.8 | Voting-Overlay + Result-Toast mit Slide-Animationen | 1 Tag |
| 3.9 | Endscreen mit Rollen-Reveal + Stats + Confetti-Particles | 1 Tag |
| 3.10 | Among-Us-Features: Vents (Animation + Sound), Body-Discovery + Report, Take-Down-Animation, Lights/Comms-VFX, Spectator-Mode | 5–8 Tage |
| 3.11 | Sound-Integration (Footsteps, UI-SFX, BGM) | 1 Tag |
| 3.12 | Polish + Bug-Fixes | 3–5 Tage |
| 3.13 | Web-Export-Deploy auf gleiche EC2 | 0.5 Tag |

**Done-Kriterium:** Godot-Web-Build läuft auf gleichem Server, fühlt sich „wie Among Us, dev-themed" an, hat mindestens dieselbe Featuredecke wie Browser-Client, plus Tier-2-Animationen + Sound + Particles.

### Tier 4 — Polish + Distribution

**Ziel:** „echt fertig"-Niveau. Was zwischen Beta und „würde ich öffentlich zeigen" liegt.

| # | Was | Aufwand |
|---|---|---|
| 4.1 | **BGM** — kuratierte Tracks, Mute-Toggle, Volume-Slider | 0.5 Tag |
| 4.2 | **Mobile-Layout** (Tablet 1024px) + Touch-Controls (virtual joystick) | 1 Woche |
| 4.3 | **Account-System** (light) — Profil mit Skin-Auswahl, Win-Stats | 3–5 Tage |
| 4.4 | **Custom Skins** — neben Color auch Hat-/Pet-Variationen, kosmetisch | 2–3 Tage |
| 4.5 | **Bessere Animationen** — Reaction-Idles, Walking-Wackel, Death-Pose | ongoing |
| 4.6 | **Lobby-Link-Sharing** — URL mit Raumcode, evtl. QR | 0.5 Tag |
| 4.7 | **Better Error-Handling** — Toast-System mit Severity-Levels | 0.5 Tag |
| 4.8 | **Settings-Menü** — Sound, Sprache, Tastenkonfiguration | 1 Tag |
| 4.9 | **Endscreen-Awards** — „Held der Kaffeemaschine", „Pipeline Whisperer", „Most Suspicious Innocent", basierend auf Per-Player-Stats | 1 Tag |

**Done-Kriterium:** Spielt sich auf Desktop + Tablet flüssig. Sieht poliert aus. Es gibt Wiederspielwert (Awards, Skins, Stats).

### Tier 5 — Community + Mod-Support

**Ziel:** Anderer Devs in deinem Team können Inhalte beitragen ohne Code-Touch.

| # | Was | Aufwand |
|---|---|---|
| 5.1 | **Tasks aus JSON** (`tasks.json`) — Reward-Werte, Räume, Dauern. Code lädt validiert. | 1 Tag |
| 5.2 | **Sabotagen aus JSON** (`sabotages.json`) | 1 Tag |
| 5.3 | **Rollen aus JSON** (`roles.json`) — Team, Description, available Sabotagen, Spezial-Fähigkeiten | 1.5 Tage |
| 5.4 | **Eventtexte aus JSON** (`event_texts.json`) — Pool pro Event-Typ, zufällig | 0.5 Tag |
| 5.5 | **Map-Editor Phase 2** — Live-Preview (Map sofort spielen), Validierung visualisieren, mehrere Maps gleichzeitig | 2–3 Tage |
| 5.6 | **Map-Browser** — Liste aller `maps/*.json` mit Vorschau, Hot-Reload | 1 Tag |
| 5.7 | **Erweiterte Rollen** — Data Wizard, Consultant, Shadow Admin, Incident Commander, Caffeine Collector, Bug Squasher, Legacy Oracle, Scrum Master mit Spezial-Fähigkeiten (Auto-Fix Bot, Distract, Speed Boost, Coffee Run, Scan Logs, Rollback) | 2 Wochen |
| 5.8 | **Insider-Gags + Memes** — kuratiert von Sven + Team, im Pool | ongoing |

**Done-Kriterium:** Person ohne Code-Wissen kann eine neue Sabotage via Pull-Request beitragen. `docs/CONTRIBUTING.md` reicht aus dafür.

### Tier 6 — Live-Service-Phase

**Ziel:** Das Game lebt. Wir oder Community erweitern es regelmäßig.

| # | Was |
|---|---|
| 6.1 | **Stable Releases + Versioning** — Server hat Version, Client checkt Kompatibilität |
| 6.2 | **Statistik-Backend** — Per-Player-Stats persistieren, Win-Rate, Lieblings-Rolle |
| 6.3 | **Saisons / Events** — temporäre Maps, Theme-Roll-outs (Halloween, Christmas-Office) |
| 6.4 | **Translation-Support** — i18n für Eventtexte, UI |
| 6.5 | **Public Release** — falls gewünscht: Itch-Page, Discord, etc. |

Diese Tier ist absichtlich vage — was hier passiert hängt davon ab wie das Game vom Team angenommen wird.

---

## Was als nächstes konkret zu tun ist

**Heute / morgen:** Tier 0.1 (Lint+Format) und 0.2 (CI) — weil die alle nachfolgenden Tiers sauberer machen. Dann 0.4 (`PROTOCOL.md`) damit der Godot-Sprint einen klaren Vertrag hat.

**Diese Woche:** Tier 0 fertig.

**Nächste 1–2 Wochen:** Tier 1 (Mechanik-Vervollständigung + Map-Editor + Multi-Map).

**Wochen 3–4:** Tier 2 (Among-Us-Features im Browser).

**Wochen 5–11:** Tier 3 (Godot-Migration mit Polish).

**Danach:** Tier 4–6 als ongoing Slices.

Total bis „polished public-fähig": ~3 Monate fokussierte Arbeit. Mit Asset-Pack-Hilfe und ohne Mobile/Account: ~2 Monate.

---

## Wie wir entscheiden

- **Slices** sind die Arbeitseinheit. Jede Slice hat ihren eigenen Branch (`slice/<kurztitel>`), Tests, Live-Server-Restart nach Merge.
- **Specs/Plans** schreiben wir nur für nicht-triviale Slices (>1 Tag Aufwand). Kleinere Slices fließen direkt in den Implementer-Prompt ein.
- **Live-Tests** validieren Tier-Übergänge — bevor wir ein Tier fertig erklären, mit echten Spielern testen.

---

## Verwandte Docs

- `docs/maps.md` — Map-JSON-Schema (Referenz für Map-Bauer)
- `docs/CONTRIBUTING.md` — wie Mitarbeitende beitragen können (kommt mit Tier 5.0)
- `docs/PROTOCOL.md` — vollständiger WS-Vertrag (kommt mit Tier 0.4)
- `docs/ARCHITECTURE.md` — High-Level-Overview (kommt mit Tier 0.5)
- `docs/DEPLOY.md` — Deploy-Workflow (kommt mit Tier 0.6)
- `docs/DEV.md` — lokale Entwicklung (kommt mit Tier 0.7)
- `merge_conflict_mayhem_project/` — ursprüngliches Design-Paket von Sven, behalten als historische Inspirations-Quelle (Roadmap ersetzt es)
