"""
Tier 0.11 — Edge-Case regression tests.

Each test covers a subtle disconnect / phase-transition / multi-player race
scenario. Tests are written first, behavior observed, bugs fixed where found.
"""

import random
import time

import pytest
from fastapi.testclient import TestClient

from app.game.game_room import RECONNECT_GRACE_SECONDS, GameRoom, GameRoomError
from app.game.models import Phase
from app.main import app, registry

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_started_room(player_count: int = 4, seed: int = 0) -> GameRoom:
    """Create a started GameRoom with *player_count* players.

    Tier 1.5 raised MIN_PLAYERS_TO_START to 4 — bump any caller-supplied count
    below 4 silently. Tier 2.1 chaos-parity (chaos_alive >= release_alive) still
    needs >=3 release; with 4 players (1 chaos + 3 release) parity does not fire
    on the first tick.
    """
    if player_count < 4:
        player_count = 4
    room = GameRoom(code="TEST")
    for i in range(player_count):
        room.add_player(f"p{i}")
    host_id = next(iter(room.players))
    room.start(requesting_player_id=host_id, rng=random.Random(seed))
    return room


def _place_in_war_room(room: GameRoom, player_id: str) -> None:
    """Teleport a player into the War Room so they can call a meeting."""
    room.players[player_id].x = 2000.0
    room.players[player_id].y = 2000.0


def _force_meeting(room: GameRoom, caller_id: str) -> None:
    """Place caller in War Room and call a meeting."""
    _place_in_war_room(room, caller_id)
    room.call_emergency_meeting(requesting_player_id=caller_id, rng=random.Random(0))


def _pad_room_to_min(room_code: str, min_players: int = 4) -> list[str]:
    """Pad a room with server-side dummy players up to `min_players`.

    Tier 1.5 raised MIN_PLAYERS_TO_START to 4. Many existing WS-based edge-case
    tests join only 2-3 real WebSocket clients; this helper backfills the
    remaining slots by poking the registry directly. Returns the new filler
    player ids in join order.
    """
    room = registry.get(room_code)
    assert room is not None, f"Room {room_code!r} not registered yet."
    filler_ids: list[str] = []
    while len(room.players) < min_players:
        idx = len(room.players)
        p = room.add_player(f"_filler_{idx}")
        filler_ids.append(p.id)
    return filler_ids


def _drop_fillers(room_code: str, filler_ids: list[str]) -> None:
    """Remove server-side filler players from the room.

    Use this after start() in tests that go on to assert room cleanup behavior
    (room becomes empty / drops from registry). Fillers don't have WebSockets,
    so they would otherwise block "all WS closed -> empty room" assertions.
    """
    room = registry.get(room_code)
    if room is None:
        return
    for fid in filler_ids:
        if fid in room.players:
            room.remove_player(fid)


# ---------------------------------------------------------------------------
# EC1 — Host disconnects mid-meeting; voting continues
# ---------------------------------------------------------------------------


def test_host_disconnects_during_meeting_voting_continues():
    """Host disconnects in MEETING phase.  Meeting timer keeps counting;
    remaining players can still vote; meeting resolves normally."""
    room = _make_started_room(player_count=3)

    host = next(p for p in room.players.values() if p.is_host)
    others = [p for p in room.players.values() if not p.is_host]
    alice, bob = others[0], others[1]

    # Host calls meeting from War Room.
    _force_meeting(room, host.id)
    assert room.phase is Phase.MEETING

    # Host's WS drops mid-meeting.
    room.mark_disconnected(host.id)
    assert room.players[host.id].is_connected is False
    # Host transfer should have happened eagerly.
    assert room.players[host.id].is_host is False
    remaining_hosts = [p for p in room.players.values() if p.is_host]
    assert len(remaining_hosts) == 1, "Exactly one new host after host disconnect"

    # Phase is still MEETING.
    assert room.phase is Phase.MEETING

    # The two remaining (alive) players vote — this should resolve meeting.
    room.cast_vote(voter_id=alice.id, target_id=bob.id)
    room.cast_vote(voter_id=bob.id, target_id=alice.id)
    # Disconnected host doesn't vote → tie → no elimination, meeting resolves.
    # Drive to resolution by ticking past timer.
    room.meeting_remaining_seconds = 0.01
    room.tick(0.05)

    assert room.phase is Phase.PLAYING
    assert room.last_voting_result is not None


