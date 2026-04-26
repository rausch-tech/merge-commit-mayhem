"""Tier 3.3 — CablePairing plugin tests."""

import pytest

from app.game.minigames.base import MiniGamePluginError
from app.game.minigames.cable_pairing import COLORS, NUM_PAIRS, CablePairing


def _matching_pair(state):
    """Return (sourceId, destinationId) for the first source whose color
    matches one of the destinations — i.e. a guaranteed valid connection."""
    for src in state["sources"]:
        for dst in state["destinations"]:
            if src["color"] == dst["color"]:
                return src["id"], dst["id"]
    raise AssertionError("no matching pair found")


def test_init_state_is_deterministic_per_seed():
    plugin = CablePairing()
    a = plugin.init_state(seed=7)
    b = plugin.init_state(seed=7)
    assert [d["color"] for d in a["destinations"]] == [d["color"] for d in b["destinations"]]


def test_init_state_has_n_sources_and_destinations_one_per_color():
    plugin = CablePairing()
    state = plugin.init_state(seed=1)
    assert len(state["sources"]) == NUM_PAIRS
    assert len(state["destinations"]) == NUM_PAIRS
    assert sorted(s["color"] for s in state["sources"]) == sorted(COLORS)
    assert sorted(d["color"] for d in state["destinations"]) == sorted(COLORS)
    assert state["connections"] == {}


def test_correct_color_pair_creates_connection():
    plugin = CablePairing()
    state = plugin.init_state(seed=1)
    src_id, dst_id = _matching_pair(state)
    state = plugin.handle_input(state, "connect", {"sourceId": src_id, "destinationId": dst_id})
    assert state["connections"] == {src_id: dst_id}


def test_wrong_color_pair_softresets_connections():
    plugin = CablePairing()
    state = plugin.init_state(seed=1)
    # Establish one good connection first.
    good_src, good_dst = _matching_pair(state)
    state = plugin.handle_input(state, "connect", {"sourceId": good_src, "destinationId": good_dst})
    assert len(state["connections"]) == 1
    # Now find a mismatching pair (different colors).
    src = next(s for s in state["sources"] if s["id"] != good_src)
    dst = next(d for d in state["destinations"] if d["color"] != src["color"])
    state = plugin.handle_input(
        state, "connect", {"sourceId": src["id"], "destinationId": dst["id"]}
    )
    assert state["connections"] == {}


def test_already_used_source_or_destination_is_silently_ignored():
    plugin = CablePairing()
    state = plugin.init_state(seed=1)
    src_id, dst_id = _matching_pair(state)
    state = plugin.handle_input(state, "connect", {"sourceId": src_id, "destinationId": dst_id})
    # Re-tap same pair: idempotent, no change.
    state = plugin.handle_input(state, "connect", {"sourceId": src_id, "destinationId": dst_id})
    assert state["connections"] == {src_id: dst_id}


def test_is_complete_when_all_pairs_connected():
    plugin = CablePairing()
    state = plugin.init_state(seed=3)
    # Wire every source to its color-twin destination directly.
    for src in state["sources"]:
        dst = next(d for d in state["destinations"] if d["color"] == src["color"])
        state = plugin.handle_input(
            state, "connect", {"sourceId": src["id"], "destinationId": dst["id"]}
        )
    assert plugin.is_complete(state) is True
    assert len(state["connections"]) == NUM_PAIRS


def test_unknown_action_raises():
    plugin = CablePairing()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError):
        plugin.handle_input(state, "wiggle", {})


def test_invalid_params_raise():
    plugin = CablePairing()
    state = plugin.init_state(seed=1)
    with pytest.raises(MiniGamePluginError):
        plugin.handle_input(state, "connect", {"sourceId": "s0"})  # missing destinationId
    with pytest.raises(MiniGamePluginError):
        plugin.handle_input(state, "connect", {"sourceId": "nope", "destinationId": "alsono"})


def test_public_view_carries_colors_and_progress():
    plugin = CablePairing()
    state = plugin.init_state(seed=1)
    view = plugin.public_view(state)
    assert {"sources", "destinations", "connections", "totalPairs"} <= view.keys()
    assert view["totalPairs"] == NUM_PAIRS
    assert all("color" in s for s in view["sources"])
    assert all("color" in d for d in view["destinations"])
