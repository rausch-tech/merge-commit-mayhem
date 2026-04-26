"""Tier 3.2 — TestSuiteRepair plugin tests."""

import pytest

from app.game.minigames.base import MiniGamePluginError
from app.game.minigames.test_suite_repair import NUM_TESTS, TestSuiteRepair


def test_init_state_is_deterministic_per_seed():
    plugin = TestSuiteRepair()
    a = plugin.init_state(seed=42)
    b = plugin.init_state(seed=42)
    assert [t["label"] for t in a["tests"]] == [t["label"] for t in b["tests"]]
    assert [t["order"] for t in a["tests"]] == [t["order"] for t in b["tests"]]


def test_init_state_assigns_orders_one_to_n():
    plugin = TestSuiteRepair()
    state = plugin.init_state(seed=1)
    assert sorted(t["order"] for t in state["tests"]) == list(range(1, NUM_TESTS + 1))
    assert state["next_order"] == 1
    assert all(t["status"] == "broken" for t in state["tests"])


def test_correct_click_advances_progress():
    plugin = TestSuiteRepair()
    state = plugin.init_state(seed=1)
    target = next(t for t in state["tests"] if t["order"] == 1)
    state = plugin.handle_input(state, "click", {"testId": target["id"]})
    assert state["next_order"] == 2
    assert next(t for t in state["tests"] if t["id"] == target["id"])["status"] == "fixed"


def test_wrong_click_resets_softly():
    plugin = TestSuiteRepair()
    state = plugin.init_state(seed=1)
    correct = next(t for t in state["tests"] if t["order"] == 1)
    state = plugin.handle_input(state, "click", {"testId": correct["id"]})
    # Now click order=5 instead of order=2.
    wrong = next(t for t in state["tests"] if t["order"] == 5)
    state = plugin.handle_input(state, "click", {"testId": wrong["id"]})
    assert state["next_order"] == 1
    assert all(t["status"] == "broken" for t in state["tests"])


def test_completing_all_in_order_marks_complete():
    plugin = TestSuiteRepair()
    state = plugin.init_state(seed=7)
    for i in range(1, NUM_TESTS + 1):
        target = next(t for t in state["tests"] if t["order"] == i)
        state = plugin.handle_input(state, "click", {"testId": target["id"]})
    assert plugin.is_complete(state) is True


def test_clicking_already_fixed_test_is_noop():
    plugin = TestSuiteRepair()
    state = plugin.init_state(seed=1)
    target = next(t for t in state["tests"] if t["order"] == 1)
    state = plugin.handle_input(state, "click", {"testId": target["id"]})
    state2 = plugin.handle_input(state, "click", {"testId": target["id"]})
    assert state2["next_order"] == 2  # unchanged, no soft-reset
    assert next(t for t in state2["tests"] if t["id"] == target["id"])["status"] == "fixed"


def test_unknown_action_raises_plugin_error():
    plugin = TestSuiteRepair()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "drag", {"testId": "t0"})
    assert exc.value.code == "UNKNOWN_ACTION"


def test_missing_test_id_raises_plugin_error():
    plugin = TestSuiteRepair()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "click", {})
    assert exc.value.code == "INVALID_PARAMS"


def test_unknown_test_id_raises_plugin_error():
    plugin = TestSuiteRepair()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "click", {"testId": "does-not-exist"})
    assert exc.value.code == "UNKNOWN_TEST"


def test_public_view_only_exposes_safe_fields():
    plugin = TestSuiteRepair()
    state = plugin.init_state(seed=1)
    view = plugin.public_view(state)
    assert set(view.keys()) == {"tests", "nextOrder", "totalTests"}
    for t in view["tests"]:
        assert set(t.keys()) == {"id", "label", "order", "status"}


def test_completing_via_room_grants_reward_and_cooldown():
    """End-to-end: route through GameRoom so the framework wiring also runs."""
    import random

    from app.game.game_room import GameRoom

    room = GameRoom(code="ENDT")
    for n in ("p0", "p1", "p2", "p3"):
        room.add_player(n)
    host = next(iter(room.players))
    room.start(requesting_player_id=host, rng=random.Random(0))
    dev_id = next(p.id for p in room.players.values() if p.team == "release_team")
    tx, ty = room._task_position["fix_unit_tests"]
    room.players[dev_id].x = tx
    room.players[dev_id].y = ty

    pre_release = room.release_progress
    room.apply_task_hold_start(dev_id, "fix_unit_tests")
    state = room.active_mini_games[dev_id].state
    for i in range(1, NUM_TESTS + 1):
        target = next(t for t in state["tests"] if t["order"] == i)
        room.apply_mini_game_input(dev_id, "click", {"testId": target["id"]})
    assert dev_id not in room.active_mini_games  # session closed
    assert room.tasks["fix_unit_tests"].status == "cooldown"
    assert room.release_progress > pre_release
    assert room.completed_tasks_by_player[dev_id] == 1
