# State & Roadmap

**Stand:** 2026-04-25
**Branch:** `main`, HEAD `a846a12`
**Tests:** 207 grün (`uv run pytest`)
**Server:** läuft auf `0.0.0.0:8000` lokal, erreichbar via `http://t-800:8000` über Tailscale

Dieses Dokument ist die kanonische Stand-Aufnahme. Halte es aktuell wenn Slices landen.

---

## 1. Was funktioniert

### Spielfluss (3 Tabs, 10–12 Min)

1. Browser-Tabs joinen denselben Raum-Code
2. Erster ist Host, sieht „Runde starten"
3. Demo-Mode-Checkbox erlaubt Solo-Test (forced chaos role)
4. Nach Start: private Rolle (developer / vibe_coder), HUD mit Release / Pipeline / Coffee / Timer
5. WASD- oder Pfeil-Bewegung, Speed wird halbiert wenn `coffee_level=0` oder Mandatory-Meeting aktiv
6. Vier Tasks mit echten Icons (Code-Brackets, PR-Symbol, Coffee-Mug, Wrench-Server) — `E` halten zum Erfüllen, Progress-Ring, 8 s Cooldown
7. Drei Sabotagen für Chaos-Agent (CI/CD-Rot, Kaffee-leer, Mandatory-Meeting) mit echten Icons + Cooldown-Anzeige
8. Walls zwischen Räumen mit 7 Türen — kein Durchlaufen, an Wänden sliden
9. Scrolling-Camera (Welt 2400×1600, Viewport 900×400) — Saboteur kann sich verstecken
10. Charakter-Sprites (color-keyed, nicht role-keyed)
11. Im War Room: Emergency Meeting Button → 60 s Voting → eliminierter Spieler wird Geist (35 % Alpha)
12. Win-Conditions: pipeline ≤ 0 (chaos), release ≥ 100 (release), all chaos eliminated (release), timer 0 (chaos)
13. Endscreen: Banner + Reason + Rollen-Reveal + Stats; Host kann zurück zur Lobby

### Architektur

- **Server autoritativ**: alle State + Bewegung + Win-Logik in Python (FastAPI + Pydantic v2 + Starlette WS)
- **Client dumm**: Vanilla JS + Canvas; sendet nur Inputs, rendert Snapshots
- **Map als Daten**: `maps/default.json` — Räume, Wand-Linien, Türen, Spawns, Task-Anker, War-Room-ID. Server lädt + validiert. Client bekommt Map in `room_joined`. Single Source of Truth.
- **WS-Protokoll**: JSON, camelCase auf der Wire, Godot-kompatibel
- **Asset-Pipeline**: composite Spritesheets in `images/` werden via CSS-`background-position` (für UI-Buttons) oder Canvas-`drawImage` (für Tasks/Charaktere) gesliced; `spriteCss`/`drawSprite` Helper in `static/sprites.js`
- **Audio**: Kenney UI-Click + Switch-Sound bei Task-Completion

### Code-Layout

