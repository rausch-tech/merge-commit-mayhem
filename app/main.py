import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.game.game_room import GameRoom, GameRoomError
from app.game.models import InputState, Phase
from app.game.room_code import generate_unique
from app.protocol import (
    ErrorMsg,
    GameStateMsg,
    JoinRoom,
    LobbyStateMsg,
    PlayerInput,
    PrivateRoleMsg,
    RoomJoinedMsg,
    StartGame,
    envelope,
    parse_incoming,
)
from app.ws import ConnectionManager

TICK_HZ = 20
TICK_DT = 1.0 / TICK_HZ

log = logging.getLogger("mcm")


class GameRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, GameRoom] = {}

    def get_or_create(self, room_code: str) -> GameRoom:
        code = room_code.upper()
        room = self._rooms.get(code)
        if room is None:
            room = GameRoom(code=code)
            self._rooms[code] = room
        return room

    def get(self, room_code: str) -> GameRoom | None:
        return self._rooms.get(room_code.upper())

    def drop_if_empty(self, room_code: str) -> None:
        room = self._rooms.get(room_code.upper())
        if room is not None and room.is_empty():
            del self._rooms[room_code.upper()]

    def active_rooms(self) -> list[GameRoom]:
        return list(self._rooms.values())

    def known_codes(self) -> set[str]:
        return set(self._rooms.keys())


registry = GameRegistry()
manager = ConnectionManager()


async def _tick_loop() -> None:
    try:
        while True:
            await asyncio.sleep(TICK_DT)
            for room in list(registry.active_rooms()):
                if room.phase is not Phase.PLAYING:
                    continue
                try:
                    room.tick(TICK_DT)
                    msg = envelope(
                        "game_state",
                        GameStateMsg(
                            phase=room.phase.value,
                            remaining_seconds=int(room.remaining_seconds),
                            players=room.public_state()["players"],
                        ),
                    )
                    await manager.broadcast(room.code, msg)
                except Exception:
                    log.exception("tick failed for room %s", room.code)
    except asyncio.CancelledError:
        log.info("tick loop cancelled")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_tick_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.accept(ws)
    try:
        while True:
            raw = await ws.receive_json()
            try:
                msg = parse_incoming(raw)
            except ValidationError as e:
                await ws.send_json(
                    envelope("error", ErrorMsg(code="BAD_MESSAGE", message=str(e)))
                )
                continue

            if isinstance(msg, JoinRoom):
                await _handle_join(ws, msg)
            elif isinstance(msg, StartGame):
                await _handle_start(ws)
            elif isinstance(msg, PlayerInput):
                await _handle_input(ws, msg)
    except WebSocketDisconnect:
        pass
    finally:
        await _handle_disconnect(ws)


async def _handle_join(ws: WebSocket, msg: JoinRoom) -> None:
    code = msg.payload.room_code.upper()
    room = registry.get_or_create(code)
    try:
        player = room.add_player(msg.payload.player_name)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
        # If the room was created empty for this join, clean it up.
        registry.drop_if_empty(code)
        return

    manager.register(ws, player.id, code)
    await ws.send_json(
        envelope(
            "room_joined",
            RoomJoinedMsg(room_code=code, player_id=player.id, is_host=player.is_host),
        )
    )
    await manager.broadcast(code, envelope("lobby_state", LobbyStateMsg(**room.lobby_snapshot())))


async def _handle_start(ws: WebSocket) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.start(requesting_player_id=session.player_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
        return
    # Send private role to each player.
    for player_id in list(room.players.keys()):
        info = room.private_role_for(player_id)
        await manager.send_to_player(
            room.code,
            player_id,
            envelope(
                "private_role",
                PrivateRoleMsg(role=info.role, team=info.team, description=info.description),
            ),
        )
    # Immediate public state so clients switch to the game view.
    await manager.broadcast(
        room.code,
        envelope(
            "game_state",
            GameStateMsg(
                phase=room.phase.value,
                remaining_seconds=int(room.remaining_seconds),
                players=room.public_state()["players"],
            ),
        ),
    )


async def _handle_input(ws: WebSocket, msg: PlayerInput) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    room.apply_input(
        session.player_id,
        InputState(
            up=msg.payload.up,
            down=msg.payload.down,
            left=msg.payload.left,
            right=msg.payload.right,
        ),
    )


async def _handle_disconnect(ws: WebSocket) -> None:
    session = manager.forget(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    room.remove_player(session.player_id)
    if room.is_empty():
        registry.drop_if_empty(session.room_code)
        return
    # Rebroadcast lobby or game state so remaining clients see the departure.
    if room.phase is Phase.LOBBY:
        await manager.broadcast(
            room.code, envelope("lobby_state", LobbyStateMsg(**room.lobby_snapshot()))
        )
    else:
        await manager.broadcast(
            room.code,
            envelope(
                "game_state",
                GameStateMsg(
                    phase=room.phase.value,
                    remaining_seconds=int(room.remaining_seconds),
                    players=room.public_state()["players"],
                ),
            ),
        )


# Static frontend — MOUNT MUST BE LAST so /ws route wins.
_static_dir = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
