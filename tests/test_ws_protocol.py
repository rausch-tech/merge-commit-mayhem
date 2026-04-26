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


def _pad_room_to_min(room_code: str, min_players: int = 4) -> list[str]:
    """Pad a room with server-side dummy players up to `min_players`.

    Tier 1.5 raised MIN_PLAYERS_TO_START to 4. Many existing WS tests join only
    2 real WebSocket clients; this helper backfills the remaining slots by
    poking the registry directly. The dummies have no socket — they sit in the
    room as if connected. Tests that don't observe these slots are unaffected.

    Returns the list of filler player ids in join order, so meeting/voting
    tests can pre-cast skip votes on their behalf.
    """
    room = registry.get(room_code)
    assert room is not None, f"Room {room_code!r} not registered yet."
    filler_ids: list[str] = []
    while len(room.players) < min_players:
        idx = len(room.players)
        p = room.add_player(f"_filler_{idx}")
        filler_ids.append(p.id)
    return filler_ids


def _skip_vote_for_fillers(room_code: str, filler_ids: list[str]) -> None:
    """Cast a server-side skip vote for each filler player.

    Only the test client's votes get cast through the WS protocol. To let a
    meeting resolve immediately when all alive players have voted, dummies
    must skip too. Safe to call only after MEETING phase has been entered.
    """
    room = registry.get(room_code)
    assert room is not None
    for fid in filler_ids:
        if fid in room.players and room.players[fid].is_alive:
            room.skip_vote(fid)


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

        _pad_room_to_min("JKLM")
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
        # With 4 players (2 real + 2 fillers) we have exactly 1 chaos. Each
        # role observed by the real clients is one of the legal values; we
        # don't assert their disjointness because both real clients could be
        # release_team.
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

        _pad_room_to_min("TASK")
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

        _pad_room_to_min("SABO")
        ws_a.send_json({"type": "start_game", "payload": {}})
        # With 2 real clients + 2 fillers the chaos may end up on a filler;
        # find a real client whose team is not chaos and try the sabotage.
        role_a = _drain_until(ws_a, "private_role")
        _drain_until(ws_a, "game_state")
        role_b = _drain_until(ws_b, "private_role")
        _drain_until(ws_b, "game_state")

        non_chaos_ws = None
        if role_a["payload"]["team"] != "chaos_agents":
            non_chaos_ws = ws_a
        elif role_b["payload"]["team"] != "chaos_agents":
            non_chaos_ws = ws_b
        assert non_chaos_ws is not None, "Expected at least one real client to be non-chaos."
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

        _pad_room_to_min("AVAIL")
        ws_a.send_json({"type": "start_game", "payload": {}})
        role_a = _drain_until(ws_a, "private_role")
        role_b = _drain_until(ws_b, "private_role")

        for role in [role_a, role_b]:
            if role["payload"]["team"] == "chaos_agents":
                assert role["payload"]["availableSabotages"] == [
                    "ci_cd_red",
                    "coffee_outage",
                    "mandatory_meeting",
                    "merge_conflict_storm",
                    "fake_customer_request",
                    "flaky_tests",
                    "lights_out",
                    "comms_outage",
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

        _pad_room_to_min("STAT")
        ws_a.send_json({"type": "start_game", "payload": {}})
        _drain_until(ws_a, "private_role")
        state = _drain_until(ws_a, "game_state")
        p = state["payload"]
        assert p["releaseProgress"] == 0
        assert p["pipelineStability"] == 100
        assert p["coffeeLevel"] == 100
        task_ids = {t["id"] for t in p["tasks"]}
        assert "fix_unit_tests" in task_ids
        sab_ids = {s["id"] for s in p["sabotages"]}
        assert sab_ids == {
            "ci_cd_red",
            "coffee_outage",
            "mandatory_meeting",
            "merge_conflict_storm",
            "fake_customer_request",
            "flaky_tests",
            "lights_out",
            "comms_outage",
        }


def test_game_ended_broadcast_on_release_win():
    """Drive release_progress to 100 directly via the server-side room and verify
    a game_ended message goes out to all clients.

    Uses 3 players so the Tier 2.1 chaos-parity rule (chaos_alive >= release_alive)
    does not fire before release_progress reaches 100.
    """
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
        client.websocket_connect("/ws") as ws_c,
    ):
        _join(ws_a, "ENDR", "Alice")
        ws_a.receive_json()
        _join(ws_b, "ENDR", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()
        _join(ws_c, "ENDR", "Carol")
        ws_a.receive_json()
        ws_b.receive_json()
        ws_c.receive_json()

        _pad_room_to_min("ENDR")
        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b, ws_c]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

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
    """Uses 3 players so chaos parity (Tier 2.1) doesn't end the round on the
    first tick before we drive release_progress to 100."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
        client.websocket_connect("/ws") as ws_c,
    ):
        _join(ws_a, "RESET", "Alice")
        ws_a.receive_json()
        _join(ws_b, "RESET", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()
        _join(ws_c, "RESET", "Carol")
        ws_a.receive_json()
        ws_b.receive_json()
        ws_c.receive_json()

        # Before start → wrong phase
        ws_a.send_json({"type": "return_to_lobby", "payload": {}})
        err = ws_a.receive_json()
        while err["type"] == "game_state":
            err = ws_a.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "WRONG_PHASE"

        # Start round
        _pad_room_to_min("RESET")
        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b, ws_c]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

        # End the round
        registry.get("RESET").release_progress = 100
        _drain_until(ws_a, "game_ended", max_msgs=50)
        _drain_until(ws_b, "game_ended", max_msgs=50)
        _drain_until(ws_c, "game_ended", max_msgs=50)

        # Non-host tries to reset
        ws_b.send_json({"type": "return_to_lobby", "payload": {}})
        err = ws_b.receive_json()
        while err["type"] in {"game_state"}:
            err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_HOST"

        # Host resets → all get lobby_state
        ws_a.send_json({"type": "return_to_lobby", "payload": {}})
        lob_a = _drain_until(ws_a, "lobby_state")
        lob_b = _drain_until(ws_b, "lobby_state")
        lob_c = _drain_until(ws_c, "lobby_state")
        # 3 real WS clients + 1 server-side filler (Tier 1.5 min-players pad)
        # = 4 players in lobby. Real clients always see all of them.
        assert len(lob_a["payload"]["players"]) == 4
        assert len(lob_b["payload"]["players"]) == 4
        assert len(lob_c["payload"]["players"]) == 4


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
            "merge_conflict_storm",
            "fake_customer_request",
            "flaky_tests",
            "lights_out",
            "comms_outage",
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
    """Uses 3 players so the Tier 2.1 chaos-parity rule does not end the round
    before we get to call the meeting."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
        client.websocket_connect("/ws") as ws_c,
    ):
        _join(ws_a, "MEET", "Alice")
        ws_a.receive_json()  # lobby
        _join(ws_b, "MEET", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()
        _join(ws_c, "MEET", "Carol")
        ws_a.receive_json()
        ws_b.receive_json()
        ws_c.receive_json()

        _pad_room_to_min("MEET")
        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b, ws_c]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

        ws_a.send_json({"type": "call_emergency_meeting", "payload": {}})
        # Skip interleaved game_state messages while waiting for the error.
        msg = ws_a.receive_json()
        while msg["type"] == "game_state":
            msg = ws_a.receive_json()
        assert msg["type"] == "error"
        assert msg["payload"]["code"] == "NOT_IN_WAR_ROOM"


