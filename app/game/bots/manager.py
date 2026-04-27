"""BotManager — owns AI-NPC lifecycle + per-tick mechanics.

Bots are real Player rows (`Player.is_bot=True`). The manager owns the
state that's bot-specific: current movement path, the work timer that
substitutes for a mini-game, and the high-level intent (what task is
the bot trying to do right now).

Decision-making lives in two layers, glued here:
- *Mechanics* (this slice, 3.9.2) — wander to a random task, hold the
  spot for a few seconds, mark task complete via the same reward path
  the mini-game controller uses. Pure heuristic, no LLM in the loop.
- *Intent* (next slice, task 54) — LLMClient picks the next target
  ("go to kitchen and refill coffee") and reactive overrides for body
  sightings / meetings. The decision module monkey-patches the
  `pick_next_target` hook on this manager.

Why bots skip mini-games (per design cut): mini-games are DOM/canvas
UIs, not domain code. A bot that "plays" them would have to drive the
mini-game framework's internal state machines from server-side, which
duplicates the framework. Hold-E → 4–6 s → reward call gets us the
Among-Us-style "task being done at a desk" silhouette without any of
that, and the mini-game-skip is even visible to other players (the
task progress bar runs to full and then resets).
"""

from __future__ import annotations

import logging
import random
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from app.game.bots.pathfinding import (
    Point,
    RoomGraph,
    build_room_graph,
    find_path,
)
from app.game.llm import LLMClient
from app.game.models import InputState, Phase, Player
from app.game.runtime import GameRoomError
from app.game.tasks import TASK_INTERACTION_RADIUS, TASK_RESPAWN_COOLDOWN

if TYPE_CHECKING:
    from app.game.bots.decision import DecisionState
    from app.game.game_room import GameRoom

logger = logging.getLogger(__name__)


# Curated bot names — recognisably bots (joke-flavored), so humans can spot
# them at a glance. LLM-generated names were considered and dropped: cute
# at first, but a bot called "Sven" in the lobby is a recipe for confusion.
BOT_NAMES: Final[tuple[str, ...]] = (
    "Bot-Promptly",
    "Bot-Cursor-Sr.",
    "Bot-StackOverflow",
    "Bot-Junior",
    "Bot-Copilot",
    "Bot-Linter",
    "Bot-Pager",
    "Bot-Standup",
)

# Bot work duration sampled per task. Range matches the design cut
# (4–6 s); short enough that bots feel productive, long enough that
# release-team players see them "working" at a desk.
_BOT_WORK_MIN_SEC: Final[float] = 4.0
_BOT_WORK_MAX_SEC: Final[float] = 6.0

# Movement waypoint reach radius. Larger than the player hitbox so the
# bot doesn't get stuck oscillating around a door center.
_WAYPOINT_REACH_PX: Final[float] = 24.0


@dataclass
class BotState:
    """Per-bot scratch state. Owned by BotManager, keyed by player_id.

    `path` is consumed front-to-back as the bot walks. `target_task_id`
    is the high-level intent (the "what" the bot is trying to do); the
    path is the "how". When `work_remaining_sec > 0` the bot is at the
    target and hold-E-ing for the remaining duration.
    """

    target_task_id: str | None = None
    path: list[Point] = field(default_factory=list)
    work_remaining_sec: float = 0.0