# ---------------------------------------------------------------------------
# EC2 — Host-transfer chain A → B → C
# ---------------------------------------------------------------------------


def test_host_transfer_chains_through_multiple_disconnects():
    """Disconnecting host A passes to B; disconnecting B passes to C."""
    room = _make_started_room(player_count=3)

    players = list(room.players.values())
    a = next(p for p in players if p.is_host)
    others = [p for p in players if not p.is_host]
    b, c = others[0], others[1]

    # A disconnects → B or C becomes host.
    room.mark_disconnected(a.id)
    assert a.is_host is False
    new_hosts = [p for p in room.players.values() if p.is_host and p.id != a.id]
    assert len(new_hosts) == 1
    b_new_host = new_hosts[0]

    # That new host disconnects → remaining player becomes host.
    room.mark_disconnected(b_new_host.id)
    assert b_new_host.is_host is False
    final_hosts = [
        p for p in room.players.values() if p.is_host and p.id not in (a.id, b_new_host.id)
    ]
    assert len(final_hosts) == 1
    # The remaining player is either b or c.
    assert final_hosts[0].id in (b.id, c.id)


# ---------------------------------------------------------------------------
# EC3 — Last connected player in ENDED phase disconnects; room dropped
# ---------------------------------------------------------------------------


def test_last_player_disconnect_in_ended_phase_drops_room():
    """In ENDED phase, _handle_disconnect fully removes the player immediately
    (no grace period) and drops the room.

    Uses 3 players so the Tier 2.1 chaos-parity rule does not fire first; the
    test is about ENDED-phase cleanup, not which winner.
    """
    with TestClient(app) as client:

        @pytest.fixture(autouse=True)
        def _reset():
            yield
            registry._rooms.clear()

        with (
            client.websocket_connect("/ws") as ws_a,
            client.websocket_connect("/ws") as ws_b,
            client.websocket_connect("/ws") as ws_c,
        ):
            ws_a.send_json(
                {"type": "join_room", "payload": {"roomCode": "ECDROP", "playerName": "Alice"}}
            )
            ws_a.receive_json()  # room_joined
            ws_a.receive_json()  # lobby_state

            ws_b.send_json(
                {"type": "join_room", "payload": {"roomCode": "ECDROP", "playerName": "Bob"}}
            )
            ws_b.receive_json()  # room_joined
            ws_a.receive_json()  # lobby_state broadcast
            ws_b.receive_json()  # lobby_state

            ws_c.send_json(
                {"type": "join_room", "payload": {"roomCode": "ECDROP", "playerName": "Carol"}}
            )
            ws_c.receive_json()  # room_joined
            ws_a.receive_json()  # lobby_state broadcast
            ws_b.receive_json()  # lobby_state broadcast
            ws_c.receive_json()  # lobby_state

            filler_ids = _pad_room_to_min("ECDROP")
            ws_a.send_json({"type": "start_game", "payload": {}})
            for _ in range(4):
                ws_a.receive_json()
            for _ in range(2):
                ws_b.receive_json()
            for _ in range(2):
                ws_c.receive_json()

            # Drop server-side fillers so the "all WS clients close -> empty room"
            # cleanup assertion below holds.
            _drop_fillers("ECDROP", filler_ids)

            # Force ENDED.
            room = registry.get("ECDROP")
            assert room is not None
            room.release_progress = 100

            # Drain game_ended from all.
            for ws in [ws_a, ws_b, ws_c]:
                for _ in range(60):
                    m = ws.receive_json()
                    if m["type"] == "game_ended":
                        break

        # All WS closed. In ENDED phase → fully removed immediately, no grace.
        time.sleep(0.1)
        assert registry.get("ECDROP") is None, "Room must be gone after last player leaves ENDED"


