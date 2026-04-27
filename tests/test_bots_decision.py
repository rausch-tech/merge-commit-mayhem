"""Tests for app/game/bots/decision.py — LLM intent + reactive overrides.

We never hit a real LLM. A `_StubLLM` records the prompts it gets and
returns canned responses. Reactive overrides (body reports, votes) are
exercised via direct manager.tick() calls in fast-forward.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.game.bots.decision import (
    LLM_DECISION_INTERVAL_SEC,
    DecisionState,
    apply_reactive_overrides,
    llm_pick_target,
    maybe_consult_llm,
    tick_llm_cooldowns,
)
from app.game.game_room import GameRoom
from app.game.models import Phase
from app.game.runtime import Body
from app.game.tasks import TASK_RESPAWN_COOLDOWN


@dataclass
class _StubLLM:
    """Deterministic LLM stand-in. Record calls + return a canned text."""

    response: str | None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 256,
    ) -> str | None:
        self.calls.append({"system": system, "user": user, "max_tokens": max_tokens})
        return self.response


# --- helpers ---------------------------------------------------------------


def _start_room_with_humans_and_bots(human_count: int = 4, bot_count: int = 1) -> GameRoom:
    room = GameRoom(code="ABCD")
    room.add_player("Host")
    for i in range(human_count - 1):
        room.add_player(f"Human{i}")
    for _ in range(bot_count):
        room._bots.add_bot()
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.start(host_id)
    return room


# --- llm_pick_target -------------------------------------------------------


def test_llm_pick_target_returns_known_id() -> None:
    room = _start_room_with_humans_and_bots()
    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    valid_id = next(iter(room.tasks)).split(":")[0]  # any task id
    valid_id = next(iter(room.tasks))
    stub = _StubLLM(response=valid_id)

    out = llm_pick_target(stub, room, bot)
    assert out == valid_id
    assert len(stub.calls) == 1
    # System prompt establishes Release-Team identity.
    assert "Release Team" in stub.calls[0]["system"]
    # User prompt enumerates the available tasks.
    assert valid_id in stub.calls[0]["user"]


def test_llm_pick_target_strips_quotes_and_whitespace() -> None:
    room = _start_room_with_humans_and_bots()
    bot = room.players[next(iter(room._bots.bot_ids()))]
    valid_id = next(iter(room.tasks))
    stub = _StubLLM(response=f'  "{valid_id}"  ')
    assert llm_pick_target(stub, room, bot) == valid_id


def test_llm_pick_target_recovers_id_from_prefixed_response() -> None:
    """Models sometimes wrap the id in 'task: <id>' or similar boilerplate."""
    room = _start_room_with_humans_and_bots()
    bot = room.players[next(iter(room._bots.bot_ids()))]
    valid_id = next(iter(room.tasks))
    stub = _StubLLM(response=f"I'd recommend doing task {valid_id} first.")
    assert llm_pick_target(stub, room, bot) == valid_id


def test_llm_pick_target_returns_none_for_unknown_id() -> None:
    room = _start_room_with_humans_and_bots()
    bot = room.players[next(iter(room._bots.bot_ids()))]
    stub = _StubLLM(response="nonexistent_task_id")
    assert llm_pick_target(stub, room, bot) is None


def test_llm_pick_target_returns_none_when_llm_returns_none() -> None:
    room = _start_room_with_humans_and_bots()
    bot = room.players[next(iter(room._bots.bot_ids()))]
    stub = _StubLLM(response=None)
    assert llm_pick_target(stub, room, bot) is None


def test_llm_pick_target_returns_none_when_no_tasks_available() -> None:
    room = _start_room_with_humans_and_bots()
    for t in room.tasks.values():
        t.status = "cooldown"
        t.cooldown_remaining = TASK_RESPAWN_COOLDOWN
    bot = room.players[next(iter(room._bots.bot_ids()))]
    stub = _StubLLM(response="anything")
    assert llm_pick_target(stub, room, bot) is None
    # Must short-circuit before calling the LLM.
    assert stub.calls == []


# --- maybe_consult_llm + cooldown ------------------------------------------


def test_maybe_consult_llm_no_op_without_llm() -> None:
    room = _start_room_with_humans_and_bots()
    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None
    assert maybe_consult_llm(room._bots, room._bots._decisions, bot, state) is False


def test_maybe_consult_llm_sets_intent_and_bumps_cooldown() -> None:
    room = _start_room_with_humans_and_bots()
    valid_id = next(iter(room.tasks))
    room._bots.set_llm(_StubLLM(response=valid_id))
    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    assert maybe_consult_llm(room._bots, room._bots._decisions, bot, state) is True
    assert state.target_task_id == valid_id
    ds = room._bots._decisions[bot_id]
    assert ds.next_llm_call_in == pytest.approx(LLM_DECISION_INTERVAL_SEC)


def test_maybe_consult_llm_skips_when_cooldown_pending() -> None:
    room = _start_room_with_humans_and_bots()
    stub = _StubLLM(response=next(iter(room.tasks)))
    room._bots.set_llm(stub)
    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    # First call hits the LLM.
    assert maybe_consult_llm(room._bots, room._bots._decisions, bot, state) is True
    # Second call within cooldown must skip.
    state.target_task_id = None
    assert maybe_consult_llm(room._bots, room._bots._decisions, bot, state) is False
    assert len(stub.calls) == 1


def test_tick_llm_cooldowns_drains_to_zero() -> None:
    decisions = {"a": DecisionState(next_llm_call_in=2.0)}
    tick_llm_cooldowns(decisions, dt=1.5)
    assert decisions["a"].next_llm_call_in == pytest.approx(0.5)
    tick_llm_cooldowns(decisions, dt=1.0)
    # Doesn't go negative — clamped at zero by the gate (< check stops decrement).
    assert decisions["a"].next_llm_call_in <= 0.0


def test_maybe_consult_llm_does_not_bump_cooldown_on_failure() -> None:
    """Transient LLM error must allow the next pick_next_target to retry."""
    room = _start_room_with_humans_and_bots()
    room._bots.set_llm(_StubLLM(response="garbage_unknown_id"))
    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    state = room._bots.state_for(bot_id)
    assert state is not None

    assert maybe_consult_llm(room._bots, room._bots._decisions, bot, state) is False
    ds = room._bots._decisions[bot_id]
    assert ds.next_llm_call_in == 0.0


# --- reactive overrides: body report ---------------------------------------


def test_bot_reports_nearby_body() -> None:
    room = _start_room_with_humans_and_bots(human_count=4, bot_count=1)
    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    bot.x = 100.0
    bot.y = 100.0
    body = Body(id="bid", x=110.0, y=110.0, color="#fff", victim_player_id="vp", victim_name="Lea")
    room.bodies[body.id] = body

    apply_reactive_overrides(room._bots, room._bots._decisions, random.Random(0), dt=0.0)
    assert room.phase is Phase.MEETING


def test_bot_does_not_report_far_body() -> None:
    room = _start_room_with_humans_and_bots(human_count=4, bot_count=1)
    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    bot.x = 100.0
    bot.y = 100.0
    body = Body(id="bid", x=900.0, y=900.0, color="#fff", victim_player_id="vp", victim_name="Lea")
    room.bodies[body.id] = body

    apply_reactive_overrides(room._bots, room._bots._decisions, random.Random(0), dt=0.0)
    assert room.phase is Phase.PLAYING


def test_dead_bot_does_not_report_body() -> None:
    room = _start_room_with_humans_and_bots(human_count=4, bot_count=1)
    bot_id = next(iter(room._bots.bot_ids()))
    bot = room.players[bot_id]
    bot.is_alive = False
    bot.x = 100.0
    bot.y = 100.0
    room.bodies["bid"] = Body(
        id="bid", x=110.0, y=110.0, color="#fff", victim_player_id="vp", victim_name="Lea"
    )

    apply_reactive_overrides(room._bots, room._bots._decisions, random.Random(0), dt=0.0)
    assert room.phase is Phase.PLAYING


# --- reactive overrides: meeting voting ------------------------------------


def test_bot_eventually_votes_in_meeting() -> None:
    """After the per-bot 'thinking' delay, a bot casts a vote (skip or target)."""
    room = _start_room_with_humans_and_bots(human_count=4, bot_count=1)
    bot_id = next(iter(room._bots.bot_ids()))
    host_id = next(p.id for p in room.players.values() if p.is_host)
    # Drive the meeting via the controller directly — avoids the
    # WAR_ROOM gate that the public emergency-call API enforces.
    room._meeting_ctl.begin_meeting(host_id, title="test meeting", body=None, consume_quota=True)
    assert room.phase is Phase.MEETING

    rng = random.Random(0)
    # 30 ticks of 1 s each must exceed the 4-12 s vote-delay band.
    for _ in range(30):
        apply_reactive_overrides(room._bots, room._bots._decisions, rng, dt=1.0)

    # Either the bot voted (recorded in room.votes) or the meeting
    # resolved early because everybody alive voted. In both cases the
    # bot's decision state captures voted_for ≠ None.
    ds = room._bots._decisions.get(bot_id)
    assert ds is not None
    assert ds.voted_for is not None


def test_bot_decision_state_resets_after_meeting_ends() -> None:
    room = _start_room_with_humans_and_bots(human_count=4, bot_count=1)
    bot_id = next(iter(room._bots.bot_ids()))
    # Pre-seed state from a previous meeting.
    room._bots._decisions[bot_id] = DecisionState(voted_for="someone", pending_vote_in=2.5)

    # Phase is PLAYING — reactive overrides should clear vote state.
    apply_reactive_overrides(room._bots, room._bots._decisions, random.Random(0), dt=0.1)
    ds = room._bots._decisions[bot_id]
    assert ds.voted_for is None
    assert ds.pending_vote_in is None
