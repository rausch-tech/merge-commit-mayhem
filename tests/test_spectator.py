"""Tier 2.6 — Spectator-Mode for ghosts.

Once a player dies, they are not done — they become a ghost spectator who can:
- still move (server accepts input, ticks, no wall collisions, normal speed)
- still complete tasks to help the release-team win
- but NOT trigger sabotages, vote, skip, call meetings, take down, or report

These tests pin those rules so future refactors do not regress them.
"""

import random

import pytest

from app.game.game_room import GameRoom, GameRoomError
from app.game.models import InputState, Phase
from app.game.sabotages import COFFEE_SLOW_SPEED, NORMAL_SPEED


def _started_room(player_count: int = 4, seed: int = 0) -> tuple[GameRoom, list[str]]:
    """Spawn a started GameRoom with at least 4 players (1 chaos + 3 release)."""
    from tests.conftest import make_task_hold_e

    if player_count < 4:
        player_count = 4
    room = GameRoom(code="GHST")
    ids = [room.add_player(f"p{i}").id for i in range(player_count)]
    room.start(requesting_player_id=ids[0], rng=random.Random(seed))
    make_task_hold_e(room, "review_pr")
    return room, ids


def _split_by_team(room: GameRoom) -> tuple[str, list[str]]:
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    release_ids = [p.id for p in room.players.values() if p.team == "release_team"]
    return chaos_id, release_ids


# --- ghost can move ----------------------------------------------------------


def test_ghost_apply_input_is_accepted():
    room, ids = _started_room()
    pid = ids[0]
    room.players[pid].is_alive = False
    room.apply_input(pid, InputState(right=True))
    assert room.players[pid].input_state.right is True


def test_ghost_moves_during_tick():
    room, ids = _started_room()
    pid = ids[0]
    p = room.players[pid]
    p.is_alive = False
    p.x, p.y = 100.0, 100.0
    room.apply_input(pid, InputState(right=True))
    room.tick(0.1)
    # No slow modifier applies to ghosts.
    assert p.x == pytest.approx(100.0 + NORMAL_SPEED * 0.1)


def test_ghost_passes_through_wall():
    """Ghosts ignore walls entirely. Default map has a vertical wall at x=1600;
    a ghost starting just before the wall should glide across it instead of
    being clamped to wx1 - radius.
    """
    room, ids = _started_room()
    pid = ids[0]
    p = room.players[pid]
    p.is_alive = False
    # y=200 is well clear of the door cutouts at y=800 and y=2400. Use the
    # real tick rate (20 Hz) so step size is small (about 7.5 px) — that's the
    # cadence the live server uses, and it ensures wall collisions would
    # actually fire for a living player at this speed.
    p.x, p.y = 1570.0, 200.0
    room.apply_input(pid, InputState(right=True))
    for _ in range(20):  # 1s at 20 Hz
        room.tick(0.05)
    # Ghost crossed the wall completely; living player would be stuck at 1572.
    assert p.x > 1610.0


def test_living_player_is_blocked_by_wall_for_comparison():
    """Sanity peer to test_ghost_passes_through_wall: at the same step size,
    a living player is pushed back by the wall instead of crossing it.
    """
    room, ids = _started_room()
    pid = ids[0]
    p = room.players[pid]
    assert p.is_alive is True
    p.x, p.y = 1570.0, 200.0
    room.apply_input(pid, InputState(right=True))
    for _ in range(20):
        room.tick(0.05)
    # Wall at x=1600 with thickness 8 (so from 1592 to 1608) and player radius
    # 20 means the player stops at x=1572.
    assert p.x == pytest.approx(1572.0)


def test_ghost_clamped_at_map_edge():
    room, ids = _started_room()
    pid = ids[0]
    p = room.players[pid]
    p.is_alive = False
    p.x, p.y = float(room.map.size.width - 5), 200.0
    room.apply_input(pid, InputState(right=True))
    room.tick(1.0)
    assert p.x == float(room.map.size.width)


def test_ghost_speed_unaffected_by_coffee_outage():
    room, ids = _started_room()
    pid = ids[0]
    p = room.players[pid]
    p.is_alive = False
    p.x, p.y = 100.0, 100.0
    room.coffee_level = 0  # would slow a living player
    room.apply_input(pid, InputState(right=True))
    room.tick(0.1)
    # Still NORMAL_SPEED * 0.1 = 15 px, not COFFEE_SLOW_SPEED * 0.1 = 8 px.
    assert p.x == pytest.approx(100.0 + NORMAL_SPEED * 0.1)
    # Sanity: the slow speed still applies for living players.
    other_pid = ids[1]
    other = room.players[other_pid]
    other.x, other.y = 100.0, 100.0
    room.apply_input(other_pid, InputState(right=True))
    room.tick(0.1)
    assert other.x == pytest.approx(100.0 + COFFEE_SLOW_SPEED * 0.1)