def test_call_meeting_from_war_room_transitions_to_meeting_phase():
    """Uses 3 players so chaos parity (Tier 2.1) doesn't end the round before
    Alice can call the meeting."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
        client.websocket_connect("/ws") as ws_c,
    ):
        _join(ws_a, "MEET2", "Alice")
        ws_a.receive_json()
        _join(ws_b, "MEET2", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()
        _join(ws_c, "MEET2", "Carol")
        ws_a.receive_json()
        ws_b.receive_json()
        ws_c.receive_json()

        _pad_room_to_min("MEET2")
        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b, ws_c]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

        # Server-side: place Alice in the war room.
        room = registry.get("MEET2")
        assert room is not None
        alice_id = next(p.id for p in room.players.values() if p.name == "Alice")
        room.players[alice_id].x = 2000.0
        room.players[alice_id].y = 2000.0

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
    """Uses 4 players so post-elimination state still keeps release in the
    majority. After voting Carol out, 3 players remain: Alice, Bob, Dave —
    the Tier 2.1 chaos-parity rule (chaos_alive >= release_alive) doesn't
    fire because at most 1 of the 3 is chaos.
    """
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
        client.websocket_connect("/ws") as ws_c,
        client.websocket_connect("/ws") as ws_d,
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
        _join(ws_d, "VOTEFL", "Dave")
        ws_a.receive_json()
        ws_b.receive_json()
        ws_c.receive_json()
        ws_d.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b, ws_c, ws_d]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

        room = registry.get("VOTEFL")
        alice_id = next(p.id for p in room.players.values() if p.name == "Alice")
        _bob_id = next(p.id for p in room.players.values() if p.name == "Bob")
        carol_id = next(p.id for p in room.players.values() if p.name == "Carol")
        # Force Carol to be release_team so eliminating her does NOT trigger
        # the all-chaos-eliminated win, and 3 release survive (vs at most 1
        # chaos), keeping the round in PLAYING phase post-vote.
        room.players[carol_id].role = "developer"
        room.players[carol_id].team = "release_team"
        # Make sure exactly one of the others is chaos (the rest are release).
        chaos_now = next(
            (p for p in room.players.values() if p.id != carol_id and p.team == "chaos_agents"),
            None,
        )
        if chaos_now is None:
            # No chaos among the others — promote Bob as chaos.
            room.players[_bob_id].role = "vibe_coder"
            room.players[_bob_id].team = "chaos_agents"
            # And demote any other chaos player to release.
            for p in room.players.values():
                if p.id != _bob_id and p.team == "chaos_agents":
                    p.role = "developer"
                    p.team = "release_team"
        room.players[alice_id].x = 2000.0
        room.players[alice_id].y = 2000.0

        ws_a.send_json({"type": "call_emergency_meeting", "payload": {}})

        # Wait for meeting phase to be observed by Alice.
        for _ in range(60):
            msg = ws_a.receive_json()
            if msg["type"] == "game_state" and msg["payload"]["phase"] == "meeting":
                break

        # Cast votes: Alice + Bob + Dave vote Carol; Carol skips.
        ws_a.send_json({"type": "cast_vote", "payload": {"targetPlayerId": carol_id}})
        ws_b.send_json({"type": "cast_vote", "payload": {"targetPlayerId": carol_id}})
        ws_d.send_json({"type": "cast_vote", "payload": {"targetPlayerId": carol_id}})
        ws_c.send_json({"type": "skip_vote", "payload": {}})

        # Wait for the voting_result broadcast on any of the four sockets.
        result = _drain_until(ws_a, "voting_result", max_msgs=120)
        assert result["payload"]["removedPlayerId"] == carol_id
        assert result["payload"]["removedPlayerName"] == "Carol"
        assert result["payload"]["tie"] is False
        assert result["payload"]["skipped"] is False
        # Phase should be back to playing afterward. Spectator-Mode (Tier 2.6):
        # alive viewers no longer see ghosts in their player list, so we look
        # at Carol's own socket (ws_c, dead viewer) which always includes herself.
        for _ in range(20):
            msg = ws_c.receive_json()
            if msg["type"] == "game_state" and msg["payload"]["phase"] == "playing":
                carol_in_state = next(p for p in msg["payload"]["players"] if p["id"] == carol_id)
                assert carol_in_state["isAlive"] is False
                break
        else:
            raise AssertionError("Phase did not return to playing")
        # And from Alice's (alive) point of view, Carol must be hidden.
        for _ in range(20):
            msg = ws_a.receive_json()
            if msg["type"] == "game_state" and msg["payload"]["phase"] == "playing":
                ids_seen = {p["id"] for p in msg["payload"]["players"]}
                assert carol_id not in ids_seen
                break
        else:
            raise AssertionError("Alice did not receive a playing-phase game_state")


# --- Reconnect integration tests ---


def test_rejoin_after_disconnect_during_playing():
    """A disconnected player can rejoin within the grace period and resume."""
    with TestClient(app) as client:
        # Both players join + start the round.
        with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
            _join(ws_a, "RECONN", "Alice")
            ws_a.receive_json()  # lobby
            _join(ws_b, "RECONN", "Bob")
            ws_a.receive_json()
            ws_b.receive_json()
            _pad_room_to_min("RECONN")
            ws_a.send_json({"type": "start_game", "payload": {}})
            _drain_until(ws_a, "private_role")
            _drain_until(ws_a, "game_state")
            _drain_until(ws_b, "private_role")
            _drain_until(ws_b, "game_state")
            room = registry.get("RECONN")
            bob_id = next(p.id for p in room.players.values() if p.name == "Bob")

        # Both connections closed. Bob is mid-round → should still be in room.
        import time

        time.sleep(0.2)
        assert bob_id in room.players
        assert room.players[bob_id].is_connected is False

        # Bob reconnects with his playerId.
        with client.websocket_connect("/ws") as ws_b2:
            ws_b2.send_json(
                {"type": "rejoin", "payload": {"roomCode": "RECONN", "playerId": bob_id}}
            )
            joined = ws_b2.receive_json()
            assert joined["type"] == "room_joined"
            assert joined["payload"]["playerId"] == bob_id
            role = ws_b2.receive_json()
            assert role["type"] == "private_role"
            state = ws_b2.receive_json()
            assert state["type"] == "game_state"
            # And the player flag is back.
            bob_in_state = next(p for p in state["payload"]["players"] if p["id"] == bob_id)
            assert bob_in_state["isConnected"] is True


def test_rejoin_with_unknown_player_id_returns_error():
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "rejoin", "payload": {"roomCode": "NONE", "playerId": "fake"}})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "REJOIN_NOT_AVAILABLE"


def test_meeting_resolves_with_skip_when_only_skips_received():
    """Uses 3 players so the Tier 2.1 chaos-parity rule does not fire while we
    drive the meeting to a skip resolution."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
        client.websocket_connect("/ws") as ws_c,
    ):
        _join(ws_a, "VOTSK", "Alice")
        ws_a.receive_json()
        _join(ws_b, "VOTSK", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()
        _join(ws_c, "VOTSK", "Carol")
        ws_a.receive_json()
        ws_b.receive_json()
        ws_c.receive_json()

        filler_ids = _pad_room_to_min("VOTSK")
        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b, ws_c]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

        room = registry.get("VOTSK")
        alice_id = next(p.id for p in room.players.values() if p.name == "Alice")
        room.players[alice_id].x = 2000.0
        room.players[alice_id].y = 2000.0
        ws_a.send_json({"type": "call_emergency_meeting", "payload": {}})

        for _ in range(60):
            msg = ws_a.receive_json()
            if msg["type"] == "game_state" and msg["payload"]["phase"] == "meeting":
                break

        ws_a.send_json({"type": "skip_vote", "payload": {}})
        ws_b.send_json({"type": "skip_vote", "payload": {}})
        ws_c.send_json({"type": "skip_vote", "payload": {}})
        _skip_vote_for_fillers("VOTSK", filler_ids)

        result = _drain_until(ws_a, "voting_result", max_msgs=120)
        assert result["payload"]["removedPlayerId"] == ""
        assert result["payload"]["skipped"] is True
        assert result["payload"]["tie"] is False


