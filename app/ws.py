from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class _Session:
    ws: WebSocket
    player_id: str
    room_code: str


@dataclass
class ConnectionManager:
    _by_ws: dict[int, _Session] = field(default_factory=dict)

    async def accept(self, ws: WebSocket) -> None:
        await ws.accept()

    def register(self, ws: WebSocket, player_id: str, room_code: str) -> None:
        self._by_ws[id(ws)] = _Session(ws=ws, player_id=player_id, room_code=room_code)

    def forget(self, ws: WebSocket) -> _Session | None:
        return self._by_ws.pop(id(ws), None)

    def session_for(self, ws: WebSocket) -> _Session | None:
        return self._by_ws.get(id(ws))

    def sessions_in_room(self, room_code: str) -> list[_Session]:
        return [s for s in self._by_ws.values() if s.room_code == room_code]

    async def send_to(self, ws: WebSocket, message: dict) -> None:
        await ws.send_json(message)

    async def send_to_player(self, room_code: str, player_id: str, message: dict) -> None:
        for session in self.sessions_in_room(room_code):
            if session.player_id == player_id:
                await session.ws.send_json(message)
                return

    async def broadcast(self, room_code: str, message: dict) -> None:
        for session in self.sessions_in_room(room_code):
            await session.ws.send_json(message)
