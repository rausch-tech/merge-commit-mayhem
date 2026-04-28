"""Tests for app/game/bots/manager.py — BotManager lifecycle + tick.

Covers add/remove, name allocation, lobby-only join, the tick loop's
work-then-complete cycle, and the per-task no-stampede heuristic. We
seed the BotManager's RNG so picks are deterministic.
"""

from __future__ import annotations

import pytest

from app.game.bots.manager import BOT_NAMES
from app.game.game_room import GameRoom, GameRoomError
from app.game.tasks import TASK_RESPAWN_COOLDOWN

# --- helpers ---------------------------------------------------------------


def _start_room_with_humans(human_count: int = 4) -> GameRoom:
    """Build a room with `human_count` humans + start a round.

    Bots are added BEFORE start so role assignment treats them as real
    players (which is what we want — the assignment doesn't know about
    bots and shouldn't have to).
    """
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    for i in range(human_count - 1):
        room.add_player(f"Human{i}")
    return room


# --- lifecycle (add / remove / name pick) ----------------------------------


def test_add_bot_creates_player_with_is_bot_true() -> None:
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    bot = room._bots.add_bot()
    assert bot.is_bot is True
    assert bot.id in room.players
    assert room._bots.is_bot(bot.id) is True


def test_add_bot_picks_next_curated_name() -> None:
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    a = room._bots.add_bot()
    b = room._bots.add_bot()
    assert a.name == BOT_NAMES[0]
    assert b.name == BOT_NAMES[1]


def test_add_bot_falls_back_to_uuid_when_curated_exhausted() -> None:
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    # Pre-claim every curated name.
    for n in BOT_NAMES:
        room.add_player(n)
    bot = room._bots.add_bot()
    assert bot.name.startswith("Bot-")
    assert bot.name not in BOT_NAMES


def test_add_bot_rejected_outside_lobby() -> None:
    room = _start_room_with_humans()
    room.start(next(iter(room.players)), demo=True)
    with pytest.raises(GameRoomError) as exc:
        room._bots.add_bot()
    assert exc.value.code == "WRONG_PHASE"


def test_remove_bot_drops_player_and_state() -> None:
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    bot = room._bots.add_bot()
    room._bots.remove_bot(bot.id)
    assert bot.id not in room.players
    assert room._bots.is_bot(bot.id) is False


def test_remove_bot_unknown_id_is_noop() -> None:
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    room._bots.remove_bot("does-not-exist")  # must not raise


def test_is_bot_distinguishes_humans_from_bots() -> None:
    room = GameRoom(code="ABCD")
    host = room.add_player("Host")
    bot = room._bots.add_bot()
    assert room._bots.is_bot(host.id) is False
    assert room._bots.is_bot(bot.id) is True


def test_player_serialized_carries_is_bot_flag() -> None:
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    bot = room._bots.add_bot()
    serialized = room._all_players_serialized()
    by_id = {p["id"]: p for p in serialized}
    assert by_id[bot.id]["isBot"] is True


# --- tick: skips when not playing ------------------------------------------


def test_tick_noop_in_lobby() -> None:
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    bot = room._bots.add_bot()
    room._bots.tick(0.1)
    # No intent should be picked while in LOBBY.
    state = room._bots.state_for(bot.id)
    assert state is not None
    assert state.target_task_id is None


def test_tick_skips_dead_bots() -> None:
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)
    bot_id = next(b for b in room._bots.bot_ids())
    room.players[bot_id].is_alive = False
    room._bots.tick(0.1)
    # Dead bot must have a cleared input_state.
    assert room.players[bot_id].input_state.up is False
    assert room.players[bot_id].input_state.right is False


# --- pick_next_target -------------------------------------------------------


def test_pick_next_target_assigns_intent_with_path() -> None:
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)
    room._bots._rng.seed(42)  # deterministic pick

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None
    room._bots.pick_next_target(bot, state)
    assert state.target_task_id is not None


def test_pick_next_target_no_op_when_no_tasks_available() -> None:
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)

    # Mark every task as on cooldown — nothing for the bot to do.
    for t in room.tasks.values():
        t.status = "cooldown"
        t.cooldown_remaining = TASK_RESPAWN_COOLDOWN

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None
    room._bots.pick_next_target(bot, state)
    assert state.target_task_id is None


def test_two_bots_dont_stampede_same_task() -> None:
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)
    room._bots._rng.seed(1)

    bot_ids = room._bots.bot_ids()
    for bid in bot_ids:
        bot = room.players[bid]
        state = room._bots.state_for(bid)
        assert state is not None
        room._bots.pick_next_target(bot, state)

    targets = [room._bots.state_for(b).target_task_id for b in bot_ids]  # type: ignore[union-attr]
    assert targets[0] != targets[1] or targets[0] is None or targets[1] is None


# --- work cycle: hold timer → auto-complete --------------------------------


def test_bot_at_target_starts_work_timer() -> None:
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    # Snap the bot onto a known task.
    target_task = next(iter(room.tasks.values()))
    bot.x = target_task.x
    bot.y = target_task.y
    state.target_task_id = target_task.definition.id
    state.path = []

    room._bots._tick_one(bot, state, dt=0.05)
    assert state.work_remaining_sec > 0
    # Standing still while working — input cleared.
    assert bot.input_state.up is False
    assert bot.input_state.right is False


