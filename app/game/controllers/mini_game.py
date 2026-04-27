"""Mini-game lifecycle controller.

Owns the per-player active session dict and the queue of lifecycle events
that the WS layer forwards to the owning sockets. The controller holds a
reference to its parent ``GameRoom`` so it can read the task table and
trigger the same reward path that the hold-E flow uses; everything else
moved out of ``game_room.py`` and lives here.

Public surface (called from ``GameRoom`` or the WS dispatcher):
    - start(player_id, task_id, mini_game_id) — open a session
    - apply_input(player_id, action, params) — handle a player input frame
    - cancel_all(reason) — drop every session (round end / meeting / reset)
    - drain_events() — pop pending lifecycle events for the WS layer

Private:
    - _complete(player_id), _cancel(player_id, reason)
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from app.game.minigames.base import MiniGamePluginError
from app.game.minigames.registry import get_plugin as get_mini_game_plugin
from app.game.minigames.registry import is_known as mini_game_is_known
from app.game.tasks import TASK_RESPAWN_COOLDOWN

if TYPE_CHECKING:
    from app.game.game_room import GameRoom, MiniGameSession  # noqa: F401


class MiniGameController:
    def __init__(self, room: GameRoom) -> None:
        self._room = room

    # --- public API ----------------------------------------------------------

    def start(self, player_id: str, task_id: str, mini_game_id: str) -> None:
        """Open a mini-game session for ``player_id`` on ``task_id``.

        Called from ``TasksController.apply_task_hold_start`` when the task
        carries a mini_game field. Emits a 'started' event for the WS layer.
        """
        from app.game.game_room import GameRoomError, MiniGameSession

        if not mini_game_is_known(mini_game_id):
            raise GameRoomError(
                code="UNKNOWN_MINI_GAME", message=f"Unknown mini-game {mini_game_id!r}."
            )
        plugin = get_mini_game_plugin(mini_game_id)
        seed = random.getrandbits(31)
        state = plugin.init_state(seed)
        session = MiniGameSession(plugin_id=mini_game_id, task_id=task_id, state=state)
        self._room.active_mini_games[player_id] = session
        # Mark the task as in_progress so other players see "Sven is at the
        # task" through the same UI affordances as hold-E.
        task = self._room.tasks.get(task_id)
        if task is not None and task.status == "available":
            task.status = "in_progress"
        self._room.pending_mini_game_events.append(
            (
                player_id,
                "started",
                {
                    "taskId": task_id,
                    "miniGameId": mini_game_id,
                    "title": plugin.title,
                    "view": plugin.public_view(state),
                },
            )
        )

    def apply_input(self, player_id: str, action: str, params: dict) -> None:
        """WS-facing entry point for a player's mini-game action."""
        from app.game.game_room import GameRoomError

        session = self._room.active_mini_games.get(player_id)
        if session is None:
            raise GameRoomError(
                code="NO_ACTIVE_MINI_GAME", message="No mini-game running for this player."
            )
        plugin = get_mini_game_plugin(session.plugin_id)
        try:
            session.state = plugin.handle_input(session.state, action, params)
        except MiniGamePluginError as exc:
            # Translate plugin-level cheat/format errors to GameRoomError so
            # the WS layer surfaces them consistently with other guards.
            raise GameRoomError(code=exc.code, message=exc.message) from exc
        # Echo the new public view back to the player.
        self._room.pending_mini_game_events.append(
            (
                player_id,
                "state",
                {"taskId": session.task_id, "view": plugin.public_view(session.state)},
            )
        )
        # Completion check.
        if plugin.is_complete(session.state):
            self._complete(player_id)

    def cancel_all(self, reason: str) -> None:
        """Used on round end / meeting start / reset to drop every session."""
        for pid in list(self._room.active_mini_games.keys()):
            self._cancel(pid, reason)

    def cancel(self, player_id: str, reason: str) -> None:
        """Drop a single player's session without applying the reward."""
        self._cancel(player_id, reason)

    def drain_events(self) -> list[tuple[str, str, dict]]:
        """WS layer pulls events here once per tick / after each input."""
        events = self._room.pending_mini_game_events
        self._room.pending_mini_game_events = []
        return events

    # --- private -------------------------------------------------------------

    def _complete(self, player_id: str) -> None:
        session = self._room.active_mini_games.pop(player_id, None)
        if session is None:
            return
        # Apply the same reward + cooldown the hold-E path uses.
        task = self._room.tasks.get(session.task_id)
        if task is not None:
            self._room._apply_task_reward(task.definition, completed_by=player_id)
            self._room.completed_tasks_by_player[player_id] = (
                self._room.completed_tasks_by_player.get(player_id, 0) + 1
            )
            task.per_player_progress.clear()
            task.status = "cooldown"
            task.cooldown_remaining = TASK_RESPAWN_COOLDOWN
        self._room.pending_mini_game_events.append(
            (
                player_id,
                "completed",
                {"taskId": session.task_id, "success": True, "reason": "solved"},
            )
        )

    def _cancel(self, player_id: str, reason: str) -> None:
        session = self._room.active_mini_games.pop(player_id, None)
        if session is None:
            return
        # Release the task back to "available" — kein Cooldown bei Cancel.
        task = self._room.tasks.get(session.task_id)
        if task is not None and task.status == "in_progress":
            task.per_player_progress.pop(player_id, None)
            if not task.per_player_progress:
                task.status = "available"
        self._room.pending_mini_game_events.append(
            (
                player_id,
                "completed",
                {"taskId": session.task_id, "success": False, "reason": reason},
            )
        )
