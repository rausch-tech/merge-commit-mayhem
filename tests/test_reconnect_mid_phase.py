"""Reconnect-during-phase regressions.

Existing test_edge_cases.py covers reconnect in LOBBY + after host-disconnect.
These exercise the harder cases: a player drops mid-MEETING, mid-mini-game,
or right after a take-down. The phase machinery and the per-controller
cleanup paths must keep their invariants when the WS bounces.
"""

from __future__ import annotations

import random

from app.game.game_room import GameRoom
from app.game.models import Phase


def _started(player_count: int = 4) -> tuple[GameRoom, list[str]]:
    room = GameRoom(code="ABCD")
    host = room.add_player("host")
    ids = [host.id]
    for i in range(player_count - 1):
        ids.append(room.add_player(f"p{i}").id)
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    return room, ids


# --- mid-MEETING reconnect --------------------------------------------------


def test_disconnect_in_meeting_keeps_seat_through_grace():
    """A player who drops during MEETING keeps their seat and their cast vote
    is preserved — reconnecting puts them right back without the meeting
    needing to restart."""
    room, ids = _started(player_count=4)
    host_id = ids[0]
    voter = ids[1]
    target = ids[2]

    room.players_with_meeting_left[host_id] = True
    # Park host in war-room so the call doesn't throw.
    x_min, y_min, x_max, y_max = room._war_room_bounds
    room.players[host_id].x = (x_min + x_max) / 2
    room.players[host_id].y = (y_min + y_max) / 2
    room.call_emergency_meeting(host_id)
    assert room.phase is Phase.MEETING

    room.cast_vote(voter, target)
    assert room.votes[voter] == target

    # Voter drops — vote stays, phase stays.
    room.mark_disconnected(voter)
    assert room.phase is Phase.MEETING
    assert room.votes[voter] == target
    assert room.players[voter].is_connected is False

    # Voter rejoins — same player object, vote intact.
    rejoined = room.mark_reconnected(voter)
    assert rejoined.id == voter
    assert rejoined.is_connected is True
    assert room.votes[voter] == target


def test_meeting_resolves_when_remaining_alive_voted_after_disconnect():
    """If the only un-voted player drops, the next tick should still let the
    meeting auto-resolve once everyone alive has cast a vote."""
    room, ids = _started(player_count=4)
    host_id = ids[0]

    room.players_with_meeting_left[host_id] = True
    x_min, y_min, x_max, y_max = room._war_room_bounds
    room.players[host_id].x = (x_min + x_max) / 2
    room.players[host_id].y = (y_min + y_max) / 2
    room.call_emergency_meeting(host_id)

    # All but one alive player skip-vote.
    voters = [pid for pid, p in room.players.items() if p.is_alive]
    skipper = voters[-1]
    for pid in voters[:-1]:
        room.skip_vote(pid)

    # The remaining alive player drops mid-meeting before voting.
    room.mark_disconnected(skipper)
    # The disconnected player still counts as alive — _all_alive_voted still
    # gates on living players, regardless of connection. So the meeting does
    # NOT auto-resolve until either the timer or a final vote arrives.
    room.tick(0.1)
    assert room.phase is Phase.MEETING

    # Have the disconnected player rejoin and skip too — meeting now resolves.
    room.mark_reconnected(skipper)
    room.skip_vote(skipper)
    room.tick(0.1)
    assert room.phase is Phase.PLAYING


# --- mid-mini-game reconnect ------------------------------------------------


def test_disconnect_during_mini_game_drops_session():
    """Tier 3.1 invariant: a disconnect cancels the mini-game session
    immediately. State is not preserved across the bounce — the docs are
    clear, this test pins the behaviour."""
    room, ids = _started(player_count=4)
    pid = ids[0]
    # Park the player at a task with mini-game and start it.
    task_id = "fix_unit_tests"
    task = room.tasks[task_id]
    room.players[pid].x = task.x
    room.players[pid].y = task.y
    room.apply_task_hold_start(pid, task_id)
    assert pid in room.active_mini_games

    room.mark_disconnected(pid)
    assert pid not in room.active_mini_games
    # Task drops back to available (no other player is on it).
    assert room.tasks[task_id].status == "available"

    # Reconnect — no auto-restart of the mini-game.
    rejoined = room.mark_reconnected(pid)
    assert rejoined.is_connected is True
    assert pid not in room.active_mini_games


# --- mid-takedown / body-state reconnect ------------------------------------


def test_disconnect_after_takedown_does_not_resurrect_victim():
    """A take-down victim who reconnects within the grace period stays
    eliminated. is_alive reflects game state, not connection state."""
    room, ids = _started(player_count=4)
    # Find a chaos and a release alive-and-connected player.
    chaos_id = next(pid for pid, p in room.players.items() if p.team == "chaos_agents")
    release_id = next(
        pid for pid, p in room.players.items() if p.team == "release_team" and p.is_alive
    )
    # Snap chaos onto victim for proximity.
    chaos = room.players[chaos_id]
    target = room.players[release_id]
    chaos.x, chaos.y = target.x, target.y
    room.apply_takedown(chaos_id, release_id)
    assert room.players[release_id].is_alive is False

    # Victim disconnects + reconnects.
    room.mark_disconnected(release_id)
    rejoined = room.mark_reconnected(release_id)
    assert rejoined.is_alive is False  # still dead, just reconnected
    assert rejoined.is_connected is True