def test_bot_auto_completes_task_after_work_duration() -> None:
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    task = next(iter(room.tasks.values()))
    bot.x = task.x
    bot.y = task.y
    state.target_task_id = task.definition.id
    state.path = []
    state.work_remaining_sec = 0.5

    initial_completed = room.completed_tasks_by_player.get(bot_id, 0)
    # Two ticks: first burns the timer, second pushes it negative → auto-complete.
    room._bots._tick_one(bot, state, dt=0.6)

    assert state.target_task_id is None
    assert state.work_remaining_sec == 0.0
    assert task.status == "cooldown"
    assert task.cooldown_remaining == pytest.approx(TASK_RESPAWN_COOLDOWN)
    assert room.completed_tasks_by_player[bot_id] == initial_completed + 1


def test_bot_drops_intent_when_target_goes_on_cooldown() -> None:
    """If a human finishes the bot's target while the bot is en-route,
    the bot must drop intent on next `_maybe_start_work`."""
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    task = next(iter(room.tasks.values()))
    bot.x = task.x
    bot.y = task.y
    state.target_task_id = task.definition.id
    state.path = []
    task.status = "cooldown"
    task.cooldown_remaining = TASK_RESPAWN_COOLDOWN

    room._bots._maybe_start_work(bot, state)
    assert state.target_task_id is None
    assert state.work_remaining_sec == 0.0


def test_bot_steers_toward_waypoint() -> None:
    """When the bot has a path, its WASD input should point at the next
    waypoint within an axis-threshold."""
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    bot.x = 100.0
    bot.y = 100.0
    state.target_task_id = "anything"
    state.path = [(500.0, 100.0)]

    room._bots._step_along_path(bot, state)
    assert bot.input_state.right is True
    assert bot.input_state.left is False
    # Same y → up/down stay False.
    assert bot.input_state.up is False
    assert bot.input_state.down is False


def test_bot_advances_waypoint_when_within_reach() -> None:
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    bot.x = 100.0
    bot.y = 100.0
    # First waypoint already within reach — should be popped, second taken.
    state.target_task_id = "anything"
    state.path = [(100.0, 100.0), (500.0, 100.0)]
    room._bots._step_along_path(bot, state)
    assert state.path == [(500.0, 100.0)]


# --- stuck-detection (regression for the desk-blocked-spawn bug) -----------


def test_bot_abandons_intent_when_stuck_against_wall() -> None:
    """If the bot wants to move but isn't actually moving (movement
    refused by collision), it must drop its target after the timeout
    so pick_next_target can try a different task. Regression for the
    spawn-on-blocked-desk bug observed live on default-office."""
    from app.game.bots.manager import _BOT_STUCK_TIMEOUT_SEC
    from app.game.models import InputState

    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    # Force the bot into the "stuck against something" shape: input set,
    # path empty, target set, but pre→post position unchanged.
    state.target_task_id = "fix_unit_tests"
    state.path = []
    bot.input_state = InputState(left=True)
    pre_x, pre_y = bot.x, bot.y

    # Push past the timeout in one synthetic call.
    room._bots._check_stuck(bot, state, dt=_BOT_STUCK_TIMEOUT_SEC + 0.1, pre_x=pre_x, pre_y=pre_y)

    assert state.target_task_id is None
    assert "fix_unit_tests" in state.recently_failed_tasks


def test_bot_stuck_counter_resets_when_it_moves() -> None:
    from app.game.models import InputState

    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    state.target_task_id = "x"
    state.stuck_seconds = 1.2  # close to limit
    bot.input_state = InputState(left=True)
    # Pretend the bot moved 50px.
    pre_x, pre_y = bot.x + 50.0, bot.y
    room._bots._check_stuck(bot, state, dt=0.5, pre_x=pre_x, pre_y=pre_y)

    assert state.stuck_seconds == 0.0
    assert state.target_task_id == "x"


def test_blacklisted_task_skipped_by_heuristic_picker() -> None:
    """Once a task is in `recently_failed_tasks`, the heuristic must
    pick a different one — even if it's the only available task we
    relax the filter so the bot never goes idle."""
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)
    room._bots._rng.seed(0)

    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    # Mark all tasks except one as blacklisted; bot must pick the leftover.
    only_id = next(iter(room.tasks))
    for t in room.tasks.values():
        if t.definition.id != only_id:
            state.recently_failed_tasks[t.definition.id] = 5.0

    room._bots.pick_next_target(bot, state)
    assert state.target_task_id == only_id


def test_blacklist_decays_via_tick() -> None:
    """Per-tick decay must drain stale blacklist entries."""
    room = _start_room_with_humans(4)
    room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)

    bot_id = next(iter(room._bots.bot_ids()))
    state = room._bots.state_for(bot_id)
    assert state is not None
    state.recently_failed_tasks["t1"] = 0.4
    state.recently_failed_tasks["t2"] = 5.0

    room._bots.tick(dt=0.5)

    assert "t1" not in state.recently_failed_tasks
    assert state.recently_failed_tasks["t2"] == pytest.approx(4.5)


# --- map invalidation ------------------------------------------------------


def test_invalidate_graph_clears_cache() -> None:
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    # Trigger graph build via internal path resolution.
    room._bots._compute_path((10.0, 10.0), (20.0, 20.0))
    assert room._bots._graph is not None
    room._bots.invalidate_graph()
    assert room._bots._graph is None
