"""Tier 2.1 — Body Report regression tests.

Body report bypasses the war-room and meeting-quota requirements; it pops the
body and triggers a meeting with a context-anchored title. Take-Down internals
live in tests/test_takedown.py.
"""

import random

import pytest

from app.game.game_room import (
    REPORT_RADIUS,
    GameRoom,
    GameRoomError,
)
from app.game.models import Phase


def _started_room(player_count: int = 4, seed: int = 0) -> tuple[GameRoom, list[str]]:
    if player_count < 4:
        player_count = 4
    room = GameRoom(code="RPRT")
    ids = []
    for i in range(player_count):
        ids.append(room.add_player(f"p{i}").id)
    room.start(requesting_player_id=ids[0], rng=random.Random(seed))
    return room, ids


def _split_by_team(room: GameRoom) -> tuple[str, list[str]]:
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    release_ids = [p.id for p in room.players.values() if p.team == "release_team"]
    return chaos_id, release_ids


def _kill_first_release(room: GameRoom) -> tuple[str, str]:
    """Drive a take-down to create a body. Returns (body_id, victim_id)."""
    chaos_id, release_ids = _split_by_team(room)
    target_id = release_ids[0]
    room.players[chaos_id].x, room.players[chaos_id].y = 500.0, 500.0
    room.players[target_id].x, room.players[target_id].y = 500.0, 505.0
    body = room.apply_takedown(killer_id=chaos_id, target_id=target_id)
    return body.id, target_id


# --- happy path ----------------------------------------------------------------


def test_report_body_in_range_triggers_meeting_and_emits_event():
    room, _ = _started_room()
    body_id, victim_id = _kill_first_release(room)
    victim_name = room.players[victim_id].name

    # A non-killer release player walks up to the body and reports it.
    chaos_id, release_ids = _split_by_team(room)
    reporter_id = next(rid for rid in release_ids if rid != victim_id)
    reporter = room.players[reporter_id]
    body = room.bodies[body_id]
    reporter.x, reporter.y = body.x, body.y + 5

    pre_seqs = {e.seq for e in room.events}
    room.apply_report_body(reporter_id=reporter_id, body_id=body_id)

    # Body removed.
    assert body_id not in room.bodies
    # Meeting started with anchored title.
    assert room.phase is Phase.MEETING
    assert room.meeting_title == f"Body Report: {victim_name}"
    assert room.meeting_caller_id == reporter_id
    assert room.meeting_remaining_seconds > 0
    # Eventfeed: a danger event names both reporter and victim.
    new_events = [e for e in room.events if e.seq not in pre_seqs]
    assert any(
        e.severity == "danger"
        and reporter.name in e.message
        and victim_name in e.message
        and "Body" in e.message
        for e in new_events
    )


# --- guards --------------------------------------------------------------------


def test_report_body_out_of_range_errors_and_keeps_body():
    room, _ = _started_room()
    body_id, _victim_id = _kill_first_release(room)
    body = room.bodies[body_id]
    chaos_id, release_ids = _split_by_team(room)
    reporter_id = next(rid for rid in release_ids if rid != _victim_id)
    reporter = room.players[reporter_id]
    reporter.x = body.x + REPORT_RADIUS + 5
    reporter.y = body.y
    with pytest.raises(GameRoomError) as exc:
        room.apply_report_body(reporter_id=reporter_id, body_id=body_id)
    assert exc.value.code == "OUT_OF_RANGE"
    assert body_id in room.bodies
    assert room.phase is Phase.PLAYING


def test_report_body_unknown_id_errors():
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    reporter_id = release_ids[0]
    with pytest.raises(GameRoomError) as exc:
        room.apply_report_body(reporter_id=reporter_id, body_id="nope")
    assert exc.value.code == "UNKNOWN_BODY"


def test_report_body_dead_reporter_errors():
    room, _ = _started_room()
    body_id, _victim_id = _kill_first_release(room)
    chaos_id, release_ids = _split_by_team(room)
    reporter_id = next(rid for rid in release_ids if rid != _victim_id)
    room.players[reporter_id].is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.apply_report_body(reporter_id=reporter_id, body_id=body_id)
    assert exc.value.code == "PLAYER_ELIMINATED"


def test_report_body_only_in_playing_phase():
    room, _ = _started_room()
    body_id, _victim_id = _kill_first_release(room)
    chaos_id, release_ids = _split_by_team(room)
    reporter_id = next(rid for rid in release_ids if rid != _victim_id)
    body = room.bodies[body_id]
    room.players[reporter_id].x, room.players[reporter_id].y = body.x, body.y
    room.phase = Phase.ENDED
    with pytest.raises(GameRoomError) as exc:
        room.apply_report_body(reporter_id=reporter_id, body_id=body_id)
    assert exc.value.code == "WRONG_PHASE"


# --- bypass semantics ----------------------------------------------------------


def test_report_does_not_consume_emergency_meeting_quota():
    room, _ = _started_room()
    body_id, victim_id = _kill_first_release(room)
    chaos_id, release_ids = _split_by_team(room)
    reporter_id = next(rid for rid in release_ids if rid != victim_id)
    reporter = room.players[reporter_id]
    body = room.bodies[body_id]
    reporter.x, reporter.y = body.x, body.y

    # Sanity: reporter still has their emergency meeting before report.
    assert room.players_with_meeting_left[reporter_id] is True

    room.apply_report_body(reporter_id=reporter_id, body_id=body_id)

    # After the body report, the reporter's emergency-meeting quota is intact.
    assert room.players_with_meeting_left[reporter_id] is True


def test_report_works_outside_war_room():
    """Body report bypasses the War Room AABB requirement of the regular
    emergency meeting flow.
    """
    room, _ = _started_room()
    chaos_id, release_ids = _split_by_team(room)
    victim_id = release_ids[0]
    reporter_id = release_ids[1]

    # Pick a coordinate clearly outside any plausible war room — the map's
    # corner. Place reporter and victim/body together far from the center.
    far_x, far_y = 50.0, 50.0
    room.players[chaos_id].x, room.players[chaos_id].y = far_x, far_y + 5
    room.players[victim_id].x, room.players[victim_id].y = far_x, far_y
    body = room.apply_takedown(killer_id=chaos_id, target_id=victim_id)
    room.players[reporter_id].x, room.players[reporter_id].y = body.x, body.y + 5

    # The reporter is NOT inside the war room AABB; report still works.
    assert not room._is_in_war_room(room.players[reporter_id])
    room.apply_report_body(reporter_id=reporter_id, body_id=body.id)
    assert room.phase is Phase.MEETING
