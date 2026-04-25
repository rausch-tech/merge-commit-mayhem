import random

import pytest

from app.game.game_room import GameRoom, GameRoomError, MEETING_DURATION_SECONDS
from app.game.models import InputState, Phase
from app.game.voting import SKIP_TARGET, all_chaos_eliminated, tally


# --- pure tally helper ----------------------------------------------------


def test_tally_empty_returns_none():
    assert tally({}) is None


def test_tally_single_voter_eliminates_target():
    assert tally({"a": "b"}) == "b"


def test_tally_skip_returns_none():
    assert tally({"a": SKIP_TARGET, "b": SKIP_TARGET}) is None


def test_tally_skip_ties_with_target_no_removal():
    assert tally({"a": SKIP_TARGET, "b": "c"}) is None  # 1 skip, 1 vote -> tie -> none


def test_tally_named_majority_eliminates():
    assert tally({"a": "x", "b": "x", "c": SKIP_TARGET}) == "x"


def test_tally_two_named_targets_tied_no_removal():
    assert tally({"a": "x", "b": "y"}) is None


def test_all_chaos_eliminated_yes():
    class P:
        def __init__(self, team, alive): self.team, self.is_alive = team, alive
    players = [P("chaos_agents", False), P("release_team", True)]
    assert all_chaos_eliminated(players) is True


def test_all_chaos_eliminated_no_chaos_left_in_game_returns_false():
    class P:
        def __init__(self, team, alive): self.team, self.is_alive = team, alive
    players = [P("release_team", True)]
    assert all_chaos_eliminated(players) is False


def test_all_chaos_eliminated_some_alive():
    class P:
        def __init__(self, team, alive): self.team, self.is_alive = team, alive
    players = [P("chaos_agents", False), P("chaos_agents", True)]
    assert all_chaos_eliminated(players) is False


# --- meeting lifecycle ----------------------------------------------------


def _started_room(player_count: int = 3) -> tuple[GameRoom, list[str]]:
    room = GameRoom(code="VOTE")
    ids = []
    for i in range(player_count):
        ids.append(room.add_player(f"p{i}").id)
    room.start(requesting_player_id=ids[0], rng=random.Random(0))
    return room, ids


def test_call_meeting_requires_war_room():
    room, ids = _started_room(3)
    pid = ids[0]
    p = room.players[pid]
    p.x, p.y = 100.0, 100.0  # Open Space
    with pytest.raises(GameRoomError) as exc:
        room.call_emergency_meeting(pid)
    assert exc.value.code == "NOT_IN_WAR_ROOM"


def test_call_meeting_in_war_room_transitions_to_meeting_phase():
    room, ids = _started_room(3)
    pid = ids[0]
    room.players[pid].x, room.players[pid].y = 1000.0, 1000.0
    room.call_emergency_meeting(pid, rng=random.Random(0))
    assert room.phase is Phase.MEETING
    assert room.meeting_caller_id == pid
    assert room.meeting_remaining_seconds == MEETING_DURATION_SECONDS
    assert room.meeting_title  # one of the flavor strings


def test_meeting_consumed_on_use():
    room, ids = _started_room(3)
    pid = ids[0]
    room.players[pid].x, room.players[pid].y = 1000.0, 1000.0
    room.call_emergency_meeting(pid, rng=random.Random(0))
    room._resolve_meeting()
    # Try to call again -- denied.
    room.players[pid].x, room.players[pid].y = 1000.0, 1000.0
    with pytest.raises(GameRoomError) as exc:
        room.call_emergency_meeting(pid)
    assert exc.value.code == "NO_MEETING_LEFT"


def test_dead_player_cannot_call_meeting():
    room, ids = _started_room(3)
    pid = ids[0]
    room.players[pid].is_alive = False
    room.players[pid].x, room.players[pid].y = 1000.0, 1000.0
    with pytest.raises(GameRoomError) as exc:
        room.call_emergency_meeting(pid)
    assert exc.value.code == "PLAYER_ELIMINATED"


# --- voting ---------------------------------------------------------------


def test_cast_vote_outside_meeting_phase_errors():
    room, ids = _started_room(3)
    with pytest.raises(GameRoomError) as exc:
        room.cast_vote(ids[0], ids[1])
    assert exc.value.code == "WRONG_PHASE"


def test_cast_vote_for_dead_player_errors():
    room, ids = _started_room(3)
    a, b, c = ids
    room.players[a].x, room.players[a].y = 1000.0, 1000.0
    room.call_emergency_meeting(a, rng=random.Random(0))
    room.players[c].is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.cast_vote(a, c)
    assert exc.value.code == "INVALID_TARGET"


def test_dead_voter_cannot_vote():
    room, ids = _started_room(3)
    a, b, c = ids
    room.players[a].x, room.players[a].y = 1000.0, 1000.0
    room.call_emergency_meeting(a, rng=random.Random(0))
    room.players[b].is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.cast_vote(b, c)
    assert exc.value.code == "CANNOT_VOTE"