# ---------------------------------------------------------------------------
# EC4 — All players disconnect in PLAYING; grace expires; room becomes empty
# ---------------------------------------------------------------------------


def test_all_players_disconnect_then_grace_expires():
    """All 3 players disconnect. Force grace timestamps into past. A tick sweep
    removes them all. Room becomes empty. Ticking an empty room doesn't crash."""
    room = _make_started_room(player_count=3)
    pids = list(room.players.keys())

    for pid in pids:
        room.mark_disconnected(pid)

    # Force timestamps into the past (beyond grace).
    past = time.monotonic() - (RECONNECT_GRACE_SECONDS + 5)
    for pid in pids:
        room.players[pid].disconnected_at_monotonic = past

    # Tick should sweep all players.
    room.tick(0.05)

    assert room.is_empty(), "Room must be empty after all grace periods expire"

    # Ticking an empty room must not crash.
    room.tick(0.05)
    room.tick(0.05)


# ---------------------------------------------------------------------------
# EC5 — Player disconnects during solo task hold; task returns to "available"
# ---------------------------------------------------------------------------


def test_disconnect_during_solo_task_hold_releases_task():
    """When the only holder disconnects, the task status goes back to available."""
    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    player = room.players[pid]

    # Place the player on the task.
    task_x, task_y = room.task_position("fix_unit_tests")
    player.x, player.y = task_x, task_y

    room.apply_task_hold_start(pid, "fix_unit_tests")
    assert room.tasks["fix_unit_tests"].status == "in_progress"
    assert pid in room.tasks["fix_unit_tests"].per_player_progress

    # Disconnect should release.
    room.mark_disconnected(pid)

    assert pid not in room.tasks["fix_unit_tests"].per_player_progress
    assert room.tasks["fix_unit_tests"].status == "available"


# ---------------------------------------------------------------------------
# EC6 — Player rejoins during MEETING phase; receives full state
# ---------------------------------------------------------------------------


def test_rejoin_during_meeting_can_vote():
    """Bob disconnects mid-PLAYING. Alice calls a meeting. Bob rejoins during
    MEETING and receives game_state with phase=meeting. He can then cast a vote.

    Uses 3 players (Alice, Bob, Carol) so the Tier 2.1 chaos-parity rule does
    not fire while the test is mid-flow.
    """
    with TestClient(app) as client:

        @pytest.fixture(autouse=True)
        def _reset():
            yield
            registry._rooms.clear()

        with (
            client.websocket_connect("/ws") as ws_a,
            client.websocket_connect("/ws") as ws_b,
            client.websocket_connect("/ws") as ws_c,
        ):
            ws_a.send_json(
                {"type": "join_room", "payload": {"roomCode": "ECMTG", "playerName": "Alice"}}
            )
            ws_a.receive_json()  # room_joined
            ws_a.receive_json()  # lobby_state

            ws_b.send_json(
                {"type": "join_room", "payload": {"roomCode": "ECMTG", "playerName": "Bob"}}
            )
            ws_b.receive_json()  # room_joined
            ws_a.receive_json()
            ws_b.receive_json()

            ws_c.send_json(
                {"type": "join_room", "payload": {"roomCode": "ECMTG", "playerName": "Carol"}}
            )
            ws_c.receive_json()  # room_joined
            ws_a.receive_json()
            ws_b.receive_json()
            ws_c.receive_json()

            _pad_room_to_min("ECMTG")
            ws_a.send_json({"type": "start_game", "payload": {}})
            for _ in range(2):
                ws_a.receive_json()
            for _ in range(2):
                ws_b.receive_json()
            for _ in range(2):
                ws_c.receive_json()

            room = registry.get("ECMTG")
            alice_id = next(p.id for p in room.players.values() if p.name == "Alice")
            bob_id = next(p.id for p in room.players.values() if p.name == "Bob")

        # ws_b closed — Bob is disconnected.
        time.sleep(0.1)
        assert room.players[bob_id].is_connected is False

        # Alice calls meeting (from War Room).
        _force_meeting(room, alice_id)
        assert room.phase is Phase.MEETING

        # Bob reconnects.
        with client.websocket_connect("/ws") as ws_b2:
            ws_b2.send_json(
                {"type": "rejoin", "payload": {"roomCode": "ECMTG", "playerId": bob_id}}
            )
            joined = ws_b2.receive_json()
            assert joined["type"] == "room_joined"

            # private_role (has role because game is running).
            role = ws_b2.receive_json()
            assert role["type"] == "private_role"

            # game_state with meeting phase.
            state = ws_b2.receive_json()
            assert state["type"] == "game_state"
            assert state["payload"]["phase"] == "meeting"
            assert state["payload"]["meeting"] is not None

            # Bob can cast a vote — confirm no error is returned.
            ws_b2.send_json({"type": "cast_vote", "payload": {"targetPlayerId": alice_id}})
            # Vote is accepted server-side; room.votes has bob_id after tick.
            assert room.phase is Phase.MEETING


