"""Role-leak regression suite.

The Architektur-Nordstern says ``game_state`` MUST NOT contain role/team
fields — those leak the social-deduction premise. test_personalized_state.py
covers ghost-vs-alive viewer filtering; this file is the catch-all gate.
For every public-facing payload-building method, for every viewer × phase,
verify role and team never appear.
"""

from __future__ import annotations

import json
import random

import pytest

from app.game.game_room import GameRoom
from app.game.models import Phase


def _started(player_count: int = 6) -> tuple[GameRoom, list[str]]:
    room = GameRoom(code="ABCD")
    host = room.add_player("host")
    ids = [host.id]
    for i in range(player_count - 1):
        ids.append(room.add_player(f"p{i}").id)
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    return room, ids


def _assert_no_role_or_team(payload) -> None:
    """Recursively walk ``payload`` and fail if any dict has a role or team
    field. The Tier 3.5 endscreen DOES include roles intentionally; we
    accept that path separately. Anywhere else: if a key called role/team
    appears with a non-empty value, that's a leak."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key.lower() not in {"role", "team"}, (
                f"Public-facing payload leaks {key}={value!r}"
            )
            _assert_no_role_or_team(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_role_or_team(item)


# --- public_state in every phase --------------------------------------------


def test_public_state_in_lobby_has_no_role_or_team():
    room = GameRoom(code="ABCD")
    room.add_player("host")
    state = room.public_state()
    _assert_no_role_or_team(state)


def test_public_state_in_playing_has_no_role_or_team():
    room, _ = _started(player_count=6)
    state = room.public_state()
    _assert_no_role_or_team(state)


def test_public_state_in_meeting_has_no_role_or_team():
    room, ids = _started(player_count=6)
    # Force MEETING and take a snapshot.
    room.phase = Phase.MEETING
    room.meeting_caller_id = ids[0]
    room.meeting_remaining_seconds = 30.0
    room._snapshot_meeting_context(reporter_id=ids[0], body=None)
    state = room.public_state()
    _assert_no_role_or_team(state)


# --- per-viewer filtering ---------------------------------------------------


@pytest.mark.parametrize("viewer_index", [0, 1, 2, 3, 4, 5])
def test_public_state_for_every_viewer_has_no_role_or_team(viewer_index):
    """Sweep every viewer index; the filtered state must never leak."""
    room, ids = _started(player_count=6)
    state = room.public_state_for(ids[viewer_index])
    _assert_no_role_or_team(state)


def test_alive_viewer_does_not_see_ghost_player_in_public_state():
    """An alive viewer must not see a ghost teammate in the players list —
    that would leak which player got force-rebooted."""
    room, ids = _started(player_count=6)
    # Eliminate ids[1].
    room.players[ids[1]].is_alive = False
    alive_viewer = next(i for i in ids if room.players[i].is_alive and i != ids[1])
    state = room.public_state_for(alive_viewer)
    seen_ids = {p["id"] for p in state["players"]}
    assert ids[1] not in seen_ids


def test_ghost_viewer_sees_other_ghosts_but_no_role_field():
    """A ghost viewer sees all other players (alive + ghost) so spectators
    can keep watching, but the player dicts still have no role/team."""
    room, ids = _started(player_count=6)
    # Two ghosts: viewer + one other.
    room.players[ids[0]].is_alive = False
    room.players[ids[1]].is_alive = False
    state = room.public_state_for(ids[0])
    # Ghost viewer sees everyone.
    seen_ids = {p["id"] for p in state["players"]}
    assert seen_ids == set(ids)
    _assert_no_role_or_team(state)


# --- assigned_tasks_for: only own tasks -------------------------------------


def test_assigned_tasks_for_only_returns_own_tasks():
    """Every player has 3 assigned tasks (Tier 3.5). The accessor must only
    return their own — leaking another player's list is a strategic info
    disclosure (cover-task patterns differ between release + chaos)."""
    room, ids = _started(player_count=6)
    for pid in ids:
        own_tasks = room.assigned_tasks_for(pid)
        own_task_ids = {t["taskId"] for t in own_tasks}
        # Should match exactly the player's stored assignment.
        assert own_task_ids == set(room.players[pid].assigned_task_ids)


# --- private_role: never accessible without ownership -----------------------


def test_private_role_for_unknown_player_does_not_leak_other_role():
    """A request for a non-existent player_id raises NO_ROLE — must not
    fall through to returning some other player's role."""
    from app.game.runtime import GameRoomError

    room, _ = _started(player_count=4)
    with pytest.raises(GameRoomError) as exc:
        room.private_role_for("definitely-not-a-player-id")
    assert exc.value.code == "NO_ROLE"


# --- meeting context: never includes role/team -----------------------------


def test_meeting_context_alive_list_has_no_role_or_team():
    """The alive-list in meeting context exists for the voting overlay's
    discussion fuel — must not include role/team fields."""
    room, ids = _started(player_count=6)
    room.phase = Phase.MEETING
    room._snapshot_meeting_context(reporter_id=ids[0], body=None)
    wire = room.meeting_context.model_dump(by_alias=True)
    for entry in wire["alive"]:
        assert "role" not in entry
        assert "team" not in entry


# --- JSON-serializability sanity --------------------------------------------


def test_public_state_for_is_json_serialisable():
    """A subtle leak vector: if state contains a non-JSON-serialisable
    object that pretty-prints to something containing role data. Verify
    every viewer's state survives a JSON round-trip cleanly."""
    room, ids = _started(player_count=4)
    for pid in ids:
        state = room.public_state_for(pid)
        text = json.dumps(state)
        # Defensive: the text must not contain "chaos_agents" or
        # "release_team" — those team strings should never reach the wire
        # in a non-end-screen context.
        assert "chaos_agents" not in text, "team string 'chaos_agents' leaked into public_state_for"
        assert "release_team" not in text, "team string 'release_team' leaked into public_state_for"
