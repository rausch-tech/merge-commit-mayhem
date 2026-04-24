import random
import uuid
from dataclasses import dataclass

from app.game.models import InputState, Phase, Player
from app.game.roles import RoleInfo, assign as assign_roles, description_for
from app.game.rooms import MAP_HEIGHT, MAP_WIDTH

MAX_PLAYERS = 6
MIN_PLAYERS_TO_START = 2
PLAYER_SPEED = 120.0  # px/s
PLAYER_RADIUS = 12
ROUND_SECONDS = 600.0

_START_POSITIONS = [
    (150.0, 100.0),  # open_space center
    (180.0, 120.0),
    (120.0, 80.0),
    (200.0, 100.0),
    (100.0, 120.0),
    (170.0, 70.0),
]

# Feste 6er-Palette (Doc 07 Farbsystem).
_COLOR_PALETTE = [
    "#4ade80",  # green
    "#60a5fa",  # blue
    "#fb923c",  # orange
    "#c084fc",  # purple
    "#facc15",  # yellow
    "#f87171",  # red
]


@dataclass
class GameRoomError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class GameRoom:
    def __init__(self, code: str) -> None:
        self.code = code
        self.phase: Phase = Phase.LOBBY
        self.players: dict[str, Player] = {}
        self.remaining_seconds: float = ROUND_SECONDS

        # Global gameplay stats (0 in LOBBY, reset on start()).
        self.release_progress: int = 0
        self.pipeline_stability: int = 100
        self.coffee_level: int = 100
        self.incident_count: int = 0

        # Per-player counters for the endscreen. Initialized on start().
        self.completed_tasks_by_player: dict[str, int] = {}
        self.triggered_sabotages_by_player: dict[str, int] = {}

        # Mandatory-meeting slow-down timer (seconds remaining; 0 = inactive).
        self.meeting_active_for: float = 0.0

        # End-of-round state.
        self.winner: str | None = None
        self.win_reason: str | None = None

    # --- player management -------------------------------------------------

    def add_player(self, name: str) -> Player:
        if len(self.players) >= MAX_PLAYERS:
            raise GameRoomError(code="ROOM_FULL", message="Room is full.")
        if any(p.name == name for p in self.players.values()):
            raise GameRoomError(
                code="NAME_TAKEN",
                message=f"Name {name!r} already taken in this room.",
            )
        player = Player(
            id=uuid.uuid4().hex,
            name=name,
            color=self._next_color(),
            is_host=len(self.players) == 0,
        )
        self.players[player.id] = player
        return player

    def remove_player(self, player_id: str) -> None:
        removed = self.players.pop(player_id, None)
        if removed is None:
            return
        if removed.is_host and self.players:
            # Promote oldest by joined_at.
            oldest = min(self.players.values(), key=lambda p: p.joined_at)
            oldest.is_host = True

    def is_empty(self) -> bool:
        return not self.players

    def _next_color(self) -> str:
        used = {p.color for p in self.players.values()}
        for color in _COLOR_PALETTE:
            if color not in used:
                return color
        # Fallback — kann nur passieren, wenn MAX_PLAYERS > Palette.
        raise GameRoomError(code="NO_COLORS", message="Color palette exhausted.")

    # --- lifecycle ---------------------------------------------------------

    def start(
        self,
        requesting_player_id: str,
        rng: random.Random | None = None,
    ) -> None:
        player = self.players.get(requesting_player_id)
        if player is None or not player.is_host:
            raise GameRoomError(
                code="NOT_HOST",
                message="Only the host can start the game.",
            )
        if self.phase is not Phase.LOBBY:
            raise GameRoomError(
                code="WRONG_PHASE",
                message=f"Cannot start in phase {self.phase.value}.",
            )
        if len(self.players) < MIN_PLAYERS_TO_START:
            raise GameRoomError(
                code="NOT_ENOUGH_PLAYERS",
                message=f"Need at least {MIN_PLAYERS_TO_START} players to start.",
            )

        role_map = assign_roles(list(self.players.keys()), rng=rng)
        for pid, info in role_map.items():
            self.players[pid].role = info.role
            self.players[pid].team = info.team

        for (pos_x, pos_y), player in zip(_START_POSITIONS, self.players.values()):
            player.x = pos_x
            player.y = pos_y

        # Reset global stats for a fresh round.
        self.release_progress = 0
        self.pipeline_stability = 100
        self.coffee_level = 100
        self.incident_count = 0
        self.meeting_active_for = 0.0
        self.winner = None
        self.win_reason = None
        self.completed_tasks_by_player = {pid: 0 for pid in self.players}
        self.triggered_sabotages_by_player = {pid: 0 for pid in self.players}

        self.remaining_seconds = ROUND_SECONDS
        self.phase = Phase.PLAYING

    # --- input + tick ------------------------------------------------------

    def apply_input(self, player_id: str, input_state: InputState) -> None:
        player = self.players.get(player_id)
        if player is None:
            return
        player.input_state = input_state

    def tick(self, dt: float) -> None:
        if self.phase is not Phase.PLAYING:
            return
        for player in self.players.values():
            dx = (int(player.input_state.right) - int(player.input_state.left))
            dy = (int(player.input_state.down) - int(player.input_state.up))
            if dx or dy:
                length = (dx * dx + dy * dy) ** 0.5
                player.x += (dx / length) * PLAYER_SPEED * dt
                player.y += (dy / length) * PLAYER_SPEED * dt
                # Clamp in map bounds.
                if player.x < 0:
                    player.x = 0.0
                elif player.x > MAP_WIDTH:
                    player.x = float(MAP_WIDTH)
                if player.y < 0:
                    player.y = 0.0
                elif player.y > MAP_HEIGHT:
                    player.y = float(MAP_HEIGHT)
        self.remaining_seconds = max(0.0, self.remaining_seconds - dt)

    # --- serialization accessors ------------------------------------------

    def public_state(self) -> dict:
        """Oeffentlicher GameState — enthaelt keine Rolle/Team/Input."""
        return {
            "phase": self.phase.value,
            "remainingSeconds": int(self.remaining_seconds),
            "releaseProgress": int(self.release_progress),
            "pipelineStability": int(self.pipeline_stability),
            "coffeeLevel": int(self.coffee_level),
            "incidentCount": int(self.incident_count),
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "x": round(p.x, 2),
                    "y": round(p.y, 2),
                    "color": p.color,
                    "isHost": p.is_host,
                }
                for p in self.players.values()
            ],
        }

    def lobby_snapshot(self) -> dict:
        return {
            "roomCode": self.code,
            "players": [
                {"id": p.id, "name": p.name, "color": p.color, "isHost": p.is_host}
                for p in self.players.values()
            ],
        }

    def private_role_for(self, player_id: str) -> RoleInfo:
        p = self.players[player_id]
        if p.role is None or p.team is None:
            raise GameRoomError(
                code="NO_ROLE",
                message="Player has no role assigned yet.",
            )
        return RoleInfo(
            role=p.role,
            team=p.team,
            description=description_for(p.role),
        )

    def reset_for_new_round(self) -> None:
        """
        Raum zurueck in LOBBY-Phase. Spieler bleiben drin, Rollen werden geloescht,
        Positionen und Inputs zurueckgesetzt. Host-Status bleibt erhalten.
        """
        if self.phase is Phase.LOBBY:
            return
        self.phase = Phase.LOBBY
        self.remaining_seconds = ROUND_SECONDS
        self.release_progress = 0
        self.pipeline_stability = 100
        self.coffee_level = 100
        self.incident_count = 0
        self.meeting_active_for = 0.0
        self.winner = None
        self.win_reason = None
        self.completed_tasks_by_player = {}
        self.triggered_sabotages_by_player = {}
        for player in self.players.values():
            player.role = None
            player.team = None
            player.x = 0.0
            player.y = 0.0
            player.input_state = InputState()