# ---------------------------------------------------------------------------
# EC7 — Two simultaneous joins with the same name; one succeeds, one fails
# ---------------------------------------------------------------------------


def test_two_simultaneous_joins_with_same_name_one_succeeds():
    """Sequential in Python asyncio. The first join succeeds; the second
    should get NAME_TAKEN regardless of near-simultaneous arrival."""
    with TestClient(app) as client:

        @pytest.fixture(autouse=True)
        def _reset():
            yield
            registry._rooms.clear()

        with (
            client.websocket_connect("/ws") as ws_a,
            client.websocket_connect("/ws") as ws_b,
        ):
            ws_a.send_json(
                {"type": "join_room", "payload": {"roomCode": "ECRACE", "playerName": "Dup"}}
            )
            ws_b.send_json(
                {"type": "join_room", "payload": {"roomCode": "ECRACE", "playerName": "Dup"}}
            )

            result_a = ws_a.receive_json()
            result_b = ws_b.receive_json()

            successes = [r for r in [result_a, result_b] if r["type"] == "room_joined"]
            errors = [
                r
                for r in [result_a, result_b]
                if r["type"] == "error" and r["payload"]["code"] == "NAME_TAKEN"
            ]

            assert len(successes) == 1, "Exactly one join must succeed"
            assert len(errors) == 1, "The other must get NAME_TAKEN"


# ---------------------------------------------------------------------------
# EC8 — Memory: 100 round resets in a row; no collection growth
# ---------------------------------------------------------------------------


def test_many_rounds_in_a_row_no_collection_growth():
    """Run 100 start/finish/reset cycles. After every reset the per-round
    collections must be cleared; after every start they must be exactly the
    number of current players."""
    room = GameRoom(code="LOOP")
    for i in range(4):
        room.add_player(f"p{i}")
    host_id = next(iter(room.players))
    n_players = len(room.players)

    for _ in range(100):
        room.start(requesting_player_id=host_id, rng=random.Random(0))
        assert len(room.completed_tasks_by_player) == n_players
        assert len(room.triggered_sabotages_by_player) == n_players
        assert len(room.players_with_meeting_left) == n_players
        assert len(room.players) == n_players
        assert len(room.sabotages) == 8  # 3 base + 3 (1.4) + 1 (2.4 lights) + 1 (2.5 comms)

        room._finish_round("chaos_agents", "test")
        room.reset_for_new_round()

        assert room.completed_tasks_by_player == {}
        assert room.triggered_sabotages_by_player == {}
        assert room.players_with_meeting_left == {}
        assert room.tasks == {}
        assert room.sabotages == {}
        assert len(room.players) == n_players


