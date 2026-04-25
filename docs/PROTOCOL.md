# WebSocket Protocol

Single Source of Truth für das Netzwerk-Protokoll zwischen MCM-Server und Client. Beide Clients (Browser jetzt, Godot später) sprechen dieses Protokoll.

**Endpoint:** `wss://<host>/ws` (live: `wss://game.prod-is-lava.dev/ws`)
**Format:** UTF-8 JSON, ein Frame = eine Message.
**Konvention:** Wire-Format ist **camelCase**. Server validiert mit Pydantic; unbekannte Typen oder fehlerhafte Payloads werfen `ValidationError` und der Server schickt einen `error`-Frame zurück.

---

## 1. Frame-Struktur

```jsonc
{
  "type": "<message_type>",
  "payload": {
    /* type-specific */
  },
}
```

Beide Richtungen (Client→Server und Server→Client) verwenden diese Hülle.

---

## 2. Lebenszyklus einer Verbindung

```text
Client                                                       Server
  │                                                            │
  │ ── WebSocket /ws ──────────────────────────────────────▶   │
  │                                                            │
  │ ◀──────────────────────────────────── (verbunden, idle) ── │
  │                                                            │
  │ ── join_room(roomCode, playerName) ──────────────────▶    │
  │                                                            │
  │ ◀── room_joined(roomCode, playerId, isHost, map) ────     │
  │ ◀── lobby_state(roomCode, players[]) ─────────────────    │  (broadcast)
  │                                                            │
  │ ── start_game(demo?) [host only] ─────────────────────▶   │
  │                                                            │
  │ ◀── private_role(role, team, description, availSabotages)─ │  (privat pro Spieler)
  │ ◀── game_state(phase=playing, ...) ───────────────────    │  (jetzt 20 Hz)
  │                                                            │
  │ ── player_input / task_hold_start / trigger_sabotage ─▶   │
  │ ◀── game_state ........................................   │
  │                                                            │
  │ ── call_emergency_meeting [in War Room] ──────────────▶   │
  │                                                            │
  │ ◀── game_state(phase=meeting, meeting=...) ───────────    │
  │ ── cast_vote / skip_vote ─────────────────────────────▶   │
  │ ◀── voting_result(removedPlayerId, ...) ──────────────    │
  │ ◀── game_state(phase=playing, ...) ───────────────────    │
  │                                                            │
  │ (Win-Condition erfüllt)                                    │
  │ ◀── game_ended(winner, reason, players[]) ────────────    │
  │                                                            │
  │ ── return_to_lobby [host only] ───────────────────────▶   │
  │                                                            │
  │ ◀── lobby_state ........................................   │
  │ ── (neuer Roundsstart möglich) ...                          │
```

---

## 3. Phasen (State-Machine)

```text
LOBBY ──(host: start_game)─▶ PLAYING ──(call_emergency_meeting)─▶ MEETING
  ▲                              │                                   │
  │                              │ (win condition)                   │ (timer 0
  │                              ▼                                   │  oder alle
  │                            ENDED ◀──────────────────────────────┘  voted)
  │                              │
  │                              │ (host: return_to_lobby)
  └──────────────────────────────┘
```

| Phase     | Server-Tick                                         | Erlaubte Inputs                                                                                                         |
| --------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `LOBBY`   | inaktiv                                             | `join_room`, `start_game` (Host)                                                                                        |
| `PLAYING` | 20 Hz: Movement, Tasks, Sabotagen, Timer, Win-Check | `player_input`, `task_hold_start`, `task_hold_stop`, `trigger_sabotage` (Chaos), `call_emergency_meeting` (im War Room) |
| `MEETING` | 20 Hz: Meeting-Timer + Auto-Resolve                 | `cast_vote`, `skip_vote` (lebende Spieler)                                                                              |
| `ENDED`   | inaktiv                                             | `return_to_lobby` (Host)                                                                                                |

---

## 4. Client → Server

### `join_room`

Erste Aktion nach Connect. Erzeugt den Raum wenn der Code neu ist, sonst Beitritt.

```jsonc
{
  "type": "join_room",
  "payload": {
    "roomCode": "ABCD",
    "playerName": "Sven",
  },
}
```

**Server antwortet** mit `room_joined` an den Joiner und `lobby_state` an alle. Bei Fehler `error` mit `code` aus:

- `ROOM_FULL` (>6 Spieler)
- `NAME_TAKEN`

### `start_game`

