"""Meeting controller — emergency meetings, voting, take-downs, body reports.

Bundles every player action that can either trigger a meeting (chaos
take-down → body → reporter call, war-room emergency call) or happen
inside one (vote, skip, the auto-resolve when the timer or unanimous-
vote condition fires). Lives together because the data flow is one
linear pipeline: take-down spawns a Body → another player reports it →
phase flips to MEETING → votes accumulate → resolve eliminates a
player and flips back to PLAYING.

Public surface:
    - apply_takedown(killer_id, target_id) -> Body
    - apply_report_body(reporter_id, body_id, rng=None)
    - call_emergency_meeting(requesting_player_id, rng=None)
    - cast_vote(voter_id, target_id)
    - skip_vote(voter_id)
    - resolve_meeting() -> eliminated player id or None
    - all_alive_voted()
    - aggregate_vote_counts()
    - snapshot_context(reporter_id, body)

Private:
    - _living_player_ids()
    - _room_label_for(x, y)
    - _begin_meeting(caller_id, title, rng_for_random_title=None,
                     body=None, consume_quota=False)
"""

from __future__ import annotations

import random
import uuid
from typing import TYPE_CHECKING

from app.game.models import InputState, Phase
from app.game.runtime import Body, GameRoomError
from app.game.voting import SKIP_TARGET
from app.game.voting import tally as _tally_votes
from app.protocol import (
    MeetingAlive,
    MeetingBody,
    MeetingContext,
    MeetingRecentEvent,
)

if TYPE_CHECKING:
    from app.game.game_room import GameRoom


TAKEDOWN_RADIUS = 40.0  # px
TAKEDOWN_COOLDOWN = 25.0  # seconds
REPORT_RADIUS = 40.0  # px

MEETING_DURATION_SECONDS = 60.0

_MEETING_TITLES = [
    "Wer hat auf main gepusht?",
    "Warum sind die Tests rot?",
    "Wieso ist der Kunde im Sprint?",
    "Wer hat den KI-Agenten unbeaufsichtigt gelassen?",
    "Wer hat den Coffee Token verbraucht?",
]


