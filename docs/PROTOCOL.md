# WebSocket Protocol

Single Source of Truth fuer das Netzwerk-Protokoll zwischen MCM-Server und Client. Beide Clients (Browser jetzt, Godot spaeter) sprechen dieses Protokoll. Stand: nach Tier 3.4 (`coffee_pour`) — alle Tier-0/1/2/3-Features abgedeckt.

**Endpoint:** `wss://<host>/ws` (live: `wss://game.prod-is-lava.dev/ws`)
**Format:** UTF-8 JSON, ein Frame = eine Message.
**Konvention:** Wire-Format ist **camelCase**. Server validiert mit Pydantic; unbekannte Typen oder fehlerhafte Payloads werfen `ValidationError` und der Server schickt einen `error`-Frame zurueck.
**Authoritative source:** `app/protocol.py` (Pydantic-Modelle) plus `app/game/game_room.py::_public_state_base`. Wenn dieses Doc widerspricht, hat der Code recht — und dann ist dieses Doc zu aktualisieren.

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

Beide Richtungen (Client→Server und Server→Client) verwenden diese Huelle.

---

## 2. Lebenszyklus einer Verbindung

```text
Client                                                       Server
  |                                                            |
  | -- WebSocket /ws ---------------------------------------->  |
  |                                                            |
  | <-------------------------------------- (verbunden, idle) -|
  |                                                            |
  | -- join_room(roomCode, playerName) -------------------->   |   (alternativ: rejoin)
  |                                                            |
  | <-- room_joined(roomCode, playerId, isHost, map) ---------|
  | <-- lobby_state(roomCode, players[], availableMaps[], ...)|   (broadcast)
  |                                                            |
  | -- select_map(mapId) [host only, optional] ------------>   |
  | <-- lobby_state(...selectedMapId/map updated) -------------|
  |                                                            |
  | -- start_game(demo?) [host only] --------------------->    |
  |                                                            |
  | <-- private_role(role, team, description, availSabotages)-|   (privat pro Spieler)
  | <-- game_state(phase=playing, ...) ----------------------|   (jetzt 20 Hz)
  | <-- private_state(takedownCooldownRemaining) ------------|   (privat, nur Chaos, jeder Tick)
  |                                                            |
  | -- player_input / task_hold_start / trigger_sabotage /     |
  |    repair_sabotage / use_vent / trigger_takedown /         |
  |    report_body / mini_game_input ---------------------->   |
  | <-- game_state .........................................|
  | <-- mini_game_started / mini_game_state / completed -----|   (privat, an Mini-Game-Spieler)
  |                                                            |
  | -- call_emergency_meeting [in War Room] -------------->    |
  | <-- game_state(phase=meeting, meeting=...) --------------|
  | -- cast_vote / skip_vote ----------------------------->    |
  | <-- voting_result(removedPlayerId, ...) ----------------|
  | <-- game_state(phase=playing, ...) ----------------------|
  |                                                            |
  | (Win-Condition erfuellt)                                   |
  | <-- game_state(phase=ended, ...) ------------------------|
  | <-- game_ended(winner, reason, players[]) ---------------|
  |                                                            |
  | -- return_to_lobby [host only] ---------------------->     |   (alternativ: leave_room jeder Spieler,
  | <-- lobby_state .........................................|    abort_round host waehrend Runde)
```

Disconnect-Verhalten: Server haelt die Spieler-ID 30 s offen (`RECONNECT_GRACE_SECONDS`). Client kann mit `rejoin(roomCode, playerId)` denselben Slot zurueckholen, sofern Phase weiterhin Existenz erlaubt (PLAYING / MEETING / ENDED). Nach Ablauf der Frist wird der Slot freigegeben und ein erneuter Join muss als neuer Spieler ueber `join_room` laufen.

---

## 3. Phasen (State-Machine)

```text
LOBBY --(host: start_game)--> PLAYING --(call_emergency_meeting | report_body)--> MEETING
  ^                              |                                                   |
  |                              | (win condition)                                   | (timer 0
  |                              v                                                   |  oder alle
  |                            ENDED  <----------------------------------------------|  voted)
  |                              |
  |                              | (host: return_to_lobby ODER abort_round)
  +------------------------------+
```

