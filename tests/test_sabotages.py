import random

import pytest

from app.game.game_room import GameRoom, GameRoomError
from app.game.sabotages import MEETING_DURATION


def _room_with_roles() -> tuple[GameRoom, str, str]:
    """Return (room, chaos_player_id, dev_player_id). Uses seeded rng for determinism.

    Tier 1.5 requires 4 players to start; with 4 players (1 chaos + 3 release)
    the Tier 2.1 chaos-parity rule is also satisfied.
    """
    room = GameRoom(code="ABCD")
    p0 = room.add_player("p0")
    room.add_player("p1")
    room.add_player("p2")
    room.add_player("p3")
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
    assert sab_ids == {
        "ci_cd_red",
        "coffee_outage",
        "mandatory_meeting",
        "merge_conflict_storm",
        "fake_customer_request",
        "flaky_tests",
        "lights_out",
        "comms_outage",
    }
    ci_cd = next(s for s in state["sabotages"] if s["id"] == "ci_cd_red")
    assert ci_cd["cooldownRemaining"] > 0
    task_ids = {t["id"] for t in state["tasks"]}
    assert "fix_unit_tests" in task_ids


# --- Tier 1.4 sabotages ----------------------------------------------------


def test_merge_conflict_storm_drops_pipeline_and_raises_incidents():
    room, chaos_id, _ = _room_with_roles()
    room.pipeline_stability = 80
    room.incidents = 10
    room.apply_sabotage(chaos_id, "merge_conflict_storm")
    assert room.pipeline_stability == 70
    assert room.incidents == 35
    sab = room.sabotages["merge_conflict_storm"]
    assert sab.cooldown_remaining > 0


def test_fake_customer_request_drops_release_progress():
    room, chaos_id, _ = _room_with_roles()
    room.release_progress = 50
    room.apply_sabotage(chaos_id, "fake_customer_request")
    assert room.release_progress == 35
    sab = room.sabotages["fake_customer_request"]
    assert sab.cooldown_remaining > 0


def test_fake_customer_request_floors_at_zero():
    room, chaos_id, _ = _room_with_roles()
    room.release_progress = 5
    room.apply_sabotage(chaos_id, "fake_customer_request")
    assert room.release_progress == 0


def test_flaky_tests_only_raises_incidents():
    room, chaos_id, _ = _room_with_roles()
    pipe_before = room.pipeline_stability
    release_before = room.release_progress
    room.apply_sabotage(chaos_id, "flaky_tests")
    assert room.pipeline_stability == pipe_before
    assert room.release_progress == release_before
    assert room.incidents == 30


def test_each_new_sabotage_emits_event():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "merge_conflict_storm")
    msgs = [e.message for e in room.events]
    assert any("Merge-Konflikt" in m for m in msgs)
    # Reset and try the other two.
    room.events.clear()
    room.sabotages["fake_customer_request"].cooldown_remaining = 0
    room.apply_sabotage(chaos_id, "fake_customer_request")
    assert any("Scope" in e.message for e in room.events)
    room.events.clear()
    room.sabotages["flaky_tests"].cooldown_remaining = 0
    room.apply_sabotage(chaos_id, "flaky_tests")
    assert any("Tests" in e.message for e in room.events)


# --- Tier 2.4: lights_out + repair_sabotage --------------------------------


def test_lights_out_sets_lights_off_flag():
    room, chaos_id, _ = _room_with_roles()
    assert room.lights_off is False
    room.apply_sabotage(chaos_id, "lights_out")
    assert room.lights_off is True
    # active flag is recomputed on the next tick.
    room.tick(0.05)
    assert room.sabotages["lights_out"].active is True


def test_repair_sabotage_at_panel_clears_lights_out():
    room, chaos_id, dev_id = _room_with_roles()
    room.apply_sabotage(chaos_id, "lights_out")
    panel = next(p for p in room.map.sabotage_panels if p.sabotage_id == "lights_out")
    dev = room.players[dev_id]
    dev.x, dev.y = panel.x, panel.y
    room.repair_sabotage(dev_id, "lights_out")
    assert room.lights_off is False
    room.tick(0.05)
    assert room.sabotages["lights_out"].active is False


def test_repair_sabotage_too_far_raises():
    room, chaos_id, dev_id = _room_with_roles()
    room.apply_sabotage(chaos_id, "lights_out")
    panel = next(p for p in room.map.sabotage_panels if p.sabotage_id == "lights_out")
    dev = room.players[dev_id]
    dev.x, dev.y = panel.x + 500, panel.y
    with pytest.raises(GameRoomError) as exc:
        room.repair_sabotage(dev_id, "lights_out")
    assert exc.value.code == "TOO_FAR"
    assert room.lights_off is True


