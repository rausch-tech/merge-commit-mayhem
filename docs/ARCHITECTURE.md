# Architecture

High-Level-Overview von Merge Conflict Mayhem. Wenn du gerade neu im Repo bist und verstehen willst _wieso es so gebaut ist_, lies das hier zuerst.

---

## 1. Architektur-Nordstern

> **Python entscheidet. Der Client zeigt nur an.**

Drei harte Regeln:

1. **Backend ist autoritativ für allen State.** Keine Spiellogik im Client.
2. **WebSocket-Protokoll ist client-agnostisch.** Browser-JS und Godot/GDScript sprechen exakt das gleiche.
3. **Öffentlicher `game_state` enthält nie geheime Rollen.** Rollen kommen nur via privates `private_role`-Event.

Begründung: wir wollen langfristig einen Godot-Client, ohne den Browser-Client wegwerfen zu müssen. Wenn die Spiellogik im Frontend steckt, müssten wir sie in beiden Clients duplizieren — das ist eine Drift-Falle. Daher: Server hält den State, Client zeigt nur.

---

## 2. Komponenten

```text
┌────────────────────────────────────────────────────────────────────┐
│                        FastAPI Process                             │
│                                                                    │
│   ┌──────────────┐       ┌────────────────┐    ┌──────────────┐   │
│   │ /ws endpoint │ ◀───▶ │ ConnectionMgr  │    │ Tick Loop    │   │
│   │ websocket    │       │ (per-ws state) │    │ (asyncio,    │   │
│   │ handlers     │       │                │    │  20 Hz)      │   │
│   └──────┬───────┘       └────────┬───────┘    └───────┬──────┘   │
│          │                        │                    │          │
│          └─────────► GameRegistry ◀────────────────────┘          │
│                            │                                       │
│                       (room_code → GameRoom)                       │
│                            │                                       │
│                ┌───────────┴────────────┐                          │
│                ▼                        ▼                          │
│         ┌───────────┐            ┌───────────┐                     │
│         │ GameRoom  │     ...    │ GameRoom  │                     │
│         │  ABCD     │            │  XYZP     │                     │
│         │           │            │           │                     │
│         │ - phase   │            └───────────┘                     │
│         │ - players │                                              │
│         │ - tasks   │                                              │
│         │ - sabotag.│                                              │
│         │ - votes   │                                              │
│         │ - timer   │                                              │
│         └───────────┘                                              │
│                                                                    │
│   ┌────────────────────────────────────────────────────────────┐   │
│   │  Static-Files-Mount: /, /static/, /images/, /sounds/       │   │
│   └────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
       ▲                                  ▲
       │ wss://...                        │ https://.../static/...
       │                                  │
   Browser-Client                    Godot-Client (Tier 4)
   (Vanilla JS + Canvas)             (3D + GDScript)
```