class BotManager:
    """Per-room bot orchestrator. Owned by GameRoom, ticked once per frame.

    Single source of truth for which players are bots: `self._bots` maps
    `player_id → BotState`. The Player.is_bot flag is the wire-visible
    mirror; this map is the authoritative server-side state.
    """

    def __init__(self, room: GameRoom) -> None:
        self._room = room
        self._bots: dict[str, BotState] = {}
        # RNG is owned per manager so tests can deterministically seed it.
        self._rng = random.Random()
        # Room graph is invalidated on map change (set_map).
        self._graph: RoomGraph | None = None
        # Optional LLM. When None, the heuristic picker is the only
        # intent source. Wired in by main.py at startup via set_llm().
        self._llm: LLMClient | None = None
        # Parallel dict for the decision layer's per-bot state. Lazy
        # imported in tick() to avoid the circular import at module load.
        self._decisions: dict[str, DecisionState] = {}

    # --- LLM glue ------------------------------------------------------------

    def set_llm(self, client: LLMClient | None) -> None:
        """Wire (or unwire) the LLM provider. None falls back to heuristic."""
        self._llm = client

    # --- lifecycle -----------------------------------------------------------

    def add_bot(self, *, name: str | None = None) -> Player:
        """Add a bot to the room as if it were a real player.

        Names default to the next unused entry in `BOT_NAMES`, falling
        back to a numeric suffix if all curated names are taken. Raises
        `GameRoomError` if the room is full or not in lobby — bots can
        only be added before round start, matching real-player join.
        """
        room = self._room
        if room.phase is not Phase.LOBBY:
            raise GameRoomError(code="WRONG_PHASE", message="Bots can only be added in the lobby.")

        chosen = name or self._next_default_name()
        # `add_player` enforces room cap + name uniqueness, so we don't
        # have to. The host bit ends up False as long as a real human
        # joined first.
        player = room.add_player(chosen)
        player.is_bot = True
        self._bots[player.id] = BotState()
        return player

    def remove_bot(self, bot_id: str) -> None:
        """Remove a bot. Idempotent — unknown id is a no-op."""
        if bot_id not in self._bots:
            return
        self._bots.pop(bot_id, None)
        self._decisions.pop(bot_id, None)
        self._room.remove_player(bot_id)

    def is_bot(self, player_id: str) -> bool:
        return player_id in self._bots

    def bot_ids(self) -> list[str]:
        return list(self._bots.keys())

    def state_for(self, bot_id: str) -> BotState | None:
        return self._bots.get(bot_id)

    def invalidate_graph(self) -> None:
        """Drop the cached room-graph (call after `room.set_map(...)`)."""
        self._graph = None

    # --- per-tick driver -----------------------------------------------------

    def tick(self, dt: float) -> None:
        """Drive every bot one step.

        Each bot independently: picks a target if it has none, walks
        toward it, then auto-completes the task once it's been at the
        spot for the work duration. Reactive overrides (body reports,
        meeting votes) run in any phase via the decision layer.
        """
        room = self._room
        # Lazy import to break the circular dependency at module load.
        from app.game.bots.decision import apply_reactive_overrides, tick_llm_cooldowns

        tick_llm_cooldowns(self._decisions, dt)
        apply_reactive_overrides(self, self._decisions, self._rng, dt)

        if room.phase is not Phase.PLAYING:
            return

        for bot_id, state in list(self._bots.items()):
            player = room.players.get(bot_id)
            if player is None:
                # Bot was swept by the disconnect grace period — clean up.
                self._bots.pop(bot_id, None)
                self._decisions.pop(bot_id, None)
                continue
            if not player.is_alive:
                player.input_state = InputState()
                continue
            self._tick_one(player, state, dt)

    # --- per-bot logic -------------------------------------------------------

    def _tick_one(self, player: Player, state: BotState, dt: float) -> None:
        # Currently working on a task — count down, then auto-complete.
        if state.work_remaining_sec > 0:
            player.input_state = InputState()  # stand still while working
            state.work_remaining_sec -= dt
            if state.work_remaining_sec <= 0:
                self._auto_complete(player, state)
            return

        # No intent yet → pick one. Falls back to no-op if the map has
        # no available tasks (everything on cooldown).
        if state.target_task_id is None:
            self.pick_next_target(player, state)
            if state.target_task_id is None:
                player.input_state = InputState()
                return

        # Have intent + path → drive toward next waypoint.
        if not state.path:
            # Already at target room (path was empty) but not yet within
            # interaction radius? Steer straight to task position.
            self._maybe_start_work(player, state)
            return

        self._step_along_path(player, state)

    def _step_along_path(self, player: Player, state: BotState) -> None:
        if not state.path:
            return
        wx, wy = state.path[0]
        dx = wx - player.x
        dy = wy - player.y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist <= _WAYPOINT_REACH_PX:
            state.path.pop(0)
            if not state.path:
                self._maybe_start_work(player, state)
                return
            wx, wy = state.path[0]
            dx = wx - player.x
            dy = wy - player.y

        # Convert direction to 4-key WASD input. We don't normalize — the
        # MovementController normalizes the (dx, dy) it derives from
        # input_state. Single-axis wins when the offset is small on the
        # other axis (avoids the bot moonwalking in tight corridors).
        threshold = 4.0
        right = dx > threshold
        left = dx < -threshold
        down = dy > threshold
        up = dy < -threshold
        player.input_state = InputState(up=up, down=down, left=left, right=right)

    def _maybe_start_work(self, player: Player, state: BotState) -> None:
        """When the bot reaches its target, kick off the work timer.

        If the task isn't actually in range (path ended before reaching
        it — happens when the target room's path returned empty but the
        in-room steering hasn't finished yet), keep walking with no
        further pathfinding (straight-line steering).
        """
        room = self._room
        task_id = state.target_task_id
        if task_id is None:
            return
        task = room.tasks.get(task_id)
        if task is None or task.status == "cooldown":
            # Task became unavailable while we were walking — drop intent.
            self._reset_intent(player, state)
            return

        dx = task.x - player.x
        dy = task.y - player.y
        dist_sq = dx * dx + dy * dy
        if dist_sq <= TASK_INTERACTION_RADIUS * TASK_INTERACTION_RADIUS:
            # In range — start the hold timer. Mark the task in_progress
            # so the public state shows "someone is working on it".
            state.work_remaining_sec = self._rng.uniform(_BOT_WORK_MIN_SEC, _BOT_WORK_MAX_SEC)
            task.status = "in_progress"
            task.per_player_progress[player.id] = 0.0
            player.input_state = InputState()
            return

        # Not in range yet — set input toward the task and let the next
        # tick cover the last leg.
        threshold = 4.0
        player.input_state = InputState(
            up=dy < -threshold,
            down=dy > threshold,
            left=dx < -threshold,
            right=dx > threshold,
        )

    def _auto_complete(self, player: Player, state: BotState) -> None:
        """Bot's hold timer expired — apply the task reward directly.

        This is the moral equivalent of a human finishing the mini-game,
        so we go through the same reward path (`TasksController.apply_reward`)
        plus the bookkeeping the live tick loop normally does on
        completion (cooldown, completed-by counter, event feed). The
        event feed entry is what tells humans "Bot-Promptly just did
        the CI fix" — keeps bots socially legible.
        """
        room = self._room
        task_id = state.target_task_id
        state.target_task_id = None
        state.path = []
        state.work_remaining_sec = 0.0
        if task_id is None:
            return
        task = room.tasks.get(task_id)
        if task is None:
            return
        # Apply reward + cooldown — same shape as the live tick path.
        room._tasks_ctl.apply_reward(task.definition, completed_by=player.id)
        room.completed_tasks_by_player[player.id] = (
            room.completed_tasks_by_player.get(player.id, 0) + 1
        )
        task.per_player_progress = {}
        task.status = "cooldown"
        task.cooldown_remaining = TASK_RESPAWN_COOLDOWN
        room._emit_event("info", f"{task.definition.title} erledigt.")

    # --- intent picker (overridable; LLM swaps this in slice 54) -------------

    def pick_next_target(self, player: Player, state: BotState) -> None:
        """Pick the bot's next target task and recompute its path.

        Decision precedence:
        1. LLM (if configured) — once per `LLM_DECISION_INTERVAL_SEC` per
           bot. The decision module enforces the cooldown and parses
           the response back to a known task id; on miss/timeout it
           returns False and we fall through.
        2. Heuristic — random choice over available tasks not already
           targeted by another bot. The no-stampede heuristic is a UX
           thing: nothing prevents two bots from working the same task,
           but they look bad doing it.
        """
        from app.game.bots.decision import maybe_consult_llm

        if maybe_consult_llm(self, self._decisions, player, state):
            return

        room = self._room
        candidates = [
            t
            for t in room.tasks.values()
            if t.status == "available"
            and t.definition.id not in self._tasks_in_progress_by_other_bots(player.id)
        ]
        if not candidates:
            return
        choice = self._rng.choice(candidates)
        self._set_intent(player, state, choice.definition.id)

    def _set_intent(self, player: Player, state: BotState, task_id: str) -> None:
        """Set the bot's target task and recompute its movement path."""
        room = self._room
        task = room.tasks.get(task_id)
        if task is None:
            return
        path = self._compute_path((player.x, player.y), (task.x, task.y))
        state.target_task_id = task_id
        state.path = path if path is not None else []

    def _reset_intent(self, player: Player, state: BotState) -> None:
        state.target_task_id = None
        state.path = []
        state.work_remaining_sec = 0.0
        player.input_state = InputState()

    def _compute_path(self, start: Point, target: Point) -> list[Point] | None:
        """Pathfinder wrapper. Caches the room graph per map."""
        if self._graph is None:
            self._graph = build_room_graph(self._room.map)
        return find_path(start, target, self._room.map, self._graph)

    def _tasks_in_progress_by_other_bots(self, exclude_bot_id: str) -> set[str]:
        """So two bots don't stampede onto the same task."""
        out: set[str] = set()
        for bid, bs in self._bots.items():
            if bid == exclude_bot_id or bs.target_task_id is None:
                continue
            out.add(bs.target_task_id)
        return out

    # --- naming helper -------------------------------------------------------

    def _next_default_name(self) -> str:
        """Pick the first BOT_NAMES entry not already used in this room.

        If every curated name is taken, fall back to a short uuid suffix
        so we never collide with `add_player`'s NAME_TAKEN check.
        """
        used = {p.name for p in self._room.players.values()}
        for n in BOT_NAMES:
            if n not in used:
                return n
        return f"Bot-{uuid.uuid4().hex[:6]}"
