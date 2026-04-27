import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.game.game_map import GameMap, get_map_registry
from app.game.game_room import GameRoom, GameRoomError
from app.game.models import InputState, Phase
from app.game.sabotages import SABOTAGE_DEFINITIONS
from app.protocol import (
    AbortRound,
    CallEmergencyMeeting,
    CastVote,
    ErrorMsg,
    GameEndedMsg,
    GameStateMsg,
    JoinRoom,
    LeaveRoom,
    LobbyStateMsg,
    MiniGameCompletedMsg,
    MiniGameInput,
    MiniGameStartedMsg,
    MiniGameStateMsg,
    PlayerInput,
    PrivateRoleMsg,
    PrivateStateMsg,
    Rejoin,
    RepairSabotage,
    ReportBody,
    ReturnToLobby,
    RoomJoinedMsg,
    SelectMap,
    SetPreferredRole,
    SkipVote,
    StartGame,
    TaskHoldStart,
    TaskHoldStop,
    TriggerSabotage,
    TriggerTakedown,
    UseAbility,
    UseVent,
    VotingResultMsg,
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


def _available_maps_payload(registry: dict[str, GameMap] | None = None) -> list[dict[str, str]]:
    """Stable [{id, name}] list of all available maps, sorted by id."""
    reg = registry if registry is not None else get_map_registry()
    return [{"id": map_id, "name": gm.name} for map_id, gm in sorted(reg.items())]


def _lobby_state_msg(room: GameRoom) -> LobbyStateMsg:
    """Build a LobbyStateMsg with the public lobby snapshot + map listing.

    Includes the active map snapshot so non-host clients re-render the
    correct geometry after the host swaps maps in the lobby.
    """
    snapshot = room.lobby_snapshot()
    return LobbyStateMsg(
        **snapshot,
        available_maps=_available_maps_payload(),
        selected_map_id=room.map_id,
        map=room.map.model_dump(by_alias=True),
    )


def _private_role_msg(room: GameRoom, player_id: str) -> PrivateRoleMsg:
    """Tier 3.5: build a rich private_role payload — role-card metadata,
    available sabotages (chaos), assigned task ids + display blobs."""
    info = room.private_role_for(player_id)
    if info.team == "chaos_agents":
        # Chaos uses the role's curated sabotage list, not the global "all" set.
        available = list(info.available_sabotages) or [s.id for s in SABOTAGE_DEFINITIONS]
    else:
        available = []
    assigned = room.assigned_tasks_for(player_id)
    return PrivateRoleMsg(
        role=info.role,
        team=info.team,
        description=info.description,
        available_sabotages=available,
        title=info.title,
        short_blurb=info.short_blurb,
        strength_categories=list(info.strength_categories),
        weak_categories=list(info.weak_categories),
        ability_id=info.ability_id,
        ability_label=info.ability_label,
        ability_hint=info.ability_hint,
        max_coffee=info.max_coffee,
        assigned_task_ids=[t["taskId"] for t in assigned],
        assigned_tasks=assigned,
    )


def _game_state_msg_for(room: GameRoom, viewer_id: str, base: dict | None = None) -> GameStateMsg:
    """Per-viewer build of GameStateMsg — alive viewers see only alive players.

    Spectator-Mode (Tier 2.6): the server is authoritative for hiding ghosts
    from alive players. There's no all-viewers variant in the broadcast path
    anymore; ghosts/unknown viewers receive the full roster as a fallback.

    The tick loop passes a shared `base` to avoid re-serializing tasks/
    sabotages/events/bodies once per socket per tick.
    """
    return GameStateMsg.model_validate(room.public_state_for(viewer_id, base=base))


async def _tick_loop() -> None:
    try:
        while True:
            await asyncio.sleep(TICK_DT)
            for room in list(registry.active_rooms()):
                try:
                    if room.phase is Phase.PLAYING or room.phase is Phase.MEETING:
                        room.tick(TICK_DT)
                        if room.is_empty():
                            registry.drop_if_empty(room.code)
                            continue
                        # Per-socket personalized game_state: alive viewers
                        # only see alive players (ghosts are hidden from them).
                        # The non-player fields are identical across viewers,
                        # so we serialize them once per tick and reuse.
                        base = room._public_state_base()
                        for session in manager.sessions_in_room(room.code):
                            await session.ws.send_json(
                                envelope(
                                    "game_state",
                                    _game_state_msg_for(room, session.player_id, base=base),
                                )
                            )
                        # Per-chaos-agent private_state with their take-down
                        # cooldown. Release-team players don't get this msg
                        # (avoids cluttering their channel + zero-leak surface).
                        for session in manager.sessions_in_room(room.code):
                            player = room.players.get(session.player_id)
                            if player is None or player.team != "chaos_agents":
                                continue
                            await session.ws.send_json(
                                envelope(
                                    "private_state",
                                    PrivateStateMsg(**room.private_state_for(session.player_id)),
                                )
                            )
                    if room.last_voting_result is not None:
                        await manager.broadcast(
                            room.code,
                            envelope("voting_result", VotingResultMsg(**room.last_voting_result)),
                        )
                        room.last_voting_result = None
                    if room.phase is Phase.ENDED and not room.has_broadcast_end:
                        await manager.broadcast(
                            room.code,
                            envelope("game_ended", GameEndedMsg(**room.ended_snapshot())),
                        )
                        room.has_broadcast_end = True
                    # Tier 3.1: forward any mini-game lifecycle events the
                    # tick produced (cancel via take-down, meeting, or finish).
                    await _drain_mini_game_events(room)
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
                await ws.send_json(envelope("error", ErrorMsg(code="BAD_MESSAGE", message=str(e))))
                continue

            if isinstance(msg, JoinRoom):
                await _handle_join(ws, msg)
            elif isinstance(msg, Rejoin):
                await _handle_rejoin(ws, msg)
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
            elif isinstance(msg, CallEmergencyMeeting):
                await _handle_call_emergency_meeting(ws)
            elif isinstance(msg, CastVote):
                await _handle_cast_vote(ws, msg)
            elif isinstance(msg, SkipVote):
                await _handle_skip_vote(ws)
            elif isinstance(msg, TriggerTakedown):
                await _handle_trigger_takedown(ws, msg)
            elif isinstance(msg, ReportBody):
                await _handle_report_body(ws, msg)
            elif isinstance(msg, SelectMap):
                await _handle_select_map(ws, msg)
            elif isinstance(msg, ReturnToLobby):
                await _handle_return_to_lobby(ws)
            elif isinstance(msg, LeaveRoom):
                await _handle_leave_room(ws)
            elif isinstance(msg, AbortRound):
                await _handle_abort_round(ws)
            elif isinstance(msg, RepairSabotage):
                await _handle_repair_sabotage(ws, msg)
            elif isinstance(msg, UseVent):
                await _handle_use_vent(ws, msg)
            elif isinstance(msg, MiniGameInput):
                await _handle_mini_game_input(ws, msg)
            elif isinstance(msg, SetPreferredRole):
                await _handle_set_preferred_role(ws, msg)
            elif isinstance(msg, UseAbility):
                await _handle_use_ability(ws)
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
            RoomJoinedMsg(
                room_code=code,
                player_id=player.id,
                is_host=player.is_host,
                map=room.map.model_dump(by_alias=True),
            ),
        )
    )
    await manager.broadcast(code, envelope("lobby_state", _lobby_state_msg(room)))