Nur vom Host akzeptiert. Wechselt Phase `LOBBY` → `PLAYING`.

```jsonc
{
  "type": "start_game",
  "payload": {
    "demo": false, // optional, default false; wenn true: min-2-Player-Guard übersprungen, Solo-Spieler wird Chaos
  },
}
```

**Server antwortet** mit `private_role` (privat pro Spieler) und `game_state` (broadcast). Bei Fehler `error`:

- `NOT_HOST`
- `WRONG_PHASE` (nicht in LOBBY)
- `NOT_ENOUGH_PLAYERS` (<2 ohne `demo`)

### `player_input`

Aktueller Tasten-Zustand (state, nicht event). Server speichert; Tick wendet ihn an.

```jsonc
{
  "type": "player_input",
  "payload": {
    "up": true,
    "down": false,
    "left": false,
    "right": true,
  },
}
```

Idempotent. Eliminierte Spieler werden ignoriert.

### `task_hold_start` / `task_hold_stop`

Beginnt/beendet das Halten eines Tasks. Server checkt Proximity (40 px) und Phase.

```jsonc
{ "type": "task_hold_start", "payload": { "taskId": "fix_unit_tests" } }
{ "type": "task_hold_stop",  "payload": { "taskId": "fix_unit_tests" } }
```

Errors auf `task_hold_start`:

- `WRONG_PHASE`
- `UNKNOWN_TASK`
- `TASK_ON_COOLDOWN`
- `TASK_TOO_FAR`
- `PLAYER_ELIMINATED`

`task_hold_stop` ist tolerant — Aufruf ohne aktiven Hold ist No-op.

### `trigger_sabotage`

Nur Chaos-Agenten. Server prüft Cooldown.

```jsonc
{ "type": "trigger_sabotage", "payload": { "sabotageId": "ci_cd_red" } }
```

Verfügbare Sabotage-IDs: `ci_cd_red`, `coffee_outage`, `mandatory_meeting`. Client weiß die Liste aus `private_role.availableSabotages`.

Errors:

- `WRONG_PHASE`
- `UNKNOWN_PLAYER`
- `PLAYER_ELIMINATED`
- `NOT_CHAOS_AGENT`
- `UNKNOWN_SABOTAGE`
- `SABOTAGE_ON_COOLDOWN`

### `call_emergency_meeting`

Triggert MEETING-Phase. Spieler muss im War Room stehen + sein einziges Meeting noch übrig haben.

```jsonc
{ "type": "call_emergency_meeting", "payload": {} }
```

Errors:

- `WRONG_PHASE`
- `UNKNOWN_PLAYER`
- `PLAYER_ELIMINATED`
- `NOT_IN_WAR_ROOM`
- `NO_MEETING_LEFT`

### `cast_vote` / `skip_vote`

Während MEETING-Phase. Lebende Spieler nur. Eine Abstimmung pro Spieler (Re-Vote überschreibt).

```jsonc
{ "type": "cast_vote", "payload": { "targetPlayerId": "abc..." } }
{ "type": "skip_vote", "payload": {} }
```

Errors auf `cast_vote`:

- `WRONG_PHASE`
- `CANNOT_VOTE` (Voter nicht lebend)
- `INVALID_TARGET` (Target unbekannt oder eliminiert)

### `return_to_lobby`

Nur in Phase `ENDED`, nur Host. Setzt Raum auf `LOBBY` zurück, alle Spieler leben wieder, neue Rollen-Verteilung beim nächsten `start_game`.

```jsonc
{ "type": "return_to_lobby", "payload": {} }
```

Errors:

- `NOT_HOST`
- `WRONG_PHASE`

---

## 5. Server → Client

### `room_joined` (privat, an den Joiner)

```jsonc
{
  "type": "room_joined",
  "payload": {
    "roomCode": "ABCD",
    "playerId": "abc1234567890def",
    "isHost": true,
    "map": {
      /* GameMap, siehe docs/maps.md */
    },
  },
}
```

`map` ist die volle Spielkarte als JSON — Räume, Wand-Linien, Türen, Spawn-Punkte, Task-Anker, War-Room-ID. Client cachet sie für die Dauer der Session.

### `lobby_state` (broadcast)

```jsonc
{
  "type": "lobby_state",
  "payload": {
    "roomCode": "ABCD",
    "players": [{ "id": "abc...", "name": "Sven", "color": "#4ade80", "isHost": true }],
  },
}
```

Wird gesendet bei: jedem Join, jedem Disconnect, `return_to_lobby`.

