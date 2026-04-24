import random

import pytest

from app.game.game_room import GameRoom, GameRoomError, MAX_PLAYERS
from app.game.models import InputState, Phase


def test_first_player_becomes_host():
    room = GameRoom(code="ABCD")
    player = room.add_player("Sven")
    assert player.is_host is True
    assert player.name == "Sven"
    assert len(room.players) == 1
    assert room.phase is Phase.LOBBY


def test_second_player_is_not_host():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    second = room.add_player("Max")
    assert second.is_host is False


def test_add_player_rejects_duplicate_name():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.add_player("Sven")
    assert exc.value.code == "NAME_TAKEN"


def test_add_player_rejects_when_full():
    room = GameRoom(code="ABCD")
    for i in range(MAX_PLAYERS):
        room.add_player(f"player_{i}")
    with pytest.raises(GameRoomError) as exc:
        room.add_player("overflow")
    assert exc.value.code == "ROOM_FULL"


def test_remove_host_promotes_oldest_remaining():
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    second = room.add_player("Max")
    third = room.add_player("Lea")

    room.remove_player(host.id)
    assert host.id not in room.players
    # Max joined second → should become host.
    assert room.players[second.id].is_host is True
    assert room.players[third.id].is_host is False


def test_remove_last_player_marks_empty():
    room = GameRoom(code="ABCD")
    player = room.add_player("Sven")
    room.remove_player(player.id)
    assert room.is_empty() is True


def test_unique_colors_assigned():
    room = GameRoom(code="ABCD")
    colors = set()
    for i in range(MAX_PLAYERS):
        p = room.add_player(f"player_{i}")
        colors.add(p.color)
    assert len(colors) == MAX_PLAYERS


# --- start() ---------------------------------------------------------------


def _make_started_room(player_count: int = 3) -> GameRoom:
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    for i in range(player_count - 1):
        room.add_player(f"p{i}")
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    return room


def test_start_requires_host():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    second = room.add_player("Max")
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=second.id, rng=random.Random(0))
    assert exc.value.code == "NOT_HOST"


def test_start_requires_min_two_players():
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=host.id, rng=random.Random(0))
    assert exc.value.code == "NOT_ENOUGH_PLAYERS"


def test_start_requires_lobby_phase():
    room = _make_started_room(player_count=2)
    host_id = next(p.id for p in room.players.values() if p.is_host)
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=host_id, rng=random.Random(0))
    assert exc.value.code == "WRONG_PHASE"


def test_start_transitions_to_playing_and_assigns_roles():
    room = _make_started_room(player_count=3)
    assert room.phase is Phase.PLAYING
    roles = [p.role for p in room.players.values()]
    assert roles.count("vibe_coder") == 1
    assert roles.count("developer") == 2
    assert all(p.team in {"release_team", "chaos_agents"} for p in room.players.values())


def test_start_sets_timer_to_600():
    room = _make_started_room(player_count=2)
    assert room.remaining_seconds == 600.0


def test_start_places_players_on_map():
    room = _make_started_room(player_count=4)
    for p in room.players.values():
        assert 0 <= p.x <= 900
        assert 0 <= p.y <= 400


# --- apply_input + tick ----------------------------------------------------


def test_apply_input_updates_state():
    room = _make_started_room(player_count=2)
    any_player = next(iter(room.players.values()))
    room.apply_input(any_player.id, InputState(right=True))
    assert room.players[any_player.id].input_state.right is True


def test_tick_moves_player_right():
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x = 100.0
    room.apply_input(p.id, InputState(right=True))
    room.tick(0.1)  # 12 px bei 120 px/s
    assert p.x == pytest.approx(112.0)


def test_tick_clamps_at_map_borders():
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x = 895.0
    room.apply_input(p.id, InputState(right=True))
    room.tick(1.0)  # Versucht 120 px rechts → wird auf 900 geclampt.
    assert p.x == 900.0

    p.y = 5.0
    room.apply_input(p.id, InputState(right=False, up=True))
    room.tick(1.0)
    assert p.y == 0.0


def test_tick_diagonal_is_not_faster_than_axis():
    # Normalisierte Bewegung: Diagonal ≈ gleiche Geschwindigkeit wie axial.
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x, p.y = 400.0, 100.0
    room.apply_input(p.id, InputState(right=True, down=True))
    room.tick(0.1)
    dx, dy = p.x - 400.0, p.y - 100.0
    speed = (dx**2 + dy**2) ** 0.5
    assert speed == pytest.approx(12.0, abs=0.01)


def test_tick_decrements_timer():
    room = _make_started_room(player_count=2)
    room.tick(0.5)
    assert room.remaining_seconds == pytest.approx(599.5)


def test_tick_is_noop_in_lobby():
    room = GameRoom(code="ABCD")
    p1 = room.add_player("Sven")
    room.add_player("Max")
    room.apply_input(p1.id, InputState(right=True))
    start_x = p1.x
    room.tick(0.1)
    assert p1.x == start_x


# --- serialization accessors ----------------------------------------------


def test_public_state_excludes_secrets():
    room = _make_started_room(player_count=3)
    state = room.public_state()
    for player in state["players"]:
        assert "role" not in player
        assert "team" not in player
        assert "inputState" not in player
        assert "input_state" not in player


def test_private_role_returns_tuple():
    room = _make_started_room(player_count=2)
    any_id = next(iter(room.players))
    info = room.private_role_for(any_id)
    assert info.role in {"vibe_coder", "developer"}
    assert info.team in {"release_team", "chaos_agents"}
    assert info.description
