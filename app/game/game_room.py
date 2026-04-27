import collections
import random
import uuid

from app.game.ai_flavor import generate_postmortem
from app.game.game_map import (
    DEFAULT_MAP,
    DEFAULT_MAP_ID,
    GameMap,
    compute_walls,
    task_position_map,
    war_room_bounds_for,
)
from app.game.models import InputState, Phase, Player
from app.game.roles import (
    RoleInfo,
    movement_speed_multiplier,
    role_by_id,
    task_speed_multiplier,
)
from app.game.roles import assign as assign_roles
from app.game.roles import (
    info_for as role_info_for,
)
from app.game.runtime import (
    VALID_EVENT_SEVERITIES as _VALID_EVENT_SEVERITIES,
)
from app.game.runtime import (
    Body,
    EventEntry,
    GameRoomError,
    MiniGameSession,
    SabotageRuntime,
    TaskRuntime,
)
from app.game.sabotages import (
    COFFEE_SLOW_SPEED,
    NORMAL_SPEED,
    SABOTAGE_DEFINITIONS,
    SabotageDefinition,
)
from app.game.tasks import (
    TASK_DEFINITIONS,
    TASK_INTERACTION_RADIUS,
    TASK_RESPAWN_COOLDOWN,
    VENT_INTERACTION_RADIUS,
    TaskDefinition,
)
from app.game.voting import SKIP_TARGET, all_chaos_eliminated
from app.game.voting import tally as _tally_votes
from app.game.walls import resolve_wall_collision
from app.protocol import MeetingAlive, MeetingBody, MeetingContext, MeetingRecentEvent

MAX_PLAYERS = 12
MIN_PLAYERS_TO_START = 4
PLAYER_RADIUS = 12
ROUND_SECONDS = 900.0
RECONNECT_GRACE_SECONDS = 30.0

INCIDENTS_LOSS_THRESHOLD = 100  # chaos wins once incidents reach this

MEETING_DURATION_SECONDS = 60.0

TAKEDOWN_RADIUS = 40.0  # px
TAKEDOWN_COOLDOWN = 25.0  # seconds
REPORT_RADIUS = 40.0  # px

_MEETING_TITLES = [
    "Wer hat auf main gepusht?",
    "Warum sind die Tests rot?",
    "Wieso ist der Kunde im Sprint?",
    "Wer hat den KI-Agenten unbeaufsichtigt gelassen?",
    "Wer hat den Coffee Token verbraucht?",
]

# Feste 12er-Palette: paarweise distinkt, sechs „klassische" Hues (Doc 07 Farbsystem)
# plus sechs zusaetzliche, gut unterscheidbare Toene fuer 7..12 Spieler.
_COLOR_PALETTE = [
    "#4ade80",  # green
    "#60a5fa",  # blue
    "#fb923c",  # orange
    "#c084fc",  # purple
    "#facc15",  # yellow
    "#f87171",  # red
    "#22d3ee",  # cyan
    "#f472b6",  # pink
    "#a3e635",  # lime
    "#fbbf24",  # amber
    "#94a3b8",  # slate
    "#e879f9",  # fuchsia
]