```
mcm/
├── app/
│   ├── main.py                # FastAPI app, lifespan, WS endpoint, handlers
│   ├── protocol.py            # Pydantic message models
│   ├── ws.py                  # ConnectionManager
│   └── game/
│       ├── game_map.py        # GameMap Pydantic + load_map() + walls/war-room helpers
│       ├── game_room.py       # Per-room state machine, tick, voting, win-conditions
│       ├── models.py          # Phase enum, Player
│       ├── room_code.py       # 4-char ABCD generator
│       ├── roles.py           # 1× vibe_coder, rest developer
│       ├── sabotages.py       # 3 sabotage definitions + speed constants
│       ├── tasks.py           # 4 task definitions (no positions — those come from map)
│       ├── voting.py          # tally helper + chaos-eliminated check
│       └── walls.py           # Wall-segment generator + axis-aligned collision
├── static/                    # Plain HTML/CSS/JS frontend, served by FastAPI
│   ├── index.html
│   ├── styles.css
│   ├── main.js                # Entry, WS handlers, state router
│   ├── ws.js                  # WebSocket wrapper
│   ├── input.js               # WASD + E (task hold)
│   ├── render.js              # Canvas, camera transform, walls, tasks, players
│   ├── hud.js                 # Stat pills + role
│   ├── tasks.js               # Left sidebar task list
│   ├── sabotages.js           # Bottom-right chaos buttons
│   ├── meetings.js            # Emergency button + voting overlay + result toast
│   ├── endscreen.js           # End overlay with role reveal
│   ├── audio.js               # Click + task-complete sounds
│   └── sprites.js             # Spritesheet metadata + drawSprite helper
├── maps/
│   └── default.json           # Single source of truth for map geometry
├── images/                    # Logo + composite spritesheets (some unused)
├── sounds/                    # Logo + Kenney UI clicks + 2 BGM tracks (BGM unused)
├── tests/                     # pytest, 207 tests
├── docs/                      # Specs, plans, handoffs, this file
└── merge_conflict_mayhem_project/  # Original design pack from Sven
```

### Gelandete Slices

| Tag | Was |
|---|---|
| `slice/lobby-movement-v1` | Lobby + WASD-Movement + WS-Pipeline (53 Tests) |
| `slice/game-loop-v1` | Tasks + Sabotagen + Win/Lose + Endscreen + Return-to-Lobby + Logo/Sounds (133 Tests) |
| (un-tagged: `feat/demo-mode`) | Single-Player-Test mit forced chaos (140 Tests) |
| `slice/scrolling-camera-v1` | Welt 2400×1600, Kamera folgt lokalem Spieler (140 Tests) |
| `slice/spritesheets-v1` | Tasks/Sabotagen/Rollen-Icons aus Composite-PNGs (140 Tests) |
| `slice/character-sprites-v1` | Spieler als Charakter-Sprites (color-keyed, nicht role-keyed) (140 Tests) |
| `slice/walls-v1` | Wände + Türen + Sliding-Kollision (150 Tests) |
| `slice/voting-v1` | Emergency Meeting + Voting + Elimination + chaos-eliminated win (187 Tests) |
| `slice/map-data-v1` | Map als JSON-Daten, Server → Client; Foundation für Editor (207 Tests) |

---

## 2. Roadmap

Priorisiert. Jede Stufe ist ein abgeschlossener Sprint-Schnitt; nicht alles in einer Stufe muss zusammen, aber typischerweise zusammenhängend gebaut.

### Tier 1 — Sprint 2 sauber abschließen

| Slice | Was | Aufwand |
|---|---|---|
| **Eventfeed** | Live-Feed rechts neben dem Canvas: „Pipeline ist rot. Niemand weiß warum.", „Ein KI-Agent hat eigenständig refactored.", „Die Kaffeemaschine ist offline." Trigger durch Server-Events (sabotage, task-complete, vote-result). | 1 Tag |
| **Incidents-Mechanik** | Drittes globales Stat. Tasks „Logs analysieren" + „Legacy-Service beruhigen" reduzieren Incidents. Eine zukünftige Sabotage erzeugt sie. Sichtbar in HUD. Ohne Win-Condition (nur Atmosphäre). | 0.5 Tag |
| **Take-Down-Mechanik** | Chaos-Agent kann lebende Spieler im Proximity-Radius „außer Gefecht setzen" (nerdig benannt: Captcha-Loop, Force-Reboot, LinkedIn-Spam-Blast). Cooldown ~25 s, kein Take-Down im War Room (Sicherheitszone). Eliminiert genauso wie Voting → `is_alive=False`, Ghost-Rendering. | 1 Tag |

### Tier 2 — Content-Erweiterung

