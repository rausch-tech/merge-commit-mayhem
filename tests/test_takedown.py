"""Tier 2.1 — Take-Down (stealth kill) regression tests.

Covers the chaos-agent-only take-down action, the per-killer cooldown, body
creation/snapshot semantics, and public_state body shape. Body-report flow
lives in tests/test_body_report.py.
"""

import random

import pytest

from app.game.controllers.meeting import TAKEDOWN_COOLDOWN, TAKEDOWN_RADIUS
from app.game.game_room import GameRoom, GameRoomError
from app.game.models import Phase


def _started_room(player_count: int = 4, seed: int = 0) -> tuple[GameRoom, list[str]]:
    """Spawn a started GameRoom with at least 4 players (1 chaos + 3 release)
    so the Tier 2.1 chaos-parity rule does not interfere with mid-test ticks.
    """
    if player_count < 4:
        player_count = 4
    room = GameRoom(code="TKDN")
    ids = []
    for i in range(player_count):
        ids.append(room.add_player(f"p{i}").id)
    room.start(requesting_player_id=ids[0], rng=random.Random(seed))
    return room, ids


def _split_by_team(room: GameRoom) -> tuple[str, list[str]]:
    """Return (chaos_id, list_of_release_ids)."""
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    release_ids = [p.id for p in room.players.values() if p.team == "release_team"]
    return chaos_id, release_ids


# --- happy path ----------------------------------------------------------------


def test_takedown_in_range_kills_target_and_creates_body():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    chaos = room.players[chaos_id]
    target = room.players[target_id]
    # Place killer next to target.
    target.x, target.y = 1000.0, 1000.0
    chaos.x, chaos.y = 1000.0, 1010.0  # well within TAKEDOWN_RADIUS = 40

    body = room.apply_takedown(killer_id=chaos_id, target_id=target_id)

    assert target.is_alive is False
    assert body.victim_player_id == target_id
    assert body.victim_name == target.name
    assert body.color == target.color
    assert body.x == 1000.0
    assert body.y == 1000.0
    assert body.id in room.bodies
    assert room.takedown_cooldowns[chaos_id] == TAKEDOWN_COOLDOWN


# --- guards --------------------------------------------------------------------


def test_takedown_requires_chaos_killer():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    killer_id = release_ids[0]
    target_id = release_ids[1]
    room.players[killer_id].x, room.players[killer_id].y = 1000.0, 1000.0
    room.players[target_id].x, room.players[target_id].y = 1000.0, 1010.0
    with pytest.raises(GameRoomError) as exc:
        room.apply_takedown(killer_id=killer_id, target_id=target_id)
    assert exc.value.code == "NOT_CHAOS_AGENT"


def test_takedown_requires_target_in_range():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    room.players[chaos_id].x, room.players[chaos_id].y = 1000.0, 1000.0
    # Place target just outside the radius.
    room.players[target_id].x = 1000.0 + TAKEDOWN_RADIUS + 5
    room.players[target_id].y = 1000.0
    with pytest.raises(GameRoomError) as exc:
        room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    assert exc.value.code == "OUT_OF_RANGE"


def test_takedown_blocked_by_cooldown():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    room.players[chaos_id].x, room.players[chaos_id].y = 500.0, 500.0
    room.players[target_id].x, room.players[target_id].y = 500.0, 510.0
    room.apply_takedown(killer_id=chaos_id, target_id=target_id)

    # Second target, but cooldown still ticking.
    other_target = release_ids[1]
    room.players[other_target].x, room.players[other_target].y = 500.0, 510.0
    with pytest.raises(GameRoomError) as exc:
        room.apply_takedown(killer_id=chaos_id, target_id=other_target)
    assert exc.value.code == "TAKEDOWN_ON_COOLDOWN"


def test_takedown_killer_must_be_alive():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    room.players[chaos_id].is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    assert exc.value.code == "PLAYER_ELIMINATED"


def test_takedown_target_must_be_alive():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    room.players[target_id].is_alive = False
    room.players[chaos_id].x, room.players[chaos_id].y = 100.0, 100.0
    room.players[target_id].x, room.players[target_id].y = 100.0, 110.0
    with pytest.raises(GameRoomError) as exc:
        room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    assert exc.value.code == "TARGET_ELIMINATED"


def test_takedown_self_target_rejected():
    room, _ = _started_room()
    chaos_id, _release_ids = _split_by_team(room)
    with pytest.raises(GameRoomError) as exc:
        room.apply_takedown(killer_id=chaos_id, target_id=chaos_id)
    assert exc.value.code == "INVALID_TARGET"