### `private_role` (privat, einmal beim Spielstart)

```jsonc
{
  "type": "private_role",
  "payload": {
    "role": "vibe_coder",
    "team": "chaos_agents",
    "description": "Du bist der Vibe Coder. Sabotiere das Release...",
    "availableSabotages": ["ci_cd_red", "coffee_outage", "mandatory_meeting"],
  },
}
```

`availableSabotages` ist leer für `release_team`. Client zeigt Sabotage-Buttons nur wenn nicht-leer.

### `game_state` (broadcast, 20 Hz während PLAYING und MEETING)

```jsonc
{
  "type": "game_state",
  "payload": {
    "phase": "playing", // oder "meeting" oder "ended"
    "remainingSeconds": 542,
    "releaseProgress": 38,
    "pipelineStability": 80,
    "coffeeLevel": 100,
    "players": [
      {
        "id": "abc...",
        "name": "Sven",
        "x": 250.5,
        "y": 100.0,
        "color": "#4ade80",
        "isHost": true,
        "isAlive": true,
      },
    ],
    "tasks": [
      {
        "id": "fix_unit_tests",
        "title": "Unit Tests fixen",
        "room": "open_space",
        "x": 200.0,
        "y": 200.0,
        "requiredSeconds": 5.0,
        "status": "available", // | "in_progress" | "cooldown"
        "progress": 0.0, // 0..1, nur sinnvoll wenn in_progress
        "cooldownRemaining": 0.0,
      },
    ],
    "sabotages": [
      {
        "id": "ci_cd_red",
        "title": "CI/CD Rot",
        "cooldownRemaining": 0.0,
        "active": false,
      },
    ],
    "meeting": null, // null außer in Phase MEETING — siehe unten
  },
}
```

### Meeting-Sub-Payload (während Phase `MEETING`)

```jsonc
"meeting": {
  "callerId": "abc...",
  "title": "Wer hat auf main gepusht?",
  "remainingSeconds": 47,
  "votesCount": { "abc...": 2, "": 1 },  // playerId → count, "" = skip
  "alreadyVoted": ["abc...", "def...", ""]  // playerIds die schon abgestimmt haben (oder "" für Skip)
}
```

`votesCount` ist anonymisiert (zeigt nur Counts, nicht WER für WEN). `alreadyVoted` zeigt welche Spieler schon dran waren (für UI-Disable).

### `voting_result` (broadcast, einmal nach Meeting-Resolve)

```jsonc
{
  "type": "voting_result",
  "payload": {
    "removedPlayerId": "abc...", // "" wenn niemand entfernt
    "removedPlayerName": "Carol", // "" wenn niemand entfernt
    "wasChaosAgent": true, // nur sinnvoll wenn removed
    "tie": false, // true bei Stimmengleichheit zwischen named targets
    "skipped": false, // true wenn Skip die Mehrheit gewann
  },
}
```

### `game_ended` (broadcast, einmal beim Phase-Wechsel zu ENDED)

```jsonc
{
  "type": "game_ended",
  "payload": {
    "winner": "release_team", // oder "chaos_agents"
    "reason": "Release deployed.",
    "players": [
      {
        "id": "abc...",
        "name": "Sven",
        "role": "developer", // ROLLE WIRD HIER ÖFFENTLICH
        "team": "release_team",
        "completedTasks": 5,
        "triggeredSabotages": 0,
        "isAlive": true,
      },
    ],
  },
}
```

Win-Conditions in Reihenfolge (First-To-Fire):

1. `pipeline_stability <= 0` → `chaos_agents` gewinnt, Reason `"Die Pipeline ist tot."`
2. Alle Chaos-Spieler eliminiert → `release_team` gewinnt, Reason `"Alle Chaos-Agenten wurden enttarnt."`
3. `release_progress >= 100` → `release_team` gewinnt, Reason `"Release deployed."`
4. `remaining_seconds <= 0` → `chaos_agents` gewinnt, Reason `"Das Release-Fenster ist geschlossen."`

### `error` (privat, an den Sender der ursprünglichen Message)

```jsonc
{
  "type": "error",
  "payload": { "code": "NOT_HOST", "message": "Only the host can start the game." },
}
```

---

## 6. Vollständige Error-Code-Liste