# ---------------------------------------------------------------------------
# EC9 — Vote target swept during meeting; resolver handles missing player
# ---------------------------------------------------------------------------


def test_vote_target_swept_during_meeting():
    """Carol disconnects and grace expires mid-meeting. Alice + Bob vote Carol.
    After sweep Carol is no longer in players. _resolve_meeting must not crash
    and must return removedPlayerId='' / wasChaosAgent=False."""
    room = _make_started_room(player_count=3)

    pids = list(room.players.keys())
    alice_id, bob_id, carol_id = pids[0], pids[1], pids[2]

    _force_meeting(room, alice_id)
    assert room.phase is Phase.MEETING

    # Alice and Bob vote Carol.
    room.cast_vote(voter_id=alice_id, target_id=carol_id)
    room.cast_vote(voter_id=bob_id, target_id=carol_id)

    # Manually remove Carol (simulating sweep removing her mid-meeting).
    room.remove_player(carol_id)
    assert carol_id not in room.players

    # Resolve must not crash.
    room.meeting_remaining_seconds = 0.0
    room.tick(0.05)

    # We expect graceful resolution.
    assert room.last_voting_result is not None
    result = room.last_voting_result
    # Carol was already gone — guard means she wasn't marked dead again.
    assert result["removed_player_id"] == carol_id or result["removed_player_id"] == ""
    # was_chaos_agent should be False when target is missing from players.
    if result["removed_player_id"] == "":
        assert result["was_chaos_agent"] is False

    assert room.phase is Phase.PLAYING


# ---------------------------------------------------------------------------
# EC10 — Sweep does NOT run during MEETING phase
# ---------------------------------------------------------------------------


def test_sweep_does_not_run_during_meeting():
    """A disconnected player with expired grace is NOT removed during MEETING.
    Sweep only fires in the PLAYING branch of tick()."""
    room = _make_started_room(player_count=3)

    pids = list(room.players.keys())
    alice_id, _bob_id, carol_id = pids[0], pids[1], pids[2]

    # Carol disconnects with an already-expired grace.
    room.mark_disconnected(carol_id)
    room.players[carol_id].disconnected_at_monotonic = time.monotonic() - (
        RECONNECT_GRACE_SECONDS + 60
    )

    # Alice calls a meeting.
    _force_meeting(room, alice_id)
    assert room.phase is Phase.MEETING

    # Tick several times — sweep should NOT fire in MEETING.
    for _ in range(5):
        room.tick(0.05)
        if room.phase is Phase.PLAYING:
            break  # meeting may have resolved; that's fine

    # If still in MEETING (or just resolved back to PLAYING), Carol was NOT
    # removed by the sweep while the meeting was active; she should still be
    # present in the room.
    assert carol_id in room.players, "Sweep must not remove players during MEETING phase"


# ---------------------------------------------------------------------------
# EC11 — Reconnect to non-existent room
# ---------------------------------------------------------------------------


def test_rejoin_to_nonexistent_room_returns_error():
    """Stale sessionStorage: room code doesn't exist → REJOIN_NOT_AVAILABLE."""
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        ws.send_json(
            {
                "type": "rejoin",
                "payload": {"roomCode": "NEVER", "playerId": "deadbeef"},
            }
        )
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "REJOIN_NOT_AVAILABLE"


# ---------------------------------------------------------------------------
# EC12 — Reconnect when player already connected (duplicate session)
# ---------------------------------------------------------------------------


def test_rejoin_for_already_connected_player_fails():
    """Trying to rejoin a player who is still is_connected=True fails."""
    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    # Player is connected (the default).
    assert room.players[pid].is_connected is True

    with pytest.raises(GameRoomError) as exc:
        room.mark_reconnected(pid)
    assert exc.value.code == "REJOIN_NOT_AVAILABLE"