| Slice | Was | Aufwand |
|---|---|---|
| **Mehr Tasks** | Logs analysieren (Server Room, –1 Incident), Legacy-Service beruhigen (Legacy Basement, –1 Incident), Scope reduzieren (Meeting Room), Release Notes schreiben (War Room). Map-JSON erweitern, TASK_DEFINITIONS erweitern. | 0.5 Tag (incl. icons) |
| **Mehr Sabotagen** | Merge Conflict Storm (neue Tasks spawnen), Fake Customer Request, Legacy Awakening, Flaky Tests, Scope Creep, Network Lag — laut Doc 06 sechs P1/P2-Sabotagen. Sub-Slices möglich. | 0.5–1 Tag pro 2–3 Sabotagen |
| **Erweiterte Rollen** | 8 zusätzliche Rollen (Data Wizard, Consultant, Shadow Admin, Incident Commander, Caffeine Collector, Bug Squasher, Legacy Oracle, Scrum Master) mit Spezialfähigkeiten. Action-Icons aus `action_ability_icons.png`. | 2–3 Tage (ist eigener Sprint) |
| **Spielerzahl 4–12** | Aktuell 2–6, Master-Doc will 4–12. Mehrere Chaos-Agenten bei großen Lobbys (z. B. 2 Chaos bei 9–12). | 0.5 Tag (Skalierung in roles.py + tests) |

### Tier 3 — Multi-Map + Editor

| Slice | Was | Aufwand |
|---|---|---|
| **Multi-Map-Support** | Lobby-Dropdown listet alle `maps/*.json`. Host wählt vor Start. Persistent pro Raum. | 0.5 Tag |
| **Map-Editor (Phase 1)** | Eigene Seite `/editor`. Canvas-Tool: Räume rechtecken, Wände + Türen platzieren, Task-Anker droppen, Spawns droppen. Export als JSON-Download. | 2–3 Tage |
| **Map-Editor (Phase 2)** | Live-Preview: aktuell editierte Map als Test-Round im selben Tab eröffnen. Validierung visualisieren (orphaned rooms, blocked spawns, Tür-Konsistenz). | 1–2 Tage |
| **Map-Editor (Phase 3)** | Auf-Server-Speichern statt nur Download. Backup/Versions. | 1 Tag |

### Tier 4 — Sprint 3 (Humor + Firmenidentität)

| Slice | Was |
|---|---|
| **Endscreen-Awards** | „Held der Kaffeemaschine", „Most Suspicious Innocent", „Pipeline Whisperer", „Lord of Legacy", „Meeting-Minister" etc. Berechnet aus Per-Player-Stats nach Rundenende. |
| **Mehr Eventtexte** | „Tests sind nur eine Meinung." „Build failed. Aber wenigstens konsistent." „Die Pipeline hat emotionalen Schaden genommen." Pool von 30+ Texten, zufällig pro Event. |
| **Lustige Tasknamen** | Statt „Unit Tests fixen" Variationen wie „Flaky-Test exorzieren", „Snapshot-Test zähmen". Pool pro Task-Slot. |
| **Insider-Gags** | Eigene Memes, Team-spezifische Texte; Sven kuratiert. |

### Tier 5 — Sprint 4 (Modding)

| Slice | Was |
|---|---|
| **Tasks aus JSON** | `tasks.json` mit Reward-Werten + Räumen + Dauern. Code lädt validiert. PR-fähig: neue Task = JSON-Zeile. |
| **Sabotagen aus JSON** | `sabotages.json` analog. |
| **Rollen aus JSON** | `roles.json` mit Team + Description + verfügbaren Sabotagen + spezial-Fähigkeiten. |
| **Eventtexte aus JSON** | `event_texts.json` mit Pool pro Event-Typ. |
| **Contribution-Guide** | `docs/contribution-guide.md` mit Beispiel-Issues („Neue Sabotage Flaky Tests", „Neue Task Find Missing Semicolon"). |

### Tier 6 — Sprint 5 (Godot-Client)

Nicht-blockierend; Browser-Client bleibt als Referenz und Web-Fallback. Ziel: **Among-Us-Polish-Niveau** (echte Tilemap, Charakter-Animationen, Sound-Mixing, smoothes Movement).