| Code                   | Wo                                                        | Bedeutung                                                                |
| ---------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------ |
| `BAD_MESSAGE`          | jeder Handler                                             | Pydantic-Validation fehlgeschlagen — Payload entspricht nicht dem Schema |
| `ROOM_FULL`            | join_room                                                 | Mehr als 6 Spieler im Raum                                               |
| `NAME_TAKEN`           | join_room                                                 | Name in diesem Raum bereits vergeben                                     |
| `NOT_HOST`             | start_game, return_to_lobby                               | Aktion erfordert Host                                                    |
| `WRONG_PHASE`          | viele                                                     | Aktion in falscher Phase versucht                                        |
| `NOT_ENOUGH_PLAYERS`   | start_game                                                | <2 Spieler ohne `demo`-Flag                                              |
| `UNKNOWN_TASK`         | task_hold_start                                           | Task-ID nicht in Map                                                     |
| `TASK_ON_COOLDOWN`     | task_hold_start                                           | Task aktuell im Cooldown                                                 |
| `TASK_TOO_FAR`         | task_hold_start                                           | Spieler nicht innerhalb 40 px                                            |
| `PLAYER_ELIMINATED`    | task_hold_start, trigger_sabotage, call_emergency_meeting | Spieler ist `isAlive=false`                                              |
| `UNKNOWN_PLAYER`       | trigger_sabotage, call_emergency_meeting                  | Spieler-Session nicht gefunden                                           |
| `NOT_CHAOS_AGENT`      | trigger_sabotage                                          | Spieler ist nicht im Chaos-Team                                          |
| `UNKNOWN_SABOTAGE`     | trigger_sabotage                                          | Sabotage-ID unbekannt                                                    |
| `SABOTAGE_ON_COOLDOWN` | trigger_sabotage                                          | Sabotage aktuell im Cooldown                                             |
| `NOT_IN_WAR_ROOM`      | call_emergency_meeting                                    | Spieler nicht im War Room                                                |
| `NO_MEETING_LEFT`      | call_emergency_meeting                                    | Spieler hat sein einziges Meeting verbraucht                             |
| `CANNOT_VOTE`          | cast_vote, skip_vote                                      | Voter nicht lebend                                                       |
| `INVALID_TARGET`       | cast_vote                                                 | Target unbekannt oder eliminiert                                         |
| `NO_COLORS`            | intern                                                    | sollte nie passieren — Color-Palette < MAX_PLAYERS                       |
| `NO_ROLE`              | intern                                                    | `private_role_for` aufgerufen bevor Rollen verteilt waren                |

---

## 7. Konstanten und Defaults

| Konstante                                 | Wert           | Wo                                                                      |
| ----------------------------------------- | -------------- | ----------------------------------------------------------------------- |
| Tick-Frequenz                             | 20 Hz          | `app/main.py:TICK_HZ`                                                   |
| Map-Größe                                 | 2400 × 1600 px | `maps/default.json`                                                     |
| Player-Speed normal                       | 150 px/s       | `app/game/sabotages.py:NORMAL_SPEED`                                    |
| Player-Speed slow (Coffee=0 oder Meeting) | 80 px/s        | `app/game/sabotages.py:COFFEE_SLOW_SPEED`                               |
| Player-Kollisions-Radius                  | 20 px          | `app/game/walls.py:PLAYER_COLLISION_RADIUS`                             |
| Task-Interaction-Radius                   | 40 px          | `app/game/tasks.py:TASK_INTERACTION_RADIUS`                             |
| Task-Respawn-Cooldown                     | 8 s            | `app/game/tasks.py:TASK_RESPAWN_COOLDOWN`                               |
| Round-Timer                               | 720 s          | `app/game/game_room.py:ROUND_SECONDS`                                   |
| Meeting-Dauer                             | 60 s           | `app/game/game_room.py:MEETING_DURATION_SECONDS`                        |
| Mandatory-Meeting-Slow                    | 5 s            | `app/game/sabotages.py:MEETING_DURATION`                                |
| MAX_PLAYERS                               | 6              | `app/game/game_room.py:MAX_PLAYERS` (wird auf 12 hochgezogen, Tier 1.5) |

---

## 8. Beispiel-Sequenzen

### 8.1 Volle Lobby-Phase, 3 Spieler

