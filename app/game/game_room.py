import random
import uuid
from dataclasses import dataclass, field

from app.game.models import InputState, Phase, Player
from app.game.roles import RoleInfo, assign as assign_roles, description_for
from app.game.voting import SKIP_TARGET, all_chaos_eliminated, tally as _tally_votes
from app.game.game_map import GameMap, DEFAULT_MAP, compute_walls, war_room_bounds_for, task_position_map
from app.game.sabotages import (
    COFFEE_SLOW_SPEED,
    MEETING_DURATION,
    NORMAL_SPEED,
    SABOTAGE_DEFINITIONS,
    SabotageDefinition,
    sabotage_by_id,
)
from app.game.walls import resolve_wall_collision
from app.game.tasks import (
    TASK_DEFINITIONS,
    TASK_INTERACTION_RADIUS,
    TASK_RESPAWN_COOLDOWN,
    TaskDefinition,
    task_by_id,
)

MAX_PLAYERS = 6
MIN_PLAYERS_TO_START = 2
PLAYER_RADIUS = 12
ROUND_SECONDS = 720.0

MEETING_DURATION_SECONDS = 60.0

_MEETING_TITLES = [
    "Wer hat auf main gepusht?",
    "Warum sind die Tests rot?",
    "Wieso ist der Kunde im Sprint?",
    "Wer hat den KI-Agenten unbeaufsichtigt gelassen?",
    "Wer hat den Coffee Token verbraucht?",
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


@dataclass
class TaskRuntime:
    definition: TaskDefinition
    x: float
    y: float
    status: str = "available"   # "available" | "in_progress" | "cooldown"
    cooldown_remaining: float = 0.0
    per_player_progress: dict[str, float] = field(default_factory=dict)


@dataclass
class SabotageRuntime:
    definition: SabotageDefinition
    cooldown_remaining: float = 0.0
    active: bool = False     # True for coffee_outage while coffee==0, for meeting while meeting_active_for>0


class GameRoom:
    def __init__(self, code: str, game_map: GameMap | None = None) -> None:
        self.code = code
        self.map = game_map if game_map is not None else DEFAULT_MAP
        self._walls = compute_walls(self.map)
        self._war_room_bounds = war_room_bounds_for(self.map)
        self._task_position = task_position_map(self.map)

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
        self.tasks: dict[str, "TaskRuntime"] = {}
        self.sabotages: dict[str, "SabotageRuntime"] = {}

        # Mandatory-meeting slow-down timer (seconds remaining; 0 = inactive).
        self.meeting_active_for: float = 0.0

        # End-of-round state.
        self.winner: str | None = None
        self.win_reason: str | None = None
        self.has_broadcast_end: bool = False

        # Meeting state.
        self.meeting_remaining_seconds: float = 0.0
        self.meeting_caller_id: str | None = None
        self.meeting_title: str = ""
        self.votes: dict[str, str] = {}                       # voter_id -> target_id (or SKIP_TARGET)
        self.players_with_meeting_left: dict[str, bool] = {}  # player_id -> True if can still call
        self.last_voting_result: dict | None = None

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
        # Fallback -- kann nur passieren, wenn MAX_PLAYERS > Palette.
        raise GameRoomError(code="NO_COLORS", message="Color palette exhausted.")

    # --- lifecycle ---------------------------------------------------------

    def start(
        self,
        requesting_player_id: str,
        rng: random.Random | None = None,
        demo: bool = False,
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
        if not demo and len(self.players) < MIN_PLAYERS_TO_START:
            raise GameRoomError(
                code="NOT_ENOUGH_PLAYERS",
                message=f"Need at least {MIN_PLAYERS_TO_START} players to start.",
            )
        if demo and len(self.players) == 0:
            raise GameRoomError(
                code="NOT_ENOUGH_PLAYERS",
                message="Demo mode still needs at least one player.",
            )

        if demo and len(self.players) == 1:
            # Single-player demo: force vibe_coder so the player sees the
            # full chaos UI (sabotage buttons + role label).
            only_pid = next(iter(self.players))
            self.players[only_pid].role = "vibe_coder"
            self.players[only_pid].team = "chaos_agents"
        else:
            role_map = assign_roles(list(self.players.keys()), rng=rng)
            for pid, info in role_map.items():
                self.players[pid].role = info.role
                self.players[pid].team = info.team

        spawn_positions = [(s.x, s.y) for s in self.map.spawn_points]
        for (pos_x, pos_y), player in zip(spawn_positions, self.players.values()):
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

        self.tasks = {
            t.id: TaskRuntime(
                definition=t,
                x=self._task_position[t.id][0],
                y=self._task_position[t.id][1],
                status="available",
            )
            for t in TASK_DEFINITIONS
        }

        self.sabotages = {
            s.id: SabotageRuntime(definition=s) for s in SABOTAGE_DEFINITIONS
        }

        # Each player gets exactly one emergency meeting per round.
        self.players_with_meeting_left = {pid: True for pid in self.players}
        # Make sure everyone is alive at start.
        for player in self.players.values():
            player.is_alive = True

        self.remaining_seconds = ROUND_SECONDS
        self.phase = Phase.PLAYING

    # --- input + tick ------------------------------------------------------

    def apply_input(self, player_id: str, input_state: InputState) -> None:
        player = self.players.get(player_id)
        if player is None or not player.is_alive:
            return
        player.input_state = input_state

    def tick(self, dt: float) -> None:
        if self.phase is Phase.MEETING:
            self.meeting_remaining_seconds = max(0.0, self.meeting_remaining_seconds - dt)
            if self.meeting_remaining_seconds <= 0 or self._all_alive_voted():
                self._resolve_meeting()
            return
        if self.phase is not Phase.PLAYING:
            return
        for player in self.players.values():
            dx = (int(player.input_state.right) - int(player.input_state.left))
            dy = (int(player.input_state.down) - int(player.input_state.up))
            if dx or dy:
                speed = self._current_speed_for(player.id)
                length = (dx * dx + dy * dy) ** 0.5
                step_x = (dx / length) * speed * dt
                step_y = (dy / length) * speed * dt

                # Move along x first, then resolve walls.
                new_x = player.x + step_x
                if step_x != 0:
                    new_x, _ = resolve_wall_collision(
                        new_x, player.y, step_x, 0.0, self._walls,
                    )
                # Then y.
                new_y = player.y + step_y
                if step_y != 0:
                    _, new_y = resolve_wall_collision(
                        new_x, new_y, 0.0, step_y, self._walls,
                    )
                player.x = new_x
                player.y = new_y

                # Map-edge clamp (perimeter).
                if player.x < 0:
                    player.x = 0.0
                elif player.x > self.map.size.width:
                    player.x = float(self.map.size.width)
                if player.y < 0:
                    player.y = 0.0
                elif player.y > self.map.size.height:
                    player.y = float(self.map.size.height)
        self._tick_tasks(dt)
        self._tick_sabotages(dt)
        self.remaining_seconds = max(0.0, self.remaining_seconds - dt)
        self._check_win_conditions()

    # --- win conditions ----------------------------------------------------

    def _check_win_conditions(self) -> None:
        """
        Inspect state in priority order and transition to ENDED if a
        condition is met. Idempotent -- does nothing once already ENDED.
        """
        if self.phase is not Phase.PLAYING:
            return
        if self.pipeline_stability <= 0:
            self._finish_round("chaos_agents", "Die Pipeline ist tot.")
        elif all_chaos_eliminated(list(self.players.values())):
            self._finish_round("release_team", "Alle Chaos-Agenten wurden enttarnt.")
        elif self.release_progress >= 100:
            self._finish_round("release_team", "Release deployed.")
        elif self.remaining_seconds <= 0:
            self._finish_round("chaos_agents", "Das Release-Fenster ist geschlossen.")

    def _finish_round(self, winner: str, reason: str) -> None:
        self.phase = Phase.ENDED
        self.winner = winner
        self.win_reason = reason

    # --- speed helpers -----------------------------------------------------

    def _current_speed_for(self, player_id: str) -> float:
        """
        Returns the effective movement speed in px/s for a player this tick.
        Effects (coffee outage + mandatory meeting) do not stack -- floor is
        COFFEE_SLOW_SPEED, normal is NORMAL_SPEED.
        """
        if self.coffee_level == 0 or self.meeting_active_for > 0:
            return COFFEE_SLOW_SPEED
        return NORMAL_SPEED

    # --- tasks -------------------------------------------------------------

    def _task_in_range(self, player_id: str, task: "TaskRuntime") -> bool:
        player = self.players.get(player_id)
        if player is None:
            return False
        dx = player.x - task.x
        dy = player.y - task.y
        return (dx * dx + dy * dy) <= (TASK_INTERACTION_RADIUS * TASK_INTERACTION_RADIUS)

    def apply_task_hold_start(self, player_id: str, task_id: str) -> None:
        if self.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Tasks only during playing.")
        player = self.players.get(player_id)
        if player is None or not player.is_alive:
            raise GameRoomError(code="PLAYER_ELIMINATED", message="Eliminated players cannot do tasks.")
        task = self.tasks.get(task_id)
        if task is None:
            raise GameRoomError(code="UNKNOWN_TASK", message=f"Unknown task {task_id!r}.")
        if task.status == "cooldown":
            raise GameRoomError(code="TASK_ON_COOLDOWN", message="Task in cooldown.")
        if not self._task_in_range(player_id, task):
            raise GameRoomError(code="TASK_TOO_FAR", message="Too far from task.")
        task.status = "in_progress"
        task.per_player_progress.setdefault(player_id, 0.0)

    def apply_task_hold_stop(self, player_id: str, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if task is None:
            return
        task.per_player_progress.pop(player_id, None)
        if not task.per_player_progress and task.status == "in_progress":
            task.status = "available"

    def _apply_task_reward(self, definition: TaskDefinition) -> None:
        if definition.release_progress_reward:
            self.release_progress = min(
                100, self.release_progress + definition.release_progress_reward
            )
        if definition.pipeline_stability_reward:
            self.pipeline_stability = min(
                100, self.pipeline_stability + definition.pipeline_stability_reward
            )
        if definition.coffee_level_set is not None:
            self.coffee_level = definition.coffee_level_set

    def _tick_tasks(self, dt: float) -> None:
        for task in self.tasks.values():
            if task.status == "cooldown":
                task.cooldown_remaining -= dt
                if task.cooldown_remaining <= 0:
                    task.cooldown_remaining = 0.0
                    task.status = "available"
            elif task.status == "in_progress":
                finishers: list[str] = []
                still_progressing: dict[str, float] = {}
                for pid, progress in task.per_player_progress.items():
                    if not self._task_in_range(pid, task):
                        continue  # player left the radius; drop their progress
                    new_progress = progress + dt
                    if new_progress >= task.definition.required_seconds:
                        finishers.append(pid)
                    else:
                        still_progressing[pid] = new_progress
                if finishers:
                    # Deterministic tiebreak: lexicographically smallest player id.
                    winner_pid = sorted(finishers)[0]
                    self._apply_task_reward(task.definition)
                    self.completed_tasks_by_player[winner_pid] = (
                        self.completed_tasks_by_player.get(winner_pid, 0) + 1
                    )
                    task.per_player_progress = {}
                    task.status = "cooldown"
                    task.cooldown_remaining = TASK_RESPAWN_COOLDOWN
                else:
                    task.per_player_progress = still_progressing
                    if not still_progressing:
                        task.status = "available"

    # --- sabotages ---------------------------------------------------------

    def apply_sabotage(self, player_id: str, sabotage_id: str) -> None:
        if self.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Sabotages only during playing.")
        player = self.players.get(player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        if not player.is_alive:
            raise GameRoomError(code="PLAYER_ELIMINATED", message="Eliminated players cannot sabotage.")
        if player.team != "chaos_agents":
            raise GameRoomError(
                code="NOT_CHAOS_AGENT",
                message="Only chaos agents can trigger sabotages.",
            )
        sab = self.sabotages.get(sabotage_id)
        if sab is None:
            raise GameRoomError(code="UNKNOWN_SABOTAGE", message=f"Unknown {sabotage_id!r}.")
        if sab.cooldown_remaining > 0:
            raise GameRoomError(code="SABOTAGE_ON_COOLDOWN", message="Sabotage on cooldown.")

        # Apply the effect.
        if sabotage_id == "ci_cd_red":
            self.pipeline_stability = max(0, self.pipeline_stability - 20)
        elif sabotage_id == "coffee_outage":
            self.coffee_level = 0
        elif sabotage_id == "mandatory_meeting":
            self.meeting_active_for = MEETING_DURATION
        # Future sabotages: add here.

        sab.cooldown_remaining = sab.definition.cooldown_seconds
        self.triggered_sabotages_by_player[player_id] = (
            self.triggered_sabotages_by_player.get(player_id, 0) + 1
        )

    def _tick_sabotages(self, dt: float) -> None:
        for sab in self.sabotages.values():
            if sab.cooldown_remaining > 0:
                sab.cooldown_remaining = max(0.0, sab.cooldown_remaining - dt)
            # Recompute active flag for UI:
            if sab.definition.id == "coffee_outage":
                sab.active = self.coffee_level == 0
            elif sab.definition.id == "mandatory_meeting":
                sab.active = self.meeting_active_for > 0
            else:
                sab.active = False
        if self.meeting_active_for > 0:
            self.meeting_active_for = max(0.0, self.meeting_active_for - dt)

    # --- meeting + voting -------------------------------------------------

    def _is_in_war_room(self, player) -> bool:
        x_min, y_min, x_max, y_max = self._war_room_bounds
        return x_min <= player.x <= x_max and y_min <= player.y <= y_max

    def call_emergency_meeting(
        self,
        requesting_player_id: str,
        rng: random.Random | None = None,
    ) -> None:
        if self.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Meetings only during playing.")
        player = self.players.get(requesting_player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        if not player.is_alive:
            raise GameRoomError(code="PLAYER_ELIMINATED", message="Eliminated players cannot call meetings.")
        if not self._is_in_war_room(player):
            raise GameRoomError(code="NOT_IN_WAR_ROOM", message="Emergency meetings can only be called from the War Room.")
        if not self.players_with_meeting_left.get(requesting_player_id, False):
            raise GameRoomError(code="NO_MEETING_LEFT", message="You already used your emergency meeting this round.")

        # Transition to MEETING.
        self.players_with_meeting_left[requesting_player_id] = False
        self.meeting_caller_id = requesting_player_id
        self.meeting_remaining_seconds = MEETING_DURATION_SECONDS
        self.votes = {}
        r = rng or random.SystemRandom()
        self.meeting_title = r.choice(_MEETING_TITLES)
        self.phase = Phase.MEETING
        # Cancel ongoing task holds -- frozen during meeting.
        for task in self.tasks.values():
            task.per_player_progress = {}
            if task.status == "in_progress":
                task.status = "available"

    def cast_vote(self, voter_id: str, target_id: str) -> None:
        if self.phase is not Phase.MEETING:
            raise GameRoomError(code="WRONG_PHASE", message="No meeting active.")
        voter = self.players.get(voter_id)
        if voter is None or not voter.is_alive:
            raise GameRoomError(code="CANNOT_VOTE", message="Only living players can vote.")
        target = self.players.get(target_id)
        if target is None or not target.is_alive:
            raise GameRoomError(code="INVALID_TARGET", message="Vote target must be a living player.")
        self.votes[voter_id] = target_id

    def skip_vote(self, voter_id: str) -> None:
        if self.phase is not Phase.MEETING:
            raise GameRoomError(code="WRONG_PHASE", message="No meeting active.")
        voter = self.players.get(voter_id)
        if voter is None or not voter.is_alive:
            raise GameRoomError(code="CANNOT_VOTE", message="Only living players can vote.")
        self.votes[voter_id] = SKIP_TARGET

    def _living_player_ids(self) -> list[str]:
        return [pid for pid, p in self.players.items() if p.is_alive]

    def _all_alive_voted(self) -> bool:
        living = set(self._living_player_ids())
        return living.issubset(set(self.votes.keys()))

    def _resolve_meeting(self) -> str | None:
        """Tally votes, eliminate the loser if any, transition back to PLAYING.
        Returns the eliminated player_id or None.
        """
        eliminated_id = _tally_votes(self.votes)
        # Compute extra fields the client needs in voting_result.
        counts: dict[str, int] = {}
        for target in self.votes.values():
            counts[target] = counts.get(target, 0) + 1
        max_count = max(counts.values()) if counts else 0
        winners = [t for t, c in counts.items() if c == max_count]
        skip_won = (eliminated_id is None) and (
            (counts.get(SKIP_TARGET, 0) == max_count and max_count > 0)
        )
        named_tie = (
            eliminated_id is None
            and len(winners) > 1
            and all(w != SKIP_TARGET for w in winners)
        )

        was_chaos = False
        removed_name = ""
        if eliminated_id and eliminated_id in self.players:
            self.players[eliminated_id].is_alive = False
            was_chaos = self.players[eliminated_id].team == "chaos_agents"
            removed_name = self.players[eliminated_id].name

        self.last_voting_result = {
            "removed_player_id": eliminated_id or "",
            "removed_player_name": removed_name,
            "was_chaos_agent": was_chaos,
            "tie": named_tie,
            "skipped": skip_won,
        }

        # Reset meeting state and return to PLAYING.
        self.meeting_remaining_seconds = 0.0
        self.meeting_caller_id = None
        self.meeting_title = ""
        self.votes = {}
        self.phase = Phase.PLAYING
        return eliminated_id

    def _aggregate_vote_counts(self) -> dict[str, int]:
        """Return {target_id: count} aggregating cast votes; SKIP_TARGET stays as ''."""
        counts: dict[str, int] = {}
        for target in self.votes.values():
            counts[target] = counts.get(target, 0) + 1
        return counts

    # --- helper accessors -------------------------------------------------

    def task_position(self, task_id: str) -> tuple[float, float]:
        """Return (x, y) for the given task_id from the map's task_anchors."""
        return self._task_position[task_id]

    # --- serialization accessors ------------------------------------------

    def public_state(self) -> dict:
        """Oeffentlicher GameState -- enthaelt keine Rolle/Team/Input."""
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
                    "isAlive": p.is_alive,
                }
                for p in self.players.values()
            ],
            "tasks": [
                {
                    "id": t.definition.id,
                    "title": t.definition.title,
                    "room": t.definition.room,
                    "x": t.x,
                    "y": t.y,
                    "requiredSeconds": t.definition.required_seconds,
                    "status": t.status,
                    "progress": (
                        max(t.per_player_progress.values()) / t.definition.required_seconds
                        if t.per_player_progress
                        else 0.0
                    ),
                    "cooldownRemaining": round(t.cooldown_remaining, 2),
                }
                for t in self.tasks.values()
            ],
            "sabotages": [
                {
                    "id": s.definition.id,
                    "title": s.definition.title,
                    "cooldownRemaining": round(s.cooldown_remaining, 2),
                    "active": s.active,
                }
                for s in self.sabotages.values()
            ],
            "meeting": (
                {
                    "callerId": self.meeting_caller_id,
                    "title": self.meeting_title,
                    "remainingSeconds": int(self.meeting_remaining_seconds),
                    "votesCount": self._aggregate_vote_counts(),
                    "alreadyVoted": list(self.votes.keys()),
                }
                if self.phase is Phase.MEETING
                else None
            ),
        }

    def ended_snapshot(self) -> dict:
        """
        Payload for the game_ended message. Reveals roles and per-player
        stats. Only meaningful in phase ENDED.
        """
        return {
            "winner": self.winner or "",
            "reason": self.win_reason or "",
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "role": p.role or "",
                    "team": p.team or "",
                    "completedTasks": self.completed_tasks_by_player.get(p.id, 0),
                    "triggeredSabotages": self.triggered_sabotages_by_player.get(p.id, 0),
                    "isAlive": p.is_alive,
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
        self.has_broadcast_end = False
        self.completed_tasks_by_player = {}
        self.triggered_sabotages_by_player = {}
        self.tasks = {}
        self.sabotages = {}
        self.meeting_remaining_seconds = 0.0
        self.meeting_caller_id = None
        self.meeting_title = ""
        self.votes = {}
        self.players_with_meeting_left = {}
        self.last_voting_result = None
        for player in self.players.values():
            player.role = None
            player.team = None
            player.x = 0.0
            player.y = 0.0
            player.input_state = InputState()
            player.is_alive = True
