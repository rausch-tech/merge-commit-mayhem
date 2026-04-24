import pytest
from pydantic import ValidationError

from app.protocol import (
    ErrorMsg,
    GameStateMsg,
    IncomingMessage,
    JoinRoom,
    LobbyStateMsg,
    PlayerInput,
    PrivateRoleMsg,
    RoomJoinedMsg,
    StartGame,
    parse_incoming,
)


# --- incoming parsing -------------------------------------------------------


def test_parse_join_room():
    raw = {"type": "join_room", "payload": {"roomCode": "ABCD", "playerName": "Sven"}}
    msg = parse_incoming(raw)
    assert isinstance(msg, JoinRoom)
    assert msg.payload.room_code == "ABCD"
    assert msg.payload.player_name == "Sven"


def test_parse_start_game():
    raw = {"type": "start_game", "payload": {}}
    msg = parse_incoming(raw)
    assert isinstance(msg, StartGame)


def test_parse_player_input():
    raw = {
        "type": "player_input",
        "payload": {"up": True, "down": False, "left": False, "right": True},
    }
    msg = parse_incoming(raw)
    assert isinstance(msg, PlayerInput)
    assert msg.payload.up is True
    assert msg.payload.right is True


def test_parse_rejects_unknown_type():
    with pytest.raises(ValidationError):
        parse_incoming({"type": "unknown_event", "payload": {}})


def test_parse_rejects_missing_type():
    with pytest.raises(ValidationError):
        parse_incoming({"payload": {}})


# --- outgoing serialization ------------------------------------------------


def test_room_joined_serializes_to_camel_case():
    msg = RoomJoinedMsg(room_code="ABCD", player_id="abc123", is_host=True)
    dumped = msg.model_dump(by_alias=True)
    assert dumped == {"roomCode": "ABCD", "playerId": "abc123", "isHost": True}


def test_lobby_state_serializes_to_camel_case():
    msg = LobbyStateMsg(
        room_code="ABCD",
        players=[
            {"id": "p1", "name": "Sven", "color": "#4ade80", "isHost": True},
        ],
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["roomCode"] == "ABCD"
    assert dumped["players"][0]["isHost"] is True


def test_game_state_serializes_to_camel_case():
    msg = GameStateMsg(
        phase="playing",
        remaining_seconds=598,
        players=[
            {"id": "p1", "name": "Sven", "x": 120.5, "y": 99.0, "color": "#4ade80", "isHost": True},
        ],
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["remainingSeconds"] == 598
    assert "phase" in dumped


def test_private_role_serializes_as_expected():
    msg = PrivateRoleMsg(
        role="vibe_coder",
        team="chaos_agents",
        description="Sabotier das Release.",
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped == {
        "role": "vibe_coder",
        "team": "chaos_agents",
        "description": "Sabotier das Release.",
    }


def test_error_msg_serializes_correctly():
    msg = ErrorMsg(code="NOT_HOST", message="Only host can start.")
    dumped = msg.model_dump(by_alias=True)
    assert dumped == {"code": "NOT_HOST", "message": "Only host can start."}
