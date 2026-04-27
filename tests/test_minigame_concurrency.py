"""Mini-game concurrency invariants.

Existing test_minigame_framework.py + test_tasks.py cover the happy path
(start, input, complete, cancel) and the cooldown contract. These tests
pin the lifecycle invariants that get exposed when sessions interleave
across phases or across multiple players: cancel-all during meeting
transition, simultaneous active sessions for different players, and
completion exactly-once.
"""

from __future__ import annotations

import random

import pytest

from app.game.game_room import GameRoom
from app.game.runtime import GameRoomError


def _started(player_count: int = 4) -> tuple[GameRoom, list[str]]:
    room = GameRoom(code="ABCD")
    host = room.add_player("host")
    ids = [host.id]
    for i in range(player_count - 1):
        ids.append(room.add_player(f"p{i}").id)
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    return room, ids


def _start_mini_game_for(room: GameRoom, pid: str, task_id: str = "fix_unit_tests") -> None:
    """Snap player onto the task anchor and trigger the hold-start that opens
    the mini-game session."""
    task = room.tasks[task_id]
    p = room.players[pid]
    p.x = task.x
    p.y = task.y
    room.apply_task_hold_start(pid, task_id)


# --- multiple sessions across players --------------------------------------


def test_two_players_can_have_simultaneous_mini_games():
    """Different players on different mini-game tasks must each get their
    own session. The active_mini_games dict keys by player_id — no cross-
    pollination."""
    room, ids = _started(player_count=4)
    _start_mini_game_for(room, ids[0], task_id="fix_unit_tests")
    _start_mini_game_for(room, ids[1], task_id="repair_deployment")
    assert ids[0] in room.active_mini_games
    assert ids[1] in room.active_mini_games
    assert room.active_mini_games[ids[0]].task_id == "fix_unit_tests"
    assert room.active_mini_games[ids[1]].task_id == "repair_deployment"


def test_starting_second_mini_game_for_same_player_raises():
    """A player already inside a session cannot open a second one even if
    they reach a different task. The framework gates on
    MINI_GAME_ALREADY_ACTIVE."""
    room, ids = _started(player_count=4)
    _start_mini_game_for(room, ids[0], task_id="fix_unit_tests")
    # Try to start another at a different task without ending the first.
    other_task = room.tasks["repair_deployment"]
    room.players[ids[0]].x = other_task.x
    room.players[ids[0]].y = other_task.y
    with pytest.raises(GameRoomError) as exc:
        room.apply_task_hold_start(ids[0], "repair_deployment")
    assert exc.value.code == "MINI_GAME_ALREADY_ACTIVE"


# --- cancel-all on meeting transition --------------------------------------


def test_meeting_cancels_every_open_mini_game_session():
    """Pinning the existing behaviour: when a meeting starts, every active
    mini-game across all players is dropped. Modals snap shut on the
    client; tests assert the server-side dict is empty."""
    room, ids = _started(player_count=4)
    _start_mini_game_for(room, ids[0], task_id="fix_unit_tests")
    _start_mini_game_for(room, ids[1], task_id="repair_deployment")
    assert len(room.active_mini_games) == 2

    # Trigger an emergency meeting from a war-room player.
    host_id = ids[0]
    x_min, y_min, x_max, y_max = room._war_room_bounds
    room.players[host_id].x = (x_min + x_max) / 2
    room.players[host_id].y = (y_min + y_max) / 2
    # First player needs ability to call meeting.
    room.players_with_meeting_left[host_id] = True
    room.call_emergency_meeting(host_id)

    assert room.active_mini_games == {}


# --- completion happens exactly once ---------------------------------------


def test_completion_via_apply_input_triggers_reward_exactly_once():
    """Once the plugin reports is_complete, the reward path runs once, the
    task moves to cooldown, and follow-up inputs cannot re-trigger the
    reward. Pins the contract that makes mini-games cheat-resistant."""
    room, ids = _started(player_count=4)
    pid = ids[0]
    _start_mini_game_for(room, pid, task_id="fix_unit_tests")

    # Drive the test_suite_repair plugin to completion: click each test in
    # numerical-order. The plugin's public_view exposes per-test status and
    # the next required ``order``.
    from app.game.minigames.registry import get_plugin

    plugin = get_plugin("test_suite_repair")
    completed_before = room.completed_tasks_by_player.get(pid, 0)
    safety = 0
    while pid in room.active_mini_games:
        state = room.active_mini_games[pid].state
        view = plugin.public_view(state)
        next_order = view["nextOrder"]
        target = next(t for t in view["tests"] if t["order"] == next_order)
        room.apply_mini_game_input(pid, "click", {"testId": target["id"]})
        safety += 1
        assert safety < 50  # plugin has 5 tests; bound the loop

    # Session ended exactly once → counter incremented exactly once.
    assert room.completed_tasks_by_player.get(pid, 0) == completed_before + 1
    # Task is in cooldown (not available, not in_progress).
    assert room.tasks["fix_unit_tests"].status == "cooldown"

    # Follow-up inputs do nothing — there's no session to address.
    with pytest.raises(GameRoomError) as exc:
        room.apply_mini_game_input(pid, "click", {"testId": "t0"})
    assert exc.value.code == "NO_ACTIVE_MINI_GAME"
    # Counter unchanged.
    assert room.completed_tasks_by_player.get(pid, 0) == completed_before + 1


def test_cancel_does_not_apply_reward():
    """Cancelling a mini-game (e.g. via meeting transition or take-down)
    must NOT credit the player. Otherwise chaos could grief release-team
    scoring by triggering meetings while teammates work."""
    room, ids = _started(player_count=4)
    pid = ids[0]
    _start_mini_game_for(room, pid, task_id="fix_unit_tests")
    completed_before = room.completed_tasks_by_player.get(pid, 0)

    room._cancel_mini_game(pid, "cancelled")
    assert room.completed_tasks_by_player.get(pid, 0) == completed_before
    assert room.tasks["fix_unit_tests"].status == "available"


# --- pending events queue ---------------------------------------------------


def test_pending_events_queue_drains_to_empty():
    """drain_pending_mini_game_events returns the queue and zeroes it.
    Two consecutive drains: first non-empty, second empty. The WS layer
    relies on this for at-most-once delivery per tick."""
    room, ids = _started(player_count=4)
    _start_mini_game_for(room, ids[0], task_id="fix_unit_tests")
    first = room.drain_pending_mini_game_events()
    assert first  # 'started' event
    second = room.drain_pending_mini_game_events()
    assert second == []