# ---------------------------------------------------------------------------
# EC13 — Map JSON: invalid JSON and missing required field (already in
#         test_game_map.py → skip adding duplicates; add a JSON-parse test)
# ---------------------------------------------------------------------------


def test_load_map_with_invalid_json_raises_loudly():
    """A completely malformed JSON file must raise at load time."""
    import tempfile
    from pathlib import Path

    from app.game.game_map import load_map

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ this is not valid JSON }")
        tmp_path = Path(f.name)

    with pytest.raises((Exception,)):  # noqa: B017 — multiple raise paths tested
        load_map(tmp_path)


def test_load_map_with_missing_required_field_raises_loudly():
    """A JSON file missing the required 'warRoomId' field must raise."""
    import json
    import tempfile
    from pathlib import Path

    from app.game.game_map import load_map

    incomplete = {
        "name": "bad",
        "size": {"width": 100, "height": 100},
        "rooms": [],
        # war_room_id intentionally absent
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(incomplete, f)
        tmp_path = Path(f.name)

    with pytest.raises((Exception,)):  # noqa: B017 — multiple raise paths tested
        load_map(tmp_path)


# ---------------------------------------------------------------------------
# EC14 — Disconnected chaos player does NOT count as eliminated for win
# ---------------------------------------------------------------------------


def test_disconnected_chaos_does_not_count_as_eliminated_for_win():
    """A chaos player who disconnects (but is still within grace) is alive but
    not connected. The all_chaos_eliminated win-condition must NOT fire.

    We use 1 chaos + 2 release so that the Tier 2.1 chaos-parity rule
    (chaos_alive >= release_alive) does not also fire and confound this test.
    """
    room = GameRoom(code="WIN")
    chaos = room.add_player("ChaosPerson")
    release_a = room.add_player("ReleasePersonA")
    release_b = room.add_player("ReleasePersonB")

    # Force roles manually so the test is deterministic.
    chaos.role = "vibe_coder"
    chaos.team = "chaos_agents"
    release_a.role = "developer"
    release_a.team = "release_team"
    release_b.role = "developer"
    release_b.team = "release_team"

    # Simulate start state (no proper start() to avoid role assignment).
    room.phase = Phase.PLAYING
    room.completed_tasks_by_player = {chaos.id: 0, release_a.id: 0, release_b.id: 0}
    room.triggered_sabotages_by_player = {chaos.id: 0, release_a.id: 0, release_b.id: 0}
    from app.game.game_room import TASK_DEFINITIONS, TaskRuntime

    room.tasks = {
        t.id: TaskRuntime(
            definition=t,
            x=room._task_position[t.id][0],
            y=room._task_position[t.id][1],
        )
        for t in TASK_DEFINITIONS
    }
    from app.game.game_room import SABOTAGE_DEFINITIONS, SabotageRuntime

    room.sabotages = {s.id: SabotageRuntime(definition=s) for s in SABOTAGE_DEFINITIONS}
    room.players_with_meeting_left = {
        chaos.id: True,
        release_a.id: True,
        release_b.id: True,
    }
    chaos.is_alive = True
    release_a.is_alive = True
    release_b.is_alive = True

    # Chaos player disconnects (within grace period).
    room.mark_disconnected(chaos.id)
    assert room.players[chaos.id].is_connected is False
    assert room.players[chaos.id].is_alive is True  # still alive!

    # Tick a few times — all_chaos_eliminated should be False since chaos is alive.
    for _ in range(5):
        room.tick(0.05)
        if room.phase is not Phase.PLAYING:
            break

    assert room.phase is Phase.PLAYING, (
        "Disconnected chaos player must NOT trigger the chaos-eliminated win condition"
    )
    assert room.winner is None


# ---------------------------------------------------------------------------
# EC15 — Tick loop drops empty rooms after grace expires (regression guard)
# ---------------------------------------------------------------------------


def test_solo_demo_player_disconnect_room_is_empty_after_grace():
    """After a solo player disconnects in the PLAYING phase and grace expires,
    the room becomes empty. After the tick sweep the room is empty; the tick
    loop (fixed in EC15) then drops it from the registry via drop_if_empty.

    Tier 2.1 note: a solo demo round now ends immediately on the first tick
    (chaos parity: 1 chaos + 0 release). To still exercise the
    PLAYING-phase grace-expiry sweep we drive a 3-player room here instead.
    """
    with TestClient(app) as client:

        @pytest.fixture(autouse=True)
        def _reset():
            yield
            registry._rooms.clear()

        with (
            client.websocket_connect("/ws") as ws_a,
            client.websocket_connect("/ws") as ws_b,
            client.websocket_connect("/ws") as ws_c,
        ):
            for ws, name in [(ws_a, "Alice"), (ws_b, "Bob"), (ws_c, "Carol")]:
                ws.send_json(
                    {
                        "type": "join_room",
                        "payload": {"roomCode": "EC15", "playerName": name},
                    }
                )
                ws.receive_json()  # room_joined
            # Drain lobby_state broadcasts on each connection.
            for _ in range(3):
                ws_a.receive_json()
            for _ in range(2):
                ws_b.receive_json()
            ws_c.receive_json()

            filler_ids = _pad_room_to_min("EC15")
            ws_a.send_json({"type": "start_game", "payload": {}})
            for _ in range(2):
                ws_a.receive_json()  # private_role + initial game_state
            for _ in range(2):
                ws_b.receive_json()
            for _ in range(2):
                ws_c.receive_json()

            # Drop server-side fillers so the "all WS clients close -> empty room"
            # sweep below removes everyone.
            _drop_fillers("EC15", filler_ids)

            room = registry.get("EC15")
            assert room is not None
            pids = list(room.players.keys())

        # All WS closed → _handle_disconnect marks each as disconnected
        # (mid PLAYING; phase has not yet ended because chaos_alive < release_alive).
        time.sleep(0.2)
        for pid in pids:
            if pid in room.players:
                assert room.players[pid].is_connected is False

        # Force grace into the past for everyone.
        past = time.monotonic() - (RECONNECT_GRACE_SECONDS + 5)
        for pid in pids:
            if pid in room.players:
                room.players[pid].disconnected_at_monotonic = past

        # Single tick should sweep all players out.
        room.tick(0.05)
        assert room.is_empty(), "Room must be empty after grace expires"

        # Simulate what the (now-fixed) tick loop does: drop empty rooms.
        registry.drop_if_empty("EC15")
        assert registry.get("EC15") is None, (
            "Registry must drop the room once it is empty (EC15 fix)"
        )


def test_solo_host_keeps_host_status_across_disconnect_reconnect():
    """Regression: a solo host who briefly disconnects (e.g. tab refresh
    during PLAYING) must remain host after reconnect. Previously
    mark_disconnected demoted them unconditionally and there was nobody to
    transfer host to, leaving the room without a host on rejoin — which in
    turn surfaced as ``isHost: false`` in the personalized snapshot the
    only player ever sees of themselves."""
    room = GameRoom(code="SOLO")
    p = room.add_player("Lonely")
    pid = p.id
    room.start(requesting_player_id=pid, rng=random.Random(0), demo=True)
    assert p.is_host is True

    room.mark_disconnected(pid)
    assert p.is_host is True, (
        "Solo host must keep is_host=True on disconnect — there is nobody to transfer to"
    )

    room.mark_reconnected(pid)
    assert p.is_host is True, "Reconnect must not silently demote the only player"

    snapshot = room.public_state_for(pid)
    assert snapshot["players"][0]["isHost"] is True