def test_ghost_speed_unaffected_by_mandatory_meeting_slowdown():
    room, ids = _started_room()
    pid = ids[0]
    p = room.players[pid]
    p.is_alive = False
    p.x, p.y = 100.0, 100.0
    room.meeting_active_for = 3.0
    room.apply_input(pid, InputState(right=True))
    room.tick(0.1)
    assert p.x == pytest.approx(100.0 + NORMAL_SPEED * 0.1)


def test_ghost_does_not_move_during_meeting_phase():
    """Self-review #6: meetings freeze movement for everyone — ghosts included."""
    room, ids = _started_room()
    pid = ids[0]
    p = room.players[pid]
    p.is_alive = False
    p.x, p.y = 100.0, 100.0
    room.phase = Phase.MEETING
    room.meeting_remaining_seconds = 60.0
    room.apply_input(pid, InputState(right=True))
    room.tick(0.1)
    assert p.x == 100.0


# --- ghost can complete tasks -----------------------------------------------


def test_ghost_can_start_task_hold():
    room, ids = _started_room()
    pid = ids[0]
    room.players[pid].is_alive = False
    tx, ty = room.task_position("review_pr")
    room.players[pid].x, room.players[pid].y = tx, ty
    room.apply_task_hold_start(pid, "review_pr")
    assert pid in room.tasks["review_pr"].per_player_progress


def test_ghost_task_completion_increments_release_progress():
    room, ids = _started_room()
    pid = ids[0]
    room.players[pid].is_alive = False
    tx, ty = room.task_position("review_pr")
    room.players[pid].x, room.players[pid].y = tx, ty
    pre_progress = room.release_progress
    pre_count = room.completed_tasks_by_player.get(pid, 0)
    room.apply_task_hold_start(pid, "review_pr")
    # Tick long enough to finish the 5s task.
    for _ in range(60):
        room.tick(0.1)
        if room.tasks["review_pr"].status == "cooldown":
            break
    assert room.release_progress > pre_progress
    assert room.completed_tasks_by_player.get(pid, 0) == pre_count + 1


# --- guards that must STILL block ghosts ------------------------------------


def test_ghost_cannot_trigger_sabotage():
    room, ids = _started_room()
    chaos_id, _ = _split_by_team(room)
    room.players[chaos_id].is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.apply_sabotage(chaos_id, "ci_cd_red")
    assert exc.value.code == "PLAYER_ELIMINATED"


def test_ghost_cannot_call_emergency_meeting():
    room, ids = _started_room()
    pid = ids[0]
    room.players[pid].is_alive = False
    # In war room so the only remaining guard would be PLAYER_ELIMINATED.
    room.players[pid].x, room.players[pid].y = 2000.0, 2000.0
    with pytest.raises(GameRoomError) as exc:
        room.call_emergency_meeting(pid)
    assert exc.value.code == "PLAYER_ELIMINATED"


def test_ghost_cannot_cast_vote():
    room, ids = _started_room()
    a, b = ids[0], ids[1]
    room.players[a].x, room.players[a].y = 2000.0, 2000.0
    room.call_emergency_meeting(a, rng=random.Random(0))
    room.players[b].is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.cast_vote(b, a)
    assert exc.value.code == "CANNOT_VOTE"


def test_ghost_cannot_skip_vote():
    room, ids = _started_room()
    a, b = ids[0], ids[1]
    room.players[a].x, room.players[a].y = 2000.0, 2000.0
    room.call_emergency_meeting(a, rng=random.Random(0))
    room.players[b].is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.skip_vote(b)
    assert exc.value.code == "CANNOT_VOTE"


def test_ghost_cannot_trigger_takedown():
    """Killer must be alive — even if they were previously chaos."""
    room, ids = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    room.players[chaos_id].is_alive = False
    room.players[chaos_id].x, room.players[chaos_id].y = 100.0, 100.0
    room.players[target_id].x, room.players[target_id].y = 100.0, 110.0
    with pytest.raises(GameRoomError) as exc:
        room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    assert exc.value.code == "PLAYER_ELIMINATED"


def test_ghost_cannot_report_body():
    room, ids = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    victim_id = release_ids[0]
    reporter_id = release_ids[1]
    room.players[chaos_id].x, room.players[chaos_id].y = 500.0, 500.0
    room.players[victim_id].x, room.players[victim_id].y = 500.0, 510.0
    body = room.apply_takedown(killer_id=chaos_id, target_id=victim_id)
    # Reporter dies → cannot report.
    room.players[reporter_id].is_alive = False
    room.players[reporter_id].x, room.players[reporter_id].y = body.x, body.y
    with pytest.raises(GameRoomError) as exc:
        room.apply_report_body(reporter_id=reporter_id, body_id=body.id)
    assert exc.value.code == "PLAYER_ELIMINATED"
