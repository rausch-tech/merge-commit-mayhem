import random

import pytest

from app.game.game_room import GameRoom, GameRoomError
from app.game.models import InputState
from app.game.tasks import TASK_INTERACTION_RADIUS, TASK_RESPAWN_COOLDOWN
from tests.conftest import make_task_hold_e


def _room_with_players(n: int) -> tuple[GameRoom, list[str]]:
    """Spawn a started GameRoom with at least MIN_PLAYERS_TO_START players.

    Tier 1.5 raised MIN_PLAYERS_TO_START to 4. Callers historically may pass
    n=2 just to grab the first two ids; we silently bump to 4. Tier 2.1's
    chaos-parity rule (chaos_alive >= release_alive) is satisfied with
    4 players (1 chaos + 3 release).

    ``review_pr`` is forced into hold-E mode so the existing tests that
    cover hold-E mechanics keep working after Tier 3.7 wired ``review_pr``
    to the diff_review mini-game.
    """
    if n < 4:
        n = 4
    room = GameRoom(code="ABCD")
    ids = []
    for i in range(n):
        p = room.add_player(f"p{i}")
        ids.append(p.id)
    host_id = ids[0]
    room.start(requesting_player_id=host_id, rng=random.Random(0))
    make_task_hold_e(room, "review_pr")
    return room, ids


def _place_on(room: GameRoom, player_id: str, x: float, y: float) -> None:
    room.players[player_id].x = x
    room.players[player_id].y = y


# --- initialization --------------------------------------------------------


def test_tasks_initialized_on_start():
    room, ids = _room_with_players(2)
    assert "review_pr" in room.tasks
    for task in room.tasks.values():
        assert task.status == "available"
        assert task.cooldown_remaining == 0.0
        assert task.per_player_progress == {}


def test_tasks_cleared_before_start():
    room = GameRoom(code="ABCD")
    assert room.tasks == {}


# --- hold start: guards ----------------------------------------------------


def test_cannot_start_task_outside_playing_phase():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.apply_task_hold_start("any", "review_pr")
    assert exc.value.code == "WRONG_PHASE"


def test_cannot_start_unknown_task():
    room, ids = _room_with_players(2)
    with pytest.raises(GameRoomError) as exc:
        room.apply_task_hold_start(ids[0], "no_such_task")
    assert exc.value.code == "UNKNOWN_TASK"


def test_cannot_start_task_when_too_far():
    room, ids = _room_with_players(2)
    pid = ids[0]
    tx, ty = room.task_position("review_pr")
    # Place player clearly outside radius.
    _place_on(room, pid, tx + TASK_INTERACTION_RADIUS + 5, ty)
    with pytest.raises(GameRoomError) as exc:
        room.apply_task_hold_start(pid, "review_pr")
    assert exc.value.code == "TASK_TOO_FAR"


def test_start_task_in_range_marks_in_progress():
    room, ids = _room_with_players(2)
    pid = ids[0]
    tx, ty = room.task_position("review_pr")
    _place_on(room, pid, tx, ty)
    room.apply_task_hold_start(pid, "review_pr")
    assert room.tasks["review_pr"].status == "in_progress"
    assert pid in room.tasks["review_pr"].per_player_progress


# --- hold stop -------------------------------------------------------------


def test_stop_removes_progress_and_flips_back_to_available():
    room, ids = _room_with_players(2)
    pid = ids[0]
    tx, ty = room.task_position("review_pr")
    _place_on(room, pid, tx, ty)
    room.apply_task_hold_start(pid, "review_pr")
    room.apply_task_hold_stop(pid, "review_pr")
    assert room.tasks["review_pr"].status == "available"
    assert room.tasks["review_pr"].per_player_progress == {}


def test_stop_on_unknown_task_is_noop():
    room, ids = _room_with_players(2)
    room.apply_task_hold_stop(ids[0], "nope")  # must not raise


# --- tick progress + completion -------------------------------------------


def test_progress_accumulates_each_tick():
    """Tier 3.5: progress per tick is dt * role-speed-multiplier (1.0 for
    neutral / role-with-no-strength-on-this-task; up to 1.35 for matching
    strength categories). Asserting strictly >0 + monotonic."""
    room, ids = _room_with_players(2)
    pid = ids[0]
    # Force a known role so the multiplier is deterministic.
    room.players[pid].role = "scrum_master"  # weak in code → x0.75
    tx, ty = room.task_position("review_pr")
    _place_on(room, pid, tx, ty)
    room.apply_task_hold_start(pid, "review_pr")
    room.tick(0.1)
    p1 = room.tasks["review_pr"].per_player_progress[pid]
    assert p1 > 0
    room.tick(0.1)
    p2 = room.tasks["review_pr"].per_player_progress[pid]
    assert p2 > p1


def test_task_completion_applies_reward_and_enters_cooldown():
    room, ids = _room_with_players(2)
    pid = ids[0]
    tx, ty = room.task_position("review_pr")
    _place_on(room, pid, tx, ty)
    # Freeze player by zeroing their input so movement doesn't push them out of radius.
    room.apply_input(pid, InputState())
    room.apply_task_hold_start(pid, "review_pr")
    # Tick past required_seconds.
    for _ in range(60):  # 60 ticks of 0.1s = 6s > required 5s
        room.tick(0.1)
    task = room.tasks["review_pr"]
    assert task.status == "cooldown"
    assert task.cooldown_remaining > 0
    assert task.per_player_progress == {}
    assert room.release_progress == 8  # review_pr reward
    assert room.completed_tasks_by_player[pid] == 1


