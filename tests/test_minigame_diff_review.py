"""Tier 3.7 — DiffReview plugin tests (Spot-the-Bug)."""

import pytest

from app.game.minigames.base import MiniGamePluginError
from app.game.minigames.diff_review import (
    NUM_BUGS,
    NUM_LINES,
    DiffReview,
)


def test_init_state_is_deterministic_per_seed():
    plugin = DiffReview()
    a = plugin.init_state(seed=11)
    b = plugin.init_state(seed=11)
    assert [line["text"] for line in a["lines"]] == [line["text"] for line in b["lines"]]


def test_init_state_has_correct_counts():
    plugin = DiffReview()
    state = plugin.init_state(seed=1)
    assert len(state["lines"]) == NUM_LINES
    assert sum(1 for line in state["lines"] if line["kind"] == "bug") == NUM_BUGS
    assert state["marked_bugs"] == 0
    assert all(line["marked"] is False for line in state["lines"])


def test_clicking_a_bug_marks_it_and_advances_progress():
    plugin = DiffReview()
    state = plugin.init_state(seed=2)
    bug_id = next(line["id"] for line in state["lines"] if line["kind"] == "bug")
    state = plugin.handle_input(state, "click", {"lineId": bug_id})
    line = next(line for line in state["lines"] if line["id"] == bug_id)
    assert line["marked"] is True
    assert state["marked_bugs"] == 1


def test_clicking_a_benign_line_soft_resets_all_marks():
    plugin = DiffReview()
    state = plugin.init_state(seed=3)
    bug_id = next(line["id"] for line in state["lines"] if line["kind"] == "bug")
    benign_id = next(line["id"] for line in state["lines"] if line["kind"] == "benign")
    state = plugin.handle_input(state, "click", {"lineId": bug_id})
    assert state["marked_bugs"] == 1
    state = plugin.handle_input(state, "click", {"lineId": benign_id})
    assert state["marked_bugs"] == 0
    assert all(line["marked"] is False for line in state["lines"])


def test_complete_when_all_bugs_marked():
    plugin = DiffReview()
    state = plugin.init_state(seed=4)
    bug_ids = [line["id"] for line in state["lines"] if line["kind"] == "bug"]
    for bid in bug_ids:
        state = plugin.handle_input(state, "click", {"lineId": bid})
    assert plugin.is_complete(state) is True


def test_clicking_a_marked_bug_is_idempotent():
    """Click-spam shouldn't double-count progress."""
    plugin = DiffReview()
    state = plugin.init_state(seed=5)
    bug_id = next(line["id"] for line in state["lines"] if line["kind"] == "bug")
    state = plugin.handle_input(state, "click", {"lineId": bug_id})
    state = plugin.handle_input(state, "click", {"lineId": bug_id})
    state = plugin.handle_input(state, "click", {"lineId": bug_id})
    assert state["marked_bugs"] == 1


def test_unknown_action_raises():
    plugin = DiffReview()
    state = plugin.init_state(seed=6)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "drag", {"lineId": "l0"})
    assert exc.value.code == "UNKNOWN_ACTION"


def test_unknown_line_id_raises():
    plugin = DiffReview()
    state = plugin.init_state(seed=7)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "click", {"lineId": "l99"})
    assert exc.value.code == "UNKNOWN_LINE"


def test_missing_line_id_raises():
    plugin = DiffReview()
    state = plugin.init_state(seed=8)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "click", {})
    assert exc.value.code == "INVALID_PARAMS"


def test_public_view_does_not_leak_kind():
    """Cheat-resistance: the client never sees which line is the bug
    until they click it. ``kind`` must be filtered out of public_view."""
    plugin = DiffReview()
    state = plugin.init_state(seed=9)
    view = plugin.public_view(state)
    for line in view["lines"]:
        assert "kind" not in line, "Bug-marker leaked into public_view"


def test_public_view_has_total_and_marked_counts():
    plugin = DiffReview()
    state = plugin.init_state(seed=10)
    view = plugin.public_view(state)
    assert view["totalBugs"] == NUM_BUGS
    assert view["markedBugs"] == 0
