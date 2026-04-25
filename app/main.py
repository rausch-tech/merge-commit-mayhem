import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.game.game_room import GameRoom, GameRoomError
from app.game.models import InputState, Phase
from app.game.room_code import generate_unique
from app.game.sabotages import SABOTAGE_DEFINITIONS
from app.protocol import (
    ErrorMsg,
    GameEndedMsg,
    GameStateMsg,
    JoinRoom,
    LobbyStateMsg,
    PlayerInput,
    PrivateRoleMsg,
    ReturnToLobby,
    RoomJoinedMsg,
    StartGame,
    TaskHoldStart,
    TaskHoldStop,
    TriggerSabotage,
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


def _game_state_msg(room: GameRoom) -> GameStateMsg:
    """
    Build a GameStateMsg from the room's public_state dict. Using model_validate
    relies on public_state using camelCase keys that match GameStateMsg field aliases.
    """
    public = room.public_state()
    return GameStateMsg.model_validate(public)


async def _tick_loop() -> None:
    try:
        while True:
            await asyncio.sleep(TICK_DT)
            for room in list(registry.active_rooms()):
                try:
                    if room.phase is Phase.PLAYING:
                        room.tick(TICK_DT)
                        await manager.broadcast(
                            room.code, envelope("game_state", _game_state_msg(room))
                        )
                    if room.phase is Phase.ENDED and not room.has_broadcast_end:
                        await manager.broadcast(
                            room.code,
                            envelope("game_ended", GameEndedMsg(**room.ended_snapshot())),
                        )
                        room.has_broadcast_end = True
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
                await _handle_start(ws, msg)
            elif isinstance(msg, PlayerInput):
                await _handle_input(ws, msg)
            elif isinstance(msg, TaskHoldStart):
                await _handle_task_hold_start(ws, msg)
            elif isinstance(msg, TaskHoldStop):
                await _handle_task_hold_stop(ws, msg)
            elif isinstance(msg, TriggerSabotage):
                await _handle_trigger_sabotage(ws, msg)
            elif isinstance(msg, ReturnToLobby):
                await _handle_return_to_lobby(ws)
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


async def _handle_start(ws: WebSocket, msg: StartGame) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.start(requesting_player_id=session.player_id, demo=msg.payload.demo)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
        return
    # Send private role to each player.
    all_sabotage_ids = [s.id for s in SABOTAGE_DEFINITIONS]
    for player_id in list(room.players.keys()):
        info = room.private_role_for(player_id)
        available = all_sabotage_ids if info.team == "chaos_agents" else []
        await manager.send_to_player(
            room.code,
            player_id,
            envelope(
                "private_role",
                PrivateRoleMsg(
                    role=info.role,
                    team=info.team,
                    description=info.description,
                    available_sabotages=available,
                ),
            ),
        )
    # Immediate public state so clients switch to the game view.
    await manager.broadcast(room.code, envelope("game_state", _game_state_msg(room)))


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


async def _handle_task_hold_start(ws: WebSocket, msg: TaskHoldStart) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.apply_task_hold_start(session.player_id, msg.payload.task_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))


async def _handle_task_hold_stop(ws: WebSocket, msg: TaskHoldStop) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    room.apply_task_hold_stop(session.player_id, msg.payload.task_id)


async def _handle_trigger_sabotage(ws: WebSocket, msg: TriggerSabotage) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.apply_sabotage(session.player_id, msg.payload.sabotage_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))


async def _handle_return_to_lobby(ws: WebSocket) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    player = room.players.get(session.player_id)
    if player is None or not player.is_host:
        await ws.send_json(
            envelope("error", ErrorMsg(code="NOT_HOST", message="Only host can reset."))
        )
        return
    if room.phase is not Phase.ENDED:
        await ws.send_json(
            envelope(
                "error",
                ErrorMsg(code="WRONG_PHASE", message="Only allowed in ENDED phase."),
            )
        )
        return
    room.reset_for_new_round()
    await manager.broadcast(
        room.code,
        envelope("lobby_state", LobbyStateMsg(**room.lobby_snapshot())),
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
            envelope("game_state", _game_state_msg(room)),
        )


# Static frontend.
# Mount assets under /static (NOT /) so the mount never catches WebSocket
# scopes — otherwise a stray ws:// to anything other than /ws would crash
# StaticFiles with AssertionError. The root path is served explicitly below.
_static_dir = Path(__file__).parent.parent / "static"
_images_dir = Path(__file__).parent.parent / "images"
_sounds_dir = Path(__file__).parent.parent / "sounds"
if _images_dir.exists():
    app.mount("/images", StaticFiles(directory=_images_dir), name="images")
if _sounds_dir.exists():
    app.mount("/sounds", StaticFiles(directory=_sounds_dir), name="sounds")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/")
async def root_index() -> FileResponse:
    return FileResponse(_static_dir / "index.html")
