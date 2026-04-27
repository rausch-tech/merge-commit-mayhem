"""LLM decision layer for bots (Tier 3.9.2).

Layered on top of `BotManager` — opt-in via `BotManager.set_llm(client)`.
Without an LLM, bots stay on the random-task heuristic from `manager.py`.

Two responsibilities:

1. **Intent picker** (`llm_pick_target`) — every ~5 s per bot, ask the LLM
   which task to do next. Return value is a task id; falls back to the
   heuristic on timeout, parse failure, or unknown id. The LLM never
   gets to set positions, vote, or trigger sabotage — only nominate
   the next high-level "what should I work on" intent.

2. **Reactive overrides** (`apply_reactive_overrides`) — checked every
   tick, no LLM. If the bot can see a body, it reports immediately. If a
   meeting is running and the bot hasn't voted, it casts a heuristic
   vote after a small "thinking" delay. Sabotage repair is deferred to
   a later slice — the panel-location lookup needs more wiring.

The split is deliberate: high-level intent benefits from LLM "vibes"
(thematic task picks, persona consistency); split-second decisions like
"there's a body right next to me" must not wait 3 s for an LLM call.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.game.llm import LLMClient
from app.game.models import Phase
from app.game.runtime import GameRoomError

if TYPE_CHECKING:
    from app.game.bots.manager import BotManager, BotState
    from app.game.game_room import GameRoom
    from app.game.models import Player

logger = logging.getLogger(__name__)


# How often each bot consults the LLM for a new intent. Slow enough that
# 8 bots with a 3 s LLM timeout don't stack up >2 in-flight requests
# at any wall-clock instant; fast enough that bots react to a changed
# task availability landscape within a comfortable window.
LLM_DECISION_INTERVAL_SEC: float = 5.0

# How close a body must be (px) before a bot auto-reports it. Larger
# than the player-interaction radius so a bot doesn't have to walk over
# the body — being in the same room is enough.
_BODY_REPORT_RADIUS_PX: float = 200.0

# How long a bot "thinks" in a meeting before voting. Avoids the
# uncanny "every bot voted on tick 1" pattern.
_BOT_VOTE_THINK_SEC_MIN: float = 4.0
_BOT_VOTE_THINK_SEC_MAX: float = 12.0

_SYSTEM_PROMPT: str = (
    "You are an AI playing a social-deduction game with developers. "
    "You are on the Release Team — your job is to complete tasks. "
    "Pick the most useful next task from the list. "
    "Reply with ONLY the task id, nothing else. No explanation."
)


@dataclass
class DecisionState:
    """Per-bot decision-layer scratch state. Held alongside BotState in
    the manager via a parallel dict keyed by player_id."""

    next_llm_call_in: float = 0.0
    pending_vote_in: float | None = None  # None when not waiting to vote
    voted_for: str | None = None  # so we don't re-vote on phase flicker


def llm_pick_target(
    client: LLMClient,
    room: GameRoom,
    bot: Player,
) -> str | None:
    """Ask the LLM which available task this bot should attempt next.

    Returns a task_id, or `None` to fall through to the heuristic. The
    LLM is constrained by the user-prompt to a hard list of available
    tasks; anything off-list (or a parse failure) returns None.
    """
    available = [t for t in room.tasks.values() if t.status == "available"]
    if not available:
        return None

    listing = "\n".join(
        f"- {t.definition.id}: {t.definition.title} (room: {t.definition.room})" for t in available
    )
    user_prompt = (
        f"You are bot {bot.name!r} at position ({bot.x:.0f}, {bot.y:.0f}).\n"
        f"Available tasks:\n{listing}\n\n"
        "Which task id?"
    )
    raw = client.complete(system=_SYSTEM_PROMPT, user=user_prompt, max_tokens=32)
    if not raw:
        return None

    cleaned = raw.strip().strip("`'\"").split()[0] if raw.strip() else ""
    valid_ids = {t.definition.id for t in available}
    if cleaned in valid_ids:
        return cleaned
    # Sometimes models prefix with "task:" or similar.
    for tid in valid_ids:
        if tid in raw:
            return tid
    logger.info("llm picked unknown task id %r; falling back to heuristic", raw)
    return None


def apply_reactive_overrides(
    manager: BotManager,
    decisions: dict[str, DecisionState],
    rng: random.Random,
    dt: float,
) -> None:
    """Body-report and meeting-vote overrides for every alive bot.

    Called from `BotManager.tick` after the per-bot work loop, so it
    runs every frame (cheap: just proximity + phase checks). Each
    override re-uses the public GameRoom API — no controller surgery.
    """
    room = manager._room

    if room.phase is Phase.PLAYING:
        _check_body_reports(room, manager)
        # Reset per-bot vote state so the next meeting starts fresh.
        for ds in decisions.values():
            if ds.voted_for is not None or ds.pending_vote_in is not None:
                ds.pending_vote_in = None
                ds.voted_for = None
        return

    if room.phase is Phase.MEETING:
        _tick_meeting_votes(room, manager, decisions, rng, dt)


def _check_body_reports(room: GameRoom, manager: BotManager) -> None:
    """If any alive bot is within `_BODY_REPORT_RADIUS_PX` of a body it
    can see, fire a report. First bot wins — `apply_report_body` flips
    the room into MEETING and subsequent calls would error."""
    if not room.bodies:
        return
    radius_sq = _BODY_REPORT_RADIUS_PX * _BODY_REPORT_RADIUS_PX
    for bot_id in manager.bot_ids():
        bot = room.players.get(bot_id)
        if bot is None or not bot.is_alive:
            continue
        for body in list(room.bodies.values()):
            dx = bot.x - body.x
            dy = bot.y - body.y
            if dx * dx + dy * dy > radius_sq:
                continue
            try:
                room.apply_report_body(bot_id, body.id)
            except GameRoomError:
                # Another bot or human beat us to it — totally fine.
                return
            return


def _tick_meeting_votes(
    room: GameRoom,
    manager: BotManager,
    decisions: dict[str, DecisionState],
    rng: random.Random,
    dt: float,
) -> None:
    """Each alive bot picks a vote target after a short "thinking" delay.

    Heuristic: vote skip with 50 % probability, else cast for a random
    other alive non-bot player. The skip-bias matches Among-Us best
    practice — uncertain players default to skip — and avoids a swarm
    of bots ganging up on a single human early in a meeting.
    """
    for bot_id in manager.bot_ids():
        bot = room.players.get(bot_id)
        if bot is None or not bot.is_alive:
            continue
        ds = decisions.setdefault(bot_id, DecisionState())
        if ds.voted_for is not None:
            continue
        # Initialise the per-meeting "thinking" countdown lazily so the
        # first MEETING tick after PLAYING resets it cleanly.
        if ds.pending_vote_in is None:
            ds.pending_vote_in = rng.uniform(_BOT_VOTE_THINK_SEC_MIN, _BOT_VOTE_THINK_SEC_MAX)
        ds.pending_vote_in -= dt
        if ds.pending_vote_in > 0:
            continue

        target_id = _pick_vote_target(room, bot_id, manager, rng)
        try:
            if target_id == "":
                room.skip_vote(bot_id)
            else:
                room.cast_vote(bot_id, target_id)
        except GameRoomError as exc:
            logger.debug("bot vote rejected: %s", exc.message)
            ds.voted_for = "_failed_"
            continue
        ds.voted_for = target_id


def _pick_vote_target(
    room: GameRoom, voter_id: str, manager: BotManager, rng: random.Random
) -> str:
    """Skip 50% of the time; else vote for a random other alive human.

    Returns "" for skip, or a player id. Only humans are candidates so
    bots don't accidentally pile votes on each other (which feels
    weird in playtests — bots should look like dispassionate filler).
    """
    if rng.random() < 0.5:
        return ""
    candidates = [
        pid
        for pid, p in room.players.items()
        if p.is_alive and pid != voter_id and not manager.is_bot(pid)
    ]
    if not candidates:
        return ""
    return rng.choice(candidates)


def tick_llm_cooldowns(decisions: dict[str, DecisionState], dt: float) -> None:
    """Decrement every bot's per-tick LLM cooldown.

    Called once per game tick from `BotManager.tick`, separately from
    the consultation itself so `pick_next_target` (which can be called
    outside the tick path, e.g. from tests) doesn't burn cooldown.
    """
    for ds in decisions.values():
        if ds.next_llm_call_in > 0:
            ds.next_llm_call_in -= dt


def maybe_consult_llm(
    manager: BotManager,
    decisions: dict[str, DecisionState],
    bot: Player,
    state: BotState,
) -> bool:
    """Consult the LLM if its cooldown has expired for this bot.

    Returns True if the LLM successfully set an intent. False means
    `BotManager` should fall through to the random-task heuristic.
    Cooldown is bumped only on a successful intent set — a failed call
    (timeout, parse miss) lets the next pick_next_target retry rather
    than locking the bot to heuristic for 5 s after a transient error.
    """
    if manager._llm is None:
        return False
    ds = decisions.setdefault(bot.id, DecisionState())
    if ds.next_llm_call_in > 0:
        return False

    target_id = llm_pick_target(manager._llm, manager._room, bot)
    if target_id is None:
        return False
    manager._set_intent(bot, state, target_id)
    if state.target_task_id is None:
        return False
    ds.next_llm_call_in = LLM_DECISION_INTERVAL_SEC
    return True