Beide Clients sprechen das gleiche WebSocket-Protokoll. Der Godot-Client zieht Map + Kinds-Registry zur Laufzeit per HTTP vom Backend (Option C, PR #36) — keine Drift zwischen den Welten, ein Server bedient beide.

---

## 3. Datenfluss pro Tick

20 Hz, also alle 50 ms:

```text
for room in registry.active_rooms():
    if room.phase == PLAYING:
        room.tick(dt):
            bots.tick(dt):                  # Bot-Input-State setzen vor Movement
                tick LLM cooldowns + reap pending futures
                apply reactive overrides (body-report, meeting-vote)
                for each bot:
                    pick_next_target (LLM via thread pool, fallback heuristic)
                    step along path or steer straight to task
                    auto-complete on hold timer
            movement_ctl.tick:               # liest input_state egal von welchem player
                for player: apply movement (input → velocity → position),
                            respect walls + map objects, clamp to map bounds
            tasks_ctl.tick:    per-player progress, completion, cooldowns
            sabotages_ctl.tick: cooldowns, meeting timer
            movement_ctl.tick_takedown_cooldowns + tick_coffee_energy
            decrement remaining_seconds
            check win conditions → maybe transition to ENDED
        broadcast game_state(...) per-viewer (alive sehen nur alive)

    if room.phase == MEETING:
        room.tick(dt):
            decrement meeting_remaining_seconds
            if all alive voted OR timer 0 → resolve_meeting()
        broadcast game_state(...)

    if room.last_voting_result is not None:
        broadcast voting_result(...)
        room.last_voting_result = None

    if room.phase == ENDED and not room.has_broadcast_end:
        broadcast game_ended(...)
        room.has_broadcast_end = True
```

Das Tick-Loop läuft serverweit als ein einziger asyncio-Task (in `app.main:_tick_loop`). Es iteriert über alle Räume — auch wenn ein Raum mal hängt (Exception), kommt der nächste dran.

**Tick darf nicht blocken.** Der LLM-Call der Bots läuft in einem `ThreadPoolExecutor` (Tier 3.9.2.1, PR #38) — der Tick prüft pro Bot nur `Future.done()` (μs) und reapt das Result wenn da, sonst fällt er auf die Heuristik zurück. Vorher-Bug: 3 s `urllib.urlopen`-Timeout fror den Tick und damit ALLE Räume gleichzeitig ein.

---

## 4. Map als Daten

Die Spielkarte ist **kein Code, sondern Daten** in `maps/default.json`. Das ist ein bewusstes Design:

- **Single Source of Truth.** Server lädt + validiert mit Pydantic beim Start.
- **An den Client gespiegelt.** Server sendet die Map als Teil von `room_joined`. Client rendert daraus, hardcoded keine Räume oder Wände.
- **Editor-fähig.** Phase-1-Editor (Tier 1.7) wird einfach JSON-Files erzeugen — das Game-Engine-Setup ändert sich nicht.
- **Mod-fähig.** Später (Tier 5) sollen auch Tasks/Sabotagen/Rollen aus JSON kommen, sodass nicht-Devs Inhalte beitragen können.

Aus den `wallLines` (axis-parallele Linien mit Tür-Cutouts) berechnet der Server zur Lade-Zeit konkrete Wand-Rechtecke für Kollisions-Checks. Der Client mirrored den gleichen Algorithmus für Rendering.

Map-Schema-Detail siehe [`maps.md`](maps.md).

---

## 5. Backend-Layout

```text
app/
├── main.py                 FastAPI app, lifespan, /ws endpoint, all message handlers,
│                           /api/maps + /api/kinds + /api/metrics
├── protocol.py             Pydantic models for incoming/outgoing messages
├── ws.py                   ConnectionManager — per-ws session tracking
└── game/
    ├── game_map.py         GameMap Pydantic + load_map + compute_walls + war-room helpers
    ├── game_room.py        Orchestrator: phase, players, lifecycle, tick(),
    │                       win-conditions, public-state serialisation
    ├── runtime.py          Shared dataclasses (TaskRuntime, SabotageRuntime,
    │                       Body, MiniGameSession) + GameRoomError
    ├── controllers/
    │   ├── tasks.py        TasksController — hold-E flow, per-tick progress,
    │   │                   rewards, personal-task allocation, coffee splash
    │   ├── sabotages.py    SabotagesController — trigger / repair / tick,
    │   │                   Tier 2.7 object-binding
    │   ├── meeting.py      MeetingController — emergency meetings, voting,
    │   │                   take-downs, body reports, context snapshot
    │   ├── mini_game.py    MiniGameController — start / input / complete /
    │   │                   cancel + pending-events queue
    │   └── movement.py     MovementController — per-tick step + collision,
    │                       coffee decay, current-speed-for, vent teleport
    ├── bots/                AI-NPCs (Tier 3.9.2)
    │   ├── manager.py      BotManager — lifecycle, tick, stuck-detection,
    │   │                   ThreadPoolExecutor for non-blocking LLM calls
    │   ├── pathfinding.py  Room-graph BFS via doors (no MapObject-awareness)
    │   └── decision.py     LLM-intent picker + reactive overrides (body, vote)
    ├── llm.py              LLMClient Protocol + AnthropicClient + LocalOpenAIClient
    ├── kinds_registry.py   maps/kinds.json single source of truth + /api/kinds
    ├── metrics_export.py + metrics_aggregate.py  per-day JSONL + /api/metrics
    ├── ai_flavor.py        LLM-styled event-feed texts + postmortem template
    ├── minigames/          Per-task plugins (test_suite_repair, cable_pairing, …)
    ├── models.py           Phase enum + Player domain model (mit is_bot)
    ├── room_code.py        4-char ABCD generator (alphabet without I/O)
    ├── roles.py            5 release + 3 chaos roles + assign()
    ├── sabotages.py        SabotageDefinition + speed constants
    ├── tasks.py            TaskDefinition + interaction constants
    ├── voting.py           tally() + chaos-eliminated check (pure helpers)
    └── walls.py            wall-segment generators + axis-aligned collision
```

**Trennungs-Prinzip:** `game_room.py` ist der Daten- und Lifecycle-Halter; jeder Controller besitzt seine Domänen-Regeln und greift via `self._room.<feld>` auf den geteilten State zu. Hard-split in Slice 2 des v1-Hardening-Releases — vorher war alles als Methoden-Wand auf `GameRoom` (~2k LoC).

`game_room.py` kennt weiterhin keine FastAPI, keine WebSockets, keine JSON-Wire — nur `main.py` und `ws.py` kennen das Transport-Layer. Tests sprechen `room.apply_<x>(...)` direkt an, ohne `TestClient`.

**Wenn du Domain-Logik anfasst:** finde den richtigen Controller über die Methode (z.B. `apply_sabotage` → `SabotagesController.trigger`). `GameRoom` selbst behält dünne Delegator-Methoden für die WS-API; das ist die Stabilitäts-Garantie für den Wire-Vertrag.

**HOWTO-Guides** für die häufigsten Erweiterungen:

- [`HOWTO-SABOTAGE.md`](HOWTO-SABOTAGE.md) — neue Sabotage hinzufügen
- [`HOWTO-MINIGAME.md`](HOWTO-MINIGAME.md) — neues Mini-Game-Plugin
- [`HOWTO-ROLE.md`](HOWTO-ROLE.md) — neue Rolle definieren

---

## 6. Frontend-Layout

```text
static/
├── landing.html            Public marketing landing under /
├── spielprinzip.html       Long-form game-tour subpage under /spielprinzip
├── index.html              /play — lobby + game screen + endscreen + meeting overlay
├── editor/                  Map-Editor under /editor (2D-Canvas + Three.js-3D-Vorschau)
├── styles.css              Dark navy theme + Among-Us-style HUD
│
├── main.js                 Entry point: state machine, WebSocket handler dispatch
├── ws.js                   Reconnecting WebSocket wrapper
├── input.js                Keyboard + E-key task interaction
│
├── render.js               Canvas: camera transform, room rects, walls, tasks, players
├── hud.js                  Top stat pills (release/pipeline/coffee/own-coffee/timer/role)
├── tasks.js                Left sidebar with personal + global tasks
├── sabotages.js            Bottom-right chaos buttons (color-coded, with cooldown)
├── meetings.js             Emergency-meeting button + voting overlay + result toast (lastWords)
├── endscreen.js            End-of-round overlay with role reveal + stats + AI postmortem
├── role_intro.js           Role-Intro modal (Tier 3.5)
├── kinds.js                Holt /api/kinds, Browser-Render-Metadaten pro Kind
├── takedown.js / report.js Force-Reboot + Body-Report buttons + interactions
├── menu.js                 Pause + role recap
├── touch-controls.js       Mobile touch joystick + edge tabs
├── minigames/              Per-task plugins (1:1 mirror of server-side)
│
├── audio.js                Click + task-complete sounds (Kenney UI)
└── sprites.js              Spritesheet metadata + drawSprite helper for canvas
```

**Verantwortungs-Splittung** (Klassen, jede in einem File):

- `WsClient` — Verbindung halten, Messages routen
- `Renderer` — Canvas zeichnen, Kamera, Walls
- `Hud` — DOM-Updates für Top-Pills
- `TaskList` — DOM-Updates für Sidebar
- `SabotagePanel` — DOM-Updates für Chaos-Buttons
- `MeetingOverlay` + `VotingResultToast` + `EmergencyMeetingBtn` — Voting-UI
- `EndscreenOverlay` — End-Card mit Awards + Postmortem
- `RoleIntroModal` — Per-Round Role-Reveal

Alle reagieren auf `game_state`-Updates, keine hat eigenen State außer dem letzten Snapshot.

Daneben existiert der **Godot-3D-Client** unter `godot-3d/` (Tier 4) — gleiches WebSocket-Protokoll, GDScript statt JS, KayKit-3D-Assets statt Canvas-Rectangles. Beide Clients sind interchangeable; der Server kennt den Unterschied nicht.

---

## 7. Wieso Vanilla JS und nicht React/Vue/...?

Bewusste Entscheidung. Begründung:

- **Browser-Client ist Reference, nicht Hero.** Godot wird der polished primary client. Browser muss funktional korrekt sein, nicht beautiful.
- **Keine Build-Pipeline = kein Vite/webpack-Tooling-Erlebnis.** `uvicorn` serviert direkt, hot-reload via Browser-Refresh.
- **Lesbar von außen.** Wer den Code zum ersten Mal sieht, versteht ihn ohne Framework-Konventionen zu kennen.
- **Klein.** Ganzes Frontend ist <2 K JS-Zeilen. Kein Tree-Shaking nötig.

Wenn das Frontend mal komplex genug wird (z. B. Map-Editor mit hunderten UI-Elementen), revisiten wir das. Bis dahin: Plain.

---

## 8. Test-Strategie

| Schicht                                 | Tool                            | Coverage-Stand                                              |
| --------------------------------------- | ------------------------------- | ----------------------------------------------------------- |
| Domain (`app/game/*`)                   | pytest                          | ~92 % auf `app/game/`, 88 % als CI-Gate-Floor               |
| Protokoll (`app/protocol.py`)           | pytest                          | Schema-Roundtrips für alle Message-Typen                    |
| Transport (`app/ws.py` + `app/main.py`) | pytest mit FastAPI `TestClient` | End-to-End-Flows (lobby join, start, voting, add_bot, etc.) |
| Frontend (`static/*.js`)                | vitest + happy-dom              | ~109 Tests (smoke, render, eventfeed, hud, mini-games, …)   |
| Godot-Scripts (`godot-3d/scripts/*`)    | `godot --check-only` (CI-gate)  | Parse-Check via `scripts/godot-check.sh`                    |

Kritische Test-Patterns:

- **Lifespan-aware Tests.** Wenn ein Test den Tick-Loop erwartet, muss er `with TestClient(app) as client:` nutzen — sonst läuft die Lifespan nicht und der Tick-Task existiert nicht.
- **Deterministische rng.** Rollen-Verteilung nimmt optionalen `rng=random.Random(seed)` für reproduzierbare Tests.

---

## 9. Deploy-Pfad

Siehe [`DEPLOY.md`](DEPLOY.md). Kurz: GitHub Actions baut Tarball, scp + ssh-restart auf EC2 t4g.nano in eu-central-1, Caddy als HTTPS-Reverse-Proxy.

---

## 10. Nächste Architektur-Entscheidungen (offen)

1. **MapObject-aware Pathfinder für Bots.** Aktueller Pathfinder kennt nur Räume + Türen. Bots können hinter blockierende Möbel laufen und stuck-detektion fängt das ab. Folge-Slice: A\* über ein Grid mit `compute_walls`-Output als Hindernissen.
2. **Async LLM-Provider mit Prompt-Cache.** PR #38 bringt non-blocking via ThreadPool, aber jeder Call schickt den vollen System-Prompt unverwendet. Anthropic-Prompt-Caching wäre 1-Zeilen-Header.
3. **JSON-Config für Tasks/Sabotagen/Rollen.** `kinds.json` ist erstes Beispiel. Tier 6: Tasks + Sabotagen + Rollen analog auslagern, macht Mod-Beiträge code-frei möglich.
4. **Reconnect-Mechanismus** ist da (Tier 0.10): 30 s grace per Player nach Disconnect.

Detail siehe `docs/ROADMAP.md`.

---

## 11. Performance-Baseline (Stand 2026-04-26)

Synthetisches Last-Skript (`scripts/perf_baseline.py`) misst die Server-Hot-Path-Kosten ohne WS-Layer — der relevante Bottleneck (Tick-Compute + Per-Viewer-Payload-Serialisation) ist von Socket-I/O unabhängig. Lokal auf einem Laptop, CPython 3.12, 400 Ticks (~20 s wall):

| Szenario   | Tick p99 | Payload p99 (1 Viewer) | Aggregat / Tick (12 Viewer) | Throughput | Headroom (50 ms Tick-Budget) |
| ---------- | -------- | ---------------------- | --------------------------- | ---------- | ---------------------------- |
| 4 Spieler  | 0.16 ms  | 3.4 KB                 | 13.5 KB                     | 263 KB/s   | ~310x                        |
| 12 Spieler | 0.60 ms  | 4.5 KB                 | 54 KB                       | 1.06 MB/s  | ~84x                         |

Lesart:

- **Tick-Compute** ist nicht ansatzweise der Engpass — selbst bei voller 12-Spieler-Lobby liegt p99 bei 0.6 ms, das sind 1.2 % des 50-ms-Budgets pro Tick.
- **Payload-Größe** wächst sub-linear mit Spielerzahl (3.4 → 4.5 KB für 3x Spieler) — die meisten Bytes sind Map/Sabotagen/Vents, die Player-Liste ist klein.
- **Aggregat** ist linear in Viewer-Anzahl (4.5 KB × 12 ≈ 54 KB pro Tick) — bei 20 Hz ergibt das ~1 MB/s Server-Egress für eine volle Runde.
- **Headroom** ist beruhigend: ein 12-Spieler-Tick könnte ~80x langsamer werden, bevor der Server hinterherhinkt.

Was die Baseline NICHT abdeckt:

- Reale WS-Layer-Latenz (Send-Buffer, Network-Stack, Caddy-Proxy)
- Client-Render-Performance
- Mehrere parallele Räume gleichzeitig
- Mini-Game-State-Frames während aktiver Sessions

Wenn das Spiel jenseits von 1 Raum × 12 Spieler skaliert, einfach den Run wiederholen mit höherer Spielerzahl oder mehreren Räumen — die Methodik bleibt gleich. Befehl:

```bash
uv run python scripts/perf_baseline.py --players 12 --seconds 20
```
