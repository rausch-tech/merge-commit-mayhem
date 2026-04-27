"""Slice 1 (Hardening): regression tests that lock in protections the audit
flagged. Most of the audit's "P1 bugs" turned out to already be guarded
correctly — these tests pin those guards in place so future refactors don't
silently weaken them. Plus shape-tests for the new ``MeetingContext`` Pydantic
model that replaced the hand-built dict in ``_snapshot_meeting_context``.
"""

import random

import pytest

from app.game.game_map import discover_maps
from app.game.game_room import GameRoom, GameRoomError
from app.game.models import Phase
from app.protocol import MeetingContext


def _make_started_room(player_count: int = 4) -> GameRoom:
    if player_count < 4:
        player_count = 4
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    for i in range(player_count - 1):
        room.add_player(f"p{i}")
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    return room


# --- private_role_for: defensive guard ---------------------------------------


def test_private_role_for_unknown_player_returns_no_role():
    """Stale ws frame (player swept after disconnect) must surface as a clean
    GameRoomError, not a bare KeyError."""
    room = _make_started_room(player_count=4)
    with pytest.raises(GameRoomError) as exc:
        room.private_role_for("ghost-id-never-existed")
    assert exc.value.code == "NO_ROLE"


def test_private_role_for_lobby_player_returns_no_role():
    """Pre-start, player has no role yet — must NO_ROLE, not crash."""
    room = GameRoom(code="ABCD")
    p = room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.private_role_for(p.id)
    assert exc.value.code == "NO_ROLE"


# --- apply_mini_game_input: graceful no-session error ------------------------


def test_apply_mini_game_input_without_session_returns_clean_error():
    """Lock in: a stray mini_game_input frame for a player without an active
    session must surface NO_ACTIVE_MINI_GAME, not crash. Single-threaded
    asyncio means there's no real race here, but the WS layer still needs the
    structured error to propagate as ErrorMsg."""
    room = _make_started_room(player_count=4)
    pid = next(iter(room.players.keys()))
    with pytest.raises(GameRoomError) as exc:
        room.apply_mini_game_input(pid, "click", {"testId": "t0"})
    assert exc.value.code == "NO_ACTIVE_MINI_GAME"


# --- set_map: phase-gated (regression-pin) -----------------------------------


def test_set_map_blocked_during_meeting():
    """Already covered for PLAYING in test_game_room.py — pin the MEETING-phase
    case too. Sabotage-object-binding would silently break if the map could
    swap mid-meeting."""
    registry = discover_maps()
    room = _make_started_room(player_count=4)
    host_id = next(p.id for p in room.players.values() if p.is_host)
    # Force the room into MEETING without going through call_emergency_meeting
    # (which has its own war-room checks unrelated to this test).
    room.phase = Phase.MEETING
    with pytest.raises(GameRoomError) as exc:
        room.set_map(requesting_player_id=host_id, map_id="small", registry=registry)
    assert exc.value.code == "WRONG_PHASE"


# --- MeetingContext Pydantic model: camelCase + shape ------------------------


def test_meeting_context_serialises_camel_case_with_body():
    """Frontend reads `reporterName`, `body.victimName`, `body.room`,
    `recentEvents[].message`. Pydantic must emit those exact keys via
    ``model_dump(by_alias=True)``."""
    ctx = MeetingContext(
        reporter_name="Sven",
        body={
            "victim_name": "Max",
            "x": 100.0,
            "y": 200.0,
            "room": "Server Room",
        },
        recent_events=[
            {"severity": "warn", "message": "CI ist rot", "seq": 7},
        ],
        alive=[{"id": "abc", "name": "Sven"}],
    )
    wire = ctx.model_dump(by_alias=True)
    assert wire["reporterName"] == "Sven"
    assert wire["body"]["victimName"] == "Max"
    assert wire["body"]["room"] == "Server Room"
    assert wire["recentEvents"][0]["message"] == "CI ist rot"
    assert wire["alive"][0]["name"] == "Sven"


def test_meeting_context_serialises_camel_case_without_body():
    """Emergency meeting with no reported body — `body` must be None on the
    wire (frontend hides the body block)."""
    ctx = MeetingContext(reporter_name="Sven", body=None)
    wire = ctx.model_dump(by_alias=True)
    assert wire["reporterName"] == "Sven"
    assert wire["body"] is None
    assert wire["recentEvents"] == []
    assert wire["alive"] == []


def test_snapshot_meeting_context_emits_pydantic_model():
    """End-to-end: after _snapshot_meeting_context, the room holds a
    MeetingContext instance, and the public_state embeds a camelCase dict."""
    room = _make_started_room(player_count=4)
    reporter_id = next(iter(room.players.keys()))
    room._snapshot_meeting_context(reporter_id=reporter_id, body=None)
    assert isinstance(room.meeting_context, MeetingContext)
    # Force public_state into a meeting view to exercise the embed path.
    room.phase = Phase.MEETING
    state = room.public_state()
    assert state["meeting"] is not None
    ctx = state["meeting"]["context"]
    assert "reporterName" in ctx
    assert ctx["body"] is None
    assert isinstance(ctx["recentEvents"], list)