def test_task_cooldown_returns_to_available():
    room, ids = _room_with_players(2)
    pid = ids[0]
    tx, ty = room.task_position("review_pr")
    _place_on(room, pid, tx, ty)
    room.apply_input(pid, InputState())
    room.apply_task_hold_start(pid, "review_pr")
    for _ in range(60):
        room.tick(0.1)  # completes

    # Tick past the cooldown.
    ticks_needed = int(TASK_RESPAWN_COOLDOWN / 0.1) + 2
    for _ in range(ticks_needed):
        room.tick(0.1)
    assert room.tasks["review_pr"].status == "available"
    assert room.tasks["review_pr"].cooldown_remaining == 0.0


def test_player_leaving_radius_drops_progress():
    room, ids = _room_with_players(2)
    pid = ids[0]
    tx, ty = room.task_position("review_pr")
    _place_on(room, pid, tx, ty)
    room.apply_input(pid, InputState())
    room.apply_task_hold_start(pid, "review_pr")
    room.tick(0.1)
    # Yank the player away; next tick the progress should be dropped.
    _place_on(room, pid, tx + TASK_INTERACTION_RADIUS + 20, ty)
    room.tick(0.1)
    assert pid not in room.tasks["review_pr"].per_player_progress
    # No other holder -> status back to available.
    assert room.tasks["review_pr"].status == "available"


def test_refill_coffee_sets_coffee_to_100(monkeypatch):
    """refill_coffee runs through the coffee_pour mini-game (Tier 3.4). We
    fake the monotonic clock so the test can land inside the sweet spot."""
    from app.game.minigames import coffee_pour

    fake = {"t": 1000.0}
    monkeypatch.setattr(coffee_pour, "_now", lambda: fake["t"])

    room, ids = _room_with_players(2)
    pid = ids[0]
    tx, ty = room.task_position("refill_coffee")
    _place_on(room, pid, tx, ty)
    room.apply_input(pid, InputState())
    room.coffee_level = 0
    room.apply_task_hold_start(pid, "refill_coffee")
    # Advance into the sweet spot then stop.
    fake["t"] += coffee_pour.CYCLE_SECONDS * 0.85
    room.apply_mini_game_input(pid, "stop", {})
    assert room.coffee_level == 100


def test_repair_deployment_raises_pipeline_clamped_at_100():
    """repair_deployment runs through the cable_pairing mini-game (Tier 3.3).
    Wire every source to its colour-twin destination to complete it."""
    room, ids = _room_with_players(2)
    pid = ids[0]
    tx, ty = room.task_position("repair_deployment")
    _place_on(room, pid, tx, ty)
    room.apply_input(pid, InputState())
    room.pipeline_stability = 92  # +15 would overshoot to 107
    room.apply_task_hold_start(pid, "repair_deployment")
    state = room.active_mini_games[pid].state
    for src in state["sources"]:
        dst = next(d for d in state["destinations"] if d["color"] == src["color"])
        room.apply_mini_game_input(
            pid, "connect", {"sourceId": src["id"], "destinationId": dst["id"]}
        )
    assert room.pipeline_stability == 100


# --- parallel workers -----------------------------------------------------


def test_parallel_workers_first_finisher_wins():
    room, ids = _room_with_players(2)
    a, b = ids[0], ids[1]
    tx, ty = room.task_position("review_pr")
    _place_on(room, a, tx, ty)
    _place_on(room, b, tx + 5, ty)
    room.apply_input(a, InputState())
    room.apply_input(b, InputState())
    room.apply_task_hold_start(a, "review_pr")
    # A has a head start of 2s of solo progress.
    for _ in range(20):
        room.tick(0.1)
    room.apply_task_hold_start(b, "review_pr")
    # Tick until A completes.
    for _ in range(60):
        room.tick(0.1)
    # Reward only counts ONCE (not doubled).
    assert room.release_progress == 8
    # Only A's counter incremented (A started first and finished first).
    assert room.completed_tasks_by_player[a] == 1
    assert room.completed_tasks_by_player[b] == 0


# --- cooldown prevents re-trigger -----------------------------------------


def test_cannot_start_task_during_cooldown():
    room, ids = _room_with_players(2)
    pid = ids[0]
    tx, ty = room.task_position("review_pr")
    _place_on(room, pid, tx, ty)
    room.apply_input(pid, InputState())
    room.apply_task_hold_start(pid, "review_pr")
    for _ in range(60):
        room.tick(0.1)
    assert room.tasks["review_pr"].status == "cooldown"
    with pytest.raises(GameRoomError) as exc:
        room.apply_task_hold_start(pid, "review_pr")
    assert exc.value.code == "TASK_ON_COOLDOWN"


# --- reset clears tasks ---------------------------------------------------


def test_reset_clears_tasks():
    room, ids = _room_with_players(2)
    room.reset_for_new_round()
    assert room.tasks == {}
