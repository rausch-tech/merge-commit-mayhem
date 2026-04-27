"""Tier 3.7 — StabilityBalance plugin tests (calm_legacy_service)."""

import pytest

from app.game.minigames.base import MiniGamePluginError
from app.game.minigames.stability_balance import (
    CROSS_DELTA,
    GREEN_HIGH,
    GREEN_LOW,
    PRIMARY_DELTA,
    SCALE_MAX,
    SCALE_MIN,
    StabilityBalance,
)


def test_init_state_is_deterministic_per_seed():
    plugin = StabilityBalance()
    a = plugin.init_state(seed=11)
    b = plugin.init_state(seed=11)
    assert a == b


def test_init_state_starts_outside_green_zone():
    """Every preset has at least one metric outside the green zone, so the
    player always has work to do — otherwise the mini-game would auto-
    complete on first tick."""
    plugin = StabilityBalance()
    for seed in range(5):
        state = plugin.init_state(seed=seed)
        in_green = all(GREEN_LOW <= state[m] <= GREEN_HIGH for m in ("cpu", "mem", "queue"))
        assert not in_green, f"Seed {seed} starts already complete: {state}"


def test_adjust_up_increases_target_and_decreases_next():
    """+cpu lifts cpu by PRIMARY_DELTA and pushes mem down by CROSS_DELTA
    (rotation: cpu→mem→queue→cpu)."""
    plugin = StabilityBalance()
    state = {"cpu": 50, "mem": 50, "queue": 50}
    state = plugin.handle_input(state, "adjust", {"metric": "cpu", "direction": "up"})
    assert state["cpu"] == 50 + PRIMARY_DELTA
    assert state["mem"] == 50 - CROSS_DELTA
    assert state["queue"] == 50  # untouched


def test_adjust_down_works_in_reverse():
    plugin = StabilityBalance()
    state = {"cpu": 50, "mem": 50, "queue": 50}
    state = plugin.handle_input(state, "adjust", {"metric": "queue", "direction": "down"})
    assert state["queue"] == 50 - PRIMARY_DELTA
    assert state["cpu"] == 50 + CROSS_DELTA  # rotation: queue→cpu


def test_adjust_clamps_at_zero():
    plugin = StabilityBalance()
    state = {"cpu": 5, "mem": 50, "queue": 50}
    state = plugin.handle_input(state, "adjust", {"metric": "cpu", "direction": "down"})
    assert state["cpu"] == SCALE_MIN
    # Cross-effect still applies even when target hit the floor.
    assert state["mem"] == 50 + CROSS_DELTA


def test_adjust_clamps_at_hundred():
    plugin = StabilityBalance()
    state = {"cpu": 95, "mem": 50, "queue": 50}
    state = plugin.handle_input(state, "adjust", {"metric": "cpu", "direction": "up"})
    assert state["cpu"] == SCALE_MAX


def test_complete_when_all_three_in_green_band():
    plugin = StabilityBalance()
    state = {"cpu": 45, "mem": 50, "queue": 55}
    assert plugin.is_complete(state) is True


def test_not_complete_when_any_metric_red():
    plugin = StabilityBalance()
    state = {"cpu": 30, "mem": 50, "queue": 50}
    assert plugin.is_complete(state) is False


def test_default_first_preset_is_solvable_in_few_clicks():
    """Trace the canonical preset (85, 20, 70) to a green state via the
    rotation rules. Sven's playtest can confirm the difficulty feels
    right — this test just guards the math."""
    plugin = StabilityBalance()
    state = {"cpu": 85, "mem": 20, "queue": 70}
    # +mem twice: mem 20→40, queue 70→60 (cross). cpu untouched.
    state = plugin.handle_input(state, "adjust", {"metric": "mem", "direction": "up"})
    state = plugin.handle_input(state, "adjust", {"metric": "mem", "direction": "up"})
    assert state["mem"] == 40
    assert state["queue"] == 60
    assert state["cpu"] == 85
    # -cpu three times: cpu 85→55, mem 40→55 (cross +5 each).
    for _ in range(3):
        state = plugin.handle_input(state, "adjust", {"metric": "cpu", "direction": "down"})
    assert state["cpu"] == 55
    assert state["mem"] == 55
    assert state["queue"] == 60
    assert plugin.is_complete(state) is True


def test_unknown_action_raises():
    plugin = StabilityBalance()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "click", {"metric": "cpu", "direction": "up"})
    assert exc.value.code == "UNKNOWN_ACTION"


def test_invalid_metric_raises():
    plugin = StabilityBalance()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "adjust", {"metric": "disk", "direction": "up"})
    assert exc.value.code == "INVALID_PARAMS"


def test_invalid_direction_raises():
    plugin = StabilityBalance()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "adjust", {"metric": "cpu", "direction": "sideways"})
    assert exc.value.code == "INVALID_PARAMS"


def test_public_view_includes_green_band_thresholds():
    """Client UI needs to know where the green band is so it can colour
    the bars. Server is the source of truth for the threshold."""
    plugin = StabilityBalance()
    state = plugin.init_state(seed=1)
    view = plugin.public_view(state)
    assert view["greenLow"] == GREEN_LOW
    assert view["greenHigh"] == GREEN_HIGH
    assert "cpu" in view and "mem" in view and "queue" in view
