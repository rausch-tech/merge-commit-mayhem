"""Tasks controller — hold-E flow, per-tick progress, rewards.

Owns the task interaction logic (hold-start / hold-stop), the per-tick
progress loop, the reward + cooldown step, the personal-task allocation
done at round start, and the small coffee-splash side-effect that the
``refill_coffee`` task triggers. All of this used to live as private
methods on ``GameRoom``.

Public surface:
    - hold_start(player_id, task_id) — WS-facing: begin task work
    - hold_stop(player_id, task_id) — WS-facing: stop / cancel mini-game
    - tick(dt) — per-tick: cooldowns + progress + rewards
    - apply_reward(definition, completed_by) — used by the mini-game
      controller when a session completes successfully
    - allocate_personal(rng) — called at round start to fill
      ``Player.assigned_task_ids``
    - apply_incidents_delta(delta) — clamp helper used by sabotages too
    - assigned_tasks_for(player_id) — wire-shaped dict list for the
      private_role payload
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.game.models import Phase
from app.game.roles import role_by_id, task_speed_multiplier
from app.game.runtime import GameRoomError, TaskRuntime
from app.game.tasks import (
    TASK_DEFINITIONS,
    TASK_INTERACTION_RADIUS,
    TASK_RESPAWN_COOLDOWN,
    TaskDefinition,
)

if TYPE_CHECKING:
    from app.game.game_room import GameRoom


class TasksController:
    def __init__(self, room: GameRoom) -> None:
        self._room = room

    # --- public API ----------------------------------------------------------

    def hold_start(self, player_id: str, task_id: str) -> None:
        room = self._room
        if room.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Tasks only during playing.")
        # Tier 2.5: Slack-Down — release team can't see or progress tasks.
        if room.comms_down:
            raise GameRoomError(code="COMMS_DOWN", message="Slack ist down — keine Tasks.")
        # Ghosts may complete tasks — they help the release-team win.
        player = room.players.get(player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        task = room.tasks.get(task_id)
        if task is None:
            raise GameRoomError(code="UNKNOWN_TASK", message=f"Unknown task {task_id!r}.")
        if task.status == "cooldown":
            raise GameRoomError(code="TASK_ON_COOLDOWN", message="Task in cooldown.")
        if not self._in_range(player_id, task):
            raise GameRoomError(code="TASK_TOO_FAR", message="Too far from task.")
        # Tier 3.1: when the task has an associated mini-game, switch into the
        # mini-game flow instead of starting hold-E progress. Hold-E remains
        # the default for tasks without mini_game set.
        if task.definition.mini_game:
            if player_id in room.active_mini_games:
                raise GameRoomError(
                    code="MINI_GAME_ALREADY_ACTIVE",
                    message="Finish the current mini-game first.",
                )
            room._mini_games.start(player_id, task_id, task.definition.mini_game)
            return
        task.status = "in_progress"
        task.per_player_progress.setdefault(player_id, 0.0)

    def hold_stop(self, player_id: str, task_id: str) -> None:
        room = self._room
        # Tier 3.1: a stop on a mini-game-bearing task cancels the mini-game.
        if player_id in room.active_mini_games:
            session = room.active_mini_games[player_id]
            if session.task_id == task_id:
                room._mini_games.cancel(player_id, "cancelled")
                return
        task = room.tasks.get(task_id)
        if task is None:
            return
        task.per_player_progress.pop(player_id, None)
        if not task.per_player_progress and task.status == "in_progress":
            task.status = "available"

    def tick(self, dt: float) -> None:
        room = self._room
        for task in room.tasks.values():
            if task.status == "cooldown":
                task.cooldown_remaining -= dt
                if task.cooldown_remaining <= 0:
                    task.cooldown_remaining = 0.0
                    task.status = "available"
            elif task.status == "in_progress":
                finishers: list[str] = []
                still_progressing: dict[str, float] = {}
                for pid, progress in task.per_player_progress.items():
                    if not self._in_range(pid, task):
                        continue  # player left the radius; drop their progress
                    # Tier 3.5: role + coffee speed up / slow down task work.
                    player = room.players.get(pid)
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
                    self.apply_reward(task.definition, completed_by=winner_pid)
                    room.completed_tasks_by_player[winner_pid] = (
                        room.completed_tasks_by_player.get(winner_pid, 0) + 1
                    )
                    room._emit_event("info", f"{task.definition.title} erledigt.")
                    task.per_player_progress = {}
                    task.status = "cooldown"
                    task.cooldown_remaining = TASK_RESPAWN_COOLDOWN
                else:
                    task.per_player_progress = still_progressing
                    if not still_progressing:
                        task.status = "available"

    def apply_reward(self, definition: TaskDefinition, completed_by: str | None = None) -> None:
        room = self._room
        if definition.release_progress_reward:
            room.release_progress = min(
                100, room.release_progress + definition.release_progress_reward
            )
        if definition.pipeline_stability_reward:
            room.pipeline_stability = min(
                100, room.pipeline_stability + definition.pipeline_stability_reward
            )
        if definition.coffee_level_set is not None:
            room.coffee_level = definition.coffee_level_set
            # Tier 3.5: refilling the team coffee also tops up the player's
            # own coffee_energy fully (and a small splash to nearby teammates).
            if completed_by and completed_by in room.players:
                p = room.players[completed_by]
                p.coffee_energy = p.max_coffee
                self._splash_coffee(completed_by, amount=15.0, radius=180.0)
        if definition.incidents_change:
            room._apply_incidents_delta(definition.incidents_change)

    def splash_coffee(self, source_player_id: str, amount: float, radius: float) -> None:
        """Public alias for the per-tile splash. Used by the Coffee-Run
        ability (apply_use_ability) and the refill_coffee reward path."""
        self._splash_coffee(source_player_id, amount, radius)

    def allocate_personal(self, rng) -> None:
        """Pick 3 task ids per player. Release players favour their role's
        strength categories; chaos players get a plausible cover-persona
        list. Stored on Player.assigned_task_ids for the wire."""
        all_task_ids = [t.id for t in TASK_DEFINITIONS]
        for player in self._room.players.values():
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

    def assigned_for(self, player_id: str) -> list[dict]:
        """Return [{taskId, title, room, category, isFake}] for the player.
        For chaos players the same shape is used but isFake=True so the UI
        can render them with a 'Cover' badge."""
        p = self._room.players.get(player_id)
        if p is None or not p.assigned_task_ids:
            return []
        is_chaos = p.team == "chaos_agents"
        by_id = {t.id: t for t in TASK_DEFINITIONS}
        out: list[dict] = []
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

    def in_range(self, player_id: str, task: TaskRuntime) -> bool:
        return self._in_range(player_id, task)

    # --- private -------------------------------------------------------------

    def _in_range(self, player_id: str, task: TaskRuntime) -> bool:
        player = self._room.players.get(player_id)
        if player is None:
            return False
        dx = player.x - task.x
        dy = player.y - task.y
        return (dx * dx + dy * dy) <= (TASK_INTERACTION_RADIUS * TASK_INTERACTION_RADIUS)

    def _splash_coffee(self, source_player_id: str, amount: float, radius: float) -> None:
        """Tier 3.5: small per-task coffee splash to nearby teammates so the
        kitchen is a real social hub. Used by refill_coffee + Coffee-Run."""
        room = self._room
        source = room.players.get(source_player_id)
        if source is None:
            return
        r2 = radius * radius
        for pid, p in room.players.items():
            if pid == source_player_id or not p.is_alive:
                continue
            dx = p.x - source.x
            dy = p.y - source.y
            if dx * dx + dy * dy <= r2:
                p.coffee_energy = min(p.max_coffee, p.coffee_energy + amount)