# --- Multi-map (Tier 1.8) ----------------------------------------------------


def test_lobby_state_includes_available_maps_and_selected_map_id():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a:
        joined = _join(ws_a, "MAPLOB", "Alice")
        assert joined["type"] == "room_joined"
        # Initial lobby_state right after the join.
        lobby = ws_a.receive_json()
        assert lobby["type"] == "lobby_state"
        payload = lobby["payload"]
        assert payload["selectedMapId"] == "default"
        ids = {m["id"] for m in payload["availableMaps"]}
        assert "default" in ids
        # Each entry has both id and name.
        for m in payload["availableMaps"]:
            assert "id" in m and "name" in m


def test_host_select_map_broadcasts_new_selected_map_id():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "MAPSEL", "Alice")
        ws_a.receive_json()  # lobby
        _join(ws_b, "MAPSEL", "Bob")
        ws_a.receive_json()  # lobby update (2 players)
        ws_b.receive_json()  # lobby update

        # Host switches map.
        ws_a.send_json({"type": "select_map", "payload": {"mapId": "small"}})

        lobby_a = _drain_until(ws_a, "lobby_state")
        lobby_b = _drain_until(ws_b, "lobby_state")
        assert lobby_a["payload"]["selectedMapId"] == "small"
        assert lobby_b["payload"]["selectedMapId"] == "small"

        # A fresh joiner now receives the small map in their room_joined.
        with client.websocket_connect("/ws") as ws_c:
            joined = _join(ws_c, "MAPSEL", "Carol")
            assert joined["type"] == "room_joined"
            assert joined["payload"]["map"]["name"] == "small-arena"