class GameRoom:
    def __init__(
        self,
        code: str,
        game_map: GameMap | None = None,
        map_id: str = DEFAULT_MAP_ID,
    ) -> None:
        self.code = code
        self.map = game_map if game_map is not None else DEFAULT_MAP
        self.map_id = map_id
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
        self.incidents: int = 0

        # Per-player counters for the endscreen. Initialized on start().
        self.completed_tasks_by_player: dict[str, int] = {}
        self.triggered_sabotages_by_player: dict[str, int] = {}
        self.tasks: dict[str, TaskRuntime] = {}
        self.sabotages: dict[str, SabotageRuntime] = {}

        # Mandatory-meeting slow-down timer (seconds remaining; 0 = inactive).
        self.meeting_active_for: float = 0.0

        # Tier 2.4: Lights-out flag. Server-authoritative; cleared by repairing
        # the lights_out panel.
        self.lights_off: bool = False

        # Tier 2.5: Comms outage flag. While true, task holds and other
        # sabotage triggers are rejected. Cleared via the comms_outage panel.
        self.comms_down: bool = False

        # End-of-round state.
        self.winner: str | None = None
        self.win_reason: str | None = None
        self.has_broadcast_end: bool = False

        # Meeting state.
        self.meeting_remaining_seconds: float = 0.0
        self.meeting_caller_id: str | None = None
        self.meeting_title: str = ""
        self.votes: dict[str, str] = {}  # voter_id -> target_id (or SKIP_TARGET)
        self.players_with_meeting_left: dict[str, bool] = {}  # player_id -> True if can still call
        self.last_voting_result: dict | None = None
        # Tier 3.6: meeting context snapshot taken when the round flips to
        # MEETING. Modeled via Pydantic (`MeetingContext`) so camelCase on the
        # wire is enforced by the same alias generator as the rest of the
        # protocol. Lets the overlay show body location, recent events, etc.
        self.meeting_context: MeetingContext | None = None
        # Tier 3.7: per-round endscreen summary (Awards + AI postmortem text).
        self.final_summary: dict | None = None

        # Rolling event feed (server-authoritative). Empty in LOBBY.
        self.events: collections.deque[EventEntry] = collections.deque(maxlen=20)
        self._next_event_seq: int = 1

        # Take-Down state. Bodies are created when a chaos agent eliminates a
        # release-team player; cooldowns gate the next take-down per chaos id.
        self.bodies: dict[str, Body] = {}
        self.takedown_cooldowns: dict[str, float] = {}

        # Tier 3.1: active mini-games per player (max one each). Keyed by
        # player_id; the framework treats this as authoritative.
        self.active_mini_games: dict[str, MiniGameSession] = {}
        # Tier 3.1: framework-emitted events for mini-game lifecycle. Drained
        # by the WS layer once per tick / on_input. Each entry is a tuple
        # (player_id, kind, payload) where kind is 'started'|'state'|'completed'.
        self.pending_mini_game_events: list[tuple[str, str, dict]] = []

        # Slice 2 refactor: domain controllers. The room owns the data; each
        # controller owns its rules. Controllers reach back via self._room
        # for cross-domain reads (e.g. mini-game completion triggers a task
        # reward).
        from app.game.controllers.mini_game import MiniGameController
        from app.game.controllers.sabotages import SabotagesController

        self._mini_games = MiniGameController(self)
        self._sabotages_ctl = SabotagesController(self)

    def _emit_event(self, severity: str, message: str) -> None:
        """Append an event to the rolling buffer. Internal use only."""
        if severity not in _VALID_EVENT_SEVERITIES:
            raise ValueError(
                f"Invalid event severity {severity!r}; must be one of {_VALID_EVENT_SEVERITIES}."
            )
        self.events.append(EventEntry(seq=self._next_event_seq, severity=severity, message=message))
        self._next_event_seq += 1

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

    def mark_disconnected(self, player_id: str) -> None:
        """
        Player's WS closed while in PLAYING/MEETING phase. Keep their slot,
        mark them disconnected, release any task holds, transfer host if
        needed. The grace-period sweep in tick() will fully remove them
        after RECONNECT_GRACE_SECONDS.
        """
        import time

        player = self.players.get(player_id)
        if player is None:
            return
        player.is_connected = False
        player.disconnected_at_monotonic = time.monotonic()
        if self.phase in (Phase.PLAYING, Phase.MEETING):
            self._emit_event("warn", f"{player.name} ist offline gegangen.")
        # Release any task holds.
        for task in self.tasks.values():
            if player_id in task.per_player_progress:
                task.per_player_progress.pop(player_id)
                if not task.per_player_progress and task.status == "in_progress":
                    task.status = "available"
        # Tier 3.1: drop any active mini-game — state is not preserved across
        # reconnects (the player resumes outside the modal).
        if player_id in self.active_mini_games:
            self._cancel_mini_game(player_id, "disconnected")
        # Reset their input.
        player.input_state = InputState()
        # Host transfer if they were host. If no candidate exists (solo
        # session), leave the bit on the disconnected player so they remain
        # host on rejoin. The grace-period sweep (remove_player) handles the
        # transfer if they never come back.
        if player.is_host:
            living_others = [
                p for p in self.players.values() if p.id != player_id and p.is_connected
            ]
            others = [p for p in self.players.values() if p.id != player_id]
            successor = None
            if living_others:
                successor = min(living_others, key=lambda p: p.joined_at)
            elif others:
                successor = min(others, key=lambda p: p.joined_at)
            if successor is not None:
                player.is_host = False
                successor.is_host = True

    def mark_reconnected(self, player_id: str) -> "Player":
        """
        Reattach a disconnected player. Returns the Player object on success.
        Raises GameRoomError(REJOIN_NOT_AVAILABLE) if the player is unknown,
        already connected, or grace period expired.
        """
        import time

        player = self.players.get(player_id)
        if player is None:
            raise GameRoomError(code="REJOIN_NOT_AVAILABLE", message="Player not found in room.")
        if player.is_connected:
            raise GameRoomError(
                code="REJOIN_NOT_AVAILABLE",
                message="Player is already connected — duplicate session?",
            )
        if player.disconnected_at_monotonic is None:
            raise GameRoomError(
                code="REJOIN_NOT_AVAILABLE",
                message="Player has no disconnect timestamp.",
            )
        elapsed = time.monotonic() - player.disconnected_at_monotonic
        if elapsed > RECONNECT_GRACE_SECONDS:
            raise GameRoomError(
                code="REJOIN_NOT_AVAILABLE",
                message="Grace period expired.",
            )
        player.is_connected = True
        player.disconnected_at_monotonic = None
        if self.phase in (Phase.PLAYING, Phase.MEETING):
            self._emit_event("info", f"{player.name} ist zurück.")
        return player

    def _sweep_disconnected(self) -> list[str]:
        """Called from tick(). Remove players whose grace expired. Returns the
        list of removed player ids so the caller can broadcast the change."""
        import time

        now = time.monotonic()
        removed = []
        for pid, player in list(self.players.items()):
            if player.is_connected:
                continue
            if player.disconnected_at_monotonic is None:
                continue
            if now - player.disconnected_at_monotonic > RECONNECT_GRACE_SECONDS:
                name = player.name
                self.remove_player(pid)
                removed.append(pid)
                if self.phase is not Phase.LOBBY:
                    self._emit_event("warn", f"{name} ist endgültig raus.")
        return removed

    def _next_color(self) -> str:
        used = {p.color for p in self.players.values()}
        for color in _COLOR_PALETTE:
            if color not in used:
                return color
        # Fallback -- kann nur passieren, wenn MAX_PLAYERS > Palette.
        raise GameRoomError(code="NO_COLORS", message="Color palette exhausted.")

    # --- map selection -----------------------------------------------------

    def set_map(
        self,
        requesting_player_id: str,
        map_id: str,
        registry: dict[str, GameMap],
    ) -> None:
        """Host swaps the active map while the room is in LOBBY.

        Tasks/sabotages/players are not reset here — they are reinitialized at
        ``start()`` from the new map's data. Updating ``_walls``,
        ``_war_room_bounds`` and ``_task_position`` is enough at this point.
        """
        if self.phase is not Phase.LOBBY:
            raise GameRoomError(
                code="WRONG_PHASE",
                message=f"Map kann nur in der Lobby gewechselt werden (aktuell {self.phase.value}).",
            )
        player = self.players.get(requesting_player_id)
        if player is None or not player.is_host:
            raise GameRoomError(
                code="NOT_HOST",
                message="Nur der Host kann die Map wechseln.",
            )
        new_map = registry.get(map_id)
        if new_map is None:
            raise GameRoomError(
                code="UNKNOWN_MAP",
                message=f"Unbekannte Map {map_id!r}.",
            )
        self.map = new_map
        self.map_id = map_id
        self._walls = compute_walls(new_map)
        self._war_room_bounds = war_room_bounds_for(new_map)
        self._task_position = task_position_map(new_map)

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
            prefs = {pid: p.preferred_role for pid, p in self.players.items()}
            role_map = assign_roles(list(self.players.keys()), rng=rng, preferences=prefs)
            for pid, info in role_map.items():
                self.players[pid].role = info.role
                self.players[pid].team = info.team

        # Tier 3.5: per-player coffee + ability state. Done after roles are
        # assigned so we can read max_coffee from the role definition.
        for player in self.players.values():
            rd = role_by_id(player.role)
            player.max_coffee = rd.max_coffee
            player.coffee_energy = rd.max_coffee
            player.ability_used = False
            player.assigned_task_ids = []

        spawn_positions = [(s.x, s.y) for s in self.map.spawn_points]
        for (pos_x, pos_y), player in zip(spawn_positions, self.players.values(), strict=False):
            player.x = pos_x
            player.y = pos_y

        # Reset global stats for a fresh round.
        self.release_progress = 0
        self.pipeline_stability = 100
        self.coffee_level = 100
        self.incidents = 0
        self.meeting_active_for = 0.0
        self.lights_off = False
        self.comms_down = False
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

        # Tier 3.5: each player gets 3 personal tasks. Release players see
        # them in the sidebar; chaos players see them as plausible "fake
        # tasks" matching their cover persona. Both lists are stored on the
        # Player.assigned_task_ids field — server uses them only to highlight
        # the per-player task panel client-side; it does NOT block other
        # players from doing tasks (no hard sackgassen — see feedback doc
        # 14.1). Same field for both teams keeps the wire shape identical.
        self._allocate_personal_tasks(rng or random.SystemRandom())

        self.sabotages = {s.id: SabotageRuntime(definition=s) for s in SABOTAGE_DEFINITIONS}

        # Each player gets exactly one emergency meeting per round.
        self.players_with_meeting_left = {pid: True for pid in self.players}
        # Make sure everyone is alive at start.
        for player in self.players.values():
            player.is_alive = True

        # Take-Down: clear bodies, prime cooldown dict for chaos agents.
        self.bodies = {}
        self.takedown_cooldowns = {
            pid: 0.0 for pid, p in self.players.items() if p.team == "chaos_agents"
        }

        self.remaining_seconds = ROUND_SECONDS
        self.phase = Phase.PLAYING

        # Reset and seed event feed for the fresh round.
        self.events.clear()
        self._next_event_seq = 1
        self._emit_event("info", "Release-Fenster offen. Los geht's.")

    # --- input + tick ------------------------------------------------------

    def apply_input(self, player_id: str, input_state: InputState) -> None:
        # Ghosts (is_alive=False) are allowed to send input — they keep moving
        # as spectators. Disconnected players still cannot.
        player = self.players.get(player_id)
        if player is None or not player.is_connected:
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
            # Tier 3.1: a player inside a mini-game is locked in place — their
            # WASD inputs are ignored until the session ends.
            if player.id in self.active_mini_games:
                continue
            dx = int(player.input_state.right) - int(player.input_state.left)
            dy = int(player.input_state.down) - int(player.input_state.up)
            if dx or dy:
                # Ghosts ignore the slow-down sabotages and pass through walls.
                speed = self._current_speed_for(player.id) if player.is_alive else NORMAL_SPEED
                length = (dx * dx + dy * dy) ** 0.5
                step_x = (dx / length) * speed * dt
                step_y = (dy / length) * speed * dt

                if player.is_alive:
                    # Move along x first, then resolve walls.
                    new_x = player.x + step_x
                    if step_x != 0:
                        new_x, _ = resolve_wall_collision(
                            new_x,
                            player.y,
                            step_x,
                            0.0,
                            self._walls,
                        )
                    # Then y.
                    new_y = player.y + step_y
                    if step_y != 0:
                        _, new_y = resolve_wall_collision(
                            new_x,
                            new_y,
                            0.0,
                            step_y,
                            self._walls,
                        )
                else:
                    # Ghosts: no wall collision resolution.
                    new_x = player.x + step_x
                    new_y = player.y + step_y
                player.x = new_x
                player.y = new_y

                # Map-edge clamp (perimeter) — applies to ghosts too.
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
        self._tick_takedown_cooldowns(dt)
        self._tick_coffee_energy(dt)
        self.remaining_seconds = max(0.0, self.remaining_seconds - dt)
        self._sweep_disconnected()
        self._check_win_conditions()

    # --- coffee energy (Tier 3.5) -----------------------------------------

    def _tick_coffee_energy(self, dt: float) -> None:
        """Each alive player's personal coffee_energy decays over time. Decay
        rate scales with the role's coffee_decay_modifier (DevOps drains fast,
        Caffeine Collector / QA Lead sip slowly). Ghosts don't decay — they
        no longer interact with the team economy."""
        if dt <= 0:
            return
        base_decay = 1.4  # points per second at modifier=1.0
        for player in self.players.values():
            if not player.is_alive:
                continue
            rd = role_by_id(player.role)
            decay = base_decay * rd.coffee_decay_modifier * dt
            new_energy = max(0.0, player.coffee_energy - decay)
            player.coffee_energy = new_energy

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
            return
        if self.incidents >= INCIDENTS_LOSS_THRESHOLD:
            self._finish_round("chaos_agents", "Zu viele Incidents. Niemand weiß mehr, was läuft.")
            return
        if all_chaos_eliminated(list(self.players.values())):
            self._finish_round("release_team", "Alle Chaos-Agenten wurden enttarnt.")
            return
        chaos_alive = sum(
            1 for p in self.players.values() if p.is_alive and p.team == "chaos_agents"
        )
        release_alive = sum(
            1 for p in self.players.values() if p.is_alive and p.team == "release_team"
        )
        # Parity only fires if a release team existed in this round at all.
        # Demo-Mode (1 player forced to chaos) has zero release players from the
        # start and would otherwise trigger a chaos win on the first tick.
        total_release = sum(1 for p in self.players.values() if p.team == "release_team")
        if total_release > 0 and chaos_alive > 0 and chaos_alive >= release_alive:
            self._finish_round("chaos_agents", "Chaos hat die Mehrheit.")
            return
        if self.release_progress >= 100:
            self._finish_round("release_team", "Release deployed.")
            return
        if self.remaining_seconds <= 0:
            self._finish_round("chaos_agents", "Das Release-Fenster ist geschlossen.")
            return

    def _finish_round(self, winner: str, reason: str) -> None:
        severity = "info" if winner == "release_team" else "danger"
        self._emit_event(severity, f"Runde vorbei: {reason}")
        self.phase = Phase.ENDED
        self.winner = winner
        self.win_reason = reason
        # Tier 3.1: end any active mini-games — no reward for in-flight sessions.
        self._cancel_all_mini_games("round_ended")
        # Tier 3.7: build the per-round summary + AI-styled postmortem so the
        # endscreen has something to show beyond just the winner.
        try:
            self.final_summary = self._build_final_summary()
        except Exception:  # noqa: BLE001 — endscreen flavor must never crash a round
            self.final_summary = None

    # --- speed helpers -----------------------------------------------------

    def _current_speed_for(self, player_id: str) -> float:
        """Effective movement speed in px/s for this player this tick.

        Floor is COFFEE_SLOW_SPEED (set by global coffee_outage / mandatory
        meeting), otherwise NORMAL_SPEED scaled by the player's role + own
        coffee_energy (Tier 3.5)."""
        if self.coffee_level == 0 or self.meeting_active_for > 0:
            return COFFEE_SLOW_SPEED
        player = self.players.get(player_id)
        if player is None:
            return NORMAL_SPEED
        return NORMAL_SPEED * movement_speed_multiplier(player.role, player.coffee_energy)

    # --- personal-task allocation (Tier 3.5) -------------------------------

    def _allocate_personal_tasks(self, rng: random.Random) -> None:
        """Pick 3 task ids per player. Release players favour their role's
        strength categories; chaos players get a plausible cover-persona
        list. Stored on Player.assigned_task_ids for the wire."""
        all_task_ids = [t.id for t in TASK_DEFINITIONS]
        for player in self.players.values():
            rd = role_by_id(player.role)
            strong_pool = [t.id for t in TASK_DEFINITIONS if t.category in rd.strength_categories]
            other_pool = [t.id for t in TASK_DEFINITIONS if t.id not in strong_pool]
            picks: list[str] = []
            shuffled_strong = list(strong_pool)
            rng.shuffle(shuffled_strong)
            shuffled_other = list(other_pool)
            rng.shuffle(shuffled_other)
            # Two from strengths if possible, then fill with others. Chaos
            # roles have empty strength_categories → falls through to random.
            for tid in shuffled_strong[:2]:
                picks.append(tid)
            for tid in shuffled_other:
                if len(picks) >= 3:
                    break
                if tid not in picks:
                    picks.append(tid)
            # Defensive: if a role somehow has zero strengths AND zero others
            # (impossible today), fall back to all_task_ids.
            if not picks:
                picks = list(all_task_ids[:3])
            player.assigned_task_ids = picks[:3]

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
        # Tier 2.5: Slack-Down — release team can't see or progress tasks.
        if self.comms_down:
            raise GameRoomError(code="COMMS_DOWN", message="Slack ist down — keine Tasks.")
        # Ghosts may complete tasks — they help the release-team win.
        player = self.players.get(player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        task = self.tasks.get(task_id)
        if task is None:
            raise GameRoomError(code="UNKNOWN_TASK", message=f"Unknown task {task_id!r}.")
        if task.status == "cooldown":
            raise GameRoomError(code="TASK_ON_COOLDOWN", message="Task in cooldown.")
        if not self._task_in_range(player_id, task):
            raise GameRoomError(code="TASK_TOO_FAR", message="Too far from task.")
        # Tier 3.1: when the task has an associated mini-game, switch into the
        # mini-game flow instead of starting hold-E progress. Hold-E remains
        # the default for tasks without mini_game set.
        if task.definition.mini_game:
            if player_id in self.active_mini_games:
                raise GameRoomError(
                    code="MINI_GAME_ALREADY_ACTIVE",
                    message="Finish the current mini-game first.",
                )
            self._start_mini_game(player_id, task_id, task.definition.mini_game)
            return
        task.status = "in_progress"
        task.per_player_progress.setdefault(player_id, 0.0)

    def apply_task_hold_stop(self, player_id: str, task_id: str) -> None:
        # Tier 3.1: a stop on a mini-game-bearing task cancels the mini-game.
        if player_id in self.active_mini_games:
            session = self.active_mini_games[player_id]
            if session.task_id == task_id:
                self._cancel_mini_game(player_id, "cancelled")
                return
        task = self.tasks.get(task_id)
        if task is None:
            return
        task.per_player_progress.pop(player_id, None)
        if not task.per_player_progress and task.status == "in_progress":
            task.status = "available"

    # --- mini-game framework (Tier 3.1) -----------------------------------

    # --- mini-game delegators ---------------------------------------------
    # Real implementation lives in ``MiniGameController``; these thin shims
    # preserve the WS-facing API and the internal call sites. Tests still
    # call ``room.apply_mini_game_input`` etc. directly.

    def _start_mini_game(self, player_id: str, task_id: str, mini_game_id: str) -> None:
        self._mini_games.start(player_id, task_id, mini_game_id)

    def apply_mini_game_input(self, player_id: str, action: str, params: dict) -> None:
        self._mini_games.apply_input(player_id, action, params)

    def _cancel_mini_game(self, player_id: str, reason: str) -> None:
        self._mini_games.cancel(player_id, reason)

    def _cancel_all_mini_games(self, reason: str) -> None:
        self._mini_games.cancel_all(reason)

    def drain_pending_mini_game_events(self) -> list[tuple[str, str, dict]]:
        return self._mini_games.drain_events()

    def _apply_incidents_delta(self, delta: int) -> None:
        """Clamp incidents into 0..100 after applying delta. Internal use only."""
        self.incidents = max(0, min(100, self.incidents + delta))

    def _apply_task_reward(
        self, definition: TaskDefinition, completed_by: str | None = None
    ) -> None:
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
            # Tier 3.5: refilling the team coffee also tops up the player's
            # own coffee_energy fully (and a small splash to nearby teammates).
            if completed_by and completed_by in self.players:
                p = self.players[completed_by]
                p.coffee_energy = p.max_coffee
                self._splash_coffee_to_neighbours(completed_by, amount=15.0, radius=180.0)
        if definition.incidents_change:
            self._apply_incidents_delta(definition.incidents_change)

    def _splash_coffee_to_neighbours(
        self, source_player_id: str, amount: float, radius: float
    ) -> None:
        """Tier 3.5: small per-task coffee splash to nearby teammates so the
        kitchen is a real social hub. Used by refill_coffee + Coffee-Run."""
        source = self.players.get(source_player_id)
        if source is None:
            return
        r2 = radius * radius
        for pid, p in self.players.items():
            if pid == source_player_id or not p.is_alive:
                continue
            dx = p.x - source.x
            dy = p.y - source.y
            if dx * dx + dy * dy <= r2:
                p.coffee_energy = min(p.max_coffee, p.coffee_energy + amount)

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
                    # Tier 3.5: role + coffee speed up / slow down task work.
                    player = self.players.get(pid)
                    if player is not None:
                        mult = task_speed_multiplier(
                            player.role, task.definition.category, player.coffee_energy
                        )
                    else:
                        mult = 1.0
                    new_progress = progress + dt * mult
                    if new_progress >= task.definition.required_seconds:
                        finishers.append(pid)
                    else:
                        still_progressing[pid] = new_progress
                if finishers:
                    # Deterministic tiebreak: lexicographically smallest player id.
                    winner_pid = sorted(finishers)[0]
                    self._apply_task_reward(task.definition, completed_by=winner_pid)
                    self.completed_tasks_by_player[winner_pid] = (
                        self.completed_tasks_by_player.get(winner_pid, 0) + 1
                    )
                    self._emit_event("info", f"{task.definition.title} erledigt.")
                    task.per_player_progress = {}
                    task.status = "cooldown"
                    task.cooldown_remaining = TASK_RESPAWN_COOLDOWN
                else:
                    task.per_player_progress = still_progressing
                    if not still_progressing:
                        task.status = "available"

    # --- sabotages ---------------------------------------------------------

    def apply_sabotage(self, player_id: str, sabotage_id: str) -> None:
        self._sabotages_ctl.trigger(player_id, sabotage_id)

    def use_vent(self, player_id: str, target_vent_id: str) -> None:
        """Tier 2.3: chaos-only teleport through the vent network.

        The player must currently be next to a vent ('source'); target_vent_id
        must be in that source vent's connected_to list. Teleport snaps the
        player to the target's coordinates. Wall collision is bypassed by
        construction (the move is a discrete jump, not a swept motion).
        """
        if self.phase is not Phase.PLAYING:
            raise GameRoomError(
                code="WRONG_PHASE", message="Vents only work during a running round."
            )
        player = self.players.get(player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        if not player.is_alive:
            raise GameRoomError(code="PLAYER_ELIMINATED", message="Eliminated players cannot vent.")
        if player.team != "chaos_agents":
            raise GameRoomError(code="NOT_CHAOS_AGENT", message="Only chaos agents can use vents.")
        # Find source vent: closest vent within reach.
        source = None
        best_dist_sq = VENT_INTERACTION_RADIUS * VENT_INTERACTION_RADIUS
        for v in self.map.vents:
            dx = player.x - v.x
            dy = player.y - v.y
            d2 = dx * dx + dy * dy
            if d2 <= best_dist_sq:
                source = v
                best_dist_sq = d2
        if source is None:
            raise GameRoomError(code="NO_VENT_NEARBY", message="No vent in reach.")
        if target_vent_id not in source.connected_to:
            raise GameRoomError(
                code="VENT_NOT_CONNECTED",
                message=f"Vent {target_vent_id!r} is not reachable from {source.id!r}.",
            )
        target = next((v for v in self.map.vents if v.id == target_vent_id), None)
        if target is None:
            raise GameRoomError(
                code="UNKNOWN_VENT", message=f"Vent {target_vent_id!r} does not exist."
            )
        player.x = float(target.x)
        player.y = float(target.y)

    def repair_sabotage(self, player_id: str, sabotage_id: str) -> None:
        self._sabotages_ctl.repair(player_id, sabotage_id)

    def _tick_sabotages(self, dt: float) -> None:
        self._sabotages_ctl.tick(dt)

    # --- take-down + body-report ------------------------------------------

    def _tick_takedown_cooldowns(self, dt: float) -> None:
        for pid, cd in list(self.takedown_cooldowns.items()):
            if cd > 0:
                self.takedown_cooldowns[pid] = max(0.0, cd - dt)

    def apply_takedown(self, killer_id: str, target_id: str) -> Body:
        """
        Eliminate the target via stealth take-down. Authoritative.
        No event emission -- a take-down must not leak to the public feed.
        """
        if self.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Take-Down nur im PLAYING.")
        killer = self.players.get(killer_id)
        if killer is None or not killer.is_connected:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Killer nicht im Raum.")
        if not killer.is_alive:
            raise GameRoomError(
                code="PLAYER_ELIMINATED", message="Eliminierte Spieler koennen nichts tun."
            )
        if killer.team != "chaos_agents":
            raise GameRoomError(
                code="NOT_CHAOS_AGENT", message="Nur Chaos-Agenten koennen Take-Down nutzen."
            )
        target = self.players.get(target_id)
        if target is None:
            raise GameRoomError(code="UNKNOWN_TARGET", message="Ziel nicht im Raum.")
        if not target.is_connected:
            raise GameRoomError(code="UNKNOWN_TARGET", message="Ziel nicht verbunden.")
        if not target.is_alive:
            raise GameRoomError(code="TARGET_ELIMINATED", message="Ziel ist bereits ausgeschaltet.")
        if target_id == killer_id:
            raise GameRoomError(
                code="INVALID_TARGET", message="Du kannst dich nicht selbst killen."
            )
        if target.team == "chaos_agents":
            raise GameRoomError(
                code="INVALID_TARGET",
                message="Chaos-Agenten koennen sich nicht gegenseitig ausschalten.",
            )
        dx = killer.x - target.x
        dy = killer.y - target.y
        if (dx * dx + dy * dy) > (TAKEDOWN_RADIUS * TAKEDOWN_RADIUS):
            raise GameRoomError(code="OUT_OF_RANGE", message="Ziel ist zu weit weg.")
        if self.takedown_cooldowns.get(killer_id, 0.0) > 0:
            raise GameRoomError(code="TAKEDOWN_ON_COOLDOWN", message="Take-Down auf Cooldown.")

        # Snapshot the victim's position before any state mutation.
        body = Body(
            id=uuid.uuid4().hex,
            x=target.x,
            y=target.y,
            victim_player_id=target.id,
            victim_name=target.name,
            color=target.color,
        )
        target.is_alive = False
        target.input_state = InputState()
        # Drop any task holds the target had (mirror mark_disconnected cleanup).
        for task in self.tasks.values():
            if target_id in task.per_player_progress:
                task.per_player_progress.pop(target_id)
                if not task.per_player_progress and task.status == "in_progress":
                    task.status = "available"
        # Tier 3.1: a take-down victim drops their mini-game (and the modal
        # snaps shut on the client when the framework forwards 'killed').
        if target_id in self.active_mini_games:
            self._cancel_mini_game(target_id, "killed")
        self.bodies[body.id] = body
        self.takedown_cooldowns[killer_id] = TAKEDOWN_COOLDOWN
        return body

    def apply_report_body(self, reporter_id: str, body_id: str, rng=None) -> None:
        """
        Reporter discovers a body. Triggers a meeting that bypasses the
        war-room requirement and the per-round emergency meeting quota.
        """
        if self.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Report nur im PLAYING.")
        reporter = self.players.get(reporter_id)
        if reporter is None or not reporter.is_connected:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Reporter nicht im Raum.")
        if not reporter.is_alive:
            raise GameRoomError(
                code="PLAYER_ELIMINATED", message="Eliminierte Spieler koennen nichts melden."
            )
        body = self.bodies.get(body_id)
        if body is None:
            raise GameRoomError(code="UNKNOWN_BODY", message="Unbekannter Body.")
        dx = reporter.x - body.x
        dy = reporter.y - body.y
        if (dx * dx + dy * dy) > (REPORT_RADIUS * REPORT_RADIUS):
            raise GameRoomError(code="OUT_OF_RANGE", message="Body ist zu weit weg.")

        # Pop the body and emit the public danger event.
        self.bodies.pop(body_id, None)
        self._emit_event(
            "danger",
            f"{reporter.name} hat einen Body gefunden: {body.victim_name}.",
        )

        # Direct transition into MEETING. Bypass war-room + meeting quota.
        self.meeting_caller_id = reporter_id
        self.meeting_remaining_seconds = MEETING_DURATION_SECONDS
        self.votes = {}
        self.meeting_title = f"Body Report: {body.victim_name}"
        self.phase = Phase.MEETING
        # Cancel ongoing task holds -- frozen during meeting.
        for task in self.tasks.values():
            task.per_player_progress = {}
            if task.status == "in_progress":
                task.status = "available"
        # Tier 3.1: end any active mini-games — modals snap shut as players
        # are pulled into the meeting overlay.
        self._cancel_all_mini_games("meeting_started")
        # Tier 3.6: snapshot meeting context (reporter, body location, recent
        # events) so the UI can give people something concrete to discuss.
        self._snapshot_meeting_context(reporter_id=reporter_id, body=body)

    def private_state_for(self, player_id: str) -> dict:
        """Per-viewer private state (Tier 3.5 expanded). Includes own coffee
        energy and ability cooldown — these are visible only to the player
        themselves, since exposing teammates' coffee would leak strategic info."""
        cd = self.takedown_cooldowns.get(player_id, 0.0)
        p = self.players.get(player_id)
        coffee_now = float(p.coffee_energy) if p else 100.0
        coffee_max = float(p.max_coffee) if p else 100.0
        ability_used = bool(p.ability_used) if p else False
        return {
            "takedownCooldownRemaining": round(cd, 2),
            "coffeeEnergy": round(coffee_now, 1),
            "coffeeMax": round(coffee_max, 1),
            "abilityUsed": ability_used,
        }

    # --- meeting + voting -------------------------------------------------

    def _map_has_typed_anchors(self) -> bool:
        return self._sabotages_ctl.has_typed_anchors()

    def _object_type_for_task(self, task_id: str) -> str | None:
        return self._sabotages_ctl.object_type_for_task(task_id)

    def _object_anchors_for(self, sab_def: SabotageDefinition) -> list[tuple[float, float]]:
        return self._sabotages_ctl.object_anchors_for(sab_def)

    def _is_in_war_room(self, player) -> bool:
        x_min, y_min, x_max, y_max = self._war_room_bounds
        return x_min <= player.x <= x_max and y_min <= player.y <= y_max

    # --- abilities (Tier 3.5) -----------------------------------------------

    def apply_use_ability(
        self,
        player_id: str,
        rng: random.Random | None = None,
    ) -> dict:
        """Trigger the active player's role ability. One use per round.

        Returns a dict with action results so the WS layer can echo a friendly
        response. Currently:
        - rollback (DevOps): +18 pipeline_stability.
        - coffee_run (Caffeine Collector): +35 coffee to nearby teammates.
        - standup (Scrum Master): immediate emergency meeting (anywhere on
          the map; the war-room rule is waived for this ability).
        - reproduce_bug (QA Lead): emits a flavor event flagging "audit done".

        Raises GameRoomError with NO_ABILITY / ABILITY_ALREADY_USED /
        WRONG_PHASE / PLAYER_ELIMINATED on failure.
        """
        if self.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Abilities only during playing.")
        player = self.players.get(player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        if not player.is_alive:
            raise GameRoomError(
                code="PLAYER_ELIMINATED", message="Eliminated players cannot use abilities."
            )
        rd = role_by_id(player.role)
        if not rd.ability_id:
            raise GameRoomError(code="NO_ABILITY", message="Your role has no active ability.")
        if player.ability_used:
            raise GameRoomError(
                code="ABILITY_ALREADY_USED",
                message="You already used your ability this round.",
            )

        ability = rd.ability_id
        result: dict = {"abilityId": ability, "playerId": player_id}

        if ability == "rollback":
            before = self.pipeline_stability
            self.pipeline_stability = min(100, self.pipeline_stability + 18)
            self._emit_event(
                "info",
                f"{player.name} hat einen Rollback ausgerollt — Pipeline +{self.pipeline_stability - before}.",
            )
            result["pipelineDelta"] = self.pipeline_stability - before

        elif ability == "coffee_run":
            self._splash_coffee_to_neighbours(player_id, amount=35.0, radius=220.0)
            player.coffee_energy = player.max_coffee
            self._emit_event(
                "info", f"{player.name} hat eine Coffee-Run-Runde gemacht. Team gebufft."
            )

        elif ability == "standup":
            # Like emergency meeting but waives the war-room location rule and
            # doesn't consume the player's normal meeting allowance.
            self.meeting_caller_id = player_id
            self.meeting_remaining_seconds = MEETING_DURATION_SECONDS
            self.votes = {}
            self.meeting_title = "STANDUP — Scrum Master called it"
            self.phase = Phase.MEETING
            for task in self.tasks.values():
                task.per_player_progress = {}
                if task.status == "in_progress":
                    task.status = "available"
            self._cancel_all_mini_games("meeting_started")
            self._emit_event("warn", f"{player.name} ruft ein Standup ein. Alle in den Slack-Call.")
            self._snapshot_meeting_context(reporter_id=player_id, body=None)

        elif ability == "reproduce_bug":
            # Flavor / placeholder hook for now — emits an event and consumes
            # the ability. Real "verdächtig?"-tag-system is its own slice.
            recent = ", ".join(e.message for e in list(self.events)[-3:]) or "nichts auffälliges"
            self._emit_event(
                "info",
                f"{player.name} (QA) reproduziert: {recent}",
            )
            result["analysis"] = recent

        else:
            raise GameRoomError(code="NO_ABILITY", message="Unknown ability.")

        player.ability_used = True
        return result

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
            raise GameRoomError(
                code="PLAYER_ELIMINATED", message="Eliminated players cannot call meetings."
            )
        if not self._is_in_war_room(player):
            raise GameRoomError(
                code="NOT_IN_WAR_ROOM",
                message="Emergency meetings can only be called from the War Room.",
            )
        if not self.players_with_meeting_left.get(requesting_player_id, False):
            raise GameRoomError(
                code="NO_MEETING_LEFT",
                message="You already used your emergency meeting this round.",
            )

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
        # Tier 3.1: end any active mini-games when the round flips to MEETING.
        self._cancel_all_mini_games("meeting_started")
        # Tier 3.6: meeting context snapshot.
        self._snapshot_meeting_context(reporter_id=requesting_player_id, body=None)

    # --- endscreen + summary (Tier 3.7) ------------------------------------

    def _build_final_summary(self) -> dict:
        """Produce the endscreen blob: per-player stats, awards, AI-styled
        postmortem text. Pure function over current room state — no side
        effects beyond reading."""
        per_player = []
        for pid, p in self.players.items():
            per_player.append(
                {
                    "playerId": pid,
                    "name": p.name,
                    "color": p.color,
                    "role": p.role or "",
                    "team": p.team or "",
                    "tasksCompleted": int(self.completed_tasks_by_player.get(pid, 0)),
                    "sabotagesTriggered": int(self.triggered_sabotages_by_player.get(pid, 0)),
                    "coffeeFinal": round(p.coffee_energy, 1),
                    "abilityUsed": bool(p.ability_used),
                    "alive": bool(p.is_alive),
                }
            )

        awards = self._compute_awards(per_player)

        summary: dict = {
            "winner": self.winner,
            "reason": self.win_reason,
            "releaseProgress": int(self.release_progress),
            "pipelineStability": int(self.pipeline_stability),
            "incidents": int(self.incidents),
            "sabotagesTriggered": sum(self.triggered_sabotages_by_player.values()),
            "repairsCompleted": sum(1 for sab in self.sabotages.values() if not sab.active),
            "kills": sum(1 for p in self.players.values() if not p.is_alive),
            "perPlayer": per_player,
            "awards": awards,
            "roundNumber": 1,
        }
        # Postmortem text last — uses the rest of the dict.
        try:
            summary["postmortem"] = generate_postmortem(summary)
        except Exception:  # noqa: BLE001
            summary["postmortem"] = ""
        return summary

    def _compute_awards(self, per_player: list[dict]) -> list[dict]:
        """Pick fun awards from per-player stats. Each award is a dict with
        title + playerName + reason — the client renders them verbatim."""
        if not per_player:
            return []
        awards: list[dict] = []

        # Most tasks completed.
        top_tasks = max(per_player, key=lambda p: p["tasksCompleted"])
        if top_tasks["tasksCompleted"] > 0:
            awards.append(
                {
                    "title": "Pipeline Whisperer",
                    "playerName": top_tasks["name"],
                    "reason": f"hat {top_tasks['tasksCompleted']} Tasks fertig gemacht",
                }
            )

        # Most sabotages triggered (chaos award).
        top_sabs = max(per_player, key=lambda p: p["sabotagesTriggered"])
        if top_sabs["sabotagesTriggered"] > 0:
            awards.append(
                {
                    "title": "Vibe of the Round",
                    "playerName": top_sabs["name"],
                    "reason": f"{top_sabs['sabotagesTriggered']} Sabotagen, ohne sich zu schaemen",
                }
            )

        # Held der Kaffeemaschine — highest final coffee.
        top_coffee = max(per_player, key=lambda p: p["coffeeFinal"])
        if top_coffee["coffeeFinal"] >= 60:
            awards.append(
                {
                    "title": "Held der Kaffeemaschine",
                    "playerName": top_coffee["name"],
                    "reason": f"hat das Spiel mit {int(top_coffee['coffeeFinal'])} Coffee beendet",
                }
            )

        # Most suspicious innocent — release-team player who got voted out.
        eliminated = [p for p in per_player if not p["alive"] and p["team"] == "release_team"]
        if eliminated:
            sus = eliminated[0]
            awards.append(
                {
                    "title": "Most Suspicious Innocent",
                    "playerName": sus["name"],
                    "reason": "war keine Sabotage. Trotzdem geforce-rebooted",
                }
            )

        return awards

    def _snapshot_meeting_context(self, reporter_id: str | None, body: "Body | None") -> None:
        """Tier 3.6: capture context for the meeting overlay. Hints, never
        proofs — list of recent events, body location, reporter name,
        approximate death window. The client renders this verbatim."""
        reporter_name = ""
        if reporter_id and reporter_id in self.players:
            reporter_name = self.players[reporter_id].name

        recent = [
            MeetingRecentEvent(severity=e.severity, message=e.message, seq=e.seq)
            for e in list(self.events)[-6:]
        ]

        body_block: MeetingBody | None = None
        if body is not None:
            body_block = MeetingBody(
                victim_name=body.victim_name,
                x=round(body.x, 1),
                y=round(body.y, 1),
                room=self._room_label_for(body.x, body.y),
            )

        self.meeting_context = MeetingContext(
            reporter_name=reporter_name,
            body=body_block,
            recent_events=recent,
            alive=[MeetingAlive(id=p.id, name=p.name) for p in self.players.values() if p.is_alive],
        )

    def _room_label_for(self, x: float, y: float) -> str:
        """Best-effort lookup of which room a coordinate falls in. Used by
        meeting context so the body's location is human-friendly ('Server
        Room' instead of '(800, 2400)')."""
        for room in self.map.rooms:
            if room.x <= x <= room.x + room.width and room.y <= y <= room.y + room.height:
                return room.title
        return "irgendwo"

    def cast_vote(self, voter_id: str, target_id: str) -> None:
        if self.phase is not Phase.MEETING:
            raise GameRoomError(code="WRONG_PHASE", message="No meeting active.")
        voter = self.players.get(voter_id)
        if voter is None or not voter.is_alive:
            raise GameRoomError(code="CANNOT_VOTE", message="Only living players can vote.")
        target = self.players.get(target_id)
        if target is None or not target.is_alive:
            raise GameRoomError(
                code="INVALID_TARGET", message="Vote target must be a living player."
            )
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
            counts.get(SKIP_TARGET, 0) == max_count and max_count > 0
        )
        named_tie = (
            eliminated_id is None and len(winners) > 1 and all(w != SKIP_TARGET for w in winners)
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

        # Emit a public, role-neutral event. The text MUST NOT depend on
        # was_chaos -- doing so would leak role info to spectators.
        if eliminated_id:
            self._emit_event("info", f"{removed_name} wurde aus dem Team entfernt.")
        elif named_tie:
            self._emit_event("warn", "Patt — niemand wurde entfernt.")
        elif skip_won:
            self._emit_event("info", "Niemand wurde entfernt.")

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

    def _all_players_serialized(self) -> list[dict]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "x": round(p.x, 2),
                "y": round(p.y, 2),
                "color": p.color,
                "isHost": p.is_host,
                "isAlive": p.is_alive,
                "isConnected": p.is_connected,
            }
            for p in self.players.values()
        ]

    def _public_state_base(self) -> dict:
        """Shared state across all viewers. The `players` field is filled by callers."""
        return {
            "phase": self.phase.value,
            "remainingSeconds": int(self.remaining_seconds),
            "releaseProgress": int(self.release_progress),
            "pipelineStability": int(self.pipeline_stability),
            "coffeeLevel": int(self.coffee_level),
            "incidents": int(self.incidents),
            "tasks": [
                {
                    "id": t.definition.id,
                    "title": t.definition.title,
                    "room": t.definition.room,
                    "x": t.x,
                    "y": t.y,
                    "objectType": self._object_type_for_task(t.definition.id),
                    "category": t.definition.category,
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
                    "triggerObjectTypes": list(s.definition.trigger_object_types),
                    "objectHint": s.definition.object_hint,
                    "triggerAnchors": [
                        {"x": ax, "y": ay} for (ax, ay) in self._object_anchors_for(s.definition)
                    ],
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
                    # Tier 3.6: discussion fuel — reporter, body location,
                    # recent events. Hints, never proofs. Pydantic serialises
                    # the model with `by_alias=True` so the wire stays camelCase.
                    "context": (
                        self.meeting_context.model_dump(by_alias=True)
                        if self.meeting_context is not None
                        else None
                    ),
                }
                if self.phase is Phase.MEETING
                else None
            ),
            # Tier 3.7: end-of-round summary (None until ENDED).
            "finalSummary": self.final_summary,
            "events": [
                {"seq": e.seq, "severity": e.severity, "message": e.message} for e in self.events
            ],
            "bodies": [
                {
                    "id": b.id,
                    "x": round(b.x, 2),
                    "y": round(b.y, 2),
                    "color": b.color,
                    "victimName": b.victim_name,
                }
                for b in self.bodies.values()
            ],
            "lightsOff": self.lights_off,
            "commsDown": self.comms_down,
            "sabotagePanels": [
                {"sabotageId": p.sabotage_id, "x": p.x, "y": p.y} for p in self.map.sabotage_panels
            ],
            "vents": [
                {"id": v.id, "x": v.x, "y": v.y, "connectedTo": list(v.connected_to)}
                for v in self.map.vents
            ],
        }

    def public_state(self) -> dict:
        """Oeffentlicher GameState -- enthaelt keine Rolle/Team/Input.

        Unfiltered: every viewer sees every player. Used by callers without a
        specific viewer (lobby snapshots, tests). For per-socket broadcasts
        prefer `public_state_for(viewer_id)`.
        """
        state = self._public_state_base()
        state["players"] = self._all_players_serialized()
        return state

    def public_state_for(self, viewer_id: str, base: dict | None = None) -> dict:
        """Personalized GameState — alive viewers do NOT see ghosts.

        Ghosts (and unknown viewers, defensive fallback) get the full player
        list including dead players. Bodies/tasks/sabotages/events/meeting are
        identical for everyone.

        Pass a pre-computed `base` (from `_public_state_base()`) to amortize
        the shared serialization across many viewers in the same tick.
        """
        state = dict(base) if base is not None else self._public_state_base()
        viewer = self.players.get(viewer_id)
        if viewer is None or not viewer.is_alive:
            state["players"] = self._all_players_serialized()
        else:
            state["players"] = [
                {
                    "id": p.id,
                    "name": p.name,
                    "x": round(p.x, 2),
                    "y": round(p.y, 2),
                    "color": p.color,
                    "isHost": p.is_host,
                    "isAlive": p.is_alive,
                    "isConnected": p.is_connected,
                }
                for p in self.players.values()
                if p.is_alive
            ]
        return state

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
                {
                    "id": p.id,
                    "name": p.name,
                    "color": p.color,
                    "isHost": p.is_host,
                    "preferredRole": p.preferred_role,
                }
                for p in self.players.values()
            ],
        }

    def set_preferred_role(self, player_id: str, role: str | None) -> None:
        """Tier 3.5: store a lobby preference. Validation is light — unknown
        ids and chaos roles are silently nulled (chaos must stay random)."""
        from app.game.roles import RELEASE_ROLES

        p = self.players.get(player_id)
        if p is None:
            return
        if role is None or role == "":
            p.preferred_role = None
            return
        if role in RELEASE_ROLES:
            p.preferred_role = role
        else:
            p.preferred_role = None

    def private_role_for(self, player_id: str) -> RoleInfo:
        # Caller-side guards (`main.py`) already check `player.role and team`
        # before invoking this. The defensive lookup here lets us return a
        # clean GameRoomError instead of a bare KeyError if a stale ws frame
        # arrives mid-disconnect-sweep.
        p = self.players.get(player_id)
        if p is None or p.role is None or p.team is None:
            raise GameRoomError(
                code="NO_ROLE",
                message="Player has no role assigned yet.",
            )
        info = role_info_for(p.role)
        # Tier 3.5: replace the bare RoleInfo with the role-card-rich variant
        # and stitch in this player's personal task ids.
        return RoleInfo(
            role=info.role,
            team=info.team,
            description=info.description,
            title=info.title,
            short_blurb=info.short_blurb,
            strength_categories=info.strength_categories,
            weak_categories=info.weak_categories,
            ability_id=info.ability_id,
            ability_label=info.ability_label,
            ability_hint=info.ability_hint,
            max_coffee=info.max_coffee,
            available_sabotages=info.available_sabotages,
        )

    def assigned_tasks_for(self, player_id: str) -> list[dict]:
        """Return [{taskId, title, room, category, isFake}] for the player.
        For chaos players the same shape is used but isFake=True so the UI
        can render them with a 'Cover' badge."""
        p = self.players.get(player_id)
        if p is None or not p.assigned_task_ids:
            return []
        is_chaos = p.team == "chaos_agents"
        out = []
        from app.game.tasks import TASK_DEFINITIONS as _TD

        by_id = {t.id: t for t in _TD}
        for tid in p.assigned_task_ids:
            td = by_id.get(tid)
            if td is None:
                continue
            out.append(
                {
                    "taskId": tid,
                    "title": td.title,
                    "room": td.room,
                    "category": td.category,
                    "isFake": is_chaos,
                }
            )
        return out

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
        self.incidents = 0
        self.meeting_active_for = 0.0
        self.lights_off = False
        self.comms_down = False
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
        self.meeting_context = None
        self.final_summary = None
        self.events.clear()
        self._next_event_seq = 1
        self.bodies = {}
        self.takedown_cooldowns = {}
        # Tier 3.1: clear mini-game state across rounds.
        self.active_mini_games = {}
        self.pending_mini_game_events = []
        for player in self.players.values():
            player.role = None
            player.team = None
            player.x = 0.0
            player.y = 0.0
            player.input_state = InputState()
            player.is_alive = True
            player.is_connected = True
            player.disconnected_at_monotonic = None