def test_majority_vote_eliminates_target():
    room, ids = _started_room(4)
    a, b, c, d = ids
    room.players[a].x, room.players[a].y = 1000.0, 1000.0
    room.call_emergency_meeting(a, rng=random.Random(0))
    room.cast_vote(a, c)
    room.cast_vote(b, c)
    room.skip_vote(d)
    eliminated = room._resolve_meeting()
    assert eliminated == c
    assert room.players[c].is_alive is False
    assert room.phase is Phase.PLAYING


def test_tied_vote_no_removal():
    room, ids = _started_room(4)
    a, b, c, d = ids
    room.players[a].x, room.players[a].y = 1000.0, 1000.0
    room.call_emergency_meeting(a, rng=random.Random(0))
    room.cast_vote(a, b)
    room.cast_vote(c, d)
    eliminated = room._resolve_meeting()
    assert eliminated is None
    assert all(p.is_alive for p in room.players.values())


def test_tick_decrements_meeting_timer_and_auto_resolves():
    room, ids = _started_room(3)
    a, b, c = ids
    room.players[a].x, room.players[a].y = 1000.0, 1000.0
    room.call_emergency_meeting(a, rng=random.Random(0))
    # Cast no votes; let the timer expire.
    for _ in range(int(MEETING_DURATION_SECONDS / 0.1) + 5):
        room.tick(0.1)
    assert room.phase is Phase.PLAYING
    # Nobody voted -> no removal.
    assert all(p.is_alive for p in room.players.values())


def test_meeting_resolves_early_when_all_alive_voted():
    room, ids = _started_room(3)
    a, b, c = ids
    room.players[a].x, room.players[a].y = 1000.0, 1000.0
    room.call_emergency_meeting(a, rng=random.Random(0))
    # All three vote at once -> next tick should resolve.
    room.cast_vote(a, b)
    room.cast_vote(b, c)
    room.cast_vote(c, b)
    room.tick(0.1)
    assert room.phase is Phase.PLAYING
    # b had majority (2 vs 1), eliminated.
    assert room.players[b].is_alive is False


# --- eliminated player gating ---------------------------------------------


def test_eliminated_player_cannot_start_task():
    room, ids = _started_room(3)
    pid = ids[0]
    room.players[pid].is_alive = False
    # Place near a task.
    from app.game.tasks import task_by_id
    defn = task_by_id("fix_unit_tests")
    room.players[pid].x, room.players[pid].y = defn.x, defn.y
    with pytest.raises(GameRoomError) as exc:
        room.apply_task_hold_start(pid, "fix_unit_tests")
    assert exc.value.code == "PLAYER_ELIMINATED"


def test_eliminated_chaos_cannot_sabotage():
    room, ids = _started_room(3)
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    room.players[chaos_id].is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.apply_sabotage(chaos_id, "ci_cd_red")
    assert exc.value.code == "PLAYER_ELIMINATED"


def test_eliminated_player_input_is_ignored():
    room, ids = _started_room(3)
    pid = ids[0]
    room.players[pid].is_alive = False
    room.apply_input(pid, InputState(right=True))
    # The input was rejected -> input_state stays at default.
    assert room.players[pid].input_state.right is False


# --- win condition --------------------------------------------------------


def test_release_team_wins_when_all_chaos_eliminated():
    room, ids = _started_room(3)
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    room.players[chaos_id].is_alive = False
    room.tick(0.1)  # win-check happens on tick
    assert room.phase is Phase.ENDED
    assert room.winner == "release_team"


# --- reset ----------------------------------------------------------------


def test_reset_restores_alive_and_meetings():
    room, ids = _started_room(3)
    pid = ids[0]
    room.players[pid].is_alive = False
    room.players_with_meeting_left[pid] = False
    room.reset_for_new_round()
    assert room.players[pid].is_alive is True
    # players_with_meeting_left is repopulated only on next start(), so it's empty here.
    assert room.players_with_meeting_left == {}


# --- public_state exposes meeting + alive ---------------------------------


def test_public_state_exposes_isalive():
    room, ids = _started_room(3)
    state = room.public_state()
    for p in state["players"]:
        assert p["isAlive"] is True


def test_public_state_meeting_is_none_outside_meeting_phase():
    room, ids = _started_room(3)
    state = room.public_state()
    assert state.get("meeting") is None


def test_public_state_meeting_present_during_meeting():
    room, ids = _started_room(3)
    pid = ids[0]
    room.players[pid].x, room.players[pid].y = 1000.0, 1000.0
    room.call_emergency_meeting(pid, rng=random.Random(0))
    room.cast_vote(pid, ids[1])
    state = room.public_state()
    meeting = state["meeting"]
    assert meeting is not None
    assert meeting["callerId"] == pid
    assert meeting["remainingSeconds"] == int(MEETING_DURATION_SECONDS)
    assert meeting["votesCount"][ids[1]] == 1
    assert pid in meeting["alreadyVoted"]
