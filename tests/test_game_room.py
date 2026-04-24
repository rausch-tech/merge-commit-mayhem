import random

import pytest

from app.game.game_room import GameRoom, GameRoomError, MAX_PLAYERS
from app.game.models import Phase


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
