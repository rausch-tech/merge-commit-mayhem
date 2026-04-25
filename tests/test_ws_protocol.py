import pytest
from fastapi.testclient import TestClient

from app.main import app, registry


@pytest.fixture(autouse=True)
def _reset_registry():
    yield
    registry._rooms.clear()


def _join(client_ws, room_code: str, name: str) -> dict:
    client_ws.send_json(
        {"type": "join_room", "payload": {"roomCode": room_code, "playerName": name}}
    )
    return client_ws.receive_json()  # room_joined


def _drain_until(ws, type_: str, max_msgs: int = 10) -> dict:
    """Receive messages until one with `type` arrives, or fail."""
    for _ in range(max_msgs):
        msg = ws.receive_json()
        if msg["type"] == type_:
            return msg
    raise AssertionError(f"Did not receive {type_!r} within {max_msgs} messages.")


def test_two_clients_can_join_same_room():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        joined_a = _join(ws_a, "ABCD", "Alice")
        assert joined_a["type"] == "room_joined"
        assert joined_a["payload"]["isHost"] is True

        # Alice receives lobby_state after joining.
        lobby_a1 = ws_a.receive_json()
        assert lobby_a1["type"] == "lobby_state"
        assert len(lobby_a1["payload"]["players"]) == 1

        joined_b = _join(ws_b, "ABCD", "Bob")
        assert joined_b["type"] == "room_joined"
        assert joined_b["payload"]["isHost"] is False

        # Both receive an updated lobby_state.
        lobby_a2 = ws_a.receive_json()
        lobby_b1 = ws_b.receive_json()
        assert lobby_a2["type"] == "lobby_state"
        assert lobby_b1["type"] == "lobby_state"
        assert len(lobby_a2["payload"]["players"]) == 2


def test_non_host_cannot_start_game():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "EFGH", "Alice")
        ws_a.receive_json()  # lobby
        _join(ws_b, "EFGH", "Bob")
        ws_a.receive_json()  # lobby update (2 players)
        ws_b.receive_json()  # lobby update

        ws_b.send_json({"type": "start_game", "payload": {}})
        err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_HOST"


def test_host_start_gives_private_role_and_game_state():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "JKLM", "Alice")
        ws_a.receive_json()
        _join(ws_b, "JKLM", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})

        # Contract: private_role MUST arrive before game_state on each client.
        role_a = ws_a.receive_json()
        assert role_a["type"] == "private_role"
        state_a = ws_a.receive_json()
        assert state_a["type"] == "game_state"
        role_b = ws_b.receive_json()
        assert role_b["type"] == "private_role"
        state_b = ws_b.receive_json()
        assert state_b["type"] == "game_state"

        assert role_a["payload"]["role"] in {"vibe_coder", "developer"}
        assert role_b["payload"]["role"] in {"vibe_coder", "developer"}
        # Exactly one is chaos, one is dev.
        roles = {role_a["payload"]["role"], role_b["payload"]["role"]}
        assert roles == {"vibe_coder", "developer"}

        assert state_a["payload"]["phase"] == "playing"
        # Public state must not leak roles.
        for p in state_a["payload"]["players"]:
            assert "role" not in p
            assert "team" not in p


def test_start_fails_with_only_one_player():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a:
        _join(ws_a, "NOPQ", "Alice")
        ws_a.receive_json()  # lobby

        ws_a.send_json({"type": "start_game", "payload": {}})
        err = ws_a.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_ENOUGH_PLAYERS"


def test_duplicate_name_rejected():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "RSTU", "Sven")
        ws_a.receive_json()

        ws_b.send_json({"type": "join_room", "payload": {"roomCode": "RSTU", "playerName": "Sven"}})
        err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NAME_TAKEN"


def test_disconnect_removes_player_and_promotes_host():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a:
        _join(ws_a, "VWXY", "Alice")
        ws_a.receive_json()

        # Second client joins inside nested with, then leaves.
        with client.websocket_connect("/ws") as ws_b:
            _join(ws_b, "VWXY", "Bob")
            ws_a.receive_json()  # lobby update after Bob joined
            ws_b.receive_json()
        # After ws_b closes, Alice should see a lobby update without Bob.
        lobby = ws_a.receive_json()
        assert lobby["type"] == "lobby_state"
        names = [p["name"] for p in lobby["payload"]["players"]]
        assert names == ["Alice"]


