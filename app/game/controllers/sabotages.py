"""Sabotage trigger / repair / tick controller.

Owns the Tier 2.7 object-binding logic and the per-tick cooldown decay.
Reads/writes the room-level state (`sabotages` dict, `pipeline_stability`,
`coffee_level`, `lights_off`, `comms_down`, `meeting_active_for`,
`triggered_sabotages_by_player`) through ``self._room``.

Public surface:
    - trigger(player_id, sabotage_id) — chaos triggers a sabotage
    - repair(player_id, sabotage_id) — anyone repairs lights_out / comms_outage
    - tick(dt) — per-tick cooldown decay + active-flag refresh
    - has_typed_anchors() — Tier 2.7 gate for object-bound triggers
    - object_anchors_for(sab_def) — positions for the public state hint UI
    - object_type_for_task(task_id) — used by the tasks controller
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.game.models import Phase
from app.game.runtime import GameRoomError
from app.game.sabotages import (
    MEETING_DURATION,
    SabotageDefinition,
)
from app.game.tasks import (
    SABOTAGE_OBJECT_INTERACTION_RADIUS,
    SABOTAGE_PANEL_INTERACTION_RADIUS,
)

if TYPE_CHECKING:
    from app.game.game_room import GameRoom


class SabotagesController:
    def __init__(self, room: GameRoom) -> None:
        self._room = room

    # --- public API ----------------------------------------------------------

    def trigger(self, player_id: str, sabotage_id: str) -> None:
        room = self._room
        if room.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Sabotages only during playing.")
        player = room.players.get(player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        if not player.is_alive:
            raise GameRoomError(
                code="PLAYER_ELIMINATED", message="Eliminated players cannot sabotage."
            )
        if player.team != "chaos_agents":
            raise GameRoomError(
                code="NOT_CHAOS_AGENT",
                message="Only chaos agents can trigger sabotages.",
            )
        sab = room.sabotages.get(sabotage_id)
        if sab is None:
            raise GameRoomError(code="UNKNOWN_SABOTAGE", message=f"Unknown {sabotage_id!r}.")
        if sab.cooldown_remaining > 0:
            raise GameRoomError(code="SABOTAGE_ON_COOLDOWN", message="Sabotage on cooldown.")
        # Tier 2.5: while comms are down, no other sabotage can be triggered.
        # Comms-outage itself is exempt so chaos can chain it (and the repair
        # path runs through repair_sabotage anyway, not here).
        if room.comms_down and sabotage_id != "comms_outage":
            raise GameRoomError(
                code="COMMS_DOWN", message="Slack ist down — keine weitere Sabotage."
            )
        # Tier 2.7 (rework): chaos must stand at a task anchor whose
        # ``object_type`` matches the sabotage's ``trigger_object_types``. Same
        # physical spot as the matching release task → observers can't tell
        # sabotage from work. Maps with zero typed anchors fall back to the
        # legacy "trigger from anywhere" path so editor maps don't break.
        if self.has_typed_anchors() and not self._near_object(player, sab.definition):
            hint = sab.definition.object_hint or "passendes Terminal"
            raise GameRoomError(
                code="NOT_NEAR_OBJECT",
                message=f"Stell dich an {hint}, um zu sabotieren.",
            )

        # Apply the effect.
        if sabotage_id == "ci_cd_red":
            room.pipeline_stability = max(0, room.pipeline_stability - 20)
        elif sabotage_id == "coffee_outage":
            room.coffee_level = 0
            # Tier 3.5: outage also halves every player's personal energy.
            for p in room.players.values():
                p.coffee_energy = min(p.coffee_energy, p.max_coffee * 0.4)
        elif sabotage_id == "mandatory_meeting":
            room.meeting_active_for = MEETING_DURATION
        elif sabotage_id == "merge_conflict_storm":
            room.pipeline_stability = max(0, room.pipeline_stability - 10)
        elif sabotage_id == "fake_customer_request":
            room.release_progress = max(0, room.release_progress - 15)
        elif sabotage_id == "flaky_tests":
            pass  # Effect lives entirely in incidents_increase.
        elif sabotage_id == "lights_out":
            room.lights_off = True
        elif sabotage_id == "comms_outage":
            room.comms_down = True
        # Future sabotages: add here.

        if sab.definition.incidents_increase:
            room._apply_incidents_delta(sab.definition.incidents_increase)

        sab.cooldown_remaining = sab.definition.cooldown_seconds
        room.triggered_sabotages_by_player[player_id] = (
            room.triggered_sabotages_by_player.get(player_id, 0) + 1
        )

        if sabotage_id == "ci_cd_red":
            room._emit_event("danger", "Die Pipeline ist rot. Niemand weiß warum.")
        elif sabotage_id == "coffee_outage":
            room._emit_event("warn", "Die Kaffeemaschine ist offline.")
        elif sabotage_id == "mandatory_meeting":
            room._emit_event("warn", "Ein Meeting ohne Agenda wurde gestartet.")
        elif sabotage_id == "merge_conflict_storm":
            room._emit_event("danger", "Merge-Konflikt-Apokalypse — die Pipeline ringt um Luft.")
        elif sabotage_id == "fake_customer_request":
            room._emit_event("warn", "Eine kleine Kundenänderung. Scope explodiert.")
        elif sabotage_id == "flaky_tests":
            room._emit_event("warn", "Die Tests schlagen fehl, aber nur manchmal.")
        elif sabotage_id == "lights_out":
            room._emit_event("danger", "PagerDuty-Storm — alle starren auf ihre Telefone.")
        elif sabotage_id == "comms_outage":
            room._emit_event("danger", "Slack ist down. Niemand kommuniziert.")

    def repair(self, player_id: str, sabotage_id: str) -> None:
        """Tier 2.4: a player at the matching sabotage panel clears the effect.

        One-shot interact (no hold) — Among Us classic uses a mini-puzzle, but
        for the MVP we keep the cost a positional one. The chaos agent has to
        physically reach the panel, which usually means crossing the map and
        risking detection.
        """
        room = self._room
        if room.phase not in (Phase.PLAYING, Phase.MEETING):
            raise GameRoomError(
                code="WRONG_PHASE", message="Repair only allowed during a running round."
            )
        player = room.players.get(player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        if not player.is_alive:
            raise GameRoomError(
                code="PLAYER_ELIMINATED", message="Eliminated players cannot repair."
            )
        sab = room.sabotages.get(sabotage_id)
        if sab is None:
            raise GameRoomError(code="UNKNOWN_SABOTAGE", message=f"Unknown {sabotage_id!r}.")
        # Only currently-active sabotages can be repaired.
        if sabotage_id == "lights_out":
            if not room.lights_off:
                raise GameRoomError(code="SABOTAGE_NOT_ACTIVE", message="lights_out is not active.")
        elif sabotage_id == "comms_outage":
            if not room.comms_down:
                raise GameRoomError(
                    code="SABOTAGE_NOT_ACTIVE", message="comms_outage is not active."
                )
        else:
            raise GameRoomError(
                code="SABOTAGE_NOT_REPAIRABLE",
                message=f"{sabotage_id!r} has no repair panel.",
            )
        # Look in legacy SabotagePanel first, then Tier-4 MapObjects with
        # ``sabotage_repair_id`` set. A map can use either.
        panel_pos = next(
            ((p.x, p.y) for p in room.map.sabotage_panels if p.sabotage_id == sabotage_id),
            None,
        )
        if panel_pos is None:
            panel_pos = next(
                ((o.x, o.y) for o in room.map.map_objects if o.sabotage_repair_id == sabotage_id),
                None,
            )
        if panel_pos is None:
            raise GameRoomError(code="NO_PANEL", message=f"Map has no panel for {sabotage_id!r}.")
        dx = player.x - panel_pos[0]
        dy = player.y - panel_pos[1]
        if (
            dx * dx + dy * dy
            > SABOTAGE_PANEL_INTERACTION_RADIUS * SABOTAGE_PANEL_INTERACTION_RADIUS
        ):
            raise GameRoomError(code="TOO_FAR", message="Move closer to the panel.")

        if sabotage_id == "lights_out":
            room.lights_off = False
            room._emit_event("info", f"{player.name} hat das PagerDuty-Storm beendet.")
        elif sabotage_id == "comms_outage":
            room.comms_down = False
            room._emit_event("info", f"{player.name} hat Slack wieder online gebracht.")

    def tick(self, dt: float) -> None:
        """Per-tick: decay cooldowns + recompute active flags for UI."""
        room = self._room
        for sab in room.sabotages.values():
            if sab.cooldown_remaining > 0:
                sab.cooldown_remaining = max(0.0, sab.cooldown_remaining - dt)
            # Recompute active flag for UI:
            if sab.definition.id == "coffee_outage":
                sab.active = room.coffee_level == 0
            elif sab.definition.id == "mandatory_meeting":
                sab.active = room.meeting_active_for > 0
            elif sab.definition.id == "lights_out":
                sab.active = room.lights_off
            elif sab.definition.id == "comms_outage":
                sab.active = room.comms_down
            else:
                sab.active = False
        if room.meeting_active_for > 0:
            room.meeting_active_for = max(0.0, room.meeting_active_for - dt)

    # --- helpers used by serializer + neighbouring controllers --------------

    def has_typed_anchors(self) -> bool:
        """True if the loaded map has at least one anchor with ``object_type``
        set. Used as the gate for Tier 2.7's themed-object sabotage binding —
        maps that haven't been ported yet fall back to the legacy "from
        anywhere" path so editor maps stay playable.

        Both legacy ``task_anchors`` and Tier-4 ``map_objects`` count.
        """
        room_map = self._room.map
        return any(a.object_type for a in room_map.task_anchors) or any(
            o.object_type for o in room_map.map_objects
        )

    def object_type_for_task(self, task_id: str) -> str | None:
        for a in self._room.map.task_anchors:
            if a.task_id == task_id:
                return a.object_type
        for o in self._room.map.map_objects:
            if o.task_id == task_id:
                return o.object_type
        return None

    def object_anchors_for(self, sab_def: SabotageDefinition) -> list[tuple[float, float]]:
        """Position list (x, y) of every anchor matching this sabotage's allowed
        types — used by client-facing public state so the UI can show hints and
        decide button availability without needing the sabotages module."""
        if not sab_def.trigger_object_types:
            return []
        allowed = set(sab_def.trigger_object_types)
        out: list[tuple[float, float]] = [
            (a.x, a.y)
            for a in self._room.map.task_anchors
            if a.object_type and a.object_type in allowed
        ]
        out.extend(
            (o.x, o.y)
            for o in self._room.map.map_objects
            if o.object_type and o.object_type in allowed
        )
        return out

    # --- private -------------------------------------------------------------

    def _near_object(self, player, sab_def: SabotageDefinition) -> bool:
        """Tier 2.7 rework: True iff the player stands within reach of any
        anchor (legacy ``task_anchor`` or Tier-4 ``map_object``) whose
        ``object_type`` matches one of the sabotage's allowed trigger types.
        Same anchor as the corresponding release task — sabotage looks like
        normal terminal work to outsiders."""
        if not sab_def.trigger_object_types:
            return True  # legacy sabotages without binding (defensive default)
        allowed = set(sab_def.trigger_object_types)
        r2 = SABOTAGE_OBJECT_INTERACTION_RADIUS * SABOTAGE_OBJECT_INTERACTION_RADIUS
        for a in self._room.map.task_anchors:
            if a.object_type and a.object_type in allowed:
                dx = player.x - a.x
                dy = player.y - a.y
                if dx * dx + dy * dy <= r2:
                    return True
        for o in self._room.map.map_objects:
            if o.object_type and o.object_type in allowed:
                dx = player.x - o.x
                dy = player.y - o.y
                if dx * dx + dy * dy <= r2:
                    return True
        return False