| Phase     | Server-Tick                                         | Erlaubte Inputs                                                                                                                                                                                                                                    |
| --------- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LOBBY`   | inaktiv                                             | `join_room`, `rejoin`, `select_map` (Host), `start_game` (Host), `leave_room`                                                                                                                                                                      |
| `PLAYING` | 20 Hz: Movement, Tasks, Sabotagen, Timer, Win-Check | `player_input`, `task_hold_start`, `task_hold_stop`, `trigger_sabotage` (Chaos), `repair_sabotage`, `use_vent` (Chaos), `trigger_takedown` (Chaos), `report_body`, `call_emergency_meeting`, `mini_game_input`, `abort_round` (Host), `leave_room` |
| `MEETING` | 20 Hz: Meeting-Timer + Auto-Resolve                 | `cast_vote`, `skip_vote` (lebende Spieler), `abort_round` (Host), `leave_room`                                                                                                                                                                     |
| `ENDED`   | inaktiv                                             | `return_to_lobby` (Host), `leave_room`                                                                                                                                                                                                             |

---

## 4. Client → Server

### `join_room`

Erste Aktion nach Connect (sofern keine alte Session per `rejoin` reaktiviert wird). Erzeugt den Raum wenn der Code neu ist, sonst Beitritt.

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

- `ROOM_FULL` (>= 12 Spieler)
- `NAME_TAKEN`

### `rejoin`

Verbindung wiederherstellen ohne neuen Spielerslot zu beanspruchen. Innerhalb von 30 s nach Disconnect (`RECONNECT_GRACE_SECONDS`).

```jsonc
{
  "type": "rejoin",
  "payload": {
    "roomCode": "ABCD",
    "playerId": "abc1234567890def",
  },
}
```

**Server antwortet** wie bei `join_room` (`room_joined` + `lobby_state` + ggf. `private_role` + erstes `game_state`). Bei Fehler:

- `REJOIN_NOT_AVAILABLE` (Raum nicht vorhanden, Spieler-ID unbekannt, oder Grace-Period abgelaufen)

### `start_game`

Nur vom Host akzeptiert. Wechselt Phase `LOBBY` → `PLAYING`.

```jsonc
{
  "type": "start_game",
  "payload": {
    "demo": false, // optional, default false; wenn true: min-2-Player-Guard uebersprungen, Solo-Spieler wird Chaos
  },
}
```

**Server antwortet** mit `private_role` (privat pro Spieler) und `game_state` (broadcast). Bei Fehler `error`:

- `NOT_HOST`
- `WRONG_PHASE` (nicht in LOBBY)
- `NOT_ENOUGH_PLAYERS` (<2 ohne `demo`)

### `select_map`

Nur Host, nur in LOBBY. Wechselt die fuer die naechste Runde verwendete Map.

```jsonc
{
  "type": "select_map",
  "payload": { "mapId": "office_v2" },
}
```

**Server antwortet** mit `lobby_state` (broadcast) mit aktualisiertem `selectedMapId` und `map`. Bei Fehler `error`:

- `NOT_HOST`
- `WRONG_PHASE`
- `UNKNOWN_MAP` (Map-ID nicht im Registry)

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

Idempotent. Geister (Spectator-Mode, Tier 2.6) duerfen sich weiter bewegen, eliminierte Spieler ohne Verbindung werden ignoriert.

### `task_hold_start` / `task_hold_stop`

Beginnt/beendet das Halten eines Tasks. Server checkt Proximity (40 px) und Phase. Wenn die Task ein `mini_game` traegt (Tier 3.1+), oeffnet `task_hold_start` stattdessen eine Mini-Game-Session und das Hold-E-Verhalten greift nicht.

```jsonc
{ "type": "task_hold_start", "payload": { "taskId": "fix_unit_tests" } }
{ "type": "task_hold_stop",  "payload": { "taskId": "fix_unit_tests" } }
```

`task_hold_stop` cancelt auch eine laufende Mini-Game-Session ohne Reward (siehe `mini_game_completed` mit `success=false`).

Errors auf `task_hold_start`:

- `WRONG_PHASE`
- `UNKNOWN_TASK`
- `TASK_ON_COOLDOWN`
- `TASK_TOO_FAR`
- `PLAYER_ELIMINATED`
- `MINI_GAME_ALREADY_ACTIVE` (versucht zweite Mini-Game-Session zu starten)
- `UNKNOWN_MINI_GAME` (Task verweist auf nicht-registrierte Mini-Game-ID)

`task_hold_stop` ist tolerant — Aufruf ohne aktiven Hold ist No-op.

### `trigger_sabotage`

Nur Chaos-Agenten. Server prueft Cooldown und ob `comms_outage` aktiv ist (blockiert andere Sabotagen).

```jsonc
{ "type": "trigger_sabotage", "payload": { "sabotageId": "ci_cd_red" } }
```

Verfuegbare Sabotage-IDs (Stand Tier 2.5):

- `ci_cd_red`
- `coffee_outage`
- `mandatory_meeting`
- `merge_conflict_storm`
- `fake_customer_request`
- `flaky_tests`
- `lights_out` (Tier 2.4 — Vignette + Repair-Panel im Server-Room)
- `comms_outage` (Tier 2.5 — blockiert Tasks + andere Sabotagen, Repair-Panel im War-Room)

Client kennt die Liste aus `private_role.availableSabotages`.

Errors:

- `WRONG_PHASE`
- `UNKNOWN_PLAYER`
- `PLAYER_ELIMINATED`
- `NOT_CHAOS_AGENT`
- `UNKNOWN_SABOTAGE`
- `SABOTAGE_ON_COOLDOWN`
- `COMMS_DOWN` (beim Trigger waehrend `comms_outage` aktiv ist und die ausgewaehlte Sabotage nicht `comms_outage` selbst ist)
- `NOT_NEAR_OBJECT` (Tier 2.7 rework: Chaos nicht in 60 px Reichweite eines Task-Anchors mit passendem `objectType` für die getriggerte Sabotage; nur wenn die Map mind. einen typed Anchor hat)

### `repair_sabotage`

Spieler in Reichweite eines Repair-Panels (`SABOTAGE_PANEL_INTERACTION_RADIUS = 50 px`) reparieren die laufende Sabotage. Geister duerfen reparieren (helfen Release-Team auch tot).

```jsonc
{ "type": "repair_sabotage", "payload": { "sabotageId": "lights_out" } }
```

Errors:

- `WRONG_PHASE`
- `UNKNOWN_SABOTAGE`
- `SABOTAGE_NOT_ACTIVE` (Sabotage existiert nicht oder ist gerade nicht broken)
- `NO_PANEL` (diese Sabotage hat kein Repair-Panel auf der Map)
- `OUT_OF_RANGE` (Spieler nicht in Reichweite)
- `UNKNOWN_PLAYER`

### `use_vent`

Nur Chaos-Agenten. Spieler steht an einem Vent (`VENT_INTERACTION_RADIUS = 50 px`), wird zu `targetVentId` teleportiert, sofern dieser in der `connectedTo`-Liste des Source-Vents enthalten ist.

```jsonc
{ "type": "use_vent", "payload": { "targetVentId": "vent_kitchen" } }
```

Errors:

- `WRONG_PHASE`
- `NOT_CHAOS_AGENT`
- `PLAYER_ELIMINATED`
- `NO_VENT_NEARBY` (Spieler steht an keinem Vent)
- `UNKNOWN_TARGET` (Target-Vent existiert nicht oder ist nicht mit der Source verbunden)
- `UNKNOWN_PLAYER`

### `trigger_takedown`

Nur Chaos-Agenten. Eliminiert ein anderes lebendes Mitglied im Take-Down-Radius (`TAKEDOWN_RADIUS = 40 px`). Cooldown `TAKEDOWN_COOLDOWN = 25 s` (siehe `private_state`).

```jsonc
{ "type": "trigger_takedown", "payload": { "targetPlayerId": "abc..." } }
```

Effekte: Target wird `isAlive=false`, ein Body-Eintrag erscheint in `game_state.bodies`, Take-Down-Cooldown des Taeters wird gesetzt.

Errors:

- `WRONG_PHASE`
- `NOT_CHAOS_AGENT`
- `PLAYER_ELIMINATED` (Taeter selbst)
- `UNKNOWN_TARGET`
- `TARGET_ELIMINATED` (Target ist schon tot)
- `TOO_FAR` (Target ausserhalb 40 px)
- `TAKEDOWN_ON_COOLDOWN`
- `UNKNOWN_PLAYER`

### `report_body`

Jeder lebende Spieler in Naehe einer Leiche kann sie reporten. Triggert MEETING-Phase.

```jsonc
{ "type": "report_body", "payload": { "bodyId": "body_abc..." } }
```

Errors:

- `WRONG_PHASE`
- `PLAYER_ELIMINATED`
- `UNKNOWN_BODY`
- `OUT_OF_RANGE`
- `UNKNOWN_PLAYER`

### `call_emergency_meeting`

Triggert MEETING-Phase. Spieler muss im War Room stehen + sein einziges Meeting noch uebrig haben.

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

Waehrend MEETING-Phase. Lebende Spieler nur. Eine Abstimmung pro Spieler (Re-Vote ueberschreibt).

```jsonc
{ "type": "cast_vote", "payload": { "targetPlayerId": "abc..." } }
{ "type": "skip_vote", "payload": {} }
```

Errors auf `cast_vote`:

- `WRONG_PHASE`
- `CANNOT_VOTE` (Voter nicht lebend)
- `INVALID_TARGET` (Target unbekannt oder eliminiert)

### `mini_game_input`

Spieler-Input innerhalb einer aktiven Mini-Game-Session. `action` ist plugin-spezifisch (z.B. `click`, `connect`, `stop`); der Server leitet ihn an das passende Plugin weiter, das eigene Validierung durchfuehrt.

```jsonc
{
  "type": "mini_game_input",
  "payload": {
    "action": "connect",
    "params": { "sourceId": "s0", "destinationId": "d2" },
  },
}
```

Errors:

- `NO_ACTIVE_MINI_GAME`
- `UNKNOWN_ACTION` (vom Plugin)
- `INVALID_PARAMS` (vom Plugin)
- weitere plugin-spezifische Codes (z.B. `UNKNOWN_TEST`, `UNKNOWN_NODE`)

### `return_to_lobby`

Nur in Phase `ENDED`, nur Host. Setzt Raum auf `LOBBY` zurueck, alle Spieler leben wieder, neue Rollen-Verteilung beim naechsten `start_game`.

```jsonc
{ "type": "return_to_lobby", "payload": {} }
```

Errors:

- `NOT_HOST`
- `WRONG_PHASE`

### `abort_round`

Nur Host, beendet die laufende Runde sofort und springt nach LOBBY zurueck.

```jsonc
{ "type": "abort_round", "payload": {} }
```

Errors:

- `NOT_HOST`
- `WRONG_PHASE` (nur PLAYING/MEETING erlaubt)

### `leave_room`

Jeder Spieler. Trennt die Session ohne 30-s-Reconnect-Grace.

```jsonc
{ "type": "leave_room", "payload": {} }
```

Antwort: kein eigener Frame, aber `lobby_state` (Broadcast) reflektiert die Entfernung.

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

`map` ist die volle Spielkarte als JSON — Raeume, Wand-Linien, Tueren, Spawn-Punkte, Task-Anker, Sabotage-Panel-Positionen, Vents, War-Room-ID. Client cachet sie fuer die Dauer der Session.

### `lobby_state` (broadcast)

```jsonc
{
  "type": "lobby_state",
  "payload": {
    "roomCode": "ABCD",
    "players": [{ "id": "abc...", "name": "Sven", "color": "#4ade80", "isHost": true }],
    "availableMaps": [
      { "id": "default", "name": "Default Office" },
      { "id": "office_v2", "name": "Bigger Office" },
    ],
    "selectedMapId": "default",
    "map": {
      /* GameMap der aktuell selektierten Map */
    },
  },
}
```

Wird gesendet bei: jedem Join, jedem Disconnect, `select_map`, `leave_room`, `return_to_lobby`, `abort_round`. Nicht-Host-Clients re-rendern bei Map-Wechsel die Geometrie aus `map`.

### `private_role` (privat, einmal beim Spielstart)

```jsonc
{
  "type": "private_role",
  "payload": {
    "role": "vibe_coder",
    "team": "chaos_agents",
    "description": "Du bist der Vibe Coder. Sabotiere das Release...",
    "availableSabotages": [
      "ci_cd_red",
      "coffee_outage",
      "mandatory_meeting",
      "merge_conflict_storm",
      "fake_customer_request",
      "flaky_tests",
      "lights_out",
      "comms_outage",
    ],
  },
}
```

`availableSabotages` ist leer fuer `release_team`. Client zeigt Sabotage-Buttons nur wenn nicht-leer. Welche Sabotagen ein Chaos-Agent hat haengt von der Rolle ab — typischerweise alle, kann aber rollen-spezifisch beschnitten werden.

### `private_state` (privat, an Chaos-Agenten, jeden Tick waehrend PLAYING)

```jsonc
{
  "type": "private_state",
  "payload": {
    "takedownCooldownRemaining": 18.4,
  },
}
```

Nur Chaos-Agenten erhalten diesen Frame. Release-Team-Spieler bekommen ihn nicht (saubere Trennung — leakt nichts). Wert wird in Sekunden gerundet auf 2 Nachkommastellen geliefert.

### `game_state` (broadcast, 20 Hz waehrend PLAYING und MEETING)

Dieser Frame ist **per-Viewer personalisiert** (Spectator-Mode, Tier 2.6): lebende Spieler sehen nur lebende Mitspieler im `players`-Feld. Geister sehen alle Spieler (inkl. anderer Geister). Die nicht-Player-Felder sind fuer alle Viewer identisch.

```jsonc
{
  "type": "game_state",
  "payload": {
    "phase": "playing", // oder "meeting" oder "ended"
    "remainingSeconds": 542,
    "releaseProgress": 38,
    "pipelineStability": 80,
    "coffeeLevel": 100,
    "incidents": 12,
    "players": [
      {
        "id": "abc...",
        "name": "Sven",
        "x": 250.5,
        "y": 100.0,
        "color": "#4ade80",
        "isHost": true,
        "isAlive": true,
        "isConnected": true,
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
    "sabotagePanels": [
      { "sabotageId": "lights_out", "x": 1200, "y": 800 },
      { "sabotageId": "comms_outage", "x": 4200, "y": 240 },
    ],
    "vents": [
      {
        "id": "vent_kitchen",
        "x": 600,
        "y": 1900,
        "connectedTo": ["vent_office", "vent_basement"],
      },
    ],
    "bodies": [
      { "id": "body_abc...", "x": 1300, "y": 940, "color": "#60a5fa", "victimName": "Carol" },
    ],
    "events": [
      { "seq": 1, "severity": "info", "message": "Release-Fenster offen." },
      { "seq": 2, "severity": "warn", "message": "Pipeline instabil." },
      { "seq": 3, "severity": "danger", "message": "Carol wurde entfernt - war Chaos-Agent." },
    ],
    "lightsOff": false,
    "commsDown": false,
    "meeting": null, // null ausser in Phase MEETING - siehe unten
  },
}
```

Felder im Detail:

- `lightsOff`: true waehrend `lights_out` aktiv ist. Client rendert Vignette.
- `commsDown`: true waehrend `comms_outage` aktiv ist. Client zeigt Disable-Hinweis auf Tasks/Sabotagen.
- `sabotagePanels`: Map-statische Liste der Repair-Panel-Positionen (eine pro repariererbarer Sabotage). Client nutzt sie fuer die UI-Hinweise „F naehe Panel".
- `vents`: Map-statische Liste, dieselbe in jedem Frame. Client zeichnet sie fuer alle, nur Chaos kann interagieren.
- `tasks[i].objectType` (Tier 2.7 rework): pro Task-Anchor, z.B. `ci_console`, `git_terminal`, `coffee_machine`, `monitoring_panel`, `meeting_screen`, `release_console`, `qa_terminal`, `legacy_terminal`. Sabotagen sind über `trigger_object_types` server-seitig an diese Typen gebunden — Chaos triggert eine Sabotage am SELBEN Anchor wie der zugehörige Release-Task → outsider sehen nicht, ob da gearbeitet oder sabotiert wird.
- `sabotages[i].triggerObjectTypes` (Tier 2.7 rework): Liste der erlaubten `objectType`-Werte. Leere Liste = Legacy „from-anywhere"-Pfad.
- `sabotages[i].triggerAnchors` (Tier 2.7 rework): konkrete Positionen `[{x,y}]` aller Anchors, an denen diese Sabotage triggerbar ist. Client berechnet daraus die per-Sabotage-Proximity für Button-Enable.
- `sabotages[i].objectHint` (Tier 2.7 rework): human-readable Hint („CI-Konsole im Server Room"), den der Client unter dem Sabotage-Button zeigt, wenn der Spieler ausser Reichweite ist.
- `tasks[i].category` (Tier 3.5): `code` / `infra` / `legacy` / `scope` / `support`. Treibt Role-Speed-Modifier serverseitig.
- `meeting.context` (Tier 3.6): `{reporterName, body?: {victimName, x, y, room}, recentEvents: [{severity, message, seq}], alive: [{id, name}]}`. Snapshot zum Zeitpunkt der Meeting-Eröffnung — Hinweise, keine Beweise.
- `finalSummary` (Tier 3.7): None ausserhalb von ENDED. In ENDED: `{winner, reason, releaseProgress, pipelineStability, incidents, sabotagesTriggered, repairsCompleted, kills, perPlayer: [{playerId, name, color, role, team, tasksCompleted, sabotagesTriggered, coffeeFinal, abilityUsed, alive}], awards: [{title, playerName, reason}], postmortem: "AI-styled markdown text"}`.
- `bodies`: alle bisher entdeckten + nicht reporteten Leichen. Verschwindet beim Report.
- `events`: kontinuierlich anwachsende Liste mit `seq`-Counter. Client trackt `lastSeq` und zeigt nur neue Eintraege.
- `players[i].isConnected`: false waehrend Reconnect-Grace (Spieler kann zurueckkommen).

### Meeting-Sub-Payload (waehrend Phase `MEETING`)

```jsonc
"meeting": {
  "callerId": "abc...",
  "title": "Wer hat auf main gepusht?",
  "remainingSeconds": 47,
  "votesCount": { "abc...": 2, "": 1 },        // playerId -> count, "" = skip
  "alreadyVoted": ["abc...", "def...", ""]      // playerIds die schon abgestimmt haben (oder "" fuer Skip)
}
```

`votesCount` ist anonymisiert (zeigt nur Counts, nicht WER fuer WEN). `alreadyVoted` zeigt welche Spieler schon dran waren (fuer UI-Disable).

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
        "role": "developer", // ROLLE WIRD HIER OEFFENTLICH
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

### `mini_game_started` (privat, an den Mini-Game-Spieler)

Folgt unmittelbar einem `task_hold_start` auf einer Task mit `mini_game`. Oeffnet die Modal-UI auf dem Client.

```jsonc
{
  "type": "mini_game_started",
  "payload": {
    "taskId": "repair_deployment",
    "miniGameId": "cable_pairing",
    "title": "Server-Racks neu verkabeln",
    "view": {
      /* plugin-spezifisch, opaque fuer Framework */
    },
  },
}
```

`view` ist plugin-spezifisch (siehe `app/game/minigames/<id>.py::public_view`). Beispiele:

- `test_suite_repair`: `{ tests: [{id, label, order, status}], nextOrder, totalTests }`
- `cable_pairing`: `{ sources, destinations, connections, totalPairs }`
- `coffee_pour`: `{ elapsed, cycleSeconds, sweetMin, sweetMax, attempts, lastAttemptFill, complete }`

### `mini_game_state` (privat, an den Mini-Game-Spieler)

Echo nach jedem `mini_game_input`. Verkapselt das aktualisierte `view`.

```jsonc
{
  "type": "mini_game_state",
  "payload": {
    "taskId": "repair_deployment",
    "view": {
      /* plugin-spezifisch */
    },
  },
}
```

### `mini_game_completed` (privat, an den Mini-Game-Spieler)

Schliesst die Session — Modal soll schliessen.

```jsonc
{
  "type": "mini_game_completed",
  "payload": {
    "taskId": "repair_deployment",
    "success": true,
    "reason": "solved", // bei success=false: "cancelled" | "meeting_started" | "round_ended" | "disconnected" | "takedown"
  },
}
```

### `error` (privat, an den Sender der urspruenglichen Message)

```jsonc
{
  "type": "error",
  "payload": { "code": "NOT_HOST", "message": "Only the host can start the game." },
}
```

---

## 6. Vollstaendige Error-Code-Liste

| Code                       | Wo                                                       | Bedeutung                                                                       |
| -------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `BAD_MESSAGE`              | jeder Handler                                            | Pydantic-Validation fehlgeschlagen — Payload entspricht nicht dem Schema        |
| `ROOM_FULL`                | join_room                                                | Mehr als 12 Spieler im Raum                                                     |
| `NAME_TAKEN`               | join_room                                                | Name in diesem Raum bereits vergeben                                            |
| `REJOIN_NOT_AVAILABLE`     | rejoin                                                   | Raum oder Spieler-ID unbekannt, oder Grace-Period abgelaufen                    |
| `NOT_HOST`                 | start_game, return_to_lobby, abort_round, select_map     | Aktion erfordert Host                                                           |
| `WRONG_PHASE`              | viele                                                    | Aktion in falscher Phase versucht                                               |
| `NOT_ENOUGH_PLAYERS`       | start_game                                               | <2 Spieler ohne `demo`-Flag                                                     |
| `UNKNOWN_MAP`              | select_map                                               | Map-ID nicht im Registry                                                        |
| `UNKNOWN_TASK`             | task_hold_start                                          | Task-ID nicht in Map                                                            |
| `TASK_ON_COOLDOWN`         | task_hold_start                                          | Task aktuell im Cooldown                                                        |
| `TASK_TOO_FAR`             | task_hold_start                                          | Spieler nicht innerhalb 40 px                                                   |
| `MINI_GAME_ALREADY_ACTIVE` | task_hold_start                                          | Spieler hat bereits eine Mini-Game-Session offen                                |
| `UNKNOWN_MINI_GAME`        | task_hold_start                                          | `mini_game`-Feld der Task verweist auf nicht-registrierte ID                    |
| `NO_ACTIVE_MINI_GAME`      | mini_game_input                                          | Spieler hat keine Mini-Game-Session                                             |
| `UNKNOWN_ACTION`           | mini_game_input (plugin)                                 | Plugin kennt diese Action nicht                                                 |
| `INVALID_PARAMS`           | mini_game_input (plugin)                                 | Plugin-Params fehlen/falsch                                                     |
| `UNKNOWN_TEST`/`_NODE`/... | mini_game_input (plugin)                                 | plugin-spezifische ID-Fehler                                                    |
| `PLAYER_ELIMINATED`        | task_hold_start, trigger_sabotage, trigger_takedown, ... | Spieler ist `isAlive=false`                                                     |
| `UNKNOWN_PLAYER`           | trigger_sabotage, trigger_takedown, repair_sabotage, ... | Spieler-Session nicht gefunden                                                  |
| `NOT_CHAOS_AGENT`          | trigger_sabotage, trigger_takedown, use_vent             | Spieler ist nicht im Chaos-Team                                                 |
| `UNKNOWN_SABOTAGE`         | trigger_sabotage, repair_sabotage                        | Sabotage-ID unbekannt                                                           |
| `SABOTAGE_ON_COOLDOWN`     | trigger_sabotage                                         | Sabotage aktuell im Cooldown                                                    |
| `SABOTAGE_NOT_ACTIVE`      | repair_sabotage                                          | Sabotage existiert nicht oder ist nicht broken                                  |
| `NO_PANEL`                 | repair_sabotage                                          | Sabotage hat kein Repair-Panel auf der Map                                      |
| `OUT_OF_RANGE`             | repair_sabotage, report_body                             | Spieler nicht in Reichweite                                                     |
| `COMMS_DOWN`               | trigger_sabotage                                         | `comms_outage` blockt andere Sabotagen                                          |
| `NOT_NEAR_OBJECT`          | trigger_sabotage                                         | Tier 2.7 rework: Chaos nicht in 60-px-Reichweite eines passenden Object-Anchors |
| `NO_ABILITY`               | use_ability                                              | Rolle hat keine aktive Fähigkeit                                                |
| `ABILITY_ALREADY_USED`     | use_ability                                              | Tier 3.5: Ability ist 1×/Runde                                                  |
| `NO_VENT_NEARBY`           | use_vent                                                 | Spieler steht an keinem Vent                                                    |
| `UNKNOWN_TARGET`           | use_vent, trigger_takedown                               | Target-Vent oder -Spieler unbekannt / nicht verbunden                           |
| `TARGET_ELIMINATED`        | trigger_takedown                                         | Target ist schon tot                                                            |
| `TOO_FAR`                  | trigger_takedown                                         | Target ausserhalb 40 px                                                         |
| `TAKEDOWN_ON_COOLDOWN`     | trigger_takedown                                         | Take-Down-Cooldown noch aktiv                                                   |
| `UNKNOWN_BODY`             | report_body                                              | Body-ID unbekannt                                                               |
| `NOT_IN_WAR_ROOM`          | call_emergency_meeting                                   | Spieler nicht im War Room                                                       |
| `NO_MEETING_LEFT`          | call_emergency_meeting                                   | Spieler hat sein einziges Meeting verbraucht                                    |
| `CANNOT_VOTE`              | cast_vote, skip_vote                                     | Voter nicht lebend                                                              |
| `INVALID_TARGET`           | cast_vote                                                | Target unbekannt oder eliminiert                                                |
| `NO_COLORS`                | intern                                                   | sollte nie passieren — Color-Palette < MAX_PLAYERS                              |
| `NO_ROLE`                  | intern                                                   | `private_role_for` aufgerufen bevor Rollen verteilt waren                       |

---

## 7. Konstanten und Defaults

| Konstante                                            | Wert                   | Wo                                                     |
| ---------------------------------------------------- | ---------------------- | ------------------------------------------------------ |
| Tick-Frequenz                                        | 20 Hz                  | `app/main.py:TICK_HZ`                                  |
| Map-Groesse (Default-Map)                            | 4800 × 3200 px         | `maps/default.json`                                    |
| Player-Speed normal                                  | 300 px/s               | `app/game/sabotages.py:NORMAL_SPEED`                   |
| Player-Speed slow (Coffee=0 oder Mandatory)          | herabgesetzt           | `app/game/sabotages.py`                                |
| Player-Kollisions-Radius                             | 20 px                  | `app/game/walls.py:PLAYER_COLLISION_RADIUS`            |
| Task-Interaction-Radius                              | 40 px                  | `app/game/tasks.py:TASK_INTERACTION_RADIUS`            |
| Sabotage-Panel-Interaction-Radius                    | 50 px                  | `app/game/tasks.py:SABOTAGE_PANEL_INTERACTION_RADIUS`  |
| Vent-Interaction-Radius                              | 50 px                  | `app/game/tasks.py:VENT_INTERACTION_RADIUS`            |
| Sabotage-Object-Interaction-Radius (Tier 2.7 rework) | 60 px                  | `app/game/tasks.py:SABOTAGE_OBJECT_INTERACTION_RADIUS` |
| Coffee-Energy Decay (Tier 3.5)                       | 1.4/s × Rolle-Modifier | `app/game/game_room.py:_tick_coffee_energy`            |
| Take-Down-Radius                                     | 40 px                  | `app/game/game_room.py:TAKEDOWN_RADIUS`                |
| Take-Down-Cooldown                                   | 25 s                   | `app/game/game_room.py:TAKEDOWN_COOLDOWN`              |
| Task-Respawn-Cooldown                                | 8 s                    | `app/game/tasks.py:TASK_RESPAWN_COOLDOWN`              |
| Round-Timer                                          | 900 s                  | `app/game/game_room.py:ROUND_SECONDS`                  |
| Meeting-Dauer                                        | 60 s                   | `app/game/game_room.py:MEETING_DURATION_SECONDS`       |
| Mandatory-Meeting-Slow                               | 5 s                    | `app/game/sabotages.py:MEETING_DURATION`               |
| Reconnect-Grace                                      | 30 s                   | `app/game/game_room.py:RECONNECT_GRACE_SECONDS`        |
| MAX_PLAYERS                                          | 12                     | `app/game/game_room.py:MAX_PLAYERS`                    |
| Multi-Chaos-Schwelle                                 | 7 Spieler → 2 Chaos    | `app/game/game_room.py` (Rollen-Verteilung)            |

---

## 8. Beispiel-Sequenzen

### 8.1 Volle Lobby-Phase, 3 Spieler

```text
Alice connects -> join_room("ABCD", "Alice")
                  <-- room_joined(roomCode=ABCD, playerId=A, isHost=true, map=...)
                  <-- lobby_state(players=[Alice], availableMaps=[...], selectedMapId="default")

Bob connects   -> join_room("ABCD", "Bob")
                  <-- room_joined(roomCode=ABCD, playerId=B, isHost=false, map=...)
Alice + Bob    <-- lobby_state(players=[Alice, Bob], ...)

Alice (host)   -> select_map({ mapId: "office_v2" })
A+B            <-- lobby_state(players=[...], selectedMapId="office_v2", map={...})

Carol joins    -> join_room("ABCD", "Carol")
                  <-- room_joined(roomCode=ABCD, playerId=C, isHost=false, map=<office_v2>)
A+B+C          <-- lobby_state(players=[Alice, Bob, Carol], ...)

Alice          -> start_game({})
                  <-- private_role to Alice (developer)
                  <-- private_role to Bob   (vibe_coder)
                  <-- private_role to Carol (developer)
A+B+C          <-- game_state(phase=playing, ...)
                  ... (jetzt 20 Hz game_state, plus private_state nur an Bob) ...
```

### 8.2 Sabotage + Repair-Panel

```text
Bob (chaos)   -> trigger_sabotage("lights_out")
                 -> server: sabotage active, lightsOff=true, cooldown 60s
all           <-- game_state(lightsOff=true, sabotages=[{lights_out, active=true, cd=60}, ...])

Carol laeuft zum Server-Room, nahe Repair-Panel
              -> repair_sabotage({ sabotageId: "lights_out" })
                 -> server: lights_out cleared
all           <-- game_state(lightsOff=false, sabotages=[{lights_out, active=false, cd=60}, ...])
```

### 8.3 Mini-Game (Tier 3)

```text
Carol nahe `repair_deployment`
              -> task_hold_start({ taskId: "repair_deployment" })
                 -> server: opens cable_pairing session
Carol         <-- mini_game_started({ taskId, miniGameId="cable_pairing", view={...4 sources, 4 dests, no connections...} })
all           <-- game_state(tasks=[{repair_deployment, status=in_progress}, ...])

Carol         -> mini_game_input({ action: "connect", params: { sourceId: "s0", destinationId: "d2" } })
Carol         <-- mini_game_state({ taskId, view={...connections={s0:d2}...} })
              ... drei weitere correct connects ...
Carol         <-- mini_game_completed({ taskId, success=true, reason="solved" })
                 -> server: pipeline_stability += 15, task auf cooldown
all           <-- game_state(pipelineStability=95, tasks=[{repair_deployment, status=cooldown, cd=8}, ...])
```

### 8.4 Take-Down → Body → Report → Voting

```text
Bob (chaos) sieht Alice allein im Server-Room
              -> trigger_takedown({ targetPlayerId: A })
                 -> server: Alice.isAlive=false, body created, takedown cooldown 25s
Bob           <-- private_state({ takedownCooldownRemaining: 25.0 })
all alive     <-- game_state(players=[Bob, Carol, ...] without Alice, bodies=[{id=body_..., x, y, color, victimName="Alice"}])
Alice (ghost) <-- game_state(players=[Bob, Carol, Alice(isAlive=false), ...] full roster)

Carol stolpert ueber Body
              -> report_body({ bodyId: "body_..." })
                 -> server: phase=MEETING, body removed
all           <-- game_state(phase=meeting, meeting={...60s, votesCount={}, alreadyVoted=[]}, bodies=[])

Carol         -> cast_vote({ targetPlayerId: B })
all           <-- game_state(meeting.votesCount={B:1}, alreadyVoted=[Carol])

Bob           -> skip_vote({})
all           <-- game_state(meeting.votesCount={B:1, "":1}, alreadyVoted=[Carol, Bob])

(Timer abgelaufen ODER alle voted) -> server resolves
all           <-- voting_result({ removedPlayerId: B, removedPlayerName: "Bob", wasChaosAgent: true, tie: false, skipped: false })
all           <-- game_state(phase=playing, players=[..., {Bob isAlive=false}, ...])
              -> server checks: alle Chaos eliminiert -> release_team gewinnt
all           <-- game_state(phase=ended, ...)
all           <-- game_ended({ winner: "release_team", reason: "Alle Chaos-Agenten wurden enttarnt.", players: [...mit Rollen...] })
```

---

## 9. Versions-Politik

Aktuell **kein** Versions-Header in den Messages. Wenn das Protokoll breaking-changes bekommt:

1. Ein neues `protocol_version`-Feld in `room_joined` einfuehren
2. Server unterstuetzt die letzten N Versionen via Branching
3. Old clients sehen `error{code: "PROTOCOL_VERSION_MISMATCH"}`

Bis dahin: Server und Client muessen vom gleichen Commit gebaut werden. Browser-Client bezieht JS direkt vom Server (`/static/main.js`), also synchron. Godot-Client wird Tier 4 — zu dem Zeitpunkt sollte spaetestens das Versions-Feld kommen.

---

## 10. Godot-Implementierungs-Hinweis

GDScript-Beispiel, das die wichtigsten Frame-Typen abdeckt (inkl. Mini-Game und Reconnect):

```gdscript
extends Node
const WS_URL = "wss://game.prod-is-lava.dev/ws"

var _socket = WebSocketPeer.new()
var _player_id: String = ""
var _room_code: String = ""
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
            _room_code = msg.payload.roomCode
            _map = msg.payload.map
        "lobby_state":
            # update lobby UI, map dropdown, player list
            pass
        "private_role":
            # store role, show available sabotages if chaos
            pass
        "private_state":
            # update take-down cooldown HUD (chaos only)
            pass
        "game_state":
            # update tilemap (only on map change), players, tasks,
            # sabotages, vents, sabotagePanels, bodies, events,
            # lightsOff vignette, commsDown UI
            pass
        "mini_game_started":
            _open_mini_game(msg.payload)
        "mini_game_state":
            _update_mini_game(msg.payload)
        "mini_game_completed":
            _close_mini_game(msg.payload)
        "voting_result":
            # show toast 5s
            pass
        "game_ended":
            # show endscreen with revealed roles
            pass
        "error":
            push_warning("server error: %s" % msg.payload.code)

func send(type: String, payload: Dictionary = {}):
    var frame = JSON.stringify({"type": type, "payload": payload})
    _socket.send_text(frame)

func join_room(code: String, name: String):
    send("join_room", {"roomCode": code, "playerName": name})

func rejoin():
    # call after a transient disconnect; server holds the slot 30s
    send("rejoin", {"roomCode": _room_code, "playerId": _player_id})

func send_input(up: bool, down: bool, left: bool, right: bool):
    send("player_input", {"up": up, "down": down, "left": left, "right": right})

func _open_mini_game(payload):
    # payload.miniGameId picks the renderer; payload.view is plugin-specific
    pass
```

Volle Godot-Integration kommt mit Tier 4 der Roadmap. Bis dahin ist der Browser-Client (`static/`) die Referenz-Implementierung jedes Frame-Typs.
