"""Tier 3.6 — SprintTrim plugin tests."""

import pytest

from app.game.minigames.base import MiniGamePluginError
from app.game.minigames.sprint_trim import NUM_TICKETS, SPRINT_BUDGET, SprintTrim


def test_init_state_is_deterministic_per_seed():
    plugin = SprintTrim()
    a = plugin.init_state(seed=42)
    b = plugin.init_state(seed=42)
    assert [t["title"] for t in a["tickets"]] == [t["title"] for t in b["tickets"]]
    assert [t["points"] for t in a["tickets"]] == [t["points"] for t in b["tickets"]]


def test_init_state_has_n_tickets_and_two_priorities_under_budget():
    plugin = SprintTrim()
    state = plugin.init_state(seed=1)
    assert len(state["tickets"]) == NUM_TICKETS
    assert state["budget"] == SPRINT_BUDGET
    assert sum(1 for t in state["tickets"] if t["priority"]) == 2
    # Solvable invariant: priority-only sum must fit budget.
    priority_sum = sum(t["points"] for t in state["tickets"] if t["priority"])
    assert priority_sum <= SPRINT_BUDGET


def test_toggle_non_priority_ticket_marks_it_removed():
    plugin = SprintTrim()
    state = plugin.init_state(seed=1)
    nonpri = next(t for t in state["tickets"] if not t["priority"])
    state = plugin.handle_input(state, "toggle", {"ticketId": nonpri["id"]})
    assert next(t for t in state["tickets"] if t["id"] == nonpri["id"])["removed"] is True


def test_toggle_priority_ticket_softresets_all_removals():
    plugin = SprintTrim()
    state = plugin.init_state(seed=1)
    nonpri = next(t for t in state["tickets"] if not t["priority"])
    state = plugin.handle_input(state, "toggle", {"ticketId": nonpri["id"]})
    pri = next(t for t in state["tickets"] if t["priority"])
    state = plugin.handle_input(state, "toggle", {"ticketId": pri["id"]})
    assert all(t["removed"] is False for t in state["tickets"])


def test_re_toggling_non_priority_unremoves_it():
    plugin = SprintTrim()
    state = plugin.init_state(seed=1)
    nonpri = next(t for t in state["tickets"] if not t["priority"])
    state = plugin.handle_input(state, "toggle", {"ticketId": nonpri["id"]})
    state = plugin.handle_input(state, "toggle", {"ticketId": nonpri["id"]})
    assert next(t for t in state["tickets"] if t["id"] == nonpri["id"])["removed"] is False


def test_minigame_completes_when_remaining_under_budget():
    plugin = SprintTrim()
    state = plugin.init_state(seed=1)
    # Greedy: remove non-priority tickets in descending point order until under budget.
    while not plugin.is_complete(state):
        candidates = [t for t in state["tickets"] if not t["priority"] and not t["removed"]]
        if not candidates:
            pytest.fail("Greedy strategy could not reach budget — broken invariant.")
        biggest = max(candidates, key=lambda t: t["points"])
        state = plugin.handle_input(state, "toggle", {"ticketId": biggest["id"]})
    assert plugin.is_complete(state) is True
    remaining = sum(t["points"] for t in state["tickets"] if not t["removed"])
    assert remaining <= SPRINT_BUDGET


def test_unknown_action_raises():
    plugin = SprintTrim()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError):
        plugin.handle_input(state, "delete", {})


def test_unknown_ticket_id_raises():
    plugin = SprintTrim()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError):
        plugin.handle_input(state, "toggle", {"ticketId": "nope"})


def test_public_view_shape_and_remaining_recompute():
    plugin = SprintTrim()
    state = plugin.init_state(seed=1)
    view0 = plugin.public_view(state)
    assert {"tickets", "budget", "remainingPoints"} <= view0.keys()
    assert view0["budget"] == SPRINT_BUDGET
    full_total = sum(t["points"] for t in state["tickets"])
    assert view0["remainingPoints"] == full_total
    nonpri = next(t for t in state["tickets"] if not t["priority"])
    state = plugin.handle_input(state, "toggle", {"ticketId": nonpri["id"]})
    view1 = plugin.public_view(state)
    assert view1["remainingPoints"] == full_total - nonpri["points"]
