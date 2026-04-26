"""Tier 1.2 — Incidents stat groundwork.

The fourth global stat `incidents` (0..100) is a Chaos-pressure stat. This
slice lays the groundwork: state, clamping helper, win-condition (Chaos wins
at >= 100), wire field, and forward-compat hooks on TaskDefinition /
SabotageDefinition. Actual content (incident-creating sabotages,
incident-reducing tasks) ships in slices 1.3 / 1.4.
"""

import random
from dataclasses import replace

from app.game.game_room import INCIDENTS_LOSS_THRESHOLD, GameRoom
from app.game.models import Phase
from app.game.sabotages import SabotageDefinition
from app.game.tasks import TaskDefinition


def _started_room(n: int = 4) -> GameRoom:
    """Tier 1.5 raised MIN_PLAYERS_TO_START to 4 — bump any caller below 4."""
    if n < 4:
        n = 4
    room = GameRoom(code="ABCD")
    for i in range(n):
        room.add_player(f"p{i}")
    host_id = next(iter(room.players))
    room.start(requesting_player_id=host_id, rng=random.Random(0))
    return room


# --- state baseline -------------------------------------------------------


def test_incidents_starts_at_zero_in_lobby():
    room = GameRoom(code="ABCD")
    assert room.incidents == 0


def test_incidents_zero_after_start():
    room = _started_room()
    assert room.incidents == 0


def test_start_resets_incidents_to_zero():
    room = GameRoom(code="ABCD")
    room.add_player("p0")
    room.add_player("p1")
    room.add_player("p2")
    room.add_player("p3")
    room.incidents = 50  # pre-start scribble; start() must wipe it
    host_id = next(iter(room.players))
    room.start(requesting_player_id=host_id, rng=random.Random(0))
    assert room.incidents == 0


def test_reset_for_new_round_resets_incidents_to_zero():
    room = _started_room()
    room.incidents = 75
    room.reset_for_new_round()
    assert room.incidents == 0


# --- clamp helper ---------------------------------------------------------


def test_apply_incidents_delta_clamps_underflow():
    room = _started_room()
    room.incidents = 5
    room._apply_incidents_delta(-50)
    assert room.incidents == 0


def test_apply_incidents_delta_clamps_overflow():
    room = _started_room()
    room.incidents = 90
    room._apply_incidents_delta(50)
    assert room.incidents == 100


def test_apply_incidents_delta_within_range():
    room = _started_room()
    room.incidents = 20
    room._apply_incidents_delta(15)
    assert room.incidents == 35
    room._apply_incidents_delta(-10)
    assert room.incidents == 25


# --- win condition --------------------------------------------------------


def test_incidents_threshold_triggers_chaos_win():
    room = _started_room()
    room.incidents = INCIDENTS_LOSS_THRESHOLD
    room.tick(0.05)
    assert room.phase is Phase.ENDED
    assert room.winner == "chaos_agents"
    assert room.win_reason == "Zu viele Incidents. Niemand weiß mehr, was läuft."


def test_incidents_at_99_does_not_trigger_win():
    room = _started_room()
    room.incidents = 99
    room.tick(0.05)
    assert room.phase is Phase.PLAYING
    assert room.winner is None


def test_pipeline_zero_wins_over_incidents_full():
    """Win-condition order: pipeline_stability <= 0 fires before incidents >= 100."""
    room = _started_room()
    room.pipeline_stability = 0
    room.incidents = 100
    room.tick(0.05)
    assert room.winner == "chaos_agents"
    assert room.win_reason == "Die Pipeline ist tot."


# --- forward-compat hooks -------------------------------------------------


def test_incidents_reducing_tasks_exist():
    """Slice 1.3 added two tasks that reduce incidents on completion."""
    from app.game.tasks import TASK_DEFINITIONS

    by_id = {t.id: t for t in TASK_DEFINITIONS}
    assert by_id["analyze_logs"].incidents_change < 0
    assert by_id["calm_legacy_service"].incidents_change < 0
    # Other tasks remain neutral on incidents.
    for t in TASK_DEFINITIONS:
        if t.id not in {"analyze_logs", "calm_legacy_service"}:
            assert t.incidents_change == 0, f"{t.id} should not change incidents"


def test_incidents_raising_sabotages_exist():
    """Slice 1.4 added two sabotages that raise incidents on trigger."""
    from app.game.sabotages import SABOTAGE_DEFINITIONS

    by_id = {s.id: s for s in SABOTAGE_DEFINITIONS}
    assert by_id["merge_conflict_storm"].incidents_increase > 0
    assert by_id["flaky_tests"].incidents_increase > 0
    # Other sabotages remain neutral on incidents.
    for s in SABOTAGE_DEFINITIONS:
        if s.id not in {"merge_conflict_storm", "flaky_tests"}:
            assert s.incidents_increase == 0, f"{s.id} should not change incidents"


def test_task_with_negative_incidents_change_reduces_incidents():
    """A task carrying incidents_change=-15 must reduce incidents on completion."""
    room = _started_room()
    room.incidents = 60

    # Replace one runtime task's definition with a clone that carries the new field.
    runtime = room.tasks["review_pr"]
    runtime.definition = replace(runtime.definition, incidents_change=-15)
    room._apply_task_reward(runtime.definition)

    assert room.incidents == 45


def test_sabotage_with_incidents_increase_raises_incidents_on_trigger():
    """A sabotage carrying incidents_increase=25 must raise incidents when triggered."""
    room = _started_room()
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")

    # Patch the runtime sabotage definition with an incidents_increase clone.
    sab_runtime = room.sabotages["ci_cd_red"]
    sab_runtime.definition = replace(sab_runtime.definition, incidents_increase=25)

    assert room.incidents == 0
    room.apply_sabotage(chaos_id, "ci_cd_red")
    assert room.incidents == 25


def test_task_definition_dataclass_supports_incidents_change_field():
    """Construction smoke test for the new optional field."""
    td = TaskDefinition(
        id="x",
        title="X",
        room="open_space",
        required_seconds=1.0,
        incidents_change=-5,
    )
    assert td.incidents_change == -5


def test_sabotage_definition_dataclass_supports_incidents_increase_field():
    sd = SabotageDefinition(id="x", title="X", cooldown_seconds=1.0, incidents_increase=10)
    assert sd.incidents_increase == 10


# --- public state wire ----------------------------------------------------


def test_public_state_contains_incidents_key():
    room = _started_room()
    state = room.public_state()
    assert "incidents" in state
    assert state["incidents"] == 0


def test_public_state_reflects_current_incidents_value():
    room = _started_room()
    room.incidents = 42
    state = room.public_state()
    assert state["incidents"] == 42


# --- idempotence ----------------------------------------------------------


def test_tick_with_no_input_does_not_change_incidents():
    room = _started_room()
    assert room.incidents == 0
    for _ in range(20):
        room.tick(0.1)
    assert room.incidents == 0