async def _handle_rejoin(ws: WebSocket, msg: Rejoin) -> None:
    code = msg.payload.room_code.upper()
    room = registry.get(code)
    if room is None:
        await ws.send_json(
            envelope("error", ErrorMsg(code="REJOIN_NOT_AVAILABLE", message="Room not found."))
        )
        return
    try:
        player = room.mark_reconnected(msg.payload.player_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
        return
    manager.register(ws, player.id, code)
    await ws.send_json(
        envelope(
            "room_joined",
            RoomJoinedMsg(
                room_code=code,
                player_id=player.id,
                is_host=player.is_host,
                map=room.map.model_dump(by_alias=True),
            ),
        )
    )
    # If they have a role (mid-round), resend it.
    if player.role and player.team:
        await ws.send_json(envelope("private_role", _private_role_msg(room, player.id)))
    # Send fresh state — phase-appropriate.
    if room.phase is Phase.LOBBY:
        await ws.send_json(envelope("lobby_state", _lobby_state_msg(room)))
    else:
        await ws.send_json(envelope("game_state", _game_state_msg_for(room, player.id)))


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
    for player_id in list(room.players.keys()):
        await manager.send_to_player(
            room.code,
            player_id,
            envelope("private_role", _private_role_msg(room, player_id)),
        )
    # Immediate public state so clients switch to the game view.
    for s in manager.sessions_in_room(room.code):
        await s.ws.send_json(envelope("game_state", _game_state_msg_for(room, s.player_id)))


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
    await _drain_mini_game_events(room)


async def _handle_task_hold_stop(ws: WebSocket, msg: TaskHoldStop) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    room.apply_task_hold_stop(session.player_id, msg.payload.task_id)
    await _drain_mini_game_events(room)


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


async def _handle_repair_sabotage(ws: WebSocket, msg: RepairSabotage) -> None:
    """Tier 2.4: a player at the matching panel clears a live sabotage."""
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.repair_sabotage(session.player_id, msg.payload.sabotage_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))


