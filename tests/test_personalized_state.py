"""Tier 2.6 — Personalized public_state for ghosts.

Alive viewers see only alive players in their game_state snapshot. Dead
viewers (ghosts) see the full roster including other ghosts. Bodies, tasks,
sabotages, events, and meeting payloads are identical regardless of viewer.
"""

import random

from app.game.game_room import GameRoom


def _started_room(player_count: int = 4, seed: int = 0) -> tuple[GameRoom, list[str]]:
    if player_count < 4:
        player_count = 4
    room = GameRoom(code="PSTT")
    ids = [room.add_player(f"p{i}").id for i in range(player_count)]
    room.start(requesting_player_id=ids[0], rng=random.Random(seed))
    return room, ids


def test_alive_viewer_sees_only_alive_players():
    room, ids = _started_room()
    dead_pid = ids[0]
    alive_pid = ids[1]
    room.players[dead_pid].is_alive = False

    state = room.public_state_for(alive_pid)
    seen_ids = {p["id"] for p in state["players"]}
    assert dead_pid not in seen_ids
    assert alive_pid in seen_ids


def test_dead_viewer_sees_all_players():
    room, ids = _started_room()
    dead_pid = ids[0]
    other_dead = ids[1]
    room.players[dead_pid].is_alive = False
    room.players[other_dead].is_alive = False

    state = room.public_state_for(dead_pid)
    seen_ids = {p["id"] for p in state["players"]}
    # Sees self, the other dead, and every alive player.
    assert seen_ids == set(room.players.keys())


def test_unknown_viewer_sees_all_players():
    """Defensive fallback: an unknown viewer (e.g., a session that lost its
    player slot mid-tick) should still get a full, non-leaking snapshot.
    """
    room, ids = _started_room()
    room.players[ids[0]].is_alive = False
    state = room.public_state_for("not-a-real-player-id")
    seen_ids = {p["id"] for p in state["players"]}
    assert seen_ids == set(room.players.keys())


def test_alive_viewer_sees_themselves():
    room, ids = _started_room()
    alive_pid = ids[0]
    state = room.public_state_for(alive_pid)
    seen_ids = {p["id"] for p in state["players"]}
    assert alive_pid in seen_ids


def test_bodies_identical_across_viewers():
    room, ids = _started_room()
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    release_ids = [p.id for p in room.players.values() if p.team == "release_team"]
    target_id = release_ids[0]
    room.players[chaos_id].x, room.players[chaos_id].y = 500.0, 500.0
    room.players[target_id].x, room.players[target_id].y = 500.0, 505.0
    room.apply_takedown(killer_id=chaos_id, target_id=target_id)

    other_alive = release_ids[1]
    state_alive = room.public_state_for(other_alive)
    state_ghost = room.public_state_for(target_id)
    state_unfiltered = room.public_state()

    assert state_alive["bodies"] == state_ghost["bodies"]
    assert state_alive["bodies"] == state_unfiltered["bodies"]
    assert len(state_alive["bodies"]) == 1


def test_tasks_sabotages_events_meeting_identical_across_viewers():
    room, ids = _started_room()
    # Make ids[0] dead, ids[1] alive.
    room.players[ids[0]].is_alive = False
    state_alive = room.public_state_for(ids[1])
    state_ghost = room.public_state_for(ids[0])

    assert state_alive["tasks"] == state_ghost["tasks"]
    assert state_alive["sabotages"] == state_ghost["sabotages"]
    assert state_alive["events"] == state_ghost["events"]
    assert state_alive["meeting"] == state_ghost["meeting"]
    # Top-level scalars must match too.
    for key in ("phase", "remainingSeconds", "releaseProgress", "pipelineStability", "coffeeLevel"):
        assert state_alive[key] == state_ghost[key]


def test_public_state_unchanged_includes_all_players():
    """Backwards-compat: public_state() (no viewer) must still include everyone.
    Used by lobby snapshots and tests that pre-date the personalized API.
    """
    room, ids = _started_room()
    room.players[ids[0]].is_alive = False
    state = room.public_state()
    seen_ids = {p["id"] for p in state["players"]}
    assert seen_ids == set(room.players.keys())


def test_alive_viewer_does_not_leak_role_or_team():
    """Personalized state must NOT introduce role/team fields by accident."""
    room, ids = _started_room()
    state = room.public_state_for(ids[0])
    for p in state["players"]:
        assert "role" not in p
        assert "team" not in p
        assert "inputState" not in p
        assert "input_state" not in p
