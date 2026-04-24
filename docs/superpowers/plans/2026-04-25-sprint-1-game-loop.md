# Sprint 1 Completion: Game Loop — Implementation Plan

> **For agentic workers:** This plan is the execution roadmap for the spec at
> `docs/superpowers/specs/2026-04-25-sprint-1-game-loop-design.md`. Each bundle
> below maps to one focused commit. Each has concrete TDD cycles. Implementer
> subagents receive the full task text in their prompt — this file is the
> coordinator's reference.

**Goal:** Extend the Vertical Slice into a playable game: tasks give release progress, sabotages attack pipeline/coffee/speed, one side wins, endscreen reveals roles.

**Architecture:** Backend-authoritative extension. New modules `tasks.py` + `sabotages.py` hold definitions; `game_room.py` grows runtime state + tick logic; `protocol.py` adds message types + extended game_state. Frontend grows HUD pills, task markers on canvas, task list sidebar, sabotage buttons, endscreen overlay. Assets: logo + click sounds only (spritesheets deferred).

**Tech Stack:** Same as Vertical Slice. Python 3.12 + uv + FastAPI + Pydantic v2 + Vanilla JS + Canvas.

**Reference Spec:** `docs/superpowers/specs/2026-04-25-sprint-1-game-loop-design.md`

---

## Worktree + Branch State

- Branch: `slice/game-loop`
- Worktree: `/home/sven-rausch/se/mcm/.worktrees/game-loop`
- Branched from `main` at `3597f60`
- Push policy: **never without Sven's explicit approval** (this plan runs overnight; branch stays local)

---

## Bundle Order

Bundles are numbered and must land in order. Each is one commit and should be reviewed before the next starts.

| # | Bundle | Files touched | Tests |
|---|---|---|---|
| B0 | Commit spec + plan | `docs/superpowers/specs/...`, `docs/superpowers/plans/...` | — |
| B1 | Task + Sabotage definitions + shared constants | `app/game/tasks.py`, `app/game/sabotages.py` | `tests/test_tasks.py` (definitions only) |
| B2 | GameRoom: ENDED phase + counters + reset | `app/game/models.py`, `app/game/game_room.py`, `tests/test_game_room.py` | existing + new reset test |
| B3 | GameRoom: task hold lifecycle | `app/game/game_room.py`, `tests/test_tasks.py` | new tests |
| B4 | GameRoom: sabotage lifecycle + effects | `app/game/game_room.py`, `tests/test_sabotages.py` | new tests |
| B5 | GameRoom: movement modifiers + tick integration | `app/game/game_room.py`, `tests/test_game_room.py` | new tests |
| B6 | GameRoom: win conditions + ENDED freeze | `app/game/game_room.py`, `tests/test_win_conditions.py` | new file |
| B7 | Protocol: new messages + extended game_state + game_ended | `app/protocol.py`, `tests/test_protocol.py` | new tests |
| B8 | Main: handlers + tick integration + game_ended broadcast | `app/main.py`, `tests/test_ws_protocol.py` | new integration tests |
| B9 | Frontend: HUD stat pills (4) | `static/hud.js`, `static/index.html`, `static/styles.css` | manual (rendered by server) |
| B10 | Frontend: task markers on canvas + task list sidebar | `static/render.js`, `static/tasks.js` (new), `static/index.html`, `static/styles.css` | manual |
| B11 | Frontend: E-key task interaction | `static/input.js`, `static/main.js` | manual |
| B12 | Frontend: sabotage buttons (chaos only) | `static/sabotages.js` (new), `static/main.js`, `static/index.html`, `static/styles.css` | manual |
| B13 | Frontend: endscreen overlay + return_to_lobby | `static/endscreen.js` (new), `static/main.js`, `static/index.html`, `static/styles.css` | manual |
| B14 | Assets: logo in lobby + click sounds | `static/audio.js` (new), `static/index.html`, `static/main.js`, `static/styles.css` | manual |
| B15 | Handoff document | `docs/HANDOFF-2026-04-25.md` | — |

**Stop criteria:**
- Any bundle breaks the test suite → stop, write what's broken into handoff
- Manual smoke test of server startup fails → stop
- Any subagent returns BLOCKED with a real blocker → stop, document

## Conventions (apply to every bundle)

- Work from `/home/sven-rausch/se/mcm/.worktrees/game-loop/` always
- `uv run pytest` must be green after every bundle
- Conventional commits (`feat(...):`, `fix(...):`, `test(...):`, etc.)
- Co-author trailer: `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- No emojis
- No `git push`, no `git config`
- Bundles land on `slice/game-loop` branch only

## Balancing constants (single source of truth)

These are used across B1 + B5 + B4 + backend speed calculation. Define once.

```python
# app/game/config_defaults.py (or inline in tasks.py / sabotages.py / game_room.py)

TASK_INTERACTION_RADIUS = 40.0        # px
NORMAL_SPEED = 120.0                  # px/s
COFFEE_SLOW_SPEED = 60.0              # px/s when coffee_level == 0
MEETING_DURATION = 5.0                # s that mandatory_meeting slows all players
TASK_RESPAWN_COOLDOWN = 8.0           # s until a completed task becomes available again
```

## Test counts expected after each bundle

| After bundle | Expected `uv run pytest` count |
|---|---|
| B0 | 53 (unchanged) |
| B1 | ~55–58 (task/sabotage definition unit tests) |
| B2 | ~59–63 (ENDED phase, reset test, counters) |
| B3 | ~68–74 (hold lifecycle, cooldown, proximity) |
| B4 | ~75–82 (three sabotage effect tests + cooldowns + chaos-only) |
| B5 | ~83–87 (speed modifiers) |
| B6 | ~90–95 (win conditions, freeze in ENDED) |
| B7 | ~100–107 (protocol models) |
| B8 | ~110–118 (WS integration) |
| B9–B14 | unchanged from B8 (frontend not unit tested) |

Exact numbers are indicative, not a hard contract — the important rule is **they never go down**.

## Handoff expectations

On completion (or early stop), `docs/HANDOFF-2026-04-25.md` must include:

- Branch name and last commit SHA
- Which bundles landed, which were skipped, why
- Full test count
- Server-start smoke result
- Known issues (ambiguous design decisions, pending asset integration, etc.)
- Proposed „first review action" for Sven (e.g. „start server, open three tabs, press E on a task")
