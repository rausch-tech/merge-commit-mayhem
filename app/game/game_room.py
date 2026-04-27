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
    role_by_id,
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
    SABOTAGE_DEFINITIONS,
    SabotageDefinition,
)
from app.game.tasks import (
    TASK_DEFINITIONS,
    TaskDefinition,
)
from app.game.voting import all_chaos_eliminated
from app.protocol import MeetingContext

MAX_PLAYERS = 12
"""Hard cap per room. Tier 1.5 raised this from 8."""

MIN_PLAYERS_TO_START = 4
"""Below this count ``start()`` raises NOT_ENOUGH_PLAYERS unless demo=True."""

PLAYER_RADIUS = 12
"""Hitbox radius (px) used for movement and interaction tests."""

ROUND_SECONDS = 900.0
"""Default time-budget per round (15 minutes). Once expired the chaos
team wins by exhaustion."""

RECONNECT_GRACE_SECONDS = 30.0
"""How long a disconnected player keeps their seat before
``_sweep_disconnected`` removes them."""

INCIDENTS_LOSS_THRESHOLD = 100
"""Chaos win threshold: once room.incidents reaches this, the round ends."""

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

        # Global gameplay stats (0 in LOBBY, reset on start()). NOTE:
        # ``coffee_level`` is the TEAM-LEVEL int 0..100 — UI pill, gates
        # the coffee_outage sabotage trigger, and feeds movement_speed
        # floor when at 0. Per-player coffee state lives on Player as
        # ``coffee_energy: float`` (Tier 3.5) and is independent.
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
        from app.game.bots.manager import BotManager
        from app.game.controllers.meeting import MeetingController
        from app.game.controllers.mini_game import MiniGameController
        from app.game.controllers.movement import MovementController
        from app.game.controllers.sabotages import SabotagesController
        from app.game.controllers.tasks import TasksController

        self._mini_games = MiniGameController(self)
        self._sabotages_ctl = SabotagesController(self)
        self._tasks_ctl = TasksController(self)
        self._movement_ctl = MovementController(self)
        self._meeting_ctl = MeetingController(self)
        # Tier 3.9.2: AI-NPCs. Constructed empty; populated by host
        # via the `add_bot` WS action (slice 53). Ticks alongside the
        # other controllers but only acts during PLAYING.
        self._bots = BotManager(self)

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
        # New map → room graph cache must be invalidated.
        self._bots.invalidate_graph()

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
        # Bots set their input_state BEFORE movement tick so the
        # MovementController treats them like any other player. Order
        # matters: tasks-tick uses task.per_player_progress which the
        # bot's auto-complete in pick_next_target sets to 0 — bots
        # finish via apply_reward, not via the per-tick progress loop.
        self._bots.tick(dt)
        self._movement_ctl.tick_movement(dt)
        self._tasks_ctl.tick(dt)
        self._sabotages_ctl.tick(dt)
        self._movement_ctl.tick_takedown_cooldowns(dt)
        self._movement_ctl.tick_coffee_energy(dt)
        self.remaining_seconds = max(0.0, self.remaining_seconds - dt)
        self._sweep_disconnected()
        self._check_win_conditions()

    # --- coffee energy (Tier 3.5) — delegated to MovementController -------

    def _tick_coffee_energy(self, dt: float) -> None:
        self._movement_ctl.tick_coffee_energy(dt)

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
        # Tier 3.7.6: per-round metrics line. No-op unless MCM_METRICS_DIR is
        # set in the environment (production deploy ships with it; tests
        # leave it unset). Errors are swallowed — never crash a round end.
        try:
            from app.game.metrics_export import export_round

            export_round(self)
        except Exception:  # noqa: BLE001
            pass

    # --- speed helpers -----------------------------------------------------

    def _current_speed_for(self, player_id: str) -> float:
        return self._movement_ctl.current_speed_for(player_id)

    # --- personal-task allocation (Tier 3.5) -------------------------------

    def _allocate_personal_tasks(self, rng: random.Random) -> None:
        self._tasks_ctl.allocate_personal(rng)

    # --- tasks (delegators to TasksController) ----------------------------

    def _task_in_range(self, player_id: str, task: "TaskRuntime") -> bool:
        return self._tasks_ctl.in_range(player_id, task)

    def apply_task_hold_start(self, player_id: str, task_id: str) -> None:
        self._tasks_ctl.hold_start(player_id, task_id)

    def apply_task_hold_stop(self, player_id: str, task_id: str) -> None:
        self._tasks_ctl.hold_stop(player_id, task_id)

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
        self._tasks_ctl.apply_reward(definition, completed_by=completed_by)

    def _splash_coffee_to_neighbours(
        self, source_player_id: str, amount: float, radius: float
    ) -> None:
        self._tasks_ctl.splash_coffee(source_player_id, amount, radius)

    def _tick_tasks(self, dt: float) -> None:
        self._tasks_ctl.tick(dt)

    # --- sabotages ---------------------------------------------------------

    def apply_sabotage(self, player_id: str, sabotage_id: str) -> None:
        self._sabotages_ctl.trigger(player_id, sabotage_id)

    def use_vent(self, player_id: str, target_vent_id: str) -> None:
        self._movement_ctl.use_vent(player_id, target_vent_id)

    def repair_sabotage(self, player_id: str, sabotage_id: str) -> None:
        self._sabotages_ctl.repair(player_id, sabotage_id)

    def _tick_sabotages(self, dt: float) -> None:
        self._sabotages_ctl.tick(dt)

    # --- take-down + body-report ------------------------------------------

    def _tick_takedown_cooldowns(self, dt: float) -> None:
        self._movement_ctl.tick_takedown_cooldowns(dt)

    def apply_takedown(self, killer_id: str, target_id: str) -> Body:
        return self._meeting_ctl.apply_takedown(killer_id, target_id)

    def apply_report_body(self, reporter_id: str, body_id: str, rng=None) -> None:
        self._meeting_ctl.apply_report_body(reporter_id, body_id, rng=rng)

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
            # doesn't consume the player's normal meeting allowance. Goes
            # through the meeting controller so the PLAYING->MEETING
            # transition is centralised (task holds cleared, mini-games
            # cancelled, context snapshotted) — no copy/paste of the eight
            # mutations that step entails.
            self._emit_event("warn", f"{player.name} ruft ein Standup ein. Alle in den Slack-Call.")
            self._meeting_ctl.begin_meeting(
                caller_id=player_id,
                title="STANDUP — Scrum Master called it",
                body=None,
                consume_quota=False,
            )

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
        self._meeting_ctl.call_emergency_meeting(requesting_player_id, rng=rng)

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
        self._meeting_ctl.snapshot_context(reporter_id, body)

    def _room_label_for(self, x: float, y: float) -> str:
        return self._meeting_ctl._room_label_for(x, y)

    def cast_vote(self, voter_id: str, target_id: str) -> None:
        self._meeting_ctl.cast_vote(voter_id, target_id)

    def skip_vote(self, voter_id: str) -> None:
        self._meeting_ctl.skip_vote(voter_id)

    def _living_player_ids(self) -> list[str]:
        return self._meeting_ctl._living_player_ids()

    def _all_alive_voted(self) -> bool:
        return self._meeting_ctl.all_alive_voted()

    def _resolve_meeting(self) -> str | None:
        return self._meeting_ctl.resolve_meeting()

    def _aggregate_vote_counts(self) -> dict[str, int]:
        return self._meeting_ctl.aggregate_vote_counts()

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
                "isBot": p.is_bot,
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
                    "isBot": p.is_bot,
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
        return self._tasks_ctl.assigned_for(player_id)

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
