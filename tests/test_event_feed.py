import random

import pytest

from app.game.game_room import (
    RECONNECT_GRACE_SECONDS,
    EventEntry,
    GameRoom,
)
from app.game.models import Phase
from app.game.tasks import TASK_RESPAWN_COOLDOWN, task_by_id

# --- helpers --------------------------------------------------------------


def _started_room(player_count: int = 4, seed: int = 0) -> tuple[GameRoom, list[str]]:
    # Tier 1.5 raised MIN_PLAYERS_TO_START to 4. With 4 players (1 chaos +
    # 3 release) Tier 2.1's chaos-parity rule still does not fire on tick.
    if player_count < 4:
        player_count = 4
    room = GameRoom(code="EVNT")
    ids = []
    for i in range(player_count):
        ids.append(room.add_player(f"p{i}").id)
    room.start(requesting_player_id=ids[0], rng=random.Random(seed))
    return room, ids


def _chaos_id(room: GameRoom) -> str:
    cid = next(p.id for p in room.players.values() if p.team == "chaos_agents")
    # Tier 2.7: sabotages now require the chaos to stand at a console.
    # Snap on lookup so existing tests don't need to know about the gate.
    from tests.conftest import snap_to_first_console

    snap_to_first_console(room, cid)
    return cid


# --- pure buffer behaviour ------------------------------------------------


def test_buffer_caps_at_20():
    room = GameRoom(code="CAPS")
    for i in range(25):
        room._emit_event("info", f"msg {i}")
    assert len(room.events) == 20
    # The first 5 events (seq 1..5) were dropped; oldest remaining is seq 6.
    first = next(iter(room.events))
    assert isinstance(first, EventEntry)
    assert first.seq == 6
    # Newest is seq 25.
    last = list(room.events)[-1]
    assert last.seq == 25


def test_seq_monotonic():
    room = GameRoom(code="SEQ")
    room._emit_event("info", "a")
    room._emit_event("warn", "b")
    room._emit_event("danger", "c")
    seqs = [e.seq for e in room.events]
    assert seqs == [1, 2, 3]


def test_invalid_severity_raises():
    room = GameRoom(code="BAD")
    with pytest.raises(ValueError):
        room._emit_event("nope", "x")


# --- hook integration -----------------------------------------------------


def test_sabotage_emits_event():
    room, _ = _started_room(player_count=3)
    chaos_id = _chaos_id(room)
    pre_seqs = {e.seq for e in room.events}
    room.apply_sabotage(chaos_id, "ci_cd_red")
    new_events = [e for e in room.events if e.seq not in pre_seqs]
    assert any(e.severity == "danger" and "Pipeline ist rot" in e.message for e in new_events)


def test_task_complete_emits_event():
    room, _ = _started_room(player_count=2)
    pid = next(iter(room.players))
    p = room.players[pid]
    task_x, task_y = room.task_position("review_pr")
    p.x, p.y = task_x, task_y
    room.apply_task_hold_start(pid, "review_pr")
    pre_seqs = {e.seq for e in room.events}
    # Required time is 5.0s -- one big tick is enough to finish.
    required = task_by_id("review_pr").required_seconds
    room.tick(required + 0.1)
    new_events = [e for e in room.events if e.seq not in pre_seqs]
    assert any(
        e.severity == "info" and e.message == "Pull Request reviewen erledigt." for e in new_events
    )


