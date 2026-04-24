# 03 – WebSocket Protocol Draft

## Ziel

Das WebSocket-Protokoll soll einfach, JSON-basiert und client-agnostisch sein. Es muss sowohl vom Browser-Client als auch später von Godot genutzt werden können.

---

# 1. Grundformat

## Client -> Server

```json
{
  "type": "event_name",
  "payload": {}
}
```

## Server -> Client

```json
{
  "type": "event_name",
  "payload": {}
}
```

---

# 2. Verbindungs- und Lobby-Events

## join_room

Client -> Server

```json
{
  "type": "join_room",
  "payload": {
    "roomCode": "ABCD",
    "playerName": "Sven"
  }
}
```

## room_joined

Server -> Client

```json
{
  "type": "room_joined",
  "payload": {
    "roomCode": "ABCD",
    "playerId": "player_123",
    "isHost": true
  }
}
```

## lobby_state

Server -> Client

```json
{
  "type": "lobby_state",
  "payload": {
    "roomCode": "ABCD",
    "players": [
      {
        "id": "player_123",
        "name": "Sven",
        "color": "green",
        "isHost": true
      }
    ]
  }
}
```

## start_game

Client -> Server

```json
{
  "type": "start_game",
  "payload": {}
}
```

---

# 3. Private Rolleninformation

Server -> Client

```json
{
  "type": "private_role",
  "payload": {
    "role": "vibe_coder",
    "team": "chaos_agents",
    "description": "Du bist der Vibe Coder. Sabotiere das Release, ohne entdeckt zu werden."
  }
}
```

Diese Nachricht geht nur an den jeweiligen Spieler.

---

# 4. Input Events

## player_input

Client -> Server

```json
{
  "type": "player_input",
  "payload": {
    "up": true,
    "down": false,
    "left": false,
    "right": true
  }
}
```

## start_task

Client -> Server

```json
{
  "type": "start_task",
  "payload": {
    "taskId": "fix_unit_tests"
  }
}
```

## cancel_task

Client -> Server

```json
{
  "type": "cancel_task",
  "payload": {
    "taskId": "fix_unit_tests"
  }
}
```

## trigger_sabotage

Client -> Server

```json
{
  "type": "trigger_sabotage",
  "payload": {
    "sabotageId": "coffee_outage"
  }
}
```

---

# 5. Meeting und Voting

## call_emergency_meeting

Client -> Server

```json
{
  "type": "call_emergency_meeting",
  "payload": {}
}
```

## cast_vote

Client -> Server

```json
{
  "type": "cast_vote",
  "payload": {
    "targetPlayerId": "player_456"
  }
}
```

## skip_vote

Client -> Server

```json
{
  "type": "skip_vote",
  "payload": {}
}
```

## meeting_state

Server -> Client

```json
{
  "type": "meeting_state",
  "payload": {
    "title": "Wer hat auf main gepusht?",
    "remainingSeconds": 58,
    "players": [
      {
        "id": "player_123",
        "name": "Sven",
        "isAlive": true
      }
    ],
    "votesCast": 2
  }
}
```

## voting_result

Server -> Client

```json
{
  "type": "voting_result",
  "payload": {
    "removedPlayerId": "player_456",
    "removedPlayerName": "Max",
    "wasChaosAgent": false,
    "tie": false,
    "skipped": false
  }
}
```

---

# 6. Game State Broadcast

Server -> Client

```json
{
  "type": "game_state",
  "payload": {
    "phase": "playing",
    "releaseProgress": 42,
    "pipelineStability": 70,
    "coffeeLevel": 100,
    "incidentCount": 1,
    "remainingSeconds": 428,
    "players": [
      {
        "id": "player_123",
        "name": "CommitNinja",
        "x": 120,
        "y": 200,
        "color": "green",
        "isAlive": true
      }
    ],
    "tasks": [
      {
        "id": "fix_unit_tests",
        "title": "Unit Tests fixen",
        "room": "open_space",
        "progress": 0.6,
        "isCompleted": false
      }
    ],
    "events": [
      {
        "timestamp": "07:16",
        "severity": "danger",
        "message": "BUILD FAILED – Unit tests are angry"
      }
    ]
  }
}
```

---

# 7. Endscreen

Server -> Client

```json
{
  "type": "game_ended",
  "payload": {
    "winner": "release_team",
    "reason": "Release Progress reached 100%",
    "players": [
      {
        "id": "player_123",
        "name": "CommitNinja",
        "role": "developer",
        "team": "release_team",
        "completedTasks": 5,
        "triggeredSabotages": 0
      }
    ],
    "awards": [
      {
        "playerId": "player_123",
        "title": "Pipeline Whisperer"
      }
    ]
  }
}
```

---

# 8. Error Event

Server -> Client

```json
{
  "type": "error",
  "payload": {
    "code": "NOT_ALLOWED",
    "message": "Only chaos agents can trigger this sabotage."
  }
}
```

---

# 9. Protokollregeln

- Alle Nachrichten haben `type` und `payload`.
- Der Server validiert alle eingehenden Nachrichten.
- Private Informationen werden nie im öffentlichen GameState gesendet.
- Rolleninformationen werden separat und nur privat gesendet.
- Der öffentliche GameState enthält keine geheimen Rollen.
- Clients müssen jederzeit mit einem vollständigen `game_state` resynchronisieren können.
- Godot und Browser müssen dasselbe Protokoll nutzen können.

