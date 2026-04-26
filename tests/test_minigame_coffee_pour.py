"""Tier 3.4 — CoffeePour plugin tests."""

import pytest

from app.game.minigames import coffee_pour
from app.game.minigames.base import MiniGamePluginError
from app.game.minigames.coffee_pour import (
    CYCLE_SECONDS,
    SWEET_MAX,
    SWEET_MIN,
    CoffeePour,
)


@pytest.fixture
def fake_clock(monkeypatch):
    """Fake monotonic clock — tests advance ``state["t"]`` deliberately."""
    state = {"t": 1000.0}

    def now() -> float:
        return state["t"]

    monkeypatch.setattr(coffee_pour, "_now", now)
    return state


def test_stop_inside_sweet_spot_completes(fake_clock):
    plugin = CoffeePour()
    state = plugin.init_state(seed=0)
    # Advance into the middle of the sweet spot.
    target_fill = (SWEET_MIN + SWEET_MAX) / 2
    fake_clock["t"] += CYCLE_SECONDS * target_fill
    state = plugin.handle_input(state, "stop", {})
    assert state["complete"] is True
    assert plugin.is_complete(state) is True
    assert state["last_attempt_fill"] == pytest.approx(target_fill, abs=1e-3)


def test_stop_too_early_softresets_and_does_not_complete(fake_clock):
    plugin = CoffeePour()
    state = plugin.init_state(seed=0)
    # Advance only halfway — below sweet spot.
    fake_clock["t"] += CYCLE_SECONDS * 0.30
    state = plugin.handle_input(state, "stop", {})
    assert state["complete"] is False
    assert plugin.is_complete(state) is False
    # Cycle was reset — fresh elapsed should be ~0 immediately after.
    assert plugin.public_view(state)["elapsed"] == pytest.approx(0.0, abs=1e-6)
    assert state["attempts"] == 1


def test_stop_after_overflow_treats_fill_modulo(fake_clock):
    """If the player ignores the first cycle and stops in the second cycle's
    sweet spot, it should still count as a hit."""
    plugin = CoffeePour()
    state = plugin.init_state(seed=0)
    # 1.85 cycles = 0.85 fill in cycle #2 -> inside sweet spot
    fake_clock["t"] += CYCLE_SECONDS * 1.85
    state = plugin.handle_input(state, "stop", {})
    assert state["complete"] is True


def test_unknown_action_raises():
    plugin = CoffeePour()
    state = plugin.init_state(seed=0)
    with pytest.raises(MiniGamePluginError):
        plugin.handle_input(state, "drink", {})


def test_public_view_exposes_animation_params(fake_clock):
    plugin = CoffeePour()
    state = plugin.init_state(seed=0)
    view = plugin.public_view(state)
    assert view["cycleSeconds"] == CYCLE_SECONDS
    assert view["sweetMin"] == SWEET_MIN
    assert view["sweetMax"] == SWEET_MAX
    assert view["complete"] is False
    assert view["elapsed"] == pytest.approx(0.0, abs=1e-6)


def test_handle_input_after_completion_is_a_noop(fake_clock):
    plugin = CoffeePour()
    state = plugin.init_state(seed=0)
    fake_clock["t"] += CYCLE_SECONDS * SWEET_MIN  # land at sweet-spot lower edge
    state = plugin.handle_input(state, "stop", {})
    assert state["complete"] is True
    # Another stop must not flip complete back off.
    state = plugin.handle_input(state, "stop", {})
    assert state["complete"] is True