def test_voting_result_does_not_leak_role():
    """Eliminating a chaos agent vs an innocent must produce identical text.

    The player name legitimately differs; what must not differ is the rest of
    the sentence -- i.e. the templated portion that follows the name.
    """

    def _eliminate_in_meeting(eliminate_team: str) -> tuple[str, str]:
        room, ids = _started_room(player_count=3)
        caller_id = ids[0]
        room.players[caller_id].x = 2000.0
        room.players[caller_id].y = 2000.0
        room.call_emergency_meeting(caller_id, rng=random.Random(0))
        target_id = next(
            p.id for p in room.players.values() if p.team == eliminate_team and p.is_alive
        )
        target_name = room.players[target_id].name
        for voter_id in [p.id for p in room.players.values() if p.is_alive]:
            room.cast_vote(voter_id, target_id)
        room._resolve_meeting()
        return room.events[-1].message, target_name

    msg_chaos, name_chaos = _eliminate_in_meeting("chaos_agents")
    msg_innocent, name_innocent = _eliminate_in_meeting("release_team")

    # Strip the leading name from each message; the rest must match.
    template_chaos = msg_chaos.removeprefix(f"{name_chaos} ")
    template_innocent = msg_innocent.removeprefix(f"{name_innocent} ")
    assert template_chaos == template_innocent

    # And no message may contain role/team words.
    for word in ("chaos", "vibe", "developer", "release"):
        assert word.lower() not in msg_chaos.lower()
        assert word.lower() not in msg_innocent.lower()


def test_round_end_emits_event_chaos_win():
    room, _ = _started_room(player_count=2)
    pre_seqs = {e.seq for e in room.events}
    room._finish_round("chaos_agents", "Die Pipeline ist tot.")
    new_events = [e for e in room.events if e.seq not in pre_seqs]
    assert len(new_events) == 1
    assert new_events[0].severity == "danger"
    assert new_events[0].message == "Runde vorbei: Die Pipeline ist tot."


def test_round_end_emits_event_release_win():
    room, _ = _started_room(player_count=2)
    pre_seqs = {e.seq for e in room.events}
    room._finish_round("release_team", "Release deployed.")
    new_events = [e for e in room.events if e.seq not in pre_seqs]
    assert len(new_events) == 1
    assert new_events[0].severity == "info"
    assert new_events[0].message == "Runde vorbei: Release deployed."


def test_disconnect_emits_event_only_during_play():
    # LOBBY: no event.
    room = GameRoom(code="DC1")
    pid = room.add_player("Alice").id
    room.add_player("Bob")
    assert room.phase is Phase.LOBBY
    pre_count = len(room.events)
    room.mark_disconnected(pid)
    assert len(room.events) == pre_count

    # PLAYING: one warn event.
    room2, ids = _started_room(player_count=3)
    pre_seqs = {e.seq for e in room2.events}
    pid2 = ids[1]
    name2 = room2.players[pid2].name
    room2.mark_disconnected(pid2)
    new_events = [e for e in room2.events if e.seq not in pre_seqs]
    assert len(new_events) == 1
    assert new_events[0].severity == "warn"
    assert name2 in new_events[0].message
    assert "offline" in new_events[0].message


def test_reconnect_emits_event_only_during_play():
    room, ids = _started_room(player_count=3)
    pid = ids[1]
    room.mark_disconnected(pid)
    pre_seqs = {e.seq for e in room.events}
    room.mark_reconnected(pid)
    new_events = [e for e in room.events if e.seq not in pre_seqs]
    assert len(new_events) == 1
    assert new_events[0].severity == "info"
    assert "zurück" in new_events[0].message


def test_sweep_disconnected_emits_finalization_event_during_play():
    import time

    room, ids = _started_room(player_count=3)
    pid = ids[1]
    name = room.players[pid].name
    room.mark_disconnected(pid)
    # Force the disconnect timestamp into the past.
    room.players[pid].disconnected_at_monotonic = time.monotonic() - RECONNECT_GRACE_SECONDS - 5
    pre_seqs = {e.seq for e in room.events}
    room._sweep_disconnected()
    assert pid not in room.players
    new_events = [e for e in room.events if e.seq not in pre_seqs]
    assert any(
        e.severity == "warn" and name in e.message and "endgültig" in e.message for e in new_events
    )