async def _handle_use_vent(ws: WebSocket, msg: UseVent) -> None:
    """Tier 2.3: chaos teleports through a vent edge."""
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.use_vent(session.player_id, msg.payload.target_vent_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))


async def _handle_set_preferred_role(ws: WebSocket, msg: SetPreferredRole) -> None:
    """Tier 3.5: lobby preference. Stored on the player; respected when the
    next round starts. Broadcast lobby_state so other clients see the choice."""
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    room.set_preferred_role(session.player_id, msg.payload.role)
    await manager.broadcast(room.code, envelope("lobby_state", _lobby_state_msg(room)))


async def _handle_use_ability(ws: WebSocket) -> None:
    """Tier 3.5: trigger the player's role ability (Coffee Run / Rollback /
    Standup / Reproduce Bug). Errors are sent back as ErrorMsg."""
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.apply_use_ability(session.player_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))


async def _handle_mini_game_input(ws: WebSocket, msg: MiniGameInput) -> None:
    """Tier 3.1: forward player action into the active mini-game session."""
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.apply_mini_game_input(session.player_id, msg.payload.action, msg.payload.params)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
    await _drain_mini_game_events(room)


async def _drain_mini_game_events(room: GameRoom) -> None:
    """Forward queued mini-game lifecycle events to the owning sockets.

    Each event is per-player by design — only the player whose mini-game it
    is receives ``mini_game_started`` / ``state`` / ``completed`` frames. The
    rest of the room sees the player as ``in_progress`` on the task via the
    regular game_state broadcast.
    """
    events = room.drain_pending_mini_game_events()
    if not events:
        return
    for player_id, kind, payload in events:
        ws = manager.ws_for_player(room.code, player_id)
        if ws is None:
            continue
        if kind == "started":
            msg = MiniGameStartedMsg(**payload)
            await ws.send_json(envelope("mini_game_started", msg))
        elif kind == "state":
            msg = MiniGameStateMsg(**payload)
            await ws.send_json(envelope("mini_game_state", msg))
        elif kind == "completed":
            msg = MiniGameCompletedMsg(**payload)
            await ws.send_json(envelope("mini_game_completed", msg))


async def _handle_call_emergency_meeting(ws: WebSocket) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.call_emergency_meeting(requesting_player_id=session.player_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
    await _drain_mini_game_events(room)


async def _handle_cast_vote(ws: WebSocket, msg: CastVote) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.cast_vote(voter_id=session.player_id, target_id=msg.payload.target_player_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))


async def _handle_skip_vote(ws: WebSocket) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.skip_vote(voter_id=session.player_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))


