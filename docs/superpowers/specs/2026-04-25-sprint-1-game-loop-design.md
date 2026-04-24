# Sprint 1 Completion: Game Loop

**Projekt:** Merge Conflict Mayhem — Lunch Break Edition
**Datum:** 2026-04-25
**Status:** Solo-Spec von Claude in Abwesenheit — alle Design-Entscheidungen markiert, Sven kann jede kippen
**Scope:** Zweiter Schnitt von Sprint 1 (Vollständigung des MVP laut `merge_conflict_mayhem_project/docs/09_first_sprint_plan.md`)

**Kontext für diese Spec:** Sven hat eine Nacht-Autorisierung für autonome Implementierung gegeben. Keine interaktive Brainstorming-Runde möglich. Daher: jede Entscheidung strikt aus dem Design-Paket abgeleitet, Abweichungen explizit begründet, alles bleibt auf Feature-Branch (kein Merge, kein Push) bis zum Review.

---

## 1. Ziel

Nach dieser Slice ist **eine volle Runde spielbar**: Release-Team erledigt Tasks, Chaos-Agent sabotiert, es entscheidet eine Win-Condition. Der Vertical-Slice-Endzustand („Figuren laufen, Timer läuft") wird zu einem echten Spiel.

## 2. Definition of Done

Drei Browser-Tabs starten eine Runde; während 10 Minuten kann passieren:

1. Spieler laufen zu Task-Markern in den Räumen, drücken `E` (halten), füllen einen Progress-Bar, der Task gilt als erledigt → globale Werte ändern sich serverseitig
2. Chaos-Agent hat unten rechts drei Sabotage-Buttons mit Cooldown-Anzeige; Klick triggert die Sabotage
3. HUD zeigt alle globalen Werte live (Release Progress, Pipeline Stability, Coffee, Timer)
4. Links zeigt eine Taskliste welche Tasks aktuell offen sind
5. Runde endet automatisch beim Erreichen einer Win-Condition; alle Tabs sehen einen Endscreen mit Gewinner, Rollen-Aufdeckung und Spieler-Stats
6. pytest-Suite bleibt grün inklusive neuer Tests für Tasks/Sabotagen/Win-Logic

## 3. Explizit nicht Teil dieser Slice

- **Voting + Emergency Meetings** — Sprint 2 laut Roadmap
- **Incidents** (als eigene Mechanik) — kein Task produziert/reduziert sie in diesem Schnitt; Feld bleibt im Protokoll, Wert bleibt 0
- **Eventfeed** — kommt wenn UI mehr Platz bekommt
- **Asset-Sheet-Slicing** — Sven hat Composite-PNGs committet, aber ohne Slicing-Guidance bleiben die draußen. Nur `logo.png` (einzelnes Asset) und Kenney-UI-Sounds (jeweils eigene Files) kommen rein.
- **JSON-Config-Loader** — Sprint 4
- **Godot-Client** — Sprint 5
- **Reconnect-State-Restore** — weiterhin: Close → Rejoin von vorn

## 4. Gameplay-Spezifikation

### 4.1 Globale Werte (im `game_state` mitgesendet)

| Wert | Start | Bereich | Quelle |
|---|---|---|---|
| `releaseProgress` | 0 | 0–100 | erhöht durch Tasks |
| `pipelineStability` | 100 | 0–100 | reduziert durch CI/CD Rot, erhöht durch Deployment-Repair |
| `coffeeLevel` | 100 | 0–100 | auf 0 gesetzt durch Kaffee-leer, auf 100 durch Refill |
| `incidentCount` | 0 | 0+ | **bleibt 0 in diesem Schnitt** (kein Gameplay daran gekoppelt) |
| `remainingSeconds` | 600 | 0–600 | tickt runter |

### 4.2 Tasks (Hold-Tasks, serverseitig autoritativ)

Vier Tasks, jeweils fest an einen Raum-Spot gebunden. Design aus `merge_conflict_mayhem_project/docs/01_game_design.md §11`.

| ID | Titel | Raum | Position (Welt) | Dauer | Reward |
|---|---|---|---|---:|---|
| `fix_unit_tests` | Unit Tests fixen | Open Space | (80, 80) | 5s | releaseProgress +10 |
| `review_pr` | Pull Request reviewen | Open Space | (220, 120) | 5s | releaseProgress +8 |
| `repair_deployment` | Deployment reparieren | Serverraum | (150, 300) | 6s | pipelineStability +15 |
| `refill_coffee` | Kaffee auffüllen | Küche | (750, 100) | 4s | coffeeLevel = 100 |

**Design-Entscheidung:** Nur vier Tasks — weniger als im Design-Paket, aber jeder Task hat klaren Zweck im vorhandenen Mechanik-Set. Tasks, die das Incidents-System brauchen (Logs analysieren, Legacy-Service beruhigen), bleiben draußen weil incidents in diesem Schnitt keine Mechanik hat. Tasks, die auf Scope/Fake-Requests basieren, bleiben draußen weil dieses System nicht spezifiziert ist. Sven kann weitere Tasks in Sprint 4 via JSON-Config nachziehen.

**Interaktionsradius:** 40 px um die Task-Position herum. Nur wenn Spieler innerhalb des Radius ist und `E` drückt und hält, tickt der Task-Progress auf Server-Seite. Beim Loslassen oder Verlassen des Radius: Progress resettet auf 0 (kein Teil-Progress-Carry für die Slice, das macht die Mechanik simpler).

**Parallel-Interaktion:** Mehrere Spieler können parallel am selben Task sein — der Server behandelt jeden Spieler-Task-Status unabhängig. Der Task ist „completed" wenn ein Spieler ihn abschließt; alle anderen Progress-States auf diesem Task werden auf 0 gesetzt, und der Reward zählt einmal.

**Respawn:** Nach Completion wird derselbe Task nach 8 Sekunden Cooldown wieder verfügbar. Gleicher Spot, gleicher Reward, erneut durchführbar. Sonst würde nach 4×Completion das Spiel einfrieren.

### 4.3 Sabotagen (nur Chaos-Agenten)

Drei Sabotagen, aus `docs/01 §12` übernommen.

| ID | Titel | Effekt | Cooldown (ab Trigger) |
|---|---|---|---:|
| `ci_cd_red` | CI/CD Rot | `pipelineStability -= 20` (clamp ≥0) | 60 s |
| `coffee_outage` | Kaffee leer | `coffeeLevel = 0` → alle Spieler auf 60 px/s statt 120 px/s bis `coffeeLevel > 0` | 75 s |
| `mandatory_meeting` | Mandatory Meeting | Alle Spieler 5 s lang auf 60 px/s | 90 s |

**Cooldown-Semantik:** Ab dem Moment des Triggers ist die Sabotage 60/75/90 s nicht erneut triggerbar. Der öffentliche `game_state` sendet pro Sabotage `cooldownRemaining: seconds` (0 heißt verfügbar). Der Chaos-Agent sieht Buttons mit Cooldown-Ring; andere Spieler sehen die Buttons nicht.

**Sabotage-Privatsphäre:** Der `game_state` enthält keine Information, wer sabotiert hat. Nur das sichtbare Ergebnis (pipeline fällt, Kaffee leer, Meeting-Flash) ist öffentlich. Das ist der Kern des Social-Deduction-Gameplays.

### 4.4 Movement-Geschwindigkeit

- Standard: 120 px/s (wie bisher)
- Coffee Level = 0: 60 px/s
- Mandatory Meeting aktiv (5 s): 60 px/s

Wenn beide aktiv sind: 60 px/s (nicht 30 — der Effekt stackt nicht). Speed wird pro Tick neu berechnet, nicht gecacht.

### 4.5 Win Conditions (pro Tick geprüft, First-To-Fire wins)

| Reihenfolge | Bedingung | Gewinner | Reason-String |
|---|---|---|---|
| 1 | `pipelineStability <= 0` | `chaos_agents` | „Die Pipeline ist tot." |
| 2 | `releaseProgress >= 100` | `release_team` | „Release deployed." |
| 3 | `remainingSeconds <= 0` | `chaos_agents` | „Der Release fenster ist geschlossen." |

Die Reihenfolge ist: Pipeline-Kill hat Vorrang vor Release-Success wenn beide gleichzeitig passieren. In der Realität praktisch irrelevant, aber deterministisch.

### 4.6 Endscreen

Phase `ENDED`. Der Server stoppt den Tick-Loop für diesen Raum (sendet aber einen letzten `game_ended` mit allen Endstand-Infos). Client zeigt Overlay:

- Großer Banner: „Release-Team gewinnt" oder „Chaos-Agenten gewinnen"
- Untertitel: Reason-String
- Rollen-Aufdeckung: Liste aller Spieler mit Name + Rolle + Team
- Pro-Spieler-Stats: Anzahl erledigter Tasks, Anzahl ausgelöster Sabotagen
- Button „Zurück zur Lobby" (bringt die Spieler zurück in LOBBY-Phase desselben Raums; alle Werte zurückgesetzt)

**Design-Entscheidung Zurück-zur-Lobby:** Reset statt Discard — der Raum bleibt bestehen, Spieler bleiben drin, nur der Gamestate wird frisch. Neue Rollenverteilung beim nächsten `start_game`. Das erlaubt „noch eine Runde"-Flow aus Doc 17.

## 5. Protokoll-Erweiterungen

### 5.1 Neue Phase

```python
class Phase(str, Enum):
    LOBBY = "lobby"
    PLAYING = "playing"
    ENDED = "ended"   # neu
```

### 5.2 Neue Client-Messages

| Type | Payload | Wirkung |
|---|---|---|
| `task_hold_start` | `{taskId: string}` | Spieler beginnt Hold; Server prüft Proximity; wenn OK, startet serverseitigen Progress pro Spieler |
| `task_hold_stop` | `{taskId: string}` | Spieler bricht Hold ab; Server resettet dessen Progress auf 0 |
| `trigger_sabotage` | `{sabotageId: string}` | Nur von Chaos-Agent akzeptiert; Server prüft Cooldown, wendet Effekt an, setzt Cooldown |
| `return_to_lobby` | `{}` | Nur Host, nur in ENDED-Phase; setzt GameRoom zurück in LOBBY |

### 5.3 Erweiterter `game_state`-Payload

```jsonc
{
  "phase": "playing",
  "remainingSeconds": 428,
  "releaseProgress": 42,
  "pipelineStability": 70,
  "coffeeLevel": 100,
  "incidentCount": 0,
  "players": [ /* wie bisher */ ],
  "tasks": [
    {
      "id": "fix_unit_tests",
      "title": "Unit Tests fixen",
      "room": "open_space",
      "x": 80, "y": 80,
      "requiredSeconds": 5,
      "status": "available" | "in_progress" | "cooldown",
      "progress": 0.6,          // 0..1 wenn in_progress, sonst 0
      "cooldownRemaining": 3    // Sekunden wenn status=cooldown, sonst 0
    }
  ],
  "sabotages": [
    {
      "id": "ci_cd_red",
      "title": "CI/CD Rot",
      "cooldownRemaining": 42,    // 0 = verfügbar
      "active": false             // für „Kaffee leer" = true solange coffee=0
    }
  ]
}
```

**Private Sabotage-Metadaten** (nur der Chaos-Agent erhält das in `private_role`, einmal beim Start):

```jsonc
{
  "role": "vibe_coder",
  "team": "chaos_agents",
  "description": "Du bist der Vibe Coder. ...",
  "availableSabotages": ["ci_cd_red", "coffee_outage", "mandatory_meeting"]
}
```

Release-Team bekommt `availableSabotages: []`. Das ist der einzige Weg wie der Client weiß ob er Sabotage-Buttons rendern soll. Kein Leak: der öffentliche `game_state` enthält keine `availableSabotages`-Info pro Spieler.

### 5.4 Neue Server → Client Event

```jsonc
// game_ended — nur einmal pro Runde, an alle
{
  "type": "game_ended",
  "payload": {
    "winner": "release_team" | "chaos_agents",
    "reason": "Release deployed.",
    "players": [
      {
        "id": "p1",
        "name": "Sven",
        "role": "developer",
        "team": "release_team",
        "completedTasks": 5,
        "triggeredSabotages": 0
      }
    ]
  }
}
```

**Rolle wird NACH Rundenende öffentlich** — das ist der Rollen-Reveal-Mechanismus aus Doc 17 („Am Ende werden Rollen aufgedeckt"). Vorher nie.

## 6. Architektur-Änderungen

### 6.1 Neue Backend-Module

**`app/game/tasks.py`** — TaskDefinition + Runtime-Status

```python
@dataclass(frozen=True)
class TaskDefinition:
    id: str
    title: str
    room: str
    x: float
    y: float
    required_seconds: float
    release_progress_reward: int = 0
    pipeline_stability_reward: int = 0
    coffee_level_set: int | None = None
    cooldown_seconds: float = 8.0

TASK_DEFINITIONS: list[TaskDefinition] = [ ... vier Tasks ... ]

@dataclass
class TaskRuntime:
    definition: TaskDefinition
    status: Literal["available", "in_progress", "cooldown"]
    cooldown_remaining: float
    per_player_progress: dict[str, float]  # player_id → seconds spent
```

**`app/game/sabotages.py`** — SabotageDefinition + Cooldown-Tracking

```python
@dataclass(frozen=True)
class SabotageDefinition:
    id: str
    title: str
    cooldown_seconds: float

SABOTAGE_DEFINITIONS: list[SabotageDefinition] = [ ... drei ... ]

@dataclass
class SabotageRuntime:
    definition: SabotageDefinition
    cooldown_remaining: float
    active_for: float  # nur für mandatory_meeting: Sekunden noch aktiv
```

**`app/game/config_defaults.py`** (optional — oder inline in obigen Dateien):

Konstanten wie `PLAYER_RADIUS_FOR_TASK_INTERACTION = 40`, `MEETING_DURATION = 5.0`, `COFFEE_SLOW_SPEED = 60.0`, `NORMAL_SPEED = 120.0`.

### 6.2 GameRoom-Erweiterungen

- `tasks: dict[str, TaskRuntime]` — beim Start initialisiert
- `sabotages: dict[str, SabotageRuntime]` — beim Start initialisiert
- `completed_tasks_by_player: dict[str, int]` — Count pro Spieler für Endscreen-Stats
- `triggered_sabotages_by_player: dict[str, int]` — Count pro Spieler für Endscreen-Stats
- `meeting_active_for: float` — globaler Slow-Down-Timer für Mandatory Meeting

Neue Methoden:
- `apply_task_hold_start(player_id, task_id)` — returns Error oder None, validiert Proximity + Status
- `apply_task_hold_stop(player_id, task_id)` — resettet Spieler-Progress
- `apply_sabotage(player_id, sabotage_id)` — validiert Rolle + Cooldown, wendet Effekt an
- `reset_for_new_round()` — zurück auf LOBBY, alle Runtime-State gelöscht
- `_check_win_conditions() -> tuple[winner, reason] | None` — pro Tick
- `_current_speed_for(player_id) -> float` — kombiniert coffee/meeting Effekte

**Tick-Loop-Änderung:** statt `tick(dt)` nur Positionen zu aktualisieren, jetzt auch:
1. Pro Task in_progress: Progress pro Spieler im Radius += dt; wenn >= required_seconds, Complete + Reward + Cooldown
2. Task-Cooldowns: runterzählen, auf 0 → status=available
3. Sabotage-Cooldowns: runterzählen
4. Meeting: `meeting_active_for -= dt`
5. Win-Check: wenn erfüllt, `phase = ENDED`, `winner = ...`

### 6.3 Main.py-Änderungen

Neue Handler:
- `_handle_task_hold_start(ws, msg)`
- `_handle_task_hold_stop(ws, msg)`
- `_handle_trigger_sabotage(ws, msg)`
- `_handle_return_to_lobby(ws)`

Tick-Loop schickt jetzt den erweiterten `game_state`. Wenn nach dem Tick `phase == ENDED` und das Room-Flag `_end_broadcast_sent` noch nicht gesetzt: `game_ended` broadcasten, Flag setzen. Weiterer `game_state`-Tick sendet `phase=ended` aber die Werte frieren ein.

**Re-Entry in LOBBY:** `return_to_lobby` ruft `room.reset_for_new_round()`, broadcast `lobby_state`. Spieler müssen nicht neu joinen.

### 6.4 Frontend-Änderungen

`static/hud.js` erweitert:
- Vier Stat-Pills statt jetzt einer (Release, Pipeline, Coffee, Timer)
- Rolle bleibt wie gehabt

`static/render.js` erweitert:
- Zeichnet Task-Marker (farbige Kreise mit Icon-Placeholder, z. B. Task-ID als Text über dem Kreis)
- Wenn lokaler Spieler im Task-Proximity-Radius: glow-Effekt um den Task
- Wenn Task status=in_progress: Progress-Ring um den Marker (0..1 aus `progress`)
- Wenn Task status=cooldown: ausgegraut

`static/input.js` erweitert:
- `E`-Key Down → `task_hold_start` für den nächsten Task in Reichweite
- `E`-Key Up → `task_hold_stop` für aktuellen Task
- Blur → auch Hold stoppen

`static/tasks.js` (neu) — Taskliste links:
- `<ul>` mit allen Tasks, status-farbig (verfügbar grün, laufend blau, cooldown grau)

`static/sabotages.js` (neu) — Sabotage-Buttons unten rechts:
- Nur sichtbar wenn `availableSabotages.length > 0`
- Drei Buttons mit Cooldown-Ring (CSS conic-gradient)
- Klick → `trigger_sabotage`

`static/endscreen.js` (neu) — Endscreen-Overlay:
- Overlay mit dimmed Background
- Winner + reason + role reveal list + stats
- „Zurück zur Lobby"-Button (nur Host) → sendet `return_to_lobby`

`static/main.js` erweitert:
- Handler für `game_ended` → Overlay anzeigen, BGM/Sounds wenn gewünscht
- Handler für erweitertes `game_state` → neue Stats an Hud, Tasks an Renderer+Taskliste, Sabotages an Sabotage-Buttons
- Reset-Flow: wenn `game_state.phase === "lobby"` nach `ended`, Overlay verstecken, Game-Screen zurück auf Lobby-Ansicht

### 6.5 Audio (nur sichere Assets)

- `sounds/kenney_ui_audio/click1.wav` auf jedem Button-Klick
- `sounds/kenney_ui_audio/switch3.wav` (oder ähnlich) bei Task-Completion
- Kein BGM in diesem Schnitt (automatisches Audio nervt, Sven kann manuell einschalten später)
- Alle Sounds via einfaches `new Audio(url).play()`, keine Audio-Engine

### 6.6 Visuals (nur sichere Assets)

- `images/logo.png` als `<img>` statt `<h1>` im Lobby-Header. Fallback bleibt der H1-Text wenn das Bild nicht lädt.
- Andere Composite-Sheets (`ui_icon_set.png`, `sabotage_icons.png`, …) werden **nicht** integriert. Wenn Sven mir morgen sagt „in `sabotage_icons.png` ist das CI-CD-Rot-Icon bei (0,0) 256×256 Pixel" kann ich in 5 Minuten slicen. Ohne diese Info kein Spritesheet-Raten.

## 7. Test-Plan

Bestehende 53 Tests bleiben grün. Neu:

| Datei | Fälle |
|---|---|
| `tests/test_tasks.py` | TaskRuntime-Lifecycle: start hold → progress → complete → cooldown → available; abbruch setzt Progress zurück; reward wird angewendet; completed_by_player-count inkrementiert |
| `tests/test_sabotages.py` | Cooldown verhindert Re-Trigger; Effekte stimmen (pipeline -20, coffee=0, meeting 5s slow); nur Chaos darf triggern (assert `apply_sabotage` mit non-chaos-player_id raised/skip) |
| `tests/test_win_conditions.py` | Pipeline=0 → chaos wins; Release=100 → release wins; Timer=0 → chaos wins; Reihenfolge bei Gleichzeitigkeit; ENDED-Phase stoppt Ticks |
| `tests/test_game_room.py` | Movement-Speed bei coffee=0 halbiert; Speed während meeting halbiert; Reset nach Endscreen stellt alle Werte her |
| `tests/test_ws_protocol.py` | `task_hold_start` mit Proximity OK → kein Error; zu weit weg → Error; `trigger_sabotage` von Non-Chaos → Error; `game_ended`-Event bei Release=100; `return_to_lobby` setzt Phase zurück |

Manuelle Verifikation wieder via Drei-Tab-Browser-Test (Sven morgen).

## 8. Scope-Cuts und warum

| Feature | Warum weggelassen |
|---|---|
| Voting + Emergency Meeting | Explizit Sprint 2 (Roadmap 08) |
| Incidents-Mechanik | Kein Task in scope nutzt sie; blast radius zu groß |
| Scope Reduzieren / Fake Customer Request | System nicht im Design fixiert; zusätzliche Komplexität |
| Legacy-Service-Task | Braucht Incidents |
| Logs analysieren | Braucht Incidents |
| Eventfeed | UI-Platz begrenzt, Runde spielbar auch ohne |
| JSON-Config-Loader | Explizit Sprint 4 |
| Sprite-Sheet-Integration | Blockiert auf Sven-Input für Tile-Mapping |
| BGM/Autoplay-Sound | UX-negativ wenn nicht kuratiert |
| Reconnect-State-Restore | Vertical-Slice-Regel: Rejoin von vorn |

## 9. Konkrete Design-Entscheidungen (Sven kann jede kippen)

| Nr | Entscheidung | Alternative | Warum so |
|---|---|---|---|
| D1 | Nur 4 Tasks (statt 8 aus Doc 01) | Alle 8 | Jeder Task braucht Mechanik-Hook; Incidents-Tasks bleiben draußen bis Incident-System gebaut ist |
| D2 | Task-Interaction-Radius 40 px | 30 / 60 | Figuren-Radius 12 + kleiner Bewegungs-Puffer → komfortabel ohne pixelgenau zu sein |
| D3 | `E`-Key zum Interact | Space, Mausklick | Standard für viele Co-op-Spiele; Space ist oft Jump, kein Konflikt hier aber intuitiv kleiner |
| D4 | Task-Cooldown 8s nach Completion | 5 / 15 / kein Respawn | Verhindert endloses Zusammenstehen; gibt Chaos-Zeit, um zu sabotieren |
| D5 | Kein Teil-Progress-Carry beim Loslassen | Progress cached pro Spieler | Einfacher zu implementieren und zu erklären |
| D6 | Parallel-Workers: Task gilt bei erstem Finisher als fertig | Summenprogress | Docs sagen Hold-Task, nicht Summenpool; simpler |
| D7 | Coffee=0 → Speed 60 statt 0 | Komplett stoppen, 80% | Hälfte ist spürbar aber nicht frustrierend; Docs sagen „langsamer", nicht „gestoppt" |
| D8 | Meeting-Dauer 5s | 10 / 3 | Doc 09 „Balancing-Werte" sagt „Mandatory Meeting Slow 5s" |
| D9 | Win-Check-Reihenfolge: Pipeline → Release → Timer | irgendeine andere | Konsistent + deterministisch; Pipeline-Kill ist „katastrophal" und sollte Release-Success überschreiben wenn sie simultan fallen (praktisch nie) |
| D10 | Endscreen offenlegt Rollen | Rollen weiter geheim | Doc 17 sagt „Rollen aufgedeckt" am Ende |
| D11 | Zurück-zur-Lobby statt Raum-Discard | Neuer Raum jedes Spiel | Sven Doc 08/17: „Noch eine Runde"-Flow bevorzugt |
| D12 | Keine Spritesheet-Integration | Sheets slicen und verwenden | Ohne Tile-Koordinaten zu raten wäre brüchig; lieber klar dokumentieren „pending" |
| D13 | Keine BGM autoplay | Automatisch Sonate | UX: Autoplay in Büro-Setting unangebracht |
| D14 | `incidentCount` bleibt im Protokoll, immer 0 | Feld entfernen | Vorwärtskompatibel, wenn Incidents in Sprint 2+ reinkommen brauchen wir das Feld sowieso |

## 10. Risiken & Offene Entscheidungen für Sven

**Was ich morgen früh fragen will:**

1. **Sabotage-Button-Placement:** Bottom-right HUD-Leiste vs. Overlay-Modal. Ich mache bottom-right (platzsparend, dauerhaft sichtbar). Wenn Sven das anders will, trivial zu ändern.
2. **Task-Icons:** Ich render Task-Marker als farbige Kreise mit `task_definition.title[:2]` als Text. Sobald er die Spritesheets-Koordinaten liefert, kann ich auf echte Icons upgraden.
3. **Audio-Volume:** Click-Sounds sind je nach Lautstärke-Setting eher penetrant. Ich setze Volume hart auf 0.3.
4. **Host-Migration nach Spielende:** Wenn der Host mittendrin die Verbindung verliert, sollte der neue Host auch die „Runde starten"-Kontrolle bekommen. Ist schon durch den `is_host`-Flag abgedeckt — neu bestätigen.
5. **End-Phase-Timeout:** Falls niemand „Zurück zur Lobby" klickt, bleibt der Raum in ENDED. Auto-Cleanup nach 5 Minuten? Ich skippe das erstmal — Raum bleibt bis alle disconnecten.

## 11. Arbeitsweg heute Nacht

1. Diese Spec committen
2. Implementierungsplan schreiben (`writing-plans`)
3. Via `subagent-driven-development` durchziehen, task-by-task, mit Reviews
4. Bei Blocker: stoppen und Handoff-Notiz schreiben
5. Branch bleibt `slice/game-loop`, nicht gepusht, nicht gemerged
6. Handoff-Datei schreiben die Sven morgen zuerst liest: `docs/HANDOFF-2026-04-25.md`
