"""Tier 2.3: Vent network — chaos-only teleport through vent edges."""

import random

import pytest

from app.game.game_room import GameRoom, GameRoomError


def _room_with_roles() -> tuple[GameRoom, str, str]:
    room = GameRoom(code="VENT")
    for n in ("p0", "p1", "p2", "p3"):
        room.add_player(n)
    host = next(iter(room.players))
    room.start(requesting_player_id=host, rng=random.Random(0))
    chaos_id = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    dev_id = next(p.id for p in room.players.values() if p.team == "release_team")
    return room, chaos_id, dev_id


def _place_at_vent(room: GameRoom, player_id: str, vent_id: str) -> None:
    v = next(v for v in room.map.vents if v.id == vent_id)
    room.players[player_id].x = float(v.x)
    room.players[player_id].y = float(v.y)


def test_chaos_can_teleport_through_connected_vent():
    room, chaos_id, _ = _room_with_roles()
    _place_at_vent(room, chaos_id, "v_open")
    target = next(v for v in room.map.vents if v.id == "v_server")
    room.use_vent(chaos_id, "v_server")
    assert room.players[chaos_id].x == pytest.approx(target.x)
    assert room.players[chaos_id].y == pytest.approx(target.y)


def test_dev_cannot_use_vent():
    room, _, dev_id = _room_with_roles()
    _place_at_vent(room, dev_id, "v_open")
    with pytest.raises(GameRoomError) as exc:
        room.use_vent(dev_id, "v_server")
    assert exc.value.code == "NOT_CHAOS_AGENT"


def test_vent_requires_proximity():
    room, chaos_id, _ = _room_with_roles()
    room.players[chaos_id].x = 50.0
    room.players[chaos_id].y = 50.0
    with pytest.raises(GameRoomError) as exc:
        room.use_vent(chaos_id, "v_server")
    assert exc.value.code == "NO_VENT_NEARBY"


def test_vent_target_must_be_connected():
    room, chaos_id, _ = _room_with_roles()
    _place_at_vent(room, chaos_id, "v_open")
    # Inject a phantom unconnected vent target.
    with pytest.raises(GameRoomError) as exc:
        room.use_vent(chaos_id, "does_not_exist")
    assert exc.value.code == "VENT_NOT_CONNECTED"


def test_dead_chaos_cannot_vent():
    room, chaos_id, _ = _room_with_roles()
    _place_at_vent(room, chaos_id, "v_open")
    room.players[chaos_id].is_alive = False
    with pytest.raises(GameRoomError) as exc:
        room.use_vent(chaos_id, "v_server")
    assert exc.value.code == "PLAYER_ELIMINATED"


def test_vent_outside_playing_phase_fails():
    room = GameRoom(code="VENT2")
    p = room.add_player("Alice")
    with pytest.raises(GameRoomError) as exc:
        room.use_vent(p.id, "v_open")
    assert exc.value.code == "WRONG_PHASE"


def test_public_state_carries_vents():
    room, chaos_id, _ = _room_with_roles()
    state = room.public_state()
    assert "vents" in state
    ids = {v["id"] for v in state["vents"]}
    assert ids == {"v_open", "v_server", "v_legacy"}
    v = next(v for v in state["vents"] if v["id"] == "v_open")
    assert "v_server" in v["connectedTo"]