def test_websocket_on_non_exact_path_does_not_crash_server():
    """
    Regression test: a WebSocket to any path other than /ws must not
    crash the server (previously, it fell through to the static mount
    and raised AssertionError).
    """
    client = TestClient(app)
    # Trailing slash was the original repro.
    with pytest.raises(Exception), client.websocket_connect("/ws/"):  # noqa: B017 — TestClient raises generic Exception on rejected upgrade
        pass
    # Server must still be usable for a legit connection after that.
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "join_room", "payload": {"roomCode": "ZZZZ", "playerName": "Zoe"}})
        first = ws.receive_json()
        assert first["type"] == "room_joined"


# --- B8 additions: game-loop integration tests -------------------------


def test_task_hold_too_far_returns_error():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "TASK", "Alice")
        ws_a.receive_json()  # lobby
        _join(ws_b, "TASK", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        _drain_until(ws_a, "private_role")
        _drain_until(ws_a, "game_state")
        _drain_until(ws_b, "private_role")
        _drain_until(ws_b, "game_state")

        # Alice is somewhere in the Open Space area (start positions). Try to start
        # a task in the Kitchen (refill_coffee) from there — must be too far.
        ws_a.send_json({"type": "task_hold_start", "payload": {"taskId": "refill_coffee"}})
        err = ws_a.receive_json()
        # Could be an error or a subsequent game_state — drain until error.
        while err["type"] == "game_state":
            err = ws_a.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "TASK_TOO_FAR"


def test_non_chaos_cannot_trigger_sabotage():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "SABO", "Alice")
        ws_a.receive_json()
        _join(ws_b, "SABO", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        role_a = _drain_until(ws_a, "private_role")
        _drain_until(ws_a, "game_state")
        _drain_until(ws_b, "private_role")
        _drain_until(ws_b, "game_state")

        non_chaos_ws = ws_a if role_a["payload"]["team"] != "chaos_agents" else ws_b
        non_chaos_ws.send_json({"type": "trigger_sabotage", "payload": {"sabotageId": "ci_cd_red"}})
        err = non_chaos_ws.receive_json()
        while err["type"] == "game_state":
            err = non_chaos_ws.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_CHAOS_AGENT"


def test_chaos_sees_available_sabotages_in_private_role():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "AVAIL", "Alice")
        ws_a.receive_json()
        _join(ws_b, "AVAIL", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        role_a = _drain_until(ws_a, "private_role")
        role_b = _drain_until(ws_b, "private_role")

        for role in [role_a, role_b]:
            if role["payload"]["team"] == "chaos_agents":
                assert role["payload"]["availableSabotages"] == [
                    "ci_cd_red",
                    "coffee_outage",
                    "mandatory_meeting",
                ]
            else:
                assert role["payload"]["availableSabotages"] == []


def test_game_state_carries_stats_and_tasks_and_sabotages():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "STAT", "Alice")
        ws_a.receive_json()
        _join(ws_b, "STAT", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        _drain_until(ws_a, "private_role")
        state = _drain_until(ws_a, "game_state")
        p = state["payload"]
        assert p["releaseProgress"] == 0
        assert p["pipelineStability"] == 100
        assert p["coffeeLevel"] == 100
        assert p["incidentCount"] == 0
        task_ids = {t["id"] for t in p["tasks"]}
        assert "fix_unit_tests" in task_ids
        sab_ids = {s["id"] for s in p["sabotages"]}
        assert sab_ids == {"ci_cd_red", "coffee_outage", "mandatory_meeting"}


def test_game_ended_broadcast_on_release_win():
    """Drive release_progress to 100 directly via the server-side room and verify
    a game_ended message goes out to both clients."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
    ):
        _join(ws_a, "ENDR", "Alice")
        ws_a.receive_json()
        _join(ws_b, "ENDR", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        _drain_until(ws_a, "private_role")
        _drain_until(ws_a, "game_state")
        _drain_until(ws_b, "private_role")
        _drain_until(ws_b, "game_state")

        # Server-side: force release_progress to 100 so the next tick ends the round.
        room = registry.get("ENDR")
        assert room is not None
        room.release_progress = 100

        ended_a = _drain_until(ws_a, "game_ended", max_msgs=50)
        ended_b = _drain_until(ws_b, "game_ended", max_msgs=50)
        assert ended_a["payload"]["winner"] == "release_team"
        assert ended_a["payload"]["reason"] == "Release deployed."
        # Roles revealed in the endscreen payload.
        for p in ended_a["payload"]["players"]:
            assert p["role"] in {"developer", "vibe_coder"}
            assert p["team"] in {"release_team", "chaos_agents"}
        # Second client sees the same winner.
        assert ended_b["payload"]["winner"] == "release_team"


def test_return_to_lobby_requires_host_and_ended_phase():
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
    ):
        _join(ws_a, "RESET", "Alice")
        ws_a.receive_json()
        _join(ws_b, "RESET", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        # Before start → wrong phase
        ws_a.send_json({"type": "return_to_lobby", "payload": {}})
        err = ws_a.receive_json()
        while err["type"] == "game_state":
            err = ws_a.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "WRONG_PHASE"

        # Start round
        ws_a.send_json({"type": "start_game", "payload": {}})
        _drain_until(ws_a, "private_role")
        _drain_until(ws_a, "game_state")
        _drain_until(ws_b, "private_role")
        _drain_until(ws_b, "game_state")

        # End the round
        registry.get("RESET").release_progress = 100
        _drain_until(ws_a, "game_ended", max_msgs=50)
        _drain_until(ws_b, "game_ended", max_msgs=50)

        # Non-host tries to reset
        ws_b.send_json({"type": "return_to_lobby", "payload": {}})
        err = ws_b.receive_json()
        while err["type"] in {"game_state"}:
            err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_HOST"

        # Host resets → both get lobby_state
        ws_a.send_json({"type": "return_to_lobby", "payload": {}})
        lob_a = _drain_until(ws_a, "lobby_state")
        lob_b = _drain_until(ws_b, "lobby_state")
        assert len(lob_a["payload"]["players"]) == 2
        assert len(lob_b["payload"]["players"]) == 2


# --- Demo mode (WS) ------------------------------------------------------


def test_demo_mode_lets_single_player_start_via_ws():
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        _join(ws, "DEMO", "Solo")
        ws.receive_json()  # lobby_state
        ws.send_json({"type": "start_game", "payload": {"demo": True}})
        role = _drain_until(ws, "private_role")
        assert role["payload"]["role"] == "vibe_coder"
        assert role["payload"]["team"] == "chaos_agents"
        assert role["payload"]["availableSabotages"] == [
            "ci_cd_red",
            "coffee_outage",
            "mandatory_meeting",
        ]
        state = _drain_until(ws, "game_state")
        assert state["payload"]["phase"] == "playing"


def test_non_demo_single_player_still_rejected():
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        _join(ws, "DEMO", "Solo")
        ws.receive_json()  # lobby_state
        ws.send_json({"type": "start_game", "payload": {}})
        err = ws.receive_json()
        # Skip any interleaved game_state (defensive — there shouldn't be any here)
        while err["type"] == "game_state":
            err = ws.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_ENOUGH_PLAYERS"


# --- VB additions: voting + emergency meeting integration tests -------------


def test_call_emergency_meeting_outside_war_room_returns_error():
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
    ):
        _join(ws_a, "MEET", "Alice")
        ws_a.receive_json()  # lobby
        _join(ws_b, "MEET", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        _drain_until(ws_a, "private_role")
        _drain_until(ws_a, "game_state")
        _drain_until(ws_b, "private_role")
        _drain_until(ws_b, "game_state")

        ws_a.send_json({"type": "call_emergency_meeting", "payload": {}})
        # Skip interleaved game_state messages while waiting for the error.
        msg = ws_a.receive_json()
        while msg["type"] == "game_state":
            msg = ws_a.receive_json()
        assert msg["type"] == "error"
        assert msg["payload"]["code"] == "NOT_IN_WAR_ROOM"


def test_call_meeting_from_war_room_transitions_to_meeting_phase():
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
    ):
        _join(ws_a, "MEET2", "Alice")
        ws_a.receive_json()
        _join(ws_b, "MEET2", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        _drain_until(ws_a, "private_role")
        _drain_until(ws_a, "game_state")
        _drain_until(ws_b, "private_role")
        _drain_until(ws_b, "game_state")

        # Server-side: place Alice in the war room.
        room = registry.get("MEET2")
        assert room is not None
        alice_id = next(p.id for p in room.players.values() if p.name == "Alice")
        room.players[alice_id].x = 1000.0
        room.players[alice_id].y = 1000.0

        ws_a.send_json({"type": "call_emergency_meeting", "payload": {}})

        # Drain game_state until phase is "meeting".
        for _ in range(60):
            msg = ws_a.receive_json()
            if msg["type"] == "game_state" and msg["payload"]["phase"] == "meeting":
                assert msg["payload"]["meeting"]["callerId"] == alice_id
                break
        else:
            raise AssertionError("Did not receive meeting-phase game_state")


def test_full_voting_round_eliminates_named_target():
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
        client.websocket_connect("/ws") as ws_c,
    ):
        _join(ws_a, "VOTEFL", "Alice")
        ws_a.receive_json()
        _join(ws_b, "VOTEFL", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()
        _join(ws_c, "VOTEFL", "Carol")
        ws_a.receive_json()
        ws_b.receive_json()
        ws_c.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b, ws_c]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

        room = registry.get("VOTEFL")
        alice_id = next(p.id for p in room.players.values() if p.name == "Alice")
        _bob_id = next(p.id for p in room.players.values() if p.name == "Bob")
        carol_id = next(p.id for p in room.players.values() if p.name == "Carol")
        room.players[alice_id].x = 1000.0
        room.players[alice_id].y = 1000.0

        ws_a.send_json({"type": "call_emergency_meeting", "payload": {}})

        # Wait for meeting phase to be observed by Alice.
        for _ in range(60):
            msg = ws_a.receive_json()
            if msg["type"] == "game_state" and msg["payload"]["phase"] == "meeting":
                break

        # Cast votes: Alice + Bob vote Carol; Carol skips.
        ws_a.send_json({"type": "cast_vote", "payload": {"targetPlayerId": carol_id}})
        ws_b.send_json({"type": "cast_vote", "payload": {"targetPlayerId": carol_id}})
        ws_c.send_json({"type": "skip_vote", "payload": {}})

        # Wait for the voting_result broadcast on any of the three sockets.
        result = _drain_until(ws_a, "voting_result", max_msgs=120)
        assert result["payload"]["removedPlayerId"] == carol_id
        assert result["payload"]["removedPlayerName"] == "Carol"
        assert result["payload"]["tie"] is False
        assert result["payload"]["skipped"] is False
        # Phase should be back to playing afterward.
        for _ in range(20):
            msg = ws_a.receive_json()
            if msg["type"] == "game_state" and msg["payload"]["phase"] == "playing":
                # Carol should be marked dead in the player list.
                carol_in_state = next(p for p in msg["payload"]["players"] if p["id"] == carol_id)
                assert carol_in_state["isAlive"] is False
                break
        else:
            raise AssertionError("Phase did not return to playing")


def test_meeting_resolves_with_skip_when_only_skips_received():
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
    ):
        _join(ws_a, "VOTSK", "Alice")
        ws_a.receive_json()
        _join(ws_b, "VOTSK", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

        room = registry.get("VOTSK")
        alice_id = next(p.id for p in room.players.values() if p.name == "Alice")
        room.players[alice_id].x = 1000.0
        room.players[alice_id].y = 1000.0
        ws_a.send_json({"type": "call_emergency_meeting", "payload": {}})

        for _ in range(60):
            msg = ws_a.receive_json()
            if msg["type"] == "game_state" and msg["payload"]["phase"] == "meeting":
                break

        ws_a.send_json({"type": "skip_vote", "payload": {}})
        ws_b.send_json({"type": "skip_vote", "payload": {}})

        result = _drain_until(ws_a, "voting_result", max_msgs=120)
        assert result["payload"]["removedPlayerId"] == ""
        assert result["payload"]["skipped"] is True
        assert result["payload"]["tie"] is False