**Eigener Plan:** [`docs/GODOT-TRANSITION.md`](GODOT-TRANSITION.md) — beschreibt was vor Godot stabil sein muss, welche Design-Entscheidungen anstehen (Among-Us-Features ja/nein, Art-Stil + -Quelle, Mobile, Account-System), Arbeitspakete + 6–10 Wochen-Schätzung.

Vor-Godot-Block: 1–2 Wochen (Protokoll-Doku, Map-Editor Phase 1, Tier-1-Mechaniken einbauen, Asset-Pipeline klären). Godot-Sprint: 3–6 Wochen je nach Featureset.

### Tier 7 — Polish & UX

| Punkt | Was |
|---|---|
| **BGM** | Kuratierte Tracks (`Cyberpunk Moonlight Sonata`, `MyVeryOwnDeadShip`), Mute-Toggle, Volume-Slider. |
| **Reconnect-State-Restore** | Nach Disconnect kann Spieler in dieselbe Runde zurück (mit gleicher Rolle). |
| **Mobile / Responsive** | Layout funktioniert auf Tablet (1024px); Touch-Controls für Bewegung wären eigene Investition. |
| **Restliche Spritesheets** | `buttons.png` (echte Buttons statt CSS), `pansels_ui_frames.png` (Panel-Frames), `room_labels.png` (in-world Schilder), `cover.png` (Splash), `ingame.png` (Reference-only — bleibt ungenutzt). |
| **Task-Cooldown-Progressbar** | Statt Sekunden-Zahl im Sidebar. |
| **Lobby Link-Sharing** | Raum-URL mit Code, evtl. QR-Code. |
| **Better Error-Toasts** | Aktuell ein einfacher Banner; richtiges Toast-System mit Severity. |

### Tier 8 — Tech-Schulden

| Punkt | Was |
|---|---|
| **Frontend-Tests** | Vitest + JSDOM für `meetings.js`, `sabotages.js`, `tasks.js`, `endscreen.js`, `hud.js`, `render.js`. |
| **Lint/Format** | `ruff` für Python (Format + Check), `prettier` für JS, pre-commit hook. |
| **CI** | GitHub-/GitLab-CI: pytest + lint bei jedem Push. |
| **Type-Hints in JS** | Optional: `// @ts-check` headers + JSDoc-Types, oder Migration zu TypeScript. |
| **Spec-/Plan-Bereinigung** | Aktuelle Specs/Plans pro Slice in `docs/superpowers/specs/` und `docs/superpowers/plans/` — zukünftig ggf. archivieren wenn die Liste zu lang wird. |

---

## 3. Bekannte Beobachtungen / Warnings

- `incidentCount` wird im Protokoll mitgeschickt, ist aber immer 0 (kein Mechanik-Hook). Entweder Tier-1-Incidents bauen oder Feld entfernen.
- 6 von 11 Composite-Spritesheets sind ungenutzt (`buttons.png`, `pansels_ui_frames.png`, `room_labels.png`, `action_ability_icons.png`, `cover.png`, `ingame.png`). Tier-7-Polish.
- Audio fest auf 0.3 Volume hard-coded, kein User-Toggle. Tier-7.
- Kein Lint/Format eingerichtet (siehe Tier 8). Code-Stil ist konsistent, aber unautomatisch.
- `merge_conflict_mayhem_project/` (das ursprüngliche Design-Paket) bleibt im Repo als Referenz; Specs/Plans pro Slice landen daneben in `docs/superpowers/`.

---

## 4. Empfohlener nächster Block

**Tier-1-Trio:** Eventfeed + Incidents + Take-Down. Macht Sprint 2 final komplett, bringt das Spiel auf das im Master-Doc dokumentierte „MVP-fertig" Niveau, und die drei sind einzeln klein genug für je einen Slice-Tag.

Danach **Multi-Map + Map-Editor (Phase 1)** — weil das Design-Investment in `slice/map-data-v1` darauf wartet, eingelöst zu werden, und ein Editor lädt zum Mitmachen ein.

Sven entscheidet pro Slice; dieses Doc dokumentiert nur die Optionen.