def test_start_clears_events_and_emits_kickoff():
    room = GameRoom(code="KICK")
    a = room.add_player("Alice")
    room.add_player("Bob")
    room.add_player("Carol")
    room.add_player("Dan")
    # Manually inject some bogus events while still in LOBBY.
    room._emit_event("info", "junk 1")
    room._emit_event("warn", "junk 2")
    assert len(room.events) == 2

    room.start(requesting_player_id=a.id, rng=random.Random(0))
    # After start: only the kickoff event remains.
    assert len(room.events) == 1
    only = room.events[0]
    assert only.seq == 1
    assert only.severity == "info"
    assert only.message == "Release-Fenster offen. Los geht's."


def test_reset_for_new_round_clears_events():
    room, _ = _started_room(player_count=3)
    chaos_id = _chaos_id(room)
    room.apply_sabotage(chaos_id, "ci_cd_red")
    assert len(room.events) >= 1
    room.reset_for_new_round()
    assert len(room.events) == 0
    assert room._next_event_seq == 1


def test_public_state_includes_events_camelcase():
    room, _ = _started_room(player_count=3)
    chaos_id = _chaos_id(room)
    room.apply_sabotage(chaos_id, "ci_cd_red")
    state = room.public_state()
    assert "events" in state
    assert isinstance(state["events"], list)
    assert state["events"], "expected at least one event after sabotage"
    for entry in state["events"]:
        assert set(entry.keys()) == {"seq", "severity", "message"}
        assert entry["severity"] in {"info", "warn", "danger"}
        assert isinstance(entry["seq"], int)
        assert isinstance(entry["message"], str)


def test_idle_tick_does_not_keep_emitting_events():
    """Sanity: ticking with no input should not spam the feed."""
    room, _ = _started_room(player_count=2)
    pre_count = len(room.events)
    for _ in range(20):
        room.tick(0.1)
    assert len(room.events) == pre_count


def test_body_found_emits_danger_event_with_both_names():
    """Tier 2.1: report_body emits a danger-level event naming both the
    reporter and the victim. Take-Down itself MUST NOT emit an event.
    """
    room, ids = _started_room(player_count=4)
    chaos_id = _chaos_id(room)
    release_ids = [p.id for p in room.players.values() if p.team == "release_team"]
    victim_id = release_ids[0]
    reporter_id = release_ids[1]

    # Stage take-down.
    room.players[chaos_id].x, room.players[chaos_id].y = 1000.0, 1000.0
    room.players[victim_id].x, room.players[victim_id].y = 1000.0, 1010.0
    pre_seqs_kill = {e.seq for e in room.events}
    body = room.apply_takedown(killer_id=chaos_id, target_id=victim_id)
    new_after_kill = [e for e in room.events if e.seq not in pre_seqs_kill]
    assert new_after_kill == [], "Take-Down must not emit any event"

    # Reporter walks to body and reports.
    room.players[reporter_id].x, room.players[reporter_id].y = body.x, body.y
    pre_seqs_report = {e.seq for e in room.events}
    room.apply_report_body(reporter_id=reporter_id, body_id=body.id)
    new_after_report = [e for e in room.events if e.seq not in pre_seqs_report]
    assert any(
        e.severity == "danger"
        and room.players[reporter_id].name in e.message
        and room.players[victim_id].name in e.message
        for e in new_after_report
    )


def test_task_cooldown_does_not_re_emit_completion():
    """Once a task is cooling down, ticking it should not emit again."""
    room, _ = _started_room(player_count=2)
    pid = next(iter(room.players))
    p = room.players[pid]
    task_x, task_y = room.task_position("review_pr")
    p.x, p.y = task_x, task_y
    room.apply_task_hold_start(pid, "review_pr")
    required = task_by_id("review_pr").required_seconds
    room.tick(required + 0.1)
    # Now in cooldown. Tick a few more times -- no further completion events.
    seen = len(room.events)
    for _ in range(5):
        room.tick(min(TASK_RESPAWN_COOLDOWN / 10, 0.5))
    assert len(room.events) == seen
