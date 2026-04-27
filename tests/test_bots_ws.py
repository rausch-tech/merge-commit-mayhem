"""WS-protocol tests for Tier 3.9.2 add_bot / remove_bot actions.

Covers:
- protocol parsing for AddBot / RemoveBot.
- host can add/remove bots; non-host gets NOT_HOST.
- bots show up in lobby_state with `isBot=True`.
- add_bot rejected outside the lobby.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, registry
from app.protocol import AddBot, RemoveBot, parse_incoming


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    yield
    registry._rooms.clear()


def _join(ws, room_code: str, name: str) -> dict:
    ws.send_json({"type": "join_room", "payload": {"roomCode": room_code, "playerName": name}})
    return ws.receive_json()


# --- protocol parsing -------------------------------------------------------


def test_parse_add_bot_with_empty_payload() -> None:
    msg = parse_incoming({"type": "add_bot", "payload": {}})
    assert isinstance(msg, AddBot)
    assert msg.payload.name is None


def test_parse_add_bot_with_name() -> None:
    msg = parse_incoming({"type": "add_bot", "payload": {"name": "Bot-Sven"}})
    assert isinstance(msg, AddBot)
    assert msg.payload.name == "Bot-Sven"


def test_parse_remove_bot() -> None:
    msg = parse_incoming({"type": "remove_bot", "payload": {"botId": "abc"}})
    assert isinstance(msg, RemoveBot)
    assert msg.payload.bot_id == "abc"


# --- host can add bot, lobby_state reflects it -----------------------------


def test_host_can_add_bot_and_lobby_state_carries_is_bot_flag() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        joined = _join(ws, "ABCD", "Host")
        assert joined["payload"]["isHost"] is True
        ws.receive_json()  # initial lobby_state

        ws.send_json({"type": "add_bot", "payload": {}})
        lobby = ws.receive_json()
        assert lobby["type"] == "lobby_state"
        names = {p["name"] for p in lobby["payload"]["players"]}
        # Host + bot present.
        assert "Host" in names
        bot = next(p for p in lobby["payload"]["players"] if p["name"].startswith("Bot-"))
        assert bot["isBot"] is True


def test_human_lobby_player_has_is_bot_false() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        _join(ws, "ABCD", "Host")
        lobby = ws.receive_json()
        host_row = lobby["payload"]["players"][0]
        assert host_row["isBot"] is False


# --- non-host gets NOT_HOST ------------------------------------------------


def test_non_host_cannot_add_bot() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "ABCD", "Host")
        ws_a.receive_json()  # initial lobby_state
        _join(ws_b, "ABCD", "Bob")
        # Drain the lobby_state broadcasts both sockets receive after Bob joins.
        ws_a.receive_json()
        ws_b.receive_json()

        ws_b.send_json({"type": "add_bot", "payload": {}})
        msg = ws_b.receive_json()
        assert msg["type"] == "error"
        assert msg["payload"]["code"] == "NOT_HOST"


def test_non_host_cannot_remove_bot() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "ABCD", "Host")
        ws_a.receive_json()  # initial lobby_state
        ws_a.send_json({"type": "add_bot", "payload": {}})
        ws_a.receive_json()  # broadcast

        _join(ws_b, "ABCD", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        room = registry.get("ABCD")
        assert room is not None
        bot_id = next(iter(room._bots.bot_ids()))
        ws_b.send_json({"type": "remove_bot", "payload": {"botId": bot_id}})
        msg = ws_b.receive_json()
        assert msg["type"] == "error"
        assert msg["payload"]["code"] == "NOT_HOST"


# --- host can remove bot ---------------------------------------------------


def test_host_can_remove_bot() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        _join(ws, "ABCD", "Host")
        ws.receive_json()  # initial lobby_state

        ws.send_json({"type": "add_bot", "payload": {}})
        lobby_after_add = ws.receive_json()
        bot_id = next(p["id"] for p in lobby_after_add["payload"]["players"] if p["isBot"])

        ws.send_json({"type": "remove_bot", "payload": {"botId": bot_id}})
        lobby_after_remove = ws.receive_json()
        assert lobby_after_remove["type"] == "lobby_state"
        assert all(not p["isBot"] for p in lobby_after_remove["payload"]["players"])


def test_remove_unknown_bot_id_is_silent() -> None:
    """Stale UI clicks (race after another host removed the bot) shouldn't
    spam every viewer with an error toast."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        _join(ws, "ABCD", "Host")
        ws.receive_json()
        ws.send_json({"type": "remove_bot", "payload": {"botId": "ghost"}})
        # No further frames expected — but the connection must still be alive.
        ws.send_json({"type": "add_bot", "payload": {}})
        next_msg = ws.receive_json()
        assert next_msg["type"] == "lobby_state"


# --- add bot rejected outside lobby ----------------------------------------


def test_add_bot_rejected_after_round_starts() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        _join(ws, "ABCD", "Host")
        ws.receive_json()
        # Pad to MIN_PLAYERS_TO_START via direct registry poke (mirrors
        # _pad_room_to_min in test_ws_protocol.py — duplicating to keep
        # this test file standalone).
        room = registry.get("ABCD")
        assert room is not None
        for i in range(3):
            room.add_player(f"_filler_{i}")

        ws.send_json({"type": "start_game", "payload": {}})
        # Drain start-game frames until we get private_role / game_state.
        for _ in range(8):
            msg = ws.receive_json()
            if msg["type"] == "game_state":
                break

        ws.send_json({"type": "add_bot", "payload": {}})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "WRONG_PHASE"
