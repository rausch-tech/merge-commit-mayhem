"""Tier 3.7 — ReleaseNotes plugin tests (write_release_notes)."""

import pytest

from app.game.minigames.base import MiniGamePluginError
from app.game.minigames.release_notes import (
    CATEGORIES,
    NUM_COMMITS,
    ReleaseNotes,
)


def test_init_state_is_deterministic_per_seed():
    plugin = ReleaseNotes()
    a = plugin.init_state(seed=11)
    b = plugin.init_state(seed=11)
    assert [c["message"] for c in a["commits"]] == [c["message"] for c in b["commits"]]


def test_init_state_has_correct_distribution():
    """Every round has exactly 2 features, 2 bugfixes, 1 breaking, 1 noprod
    so the four-bucket choice stays meaningful."""
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=1)
    assert len(state["commits"]) == NUM_COMMITS
    counts = {cat: 0 for cat in CATEGORIES}
    for c in state["commits"]:
        counts[c["correct"]] += 1
    assert counts == {"feature": 2, "bugfix": 2, "breaking": 1, "noprod": 1}


def test_init_state_starts_unassigned():
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=2)
    assert all(c["assigned"] is None for c in state["commits"])


def test_cycle_advances_through_categories_then_back_to_unassigned():
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=3)
    cid = state["commits"][0]["id"]
    expected = ["feature", "bugfix", "breaking", "noprod", None]
    for want in expected:
        state = plugin.handle_input(state, "cycle", {"commitId": cid})
        commit = next(c for c in state["commits"] if c["id"] == cid)
        assert commit["assigned"] == want


def test_submit_with_unassigned_commits_raises():
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=4)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "submit", {})
    assert exc.value.code == "NOT_READY"


def test_submit_when_all_correct_marks_solved():
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=5)
    for c in state["commits"]:
        c["assigned"] = c["correct"]
    state = plugin.handle_input(state, "submit", {})
    assert plugin.is_complete(state) is True


def test_submit_when_any_wrong_resets_assignments():
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=6)
    for c in state["commits"]:
        c["assigned"] = c["correct"]
    # Flip one assignment to be wrong.
    wrong_target = state["commits"][0]
    wrong_target["assigned"] = "noprod" if wrong_target["correct"] != "noprod" else "feature"
    state = plugin.handle_input(state, "submit", {})
    # Soft reset: every commit back to unassigned, not solved.
    assert all(c["assigned"] is None for c in state["commits"])
    assert plugin.is_complete(state) is False


def test_unknown_action_raises():
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=7)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "drag", {"commitId": "c0"})
    assert exc.value.code == "UNKNOWN_ACTION"


def test_unknown_commit_raises():
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=8)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "cycle", {"commitId": "c99"})
    assert exc.value.code == "UNKNOWN_COMMIT"


def test_missing_commit_id_raises():
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=9)
    with pytest.raises(MiniGamePluginError) as exc:
        plugin.handle_input(state, "cycle", {})
    assert exc.value.code == "INVALID_PARAMS"


def test_public_view_does_not_leak_correct_category():
    """Cheat-resistance: the client must never see the right bucket
    until after a successful submit."""
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=10)
    view = plugin.public_view(state)
    for commit in view["commits"]:
        assert "correct" not in commit


def test_public_view_includes_progress_counters():
    plugin = ReleaseNotes()
    state = plugin.init_state(seed=11)
    state["commits"][0]["assigned"] = "feature"
    state["commits"][1]["assigned"] = "bugfix"
    view = plugin.public_view(state)
    assert view["totalCommits"] == NUM_COMMITS
    assert view["assignedCount"] == 2
    assert list(view["categories"]) == list(CATEGORIES)
