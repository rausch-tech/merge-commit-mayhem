import random

import pytest

from app.game.game_room import GameRoom, GameRoomError
from app.game.models import Phase
from app.game.sabotages import MEETING_DURATION, sabotage_by_id


def _room_with_roles() -> tuple[GameRoom, str, str]:
    """Return (room, chaos_player_id, dev_player_id). Uses seeded rng for determinism."""
    room = GameRoom(code="ABCD")
    p0 = room.add_player("p0")
    p1 = room.add_player("p1")
    host_id = p0.id
    room.start(requesting_player_id=host_id, rng=random.Random(0))
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    dev_id = next(p.id for p in room.players.values() if p.team == "release_team")
    return room, chaos_id, dev_id


# --- guards -----------------------------------------------------------------


def test_cannot_trigger_outside_playing():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.apply_sabotage("whatever", "ci_cd_red")
    assert exc.value.code == "WRONG_PHASE"


def test_cannot_trigger_unknown_sabotage():
    room, chaos_id, _ = _room_with_roles()
    with pytest.raises(GameRoomError) as exc:
        room.apply_sabotage(chaos_id, "nope")
    assert exc.value.code == "UNKNOWN_SABOTAGE"


def test_release_team_cannot_trigger():
    room, _, dev_id = _room_with_roles()
    with pytest.raises(GameRoomError) as exc:
        room.apply_sabotage(dev_id, "ci_cd_red")
    assert exc.value.code == "NOT_CHAOS_AGENT"


def test_cooldown_prevents_retrigger():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "ci_cd_red")
    with pytest.raises(GameRoomError) as exc:
        room.apply_sabotage(chaos_id, "ci_cd_red")
    assert exc.value.code == "SABOTAGE_ON_COOLDOWN"


# --- effects ---------------------------------------------------------------


def test_ci_cd_red_drops_pipeline_by_20():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "ci_cd_red")
    assert room.pipeline_stability == 80


def test_ci_cd_red_clamps_at_zero():
    room, chaos_id, _ = _room_with_roles()
    room.pipeline_stability = 10
    room.apply_sabotage(chaos_id, "ci_cd_red")
    assert room.pipeline_stability == 0


def test_coffee_outage_zeroes_coffee():
    room, chaos_id, _ = _room_with_roles()
    assert room.coffee_level == 100
    room.apply_sabotage(chaos_id, "coffee_outage")
    assert room.coffee_level == 0


def test_mandatory_meeting_sets_meeting_timer():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "mandatory_meeting")
    assert room.meeting_active_for == MEETING_DURATION


# --- cooldown + active flag tick ------------------------------------------


def test_cooldown_ticks_down():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "ci_cd_red")
    sab = room.sabotages["ci_cd_red"]
    cd_start = sab.cooldown_remaining
    room.tick(1.0)
    assert sab.cooldown_remaining == pytest.approx(cd_start - 1.0)


def test_cooldown_clamps_at_zero_and_allows_retrigger():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "ci_cd_red")
    # Fast-forward past the 60s cooldown.
    for _ in range(610):
        room.tick(0.1)
    assert room.sabotages["ci_cd_red"].cooldown_remaining == 0.0
    # Must be triggerable again.
    room.apply_sabotage(chaos_id, "ci_cd_red")
    assert room.pipeline_stability == 60  # 80 after first → 60 after second


def test_meeting_timer_decays_and_active_flag_tracks():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "mandatory_meeting")
    assert room.meeting_active_for > 0
    # Tick one frame → still active
    room.tick(0.1)
    assert room.sabotages["mandatory_meeting"].active is True
    # Tick past the full duration.
    for _ in range(int(MEETING_DURATION / 0.1) + 5):
        room.tick(0.1)
    assert room.meeting_active_for == 0.0
    assert room.sabotages["mandatory_meeting"].active is False


def test_coffee_outage_active_flag_follows_coffee_level():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "coffee_outage")
    room.tick(0.05)
    assert room.sabotages["coffee_outage"].active is True
    # Refill.
    room.coffee_level = 100
    room.tick(0.05)
    assert room.sabotages["coffee_outage"].active is False


# --- counter + reset ------------------------------------------------------


def test_triggered_counter_increments_on_success():
    room, chaos_id, _ = _room_with_roles()
    assert room.triggered_sabotages_by_player[chaos_id] == 0
    room.apply_sabotage(chaos_id, "ci_cd_red")
    assert room.triggered_sabotages_by_player[chaos_id] == 1
    room.apply_sabotage(chaos_id, "coffee_outage")
    assert room.triggered_sabotages_by_player[chaos_id] == 2


def test_failed_trigger_does_not_increment_counter():
    room, chaos_id, dev_id = _room_with_roles()
    try:
        room.apply_sabotage(dev_id, "ci_cd_red")
    except GameRoomError:
        pass
    assert room.triggered_sabotages_by_player[dev_id] == 0


def test_reset_clears_sabotages():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "ci_cd_red")
    room.reset_for_new_round()
    assert room.sabotages == {}


# --- public_state ---------------------------------------------------------


def test_public_state_exposes_sabotages_and_tasks():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "ci_cd_red")
    state = room.public_state()
    sab_ids = {s["id"] for s in state["sabotages"]}
    assert sab_ids == {"ci_cd_red", "coffee_outage", "mandatory_meeting"}
    ci_cd = next(s for s in state["sabotages"] if s["id"] == "ci_cd_red")
    assert ci_cd["cooldownRemaining"] > 0
    task_ids = {t["id"] for t in state["tasks"]}
    assert "fix_unit_tests" in task_ids