def test_non_host_select_map_returns_not_host_error():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "MAPNH", "Alice")
        ws_a.receive_json()  # lobby
        _join(ws_b, "MAPNH", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_b.send_json({"type": "select_map", "payload": {"mapId": "small"}})
        msg = ws_b.receive_json()
        # Drain past any extra lobby_state if interleaved.
        while msg["type"] != "error":
            msg = ws_b.receive_json()
        assert msg["payload"]["code"] == "NOT_HOST"


# --- Tier 1.9: in-game menu — leave_room / abort_round -----------------


def test_leave_room_in_lobby_removes_player_and_broadcasts():
    """Any player can leave from the lobby; remaining players see updated list."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
    ):
        _join(ws_a, "LEAV", "Alice")
        ws_a.receive_json()  # initial lobby_state
        _join(ws_b, "LEAV", "Bob")
        ws_a.receive_json()  # lobby_state after Bob joined
        ws_b.receive_json()  # lobby_state for Bob

        ws_b.send_json({"type": "leave_room", "payload": {}})
        lob = _drain_until(ws_a, "lobby_state")
        names = {p["name"] for p in lob["payload"]["players"]}
        assert names == {"Alice"}
        # Room still exists with Alice as host.
        assert registry.get("LEAV") is not None
        assert any(p.is_host for p in registry.get("LEAV").players.values())


def test_leave_room_during_playing_removes_player_and_broadcasts_game_state():
    """Leaving mid-round must be intentional — remaining players see them gone
    on the next game_state, not a 'disconnected' grace-period entry."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
    ):
        _join(ws_a, "LMID", "Alice")
        ws_a.receive_json()
        _join(ws_b, "LMID", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()
        _pad_room_to_min("LMID")

        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

        ws_b.send_json({"type": "leave_room", "payload": {}})
        # Alice's next game_state must not list Bob anymore.
        gs = _drain_until(ws_a, "game_state", max_msgs=40)
        names = {p["name"] for p in gs["payload"]["players"]}
        assert "Bob" not in names


def test_leave_room_when_last_player_drops_room():
    """A solo player leaving cleans the room out of the registry."""
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        _join(ws, "SOLOX", "Alice")
        ws.receive_json()
        ws.send_json({"type": "leave_room", "payload": {}})
        # No more frames are guaranteed; the room should be gone.
        assert registry.get("SOLOX") is None


def test_abort_round_requires_host_and_running_round():
    """Non-host gets NOT_HOST; host before-start gets WRONG_PHASE; host during
    PLAYING aborts and everyone falls back to lobby_state."""
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws") as ws_a,
        client.websocket_connect("/ws") as ws_b,
    ):
        _join(ws_a, "ABRT", "Alice")
        ws_a.receive_json()
        _join(ws_b, "ABRT", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        # Host before start → WRONG_PHASE.
        ws_a.send_json({"type": "abort_round", "payload": {}})
        err = _drain_until(ws_a, "error")
        assert err["payload"]["code"] == "WRONG_PHASE"

        _pad_room_to_min("ABRT")
        ws_a.send_json({"type": "start_game", "payload": {}})
        for ws in [ws_a, ws_b]:
            _drain_until(ws, "private_role")
            _drain_until(ws, "game_state")

        # Non-host abort → NOT_HOST.
        ws_b.send_json({"type": "abort_round", "payload": {}})
        err = _drain_until(ws_b, "error", max_msgs=40)
        assert err["payload"]["code"] == "NOT_HOST"

        # Host abort during PLAYING → both clients receive lobby_state.
        ws_a.send_json({"type": "abort_round", "payload": {}})
        lob_a = _drain_until(ws_a, "lobby_state", max_msgs=40)
        lob_b = _drain_until(ws_b, "lobby_state", max_msgs=40)
        assert lob_a["payload"]["roomCode"] == "ABRT"
        assert lob_b["payload"]["roomCode"] == "ABRT"
        # Phase reset puts the room back into lobby.
        assert registry.get("ABRT").phase.value == "lobby"