async def _handle_trigger_takedown(ws: WebSocket, msg: TriggerTakedown) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.apply_takedown(killer_id=session.player_id, target_id=msg.payload.target_player_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
    await _drain_mini_game_events(room)


async def _handle_report_body(ws: WebSocket, msg: ReportBody) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.apply_report_body(reporter_id=session.player_id, body_id=msg.payload.body_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
    await _drain_mini_game_events(room)


async def _handle_select_map(ws: WebSocket, msg: SelectMap) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.set_map(
            requesting_player_id=session.player_id,
            map_id=msg.payload.map_id,
            registry=get_map_registry(),
        )
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
        return
    await manager.broadcast(room.code, envelope("lobby_state", _lobby_state_msg(room)))


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
        envelope("lobby_state", _lobby_state_msg(room)),
    )


async def _handle_leave_room(ws: WebSocket) -> None:
    """Player explicitly leaves the room (in-game menu → 'Lobby verlassen').

    Differs from _handle_disconnect in two ways: it is intentional, so we do
    not preserve identity for grace-period reconnect; and the WS stays open
    so the client can immediately re-join under a new identity if it wants.
    """
    session = manager.forget(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    if session.player_id not in room.players:
        return
    room.remove_player(session.player_id)
    if room.is_empty():
        registry.drop_if_empty(session.room_code)
        return
    if room.phase is Phase.LOBBY:
        await manager.broadcast(room.code, envelope("lobby_state", _lobby_state_msg(room)))
    else:
        for s in manager.sessions_in_room(room.code):
            await s.ws.send_json(envelope("game_state", _game_state_msg_for(room, s.player_id)))


async def _handle_abort_round(ws: WebSocket) -> None:
    """Host bricht eine laufende Runde ab (in-game menu → 'Runde beenden').

    Erlaubt nur in PLAYING/MEETING und nur dem Host. Setzt den Raum direkt
    zurück in die Lobby — kein Endscreen, weil die Rollen-Reveal bei einem
    bewussten Host-Abbruch unangebracht ist.
    """
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    player = room.players.get(session.player_id)
    if player is None or not player.is_host:
        await ws.send_json(
            envelope("error", ErrorMsg(code="NOT_HOST", message="Only host can abort the round."))
        )
        return
    if room.phase not in (Phase.PLAYING, Phase.MEETING):
        await ws.send_json(
            envelope(
                "error",
                ErrorMsg(code="WRONG_PHASE", message="Can only abort a running round."),
            )
        )
        return
    room.reset_for_new_round()
    await manager.broadcast(
        room.code,
        envelope("lobby_state", _lobby_state_msg(room)),
    )


async def _handle_disconnect(ws: WebSocket) -> None:
    session = manager.forget(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    player = room.players.get(session.player_id)
    if player is None:
        return

    if room.phase in (Phase.PLAYING, Phase.MEETING) and player.role and player.team:
        # Mid-round disconnect — preserve identity for grace period.
        room.mark_disconnected(session.player_id)
        # Broadcast updated state so others see them as disconnected.
        for s in manager.sessions_in_room(room.code):
            await s.ws.send_json(envelope("game_state", _game_state_msg_for(room, s.player_id)))
    else:
        # Lobby/Ended — fully remove.
        room.remove_player(session.player_id)
        if room.is_empty():
            registry.drop_if_empty(session.room_code)
            return
        if room.phase is Phase.LOBBY:
            await manager.broadcast(room.code, envelope("lobby_state", _lobby_state_msg(room)))
        else:
            for s in manager.sessions_in_room(room.code):
                await s.ws.send_json(envelope("game_state", _game_state_msg_for(room, s.player_id)))


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
    return FileResponse(_static_dir / "landing.html")


@app.get("/play")
async def play_page() -> FileResponse:
    return FileResponse(_static_dir / "index.html")


@app.get("/editor")
async def editor_page() -> FileResponse:
    """Serve the standalone map-editor page.

    The editor is a pure client-side tool — it only consumes/produces JSON
    files conforming to ``docs/maps.md``. No editor-specific server state.
    """
    return FileResponse(_static_dir / "editor" / "editor.html")


@app.get("/spielprinzip")
async def spielprinzip_page() -> FileResponse:
    """Serve the long-form game-overview subpage with screenshots, role
    matrix, sabotage-object map and design philosophy."""
    return FileResponse(_static_dir / "spielprinzip.html")
