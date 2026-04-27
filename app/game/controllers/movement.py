"""Movement controller — per-tick player movement, coffee decay, vents.

Owns everything the per-tick loop does to player positions and the
energy economy that gates speed: WASD-driven step + wall collision +
map-edge clamp, the takedown cooldown timer that decays in lockstep
with movement, the personal coffee-energy decay, and the chaos-only
vent teleport (the only off-tick movement primitive in the game).

Public surface:
    - tick_movement(dt) — run the per-tick step loop for every alive
      player, applying speed scaling and wall collision
    - tick_takedown_cooldowns(dt) — decay every chaos player's
      takedown cooldown
    - tick_coffee_energy(dt) — decay personal coffee_energy for
      every alive player
    - current_speed_for(player_id) — px/s the room would step the
      given player this tick
    - use_vent(player_id, target_vent_id) — chaos-only teleport
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.game.models import Phase
from app.game.roles import movement_speed_multiplier, role_by_id
from app.game.runtime import GameRoomError
from app.game.sabotages import COFFEE_SLOW_SPEED, NORMAL_SPEED
from app.game.tasks import VENT_INTERACTION_RADIUS
from app.game.walls import resolve_wall_collision

if TYPE_CHECKING:
    from app.game.game_room import GameRoom


COFFEE_BASE_DECAY_PER_SECOND = 1.4
"""Decay points-per-second at coffee_decay_modifier=1.0 (Tier 3.5).

The role's coffee_decay_modifier scales this — DevOps drains fastest,
QA Lead and the Caffeine Collector drain slower."""


class MovementController:
    def __init__(self, room: GameRoom) -> None:
        self._room = room

    # --- per-tick steps ------------------------------------------------------

    def tick_movement(self, dt: float) -> None:
        """Per-tick step loop. Called from GameRoom.tick() while in PLAYING."""
        room = self._room
        for player in room.players.values():
            # Tier 3.1: a player inside a mini-game is locked in place — their
            # WASD inputs are ignored until the session ends.
            if player.id in room.active_mini_games:
                continue
            dx = int(player.input_state.right) - int(player.input_state.left)
            dy = int(player.input_state.down) - int(player.input_state.up)
            if not (dx or dy):
                continue
            # Ghosts ignore the slow-down sabotages and pass through walls.
            speed = self.current_speed_for(player.id) if player.is_alive else NORMAL_SPEED
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
                        room._walls,
                    )
                # Then y.
                new_y = player.y + step_y
                if step_y != 0:
                    _, new_y = resolve_wall_collision(
                        new_x,
                        new_y,
                        0.0,
                        step_y,
                        room._walls,
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
            elif player.x > room.map.size.width:
                player.x = float(room.map.size.width)
            if player.y < 0:
                player.y = 0.0
            elif player.y > room.map.size.height:
                player.y = float(room.map.size.height)

    def tick_takedown_cooldowns(self, dt: float) -> None:
        room = self._room
        for pid, cd in list(room.takedown_cooldowns.items()):
            if cd > 0:
                room.takedown_cooldowns[pid] = max(0.0, cd - dt)

    def tick_coffee_energy(self, dt: float) -> None:
        """Each alive player's personal coffee_energy decays over time. Decay
        rate scales with the role's coffee_decay_modifier (DevOps drains fast,
        Caffeine Collector / QA Lead sip slowly). Ghosts don't decay — they
        no longer interact with the team economy."""
        if dt <= 0:
            return
        for player in self._room.players.values():
            if not player.is_alive:
                continue
            rd = role_by_id(player.role)
            decay = COFFEE_BASE_DECAY_PER_SECOND * rd.coffee_decay_modifier * dt
            player.coffee_energy = max(0.0, player.coffee_energy - decay)

    # --- speed query ---------------------------------------------------------

    def current_speed_for(self, player_id: str) -> float:
        """Effective movement speed in px/s for this player this tick.

        Floor is COFFEE_SLOW_SPEED (set by global coffee_outage / mandatory
        meeting), otherwise NORMAL_SPEED scaled by the player's role + own
        coffee_energy (Tier 3.5)."""
        room = self._room
        if room.coffee_level == 0 or room.meeting_active_for > 0:
            return COFFEE_SLOW_SPEED
        player = room.players.get(player_id)
        if player is None:
            return NORMAL_SPEED
        return NORMAL_SPEED * movement_speed_multiplier(player.role, player.coffee_energy)

    # --- vents (chaos-only teleport) -----------------------------------------

    def use_vent(self, player_id: str, target_vent_id: str) -> None:
        """Tier 2.3: chaos-only teleport through the vent network.

        The player must currently be next to a vent ('source'); target_vent_id
        must be in that source vent's connected_to list. Teleport snaps the
        player to the target's coordinates. Wall collision is bypassed by
        construction (the move is a discrete jump, not a swept motion).
        """
        room = self._room
        if room.phase is not Phase.PLAYING:
            raise GameRoomError(
                code="WRONG_PHASE", message="Vents only work during a running round."
            )
        player = room.players.get(player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        if not player.is_alive:
            raise GameRoomError(code="PLAYER_ELIMINATED", message="Eliminated players cannot vent.")
        if player.team != "chaos_agents":
            raise GameRoomError(code="NOT_CHAOS_AGENT", message="Only chaos agents can use vents.")
        # Find source vent: closest vent within reach.
        source = None
        best_dist_sq = VENT_INTERACTION_RADIUS * VENT_INTERACTION_RADIUS
        for v in room.map.vents:
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
        target = next((v for v in room.map.vents if v.id == target_vent_id), None)
        if target is None:
            raise GameRoomError(
                code="UNKNOWN_VENT", message=f"Vent {target_vent_id!r} does not exist."
            )
        player.x = float(target.x)
        player.y = float(target.y)
