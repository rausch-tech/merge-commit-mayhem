"""Tier 3.5 — LogFilter plugin tests."""

import pytest

from app.game.minigames.base import MiniGamePluginError
from app.game.minigames.log_filter import (
    NUM_ERRORS,
    NUM_LINES,
    LogFilter,
)


def test_init_state_is_deterministic_per_seed():
    plugin = LogFilter()
    a = plugin.init_state(seed=11)
    b = plugin.init_state(seed=11)
    assert [line["message"] for line in a["lines"]] == [line["message"] for line in b["lines"]]


def test_init_state_has_n_lines_and_correct_severity_counts():
    plugin = LogFilter()
    state = plugin.init_state(seed=1)
    assert len(state["lines"]) == NUM_LINES
    assert sum(1 for line in state["lines"] if line["level"] == "error") == NUM_ERRORS
    assert state["marked_errors"] == 0
    assert all(line["marked"] is False for line in state["lines"])


def test_clicking_an_error_marks_it_and_advances_progress():
    plugin = LogFilter()
    state = plugin.init_state(seed=1)
    err = next(line for line in state["lines"] if line["level"] == "error")
    state = plugin.handle_input(state, "click", {"lineId": err["id"]})
    assert state["marked_errors"] == 1
    assert next(line for line in state["lines"] if line["id"] == err["id"])["marked"] is True


def test_clicking_a_warn_or_info_softresets_all_marks():
    plugin = LogFilter()
    state = plugin.init_state(seed=1)
    err = next(line for line in state["lines"] if line["level"] == "error")
    state = plugin.handle_input(state, "click", {"lineId": err["id"]})
    assert state["marked_errors"] == 1
    non_error = next(line for line in state["lines"] if line["level"] != "error")
    state = plugin.handle_input(state, "click", {"lineId": non_error["id"]})
    assert state["marked_errors"] == 0
    assert all(line["marked"] is False for line in state["lines"])


def test_re_clicking_already_marked_error_is_idempotent():
    plugin = LogFilter()
    state = plugin.init_state(seed=1)
    err = next(line for line in state["lines"] if line["level"] == "error")
    state = plugin.handle_input(state, "click", {"lineId": err["id"]})
    state = plugin.handle_input(state, "click", {"lineId": err["id"]})
    assert state["marked_errors"] == 1


def test_marking_all_errors_completes_the_minigame():
    plugin = LogFilter()
    state = plugin.init_state(seed=1)
    for err in [line for line in state["lines"] if line["level"] == "error"]:
        state = plugin.handle_input(state, "click", {"lineId": err["id"]})
    assert plugin.is_complete(state) is True
    assert state["marked_errors"] == NUM_ERRORS


def test_unknown_action_raises():
    plugin = LogFilter()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError):
        plugin.handle_input(state, "drag", {})


def test_unknown_line_id_raises():
    plugin = LogFilter()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError):
        plugin.handle_input(state, "click", {"lineId": "nope"})


def test_public_view_shape():
    plugin = LogFilter()
    state = plugin.init_state(seed=1)
    view = plugin.public_view(state)
    assert {"lines", "totalErrors", "markedErrors"} <= view.keys()
    assert view["totalErrors"] == NUM_ERRORS
    assert all({"id", "level", "message", "marked"} <= line.keys() for line in view["lines"])