class MeetingController:
    def __init__(self, room: GameRoom) -> None:
        self._room = room

    # --- take-down + body-report --------------------------------------------

    def apply_takedown(self, killer_id: str, target_id: str) -> Body:
        """Eliminate the target via stealth take-down. Authoritative.
        No event emission — a take-down must not leak to the public feed."""
        room = self._room
        if room.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Take-Down nur im PLAYING.")
        killer = room.players.get(killer_id)
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
        target = room.players.get(target_id)
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
        if room.takedown_cooldowns.get(killer_id, 0.0) > 0:
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
        for task in room.tasks.values():
            if target_id in task.per_player_progress:
                task.per_player_progress.pop(target_id)
                if not task.per_player_progress and task.status == "in_progress":
                    task.status = "available"
        # Tier 3.1: a take-down victim drops their mini-game (and the modal
        # snaps shut on the client when the framework forwards 'killed').
        if target_id in room.active_mini_games:
            room._mini_games.cancel(target_id, "killed")
        room.bodies[body.id] = body
        room.takedown_cooldowns[killer_id] = TAKEDOWN_COOLDOWN
        return body

    def apply_report_body(self, reporter_id: str, body_id: str, rng=None) -> None:
        """Reporter discovers a body. Triggers a meeting that bypasses the
        war-room requirement and the per-round emergency meeting quota."""
        room = self._room
        if room.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Report nur im PLAYING.")
        reporter = room.players.get(reporter_id)
        if reporter is None or not reporter.is_connected:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Reporter nicht im Raum.")
        if not reporter.is_alive:
            raise GameRoomError(
                code="PLAYER_ELIMINATED", message="Eliminierte Spieler koennen nichts melden."
            )
        body = room.bodies.get(body_id)
        if body is None:
            raise GameRoomError(code="UNKNOWN_BODY", message="Unbekannter Body.")
        dx = reporter.x - body.x
        dy = reporter.y - body.y
        if (dx * dx + dy * dy) > (REPORT_RADIUS * REPORT_RADIUS):
            raise GameRoomError(code="OUT_OF_RANGE", message="Body ist zu weit weg.")

        # Pop the body and emit the public danger event.
        room.bodies.pop(body_id, None)
        room._emit_event(
            "danger",
            f"{reporter.name} hat einen Body gefunden: {body.victim_name}.",
        )

        # Direct transition into MEETING. Bypass war-room + meeting quota.
        self._begin_meeting(
            caller_id=reporter_id,
            title=f"Body Report: {body.victim_name}",
            body=body,
            consume_quota=False,
        )

    # --- emergency meetings --------------------------------------------------

    def call_emergency_meeting(
        self,
        requesting_player_id: str,
        rng: random.Random | None = None,
    ) -> None:
        room = self._room
        if room.phase is not Phase.PLAYING:
            raise GameRoomError(code="WRONG_PHASE", message="Meetings only during playing.")
        player = room.players.get(requesting_player_id)
        if player is None:
            raise GameRoomError(code="UNKNOWN_PLAYER", message="Player not in room.")
        if not player.is_alive:
            raise GameRoomError(
                code="PLAYER_ELIMINATED", message="Eliminated players cannot call meetings."
            )
        if not room._is_in_war_room(player):
            raise GameRoomError(
                code="NOT_IN_WAR_ROOM",
                message="Emergency meetings can only be called from the War Room.",
            )
        if not room.players_with_meeting_left.get(requesting_player_id, False):
            raise GameRoomError(
                code="NO_MEETING_LEFT",
                message="You already used your emergency meeting this round.",
            )

        r = rng or random.SystemRandom()
        self._begin_meeting(
            caller_id=requesting_player_id,
            title=r.choice(_MEETING_TITLES),
            body=None,
            consume_quota=True,
        )

    # --- voting --------------------------------------------------------------

    def cast_vote(self, voter_id: str, target_id: str) -> None:
        room = self._room
        if room.phase is not Phase.MEETING:
            raise GameRoomError(code="WRONG_PHASE", message="No meeting active.")
        voter = room.players.get(voter_id)
        if voter is None or not voter.is_alive:
            raise GameRoomError(code="CANNOT_VOTE", message="Only living players can vote.")
        target = room.players.get(target_id)
        if target is None or not target.is_alive:
            raise GameRoomError(
                code="INVALID_TARGET", message="Vote target must be a living player."
            )
        room.votes[voter_id] = target_id

    def skip_vote(self, voter_id: str) -> None:
        room = self._room
        if room.phase is not Phase.MEETING:
            raise GameRoomError(code="WRONG_PHASE", message="No meeting active.")
        voter = room.players.get(voter_id)
        if voter is None or not voter.is_alive:
            raise GameRoomError(code="CANNOT_VOTE", message="Only living players can vote.")
        room.votes[voter_id] = SKIP_TARGET

    def all_alive_voted(self) -> bool:
        living = set(self._living_player_ids())
        return living.issubset(set(self._room.votes.keys()))

    def aggregate_vote_counts(self) -> dict[str, int]:
        """Return {target_id: count} aggregating cast votes; SKIP_TARGET stays as ''."""
        counts: dict[str, int] = {}
        for target in self._room.votes.values():
            counts[target] = counts.get(target, 0) + 1
        return counts

    def resolve_meeting(self) -> str | None:
        """Tally votes, eliminate the loser if any, transition back to PLAYING.
        Returns the eliminated player_id or None."""
        room = self._room
        eliminated_id = _tally_votes(room.votes)
        # Compute extra fields the client needs in voting_result.
        counts: dict[str, int] = {}
        for target in room.votes.values():
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
        if eliminated_id and eliminated_id in room.players:
            room.players[eliminated_id].is_alive = False
            was_chaos = room.players[eliminated_id].team == "chaos_agents"
            removed_name = room.players[eliminated_id].name

        room.last_voting_result = {
            "removed_player_id": eliminated_id or "",
            "removed_player_name": removed_name,
            "was_chaos_agent": was_chaos,
            "tie": named_tie,
            "skipped": skip_won,
        }

        # Emit a public, role-neutral event. The text MUST NOT depend on
        # was_chaos — doing so would leak role info to spectators.
        if eliminated_id:
            room._emit_event("info", f"{removed_name} wurde aus dem Team entfernt.")
        elif named_tie:
            room._emit_event("warn", "Patt — niemand wurde entfernt.")
        elif skip_won:
            room._emit_event("info", "Niemand wurde entfernt.")

        # Reset meeting state and return to PLAYING.
        room.meeting_remaining_seconds = 0.0
        room.meeting_caller_id = None
        room.meeting_title = ""
        room.votes = {}
        room.phase = Phase.PLAYING
        return eliminated_id

    # --- meeting context snapshot (Tier 3.6) --------------------------------

    def snapshot_context(self, reporter_id: str | None, body: Body | None) -> None:
        """Capture context for the meeting overlay. Hints, never proofs — list
        of recent events, body location, reporter name, approximate death
        window. The client renders this verbatim."""
        room = self._room
        reporter_name = ""
        if reporter_id and reporter_id in room.players:
            reporter_name = room.players[reporter_id].name

        recent = [
            MeetingRecentEvent(severity=e.severity, message=e.message, seq=e.seq)
            for e in list(room.events)[-6:]
        ]

        body_block: MeetingBody | None = None
        if body is not None:
            body_block = MeetingBody(
                victim_name=body.victim_name,
                x=round(body.x, 1),
                y=round(body.y, 1),
                room=self._room_label_for(body.x, body.y),
            )

        room.meeting_context = MeetingContext(
            reporter_name=reporter_name,
            body=body_block,
            recent_events=recent,
            alive=[MeetingAlive(id=p.id, name=p.name) for p in room.players.values() if p.is_alive],
        )

    # --- private -------------------------------------------------------------

    def _begin_meeting(
        self,
        caller_id: str,
        title: str,
        body: Body | None,
        consume_quota: bool,
    ) -> None:
        """Shared transition: PLAYING -> MEETING. Resets task holds, cancels
        all mini-games, snapshots discussion context. Used by emergency
        meetings, body reports, and the Scrum-Master 'standup' ability via
        the room-level apply_use_ability shim."""
        room = self._room
        if consume_quota:
            room.players_with_meeting_left[caller_id] = False
        room.meeting_caller_id = caller_id
        room.meeting_remaining_seconds = MEETING_DURATION_SECONDS
        room.votes = {}
        room.meeting_title = title
        room.phase = Phase.MEETING
        # Cancel ongoing task holds — frozen during meeting.
        for task in room.tasks.values():
            task.per_player_progress = {}
            if task.status == "in_progress":
                task.status = "available"
        # Tier 3.1: end any active mini-games — modals snap shut as players
        # are pulled into the meeting overlay.
        room._mini_games.cancel_all("meeting_started")
        # Tier 3.6: meeting context snapshot.
        self.snapshot_context(reporter_id=caller_id, body=body)

    def _living_player_ids(self) -> list[str]:
        return [pid for pid, p in self._room.players.items() if p.is_alive]

    def _room_label_for(self, x: float, y: float) -> str:
        """Best-effort lookup of which room a coordinate falls in. Used by
        meeting context so the body's location is human-friendly ('Server
        Room' instead of '(800, 2400)')."""
        for room in self._room.map.rooms:
            if room.x <= x <= room.x + room.width and room.y <= y <= room.y + room.height:
                return room.title
        return "irgendwo"
