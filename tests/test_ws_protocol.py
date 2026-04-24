import json

import pytest
from fastapi.testclient import TestClient

from app.main import app, registry


@pytest.fixture(autouse=True)
def _reset_registry():
    yield
    registry._rooms.clear()


def _join(client_ws, room_code: str, name: str) -> dict:
    client_ws.send_json(
        {"type": "join_room", "payload": {"roomCode": room_code, "playerName": name}}
    )
    return client_ws.receive_json()  # room_joined


def _drain_until(ws, type_: str, max_msgs: int = 10) -> dict:
    """Receive messages until one with `type` arrives, or fail."""
    for _ in range(max_msgs):
        msg = ws.receive_json()
        if msg["type"] == type_:
            return msg
    raise AssertionError(f"Did not receive {type_!r} within {max_msgs} messages.")


def test_two_clients_can_join_same_room():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        joined_a = _join(ws_a, "ABCD", "Alice")
        assert joined_a["type"] == "room_joined"
        assert joined_a["payload"]["isHost"] is True

        # Alice receives lobby_state after joining.
        lobby_a1 = ws_a.receive_json()
        assert lobby_a1["type"] == "lobby_state"
        assert len(lobby_a1["payload"]["players"]) == 1

        joined_b = _join(ws_b, "ABCD", "Bob")
        assert joined_b["type"] == "room_joined"
        assert joined_b["payload"]["isHost"] is False

        # Both receive an updated lobby_state.
        lobby_a2 = ws_a.receive_json()
        lobby_b1 = ws_b.receive_json()
        assert lobby_a2["type"] == "lobby_state"
        assert lobby_b1["type"] == "lobby_state"
        assert len(lobby_a2["payload"]["players"]) == 2


def test_non_host_cannot_start_game():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "EFGH", "Alice")
        ws_a.receive_json()  # lobby
        _join(ws_b, "EFGH", "Bob")
        ws_a.receive_json()  # lobby update (2 players)
        ws_b.receive_json()  # lobby update

        ws_b.send_json({"type": "start_game", "payload": {}})
        err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_HOST"


def test_host_start_gives_private_role_and_game_state():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "JKLM", "Alice")
        ws_a.receive_json()
        _join(ws_b, "JKLM", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})

        # Each client should receive a private_role and then a game_state.
        role_a = _drain_until(ws_a, "private_role")
        state_a = _drain_until(ws_a, "game_state")
        role_b = _drain_until(ws_b, "private_role")
        state_b = _drain_until(ws_b, "game_state")

        assert role_a["payload"]["role"] in {"vibe_coder", "developer"}
        assert role_b["payload"]["role"] in {"vibe_coder", "developer"}
        # Exactly one is chaos, one is dev.
        roles = {role_a["payload"]["role"], role_b["payload"]["role"]}
        assert roles == {"vibe_coder", "developer"}

        assert state_a["payload"]["phase"] == "playing"
        # Public state must not leak roles.
        for p in state_a["payload"]["players"]:
            assert "role" not in p
            assert "team" not in p


def test_start_fails_with_only_one_player():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a:
        _join(ws_a, "NOPQ", "Alice")
        ws_a.receive_json()  # lobby

        ws_a.send_json({"type": "start_game", "payload": {}})
        err = ws_a.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_ENOUGH_PLAYERS"


def test_duplicate_name_rejected():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "RSTU", "Sven")
        ws_a.receive_json()

        ws_b.send_json(
            {"type": "join_room", "payload": {"roomCode": "RSTU", "playerName": "Sven"}}
        )
        err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NAME_TAKEN"


def test_disconnect_removes_player_and_promotes_host():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a:
        _join(ws_a, "VWXY", "Alice")
        ws_a.receive_json()

        # Second client joins inside nested with, then leaves.
        with client.websocket_connect("/ws") as ws_b:
            _join(ws_b, "VWXY", "Bob")
            ws_a.receive_json()  # lobby update after Bob joined
            ws_b.receive_json()
        # After ws_b closes, Alice should see a lobby update without Bob.
        lobby = ws_a.receive_json()
        assert lobby["type"] == "lobby_state"
        names = [p["name"] for p in lobby["payload"]["players"]]
        assert names == ["Alice"]