def test_takedown_chaos_cannot_kill_chaos():
    """Friendly fire guard: a chaos agent must not be able to take down another
    chaos agent. Without this guard, chaos parity could fire against chaos's
    own team if two chaos agents bumped into each other near a button mash."""
    room = GameRoom(code="TKDN")
    ids = [room.add_player(f"p{i}").id for i in range(6)]
    # Force a fixed role layout: 2 chaos, 4 release.
    room.start(requesting_player_id=ids[0], rng=random.Random(0))
    chaos_ids = [pid for pid, p in room.players.items() if p.team == "chaos_agents"]
    if len(chaos_ids) < 2:
        # Bump a release player into chaos manually to construct the scenario
        # (default 6-player rng layout may yield only 1 chaos).
        release_ids = [pid for pid, p in room.players.items() if p.team == "release_team"]
        room.players[release_ids[0]].team = "chaos_agents"
        room.players[release_ids[0]].role = "vibe_coder"
        chaos_ids.append(release_ids[0])
        room.takedown_cooldowns[release_ids[0]] = 0.0
    killer_id, target_id = chaos_ids[0], chaos_ids[1]
    room.players[killer_id].x, room.players[killer_id].y = 500.0, 500.0
    room.players[target_id].x, room.players[target_id].y = 500.0, 510.0
    with pytest.raises(GameRoomError) as exc:
        room.apply_takedown(killer_id=killer_id, target_id=target_id)
    assert exc.value.code == "INVALID_TARGET"
    # Target must remain alive and no body must have been created.
    assert room.players[target_id].is_alive is True
    assert room.bodies == {}


def test_takedown_only_in_playing_phase():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    # Force ENDED.
    room.phase = Phase.ENDED
    with pytest.raises(GameRoomError) as exc:
        room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    assert exc.value.code == "WRONG_PHASE"


# --- cooldown tick + reset -----------------------------------------------------


def test_cooldown_ticks_down_with_dt():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    room.players[chaos_id].x, room.players[chaos_id].y = 500.0, 500.0
    room.players[target_id].x, room.players[target_id].y = 500.0, 510.0
    room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    cd_start = room.takedown_cooldowns[chaos_id]
    room.tick(1.0)
    assert room.takedown_cooldowns[chaos_id] == pytest.approx(cd_start - 1.0)


def test_cooldown_initialized_zero_in_start_for_each_chaos():
    room, _ = _started_room()
    chaos_id, _ = _split_by_team(room)
    assert chaos_id in room.takedown_cooldowns
    assert room.takedown_cooldowns[chaos_id] == 0.0


def test_bodies_cleared_in_start():
    room = GameRoom(code="STRT")
    room.add_player("p0")
    room.add_player("p1")
    room.add_player("p2")
    room.add_player("p3")
    # Before start: empty.
    assert room.bodies == {}
    room.start(requesting_player_id=next(iter(room.players)), rng=random.Random(0))
    assert room.bodies == {}


def test_bodies_and_cooldowns_cleared_in_reset_for_new_round():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    room.players[chaos_id].x, room.players[chaos_id].y = 100.0, 100.0
    room.players[target_id].x, room.players[target_id].y = 100.0, 110.0
    room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    assert room.bodies
    assert room.takedown_cooldowns[chaos_id] > 0

    room.reset_for_new_round()
    assert room.bodies == {}
    assert room.takedown_cooldowns == {}


# --- public_state shape --------------------------------------------------------


def test_public_state_bodies_shape_camelcase():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    target = room.players[target_id]
    target.x, target.y = 250.5, 320.25
    room.players[chaos_id].x, room.players[chaos_id].y = 250.0, 320.0

    body = room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    state = room.public_state()
    assert "bodies" in state
    assert isinstance(state["bodies"], list)
    assert len(state["bodies"]) == 1
    entry = state["bodies"][0]
    assert set(entry.keys()) == {"id", "x", "y", "color", "victimName"}
    assert entry["id"] == body.id
    assert entry["color"] == target.color
    assert entry["victimName"] == target.name
    assert entry["x"] == pytest.approx(round(target.x, 2))
    assert entry["y"] == pytest.approx(round(target.y, 2))


def test_takedown_drops_target_task_holds():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    target = room.players[target_id]
    # Place target ON a task and start a hold.
    tx, ty = room.task_position("review_pr")
    target.x, target.y = tx, ty
    room.apply_task_hold_start(target_id, "review_pr")
    assert target_id in room.tasks["review_pr"].per_player_progress

    # Place chaos in range and kill.
    room.players[chaos_id].x, room.players[chaos_id].y = tx, ty + 5
    room.apply_takedown(killer_id=chaos_id, target_id=target_id)

    assert target_id not in room.tasks["review_pr"].per_player_progress
    assert room.tasks["review_pr"].status == "available"


def test_takedown_does_not_emit_event():
    """Take-Down must NOT leak into the public event feed."""
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    room.players[chaos_id].x, room.players[chaos_id].y = 100.0, 100.0
    room.players[target_id].x, room.players[target_id].y = 100.0, 110.0
    pre_seqs = {e.seq for e in room.events}
    room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    new_events = [e for e in room.events if e.seq not in pre_seqs]
    assert new_events == []