def test_repair_sabotage_when_inactive_raises():
    room, _, dev_id = _room_with_roles()
    panel = next(p for p in room.map.sabotage_panels if p.sabotage_id == "lights_out")
    dev = room.players[dev_id]
    dev.x, dev.y = panel.x, panel.y
    with pytest.raises(GameRoomError) as exc:
        room.repair_sabotage(dev_id, "lights_out")
    assert exc.value.code == "SABOTAGE_NOT_ACTIVE"


def test_repair_sabotage_unknown_id_raises():
    room, _, dev_id = _room_with_roles()
    with pytest.raises(GameRoomError) as exc:
        room.repair_sabotage(dev_id, "nonsense")
    assert exc.value.code == "UNKNOWN_SABOTAGE"


def test_repair_sabotage_not_repairable_raises():
    room, _, dev_id = _room_with_roles()
    with pytest.raises(GameRoomError) as exc:
        room.repair_sabotage(dev_id, "ci_cd_red")
    assert exc.value.code == "SABOTAGE_NOT_REPAIRABLE"


def test_dead_player_cannot_repair():
    room, chaos_id, dev_id = _room_with_roles()
    room.apply_sabotage(chaos_id, "lights_out")
    panel = next(p for p in room.map.sabotage_panels if p.sabotage_id == "lights_out")
    dev = room.players[dev_id]
    dev.x, dev.y = panel.x, panel.y
    dev.is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.repair_sabotage(dev_id, "lights_out")
    assert exc.value.code == "PLAYER_ELIMINATED"


def test_lights_off_resets_on_new_round():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "lights_out")
    assert room.lights_off is True
    # End round and reset.
    room._finish_round("release_team", "test")
    room.reset_for_new_round()
    assert room.lights_off is False


def test_public_state_carries_lights_off_and_panels():
    room, chaos_id, _ = _room_with_roles()
    state = room.public_state()
    assert state["lightsOff"] is False
    assert any(p["sabotageId"] == "lights_out" for p in state["sabotagePanels"])
    room.apply_sabotage(chaos_id, "lights_out")
    state = room.public_state()
    assert state["lightsOff"] is True


# --- Tier 2.5: comms_outage + repair --------------------------------------


def test_comms_outage_sets_comms_down_flag():
    room, chaos_id, _ = _room_with_roles()
    assert room.comms_down is False
    room.apply_sabotage(chaos_id, "comms_outage")
    assert room.comms_down is True
    room.tick(0.05)
    assert room.sabotages["comms_outage"].active is True


def test_comms_down_blocks_task_hold_start():
    room, chaos_id, dev_id = _room_with_roles()
    room.apply_sabotage(chaos_id, "comms_outage")
    # Park the dev player on top of an actual task anchor.
    task_id, (tx, ty) = next(iter(room._task_position.items()))
    room.players[dev_id].x = tx
    room.players[dev_id].y = ty
    with pytest.raises(GameRoomError) as exc:
        room.apply_task_hold_start(dev_id, task_id)
    assert exc.value.code == "COMMS_DOWN"


def test_comms_down_blocks_other_sabotage_triggers():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "comms_outage")
    # ci_cd_red would normally be available on a fresh round.
    room.sabotages["ci_cd_red"].cooldown_remaining = 0.0
    with pytest.raises(GameRoomError) as exc:
        room.apply_sabotage(chaos_id, "ci_cd_red")
    assert exc.value.code == "COMMS_DOWN"


def test_repair_comms_outage_clears_flag():
    room, chaos_id, dev_id = _room_with_roles()
    room.apply_sabotage(chaos_id, "comms_outage")
    panel = next(p for p in room.map.sabotage_panels if p.sabotage_id == "comms_outage")
    dev = room.players[dev_id]
    dev.x, dev.y = panel.x, panel.y
    room.repair_sabotage(dev_id, "comms_outage")
    assert room.comms_down is False
    room.tick(0.05)
    assert room.sabotages["comms_outage"].active is False


def test_comms_down_resets_on_new_round():
    room, chaos_id, _ = _room_with_roles()
    room.apply_sabotage(chaos_id, "comms_outage")
    assert room.comms_down is True
    room._finish_round("release_team", "test")
    room.reset_for_new_round()
    assert room.comms_down is False


def test_public_state_carries_comms_down():
    room, chaos_id, _ = _room_with_roles()
    state = room.public_state()
    assert state["commsDown"] is False
    room.apply_sabotage(chaos_id, "comms_outage")
    state = room.public_state()
    assert state["commsDown"] is True
