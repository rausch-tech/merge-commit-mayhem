"""Tier 3.1 — generic mini-game framework lifecycle tests.

These tests exercise GameRoom-level branching (task with mini_game vs.
without), cancel paths (task_hold_stop, take-down, meeting, disconnect,
round end), and the pending-events queue. Plugin-specific behaviour is
covered in tests/test_minigame_test_suite_repair.py.
"""

import random

import pytest

from app.game.game_room import GameRoom, GameRoomError, MiniGameSession


def _room_with_roles() -> tuple[GameRoom, str, str]:
    room = GameRoom(code="MGAM")
    for n in ("p0", "p1", "p2", "p3"):
        room.add_player(n)
    host = next(iter(room.players))
    room.start(requesting_player_id=host, rng=random.Random(0))
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    dev_id = next(p.id for p in room.players.values() if p.team == "release_team")
    return room, chaos_id, dev_id


def _place_at_task(room: GameRoom, player_id: str, task_id: str) -> None:
    tx, ty = room._task_position[task_id]
    room.players[player_id].x = tx
    room.players[player_id].y = ty


def test_task_with_mini_game_routes_into_session_not_hold_e():
    room, _, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "fix_unit_tests")
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    # Mini-game session was created and queued the started event.
    assert dev_id in room.active_mini_games
    session = room.active_mini_games[dev_id]
    assert isinstance(session, MiniGameSession)
    assert session.plugin_id == "test_suite_repair"
    events = room.drain_pending_mini_game_events()
    kinds = [k for _, k, _ in events]
    assert "started" in kinds
    # Task itself reads as in_progress so other players see "Sven busy".
    assert room.tasks["fix_unit_tests"].status == "in_progress"


def test_task_without_mini_game_still_uses_hold_e():
    room, _, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "review_pr")
    room.apply_task_hold_start(dev_id, "review_pr")
    assert dev_id not in room.active_mini_games
    assert room.tasks["review_pr"].status == "in_progress"


def test_task_hold_stop_cancels_active_mini_game():
    room, _, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "fix_unit_tests")
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    room.drain_pending_mini_game_events()  # discard 'started'
    room.apply_task_hold_stop(dev_id, "fix_unit_tests")
    assert dev_id not in room.active_mini_games
    events = room.drain_pending_mini_game_events()
    kinds = [(k, p["success"]) for _, k, p in events]
    assert ("completed", False) in kinds


def test_starting_second_mini_game_while_active_raises():
    room, _, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "fix_unit_tests")
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    room.drain_pending_mini_game_events()
    with pytest.raises(GameRoomError) as exc:
        room.apply_task_hold_start(dev_id, "fix_unit_tests")
    assert exc.value.code == "MINI_GAME_ALREADY_ACTIVE"


def test_takedown_cancels_victims_mini_game():
    room, chaos_id, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "fix_unit_tests")
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    room.drain_pending_mini_game_events()
    # Place chaos within takedown radius of victim.
    chaos = room.players[chaos_id]
    dev = room.players[dev_id]
    chaos.x, chaos.y = dev.x, dev.y
    room.apply_takedown(chaos_id, dev_id)
    assert dev_id not in room.active_mini_games
    events = room.drain_pending_mini_game_events()
    reasons = [(k, p.get("reason")) for _, k, p in events]
    assert ("completed", "killed") in reasons


def test_meeting_cancels_all_mini_games():
    room, _, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "fix_unit_tests")
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    room.drain_pending_mini_game_events()
    # Force a meeting via War-Room teleport on another player.
    caller = next(p for p in room.players.values() if p.id != dev_id and p.is_alive)
    # War-Room center: bounds (1600..3200, 1600..3200) in default.json.
    caller.x, caller.y = 2400.0, 2400.0
    room.call_emergency_meeting(caller.id, rng=random.Random(0))
    assert dev_id not in room.active_mini_games
    events = room.drain_pending_mini_game_events()
    reasons = [(k, p.get("reason")) for _, k, p in events]
    assert ("completed", "meeting_started") in reasons


def test_round_end_cancels_active_mini_games():
    room, _, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "fix_unit_tests")
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    room.drain_pending_mini_game_events()
    room._finish_round("release_team", "test")
    assert dev_id not in room.active_mini_games
    events = room.drain_pending_mini_game_events()
    reasons = [(k, p.get("reason")) for _, k, p in events]
    assert ("completed", "round_ended") in reasons


def test_disconnect_cancels_mini_game():
    room, _, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "fix_unit_tests")
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    room.drain_pending_mini_game_events()
    room.mark_disconnected(dev_id)
    assert dev_id not in room.active_mini_games
    events = room.drain_pending_mini_game_events()
    reasons = [(k, p.get("reason")) for _, k, p in events]
    assert ("completed", "disconnected") in reasons


def test_movement_locked_during_mini_game():
    """Server tick ignores WASD while a mini-game is active."""
    from app.game.models import InputState

    room, _, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "fix_unit_tests")
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    room.drain_pending_mini_game_events()
    dev = room.players[dev_id]
    start_x = dev.x
    room.apply_input(dev_id, InputState(right=True))
    room.tick(0.1)
    assert dev.x == start_x  # frozen


def test_apply_input_to_inactive_session_raises():
    room, _, dev_id = _room_with_roles()
    with pytest.raises(GameRoomError) as exc:
        room.apply_mini_game_input(dev_id, "click", {"testId": "t0"})
    assert exc.value.code == "NO_ACTIVE_MINI_GAME"


def test_reset_for_new_round_clears_mini_games_and_pending_events():
    room, _, dev_id = _room_with_roles()
    _place_at_task(room, dev_id, "fix_unit_tests")
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    room._finish_round("release_team", "test")
    room.reset_for_new_round()
    assert room.active_mini_games == {}
    assert room.pending_mini_game_events == []
