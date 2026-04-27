"""Property-based tests for the Tier 3.5 coffee economy.

These tests exercise the invariants that hand-rolled examples would miss
— Hypothesis generates dt schedules, energy-init values, decay-modifier
combinations, and verifies the controller never violates the bounds the
rest of the game assumes (0 <= coffee_energy <= max_coffee, ghosts don't
decay, the decay constant matches what the docstring promises).
"""

from __future__ import annotations

import random

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from app.game.controllers.movement import COFFEE_BASE_DECAY_PER_SECOND
from app.game.game_room import GameRoom
from app.game.roles import role_by_id


def _make_started_room(player_count: int = 4) -> GameRoom:
    """Spin up a room in PLAYING with a deterministic role assignment so
    decay-modifiers are reproducible."""
    if player_count < 4:
        player_count = 4
    room = GameRoom(code="ABCD")
    host = room.add_player("host")
    for i in range(player_count - 1):
        room.add_player(f"p{i}")
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    return room


# Generator: a sequence of delta-times. Each between 0.001 s and 5 s,
# total length 1..40. Empty schedules are dull; we filter them out.
_dt_schedule = st.lists(
    st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=40,
)


@given(schedule=_dt_schedule)
@settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.differing_executors])
def test_coffee_energy_stays_in_bounds_after_any_decay_schedule(schedule: list[float]) -> None:
    """Invariant: 0 <= coffee_energy <= max_coffee after any tick schedule.

    No matter how many ticks we run with any allowed dt, the per-player
    coffee_energy must never go negative or exceed the player's role-
    derived ``max_coffee`` cap."""
    room = _make_started_room(player_count=4)
    for dt in schedule:
        room._tick_coffee_energy(dt)
        for p in room.players.values():
            assert 0.0 <= p.coffee_energy <= p.max_coffee + 1e-6


@given(dt=st.floats(min_value=0.001, max_value=10.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=60, deadline=None)
def test_alive_players_decay_at_role_rate(dt: float) -> None:
    """Each alive player's energy drops by exactly
    ``COFFEE_BASE_DECAY_PER_SECOND * role.coffee_decay_modifier * dt``
    in a single tick — modulo the 0.0 floor when the schedule undershoots."""
    room = _make_started_room(player_count=4)
    before = {pid: p.coffee_energy for pid, p in room.players.items()}
    room._tick_coffee_energy(dt)
    for pid, p in room.players.items():
        if not p.is_alive:
            continue
        rd = role_by_id(p.role)
        expected_drop = COFFEE_BASE_DECAY_PER_SECOND * rd.coffee_decay_modifier * dt
        expected_after = max(0.0, before[pid] - expected_drop)
        assert abs(p.coffee_energy - expected_after) < 1e-6


@given(schedule=_dt_schedule)
@settings(max_examples=40, deadline=None)
def test_ghosts_do_not_decay(schedule: list[float]) -> None:
    """A dead player's coffee_energy must be invariant under tick — ghosts
    are out of the team economy."""
    room = _make_started_room(player_count=4)
    # Force one player to ghost state.
    pid = next(iter(room.players.keys()))
    room.players[pid].is_alive = False
    snapshot = room.players[pid].coffee_energy
    for dt in schedule:
        room._tick_coffee_energy(dt)
    assert room.players[pid].coffee_energy == snapshot


@pytest.mark.parametrize(
    "dt",
    [0.0, -1.0, -0.5],
)
def test_zero_or_negative_dt_is_a_no_op(dt: float) -> None:
    """Defensive: a zero or accidentally-negative dt must not change energy."""
    room = _make_started_room(player_count=4)
    before = {pid: p.coffee_energy for pid, p in room.players.items()}
    room._tick_coffee_energy(dt)
    for pid, p in room.players.items():
        assert p.coffee_energy == before[pid]


@given(amount=st.floats(min_value=0.0, max_value=120.0))
@settings(max_examples=40, deadline=None)
def test_splash_coffee_never_exceeds_max(amount: float) -> None:
    """``_splash_coffee_to_neighbours`` adds energy to teammates within
    radius — but never above their personal max_coffee cap."""
    room = _make_started_room(player_count=4)
    src_pid = next(iter(room.players.keys()))
    src = room.players[src_pid]
    # Park everyone at the same location so they're all in radius.
    for p in room.players.values():
        p.x = src.x
        p.y = src.y
    room._splash_coffee_to_neighbours(src_pid, amount=amount, radius=500.0)
    for p in room.players.values():
        assert p.coffee_energy <= p.max_coffee + 1e-6


@given(
    amount=st.floats(min_value=0.0, max_value=200.0),
    radius=st.floats(min_value=0.0, max_value=600.0),
)
@settings(max_examples=40, deadline=None)
def test_splash_coffee_only_helps_neighbours_within_radius(amount: float, radius: float) -> None:
    """Players strictly outside the splash radius never gain energy."""
    room = _make_started_room(player_count=4)
    src_pid = next(iter(room.players.keys()))
    src = room.players[src_pid]
    far_pids = []
    for pid, p in room.players.items():
        if pid == src_pid:
            continue
        # Park them >> radius away.
        p.x = src.x + radius + 100.0
        p.y = src.y
        far_pids.append(pid)
    assume(far_pids)  # need at least one far player
    before = {pid: room.players[pid].coffee_energy for pid in far_pids}
    room._splash_coffee_to_neighbours(src_pid, amount=amount, radius=radius)
    for pid in far_pids:
        assert room.players[pid].coffee_energy == before[pid]