```text
Alice connects → join_room("ABCD", "Alice")
                 ◀── room_joined(roomCode=ABCD, playerId=A, isHost=true, map=…)
                 ◀── lobby_state(players=[Alice])

Bob connects   → join_room("ABCD", "Bob")
                 ◀── room_joined(roomCode=ABCD, playerId=B, isHost=false, map=…)
Alice + Bob   ◀── lobby_state(players=[Alice, Bob])

Carol joins   → join_room("ABCD", "Carol")
                 ◀── room_joined(roomCode=ABCD, playerId=C, isHost=false, map=…)
A+B+C         ◀── lobby_state(players=[Alice, Bob, Carol])

Alice (host)  → start_game({})
                 ◀── private_role to Alice (developer)
                 ◀── private_role to Bob   (vibe_coder)
                 ◀── private_role to Carol (developer)
A+B+C         ◀── game_state(phase=playing, ...)
                 ... (jetzt 20 Hz game_state) ...
```

### 8.2 Sabotage + Reparatur

```text
Bob (chaos)   → trigger_sabotage("ci_cd_red")
                 → server: pipeline_stability -= 20, sabotage cooldown 60s
all           ◀── game_state(pipelineStability=80, sabotages=[{ci_cd_red, cd=60}, ...])

Carol läuft zum Server-Raum, drückt E nahe `repair_deployment`
              → task_hold_start("repair_deployment")
all           ◀── game_state(tasks=[{..., status=in_progress, progress=0.0}, ...])
              ... 6 Sekunden Hold ...
all           ◀── game_state(tasks=[{..., status=cooldown, cooldownRemaining=8}, ...])
                 → server: pipeline_stability += 15 → 95
all           ◀── game_state(pipelineStability=95, ...)
```

### 8.3 Voting

```text
Alice ist im War Room
              → call_emergency_meeting({})
all           ◀── game_state(phase=meeting, meeting={...60s...})

Alice         → cast_vote(targetPlayerId=Bob)
all           ◀── game_state(meeting.votesCount={Bob: 1}, alreadyVoted=[Alice])

Bob           → skip_vote()
all           ◀── game_state(meeting.votesCount={Bob: 1, "": 1}, alreadyVoted=[Alice, Bob])

Carol         → cast_vote(targetPlayerId=Bob)
all           ◀── game_state(meeting.votesCount={Bob: 2, "": 1}, alreadyVoted=[Alice, Bob, Carol])
              → server detects: alle voted → resolve
              → server: Bob.isAlive=false (most votes)
all           ◀── voting_result(removedPlayerId=Bob, removedPlayerName="Bob",
                                wasChaosAgent=true, tie=false, skipped=false)
all           ◀── game_state(phase=playing, players=[..., {id=Bob, isAlive=false}, ...])
              → server checks: alle Chaos-Agenten eliminiert → release_team gewinnt
all           ◀── game_state(phase=ended, ...)
all           ◀── game_ended(winner=release_team, reason="Alle Chaos-Agenten...", players=[...mit Rollen...])
```

---

## 9. Versions-Politik

Aktuell **kein** Versions-Header in den Messages. Wenn das Protokoll breaking-changes bekommt:

1. Ein neues `protocol_version`-Feld in `room_joined` einführen
2. Server unterstützt die letzten N Versionen via Branching
3. Old clients sehen `error{code: "PROTOCOL_VERSION_MISMATCH"}`

Bis dahin: Server und Client müssen vom gleichen Commit gebaut werden.

---

## 10. Godot-Implementierungs-Hinweis

GDScript-Beispiel für die Initialisierung:

```gdscript
extends Node
const WS_URL = "wss://game.prod-is-lava.dev/ws"

var _socket = WebSocketPeer.new()
var _player_id: String = ""
var _map: Dictionary = {}

func _ready():
    _socket.connect_to_url(WS_URL)

func _process(_dt):
    _socket.poll()
    var state = _socket.get_ready_state()
    if state == WebSocketPeer.STATE_OPEN:
        while _socket.get_available_packet_count() > 0:
            var pkt = _socket.get_packet().get_string_from_utf8()
            var msg = JSON.parse_string(pkt)
            _handle_message(msg)

func _handle_message(msg):
    match msg.type:
        "room_joined":
            _player_id = msg.payload.playerId
            _map = msg.payload.map
        "game_state":
            # update tilemap, players, etc.
            pass
        # ... weitere Handler ...

func send(type: String, payload: Dictionary = {}):
    var frame = JSON.stringify({"type": type, "payload": payload})
    _socket.send_text(frame)

# Beispiel: Join
func join_room(code: String, name: String):
    send("join_room", {"roomCode": code, "playerName": name})
```

Das ist der erwartete Shape. Volle Godot-Integration kommt mit Tier 3 der Roadmap.
