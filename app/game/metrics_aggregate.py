"""Read the per-round JSONL files written by ``metrics_export.py`` and
aggregate them for the ``GET /api/metrics`` endpoint.

Schema of one input line (see ``metrics_export.round_metrics_payload``):
``{timestamp, roomCode, winner, reason, durationSeconds, numPlayers,
meetingsCalled, forceReboots, tasksByRole, sabotagesTriggeredTotal,
repairsCompleted, coffeeEnergyAvgAtEnd, playersAliveAtEnd}``.

Aggregator returns win-rates per team, mean duration / meetings /
force-reboots, summed task counts per role, etc. Designed for cheap
read-only access — Sven hits ``/api/metrics`` after a Live-Test to see
balancing trends without scp'ing the JSONL files off the server.

Failure modes:

- ``MCM_METRICS_DIR`` unset / directory missing → ``metricsAvailable=False``.
- File unreadable / malformed line → skipped silently (one bad row
  shouldn't poison the aggregation).
- No rounds in window → ``totalRounds=0`` with the same shape so callers
  don't need to special-case empty.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from app.game.metrics_export import _resolve_metrics_dir


def aggregate_metrics(since: date | None = None, metrics_dir: Path | None = None) -> dict[str, Any]:
    """Aggregate all JSONL metric files under ``metrics_dir`` (or the
    env-resolved default). Filter by per-file ``YYYY-MM-DD`` filename to
    keep IO cheap when ``since`` is recent."""
    target = metrics_dir if metrics_dir is not None else _resolve_metrics_dir()
    if target is None or not target.exists():
        return {
            "metricsAvailable": False,
            "message": "MCM_METRICS_DIR not configured or directory missing.",
        }

    rounds: list[dict[str, Any]] = []
    for path in sorted(target.glob("*.jsonl")):
        try:
            file_date = date.fromisoformat(path.stem)
        except ValueError:
            # Files with non-ISO names (e.g. backups) — skip silently.
            continue
        if since is not None and file_date < since:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rounds.append(json.loads(stripped))
            except json.JSONDecodeError:
                # One corrupt row — skip, keep aggregating the rest.
                continue
    return _aggregate(rounds, since)


def _aggregate(rounds: list[dict[str, Any]], since: date | None) -> dict[str, Any]:
    n = len(rounds)
    if n == 0:
        return {
            "metricsAvailable": True,
            "totalRounds": 0,
            "since": since.isoformat() if since else None,
            "message": "No rounds in the requested window.",
        }

    winners: dict[str, int] = {}
    durations: list[float] = []
    num_players: list[int] = []
    meetings: list[int] = []
    force_reboots: list[int] = []
    tasks_by_role: dict[str, int] = {}
    reasons: dict[str, int] = {}
    sabotages_total = 0
    repairs_total = 0
    coffee_end: list[float] = []
    players_alive_end: list[int] = []

    for r in rounds:
        winner = str(r.get("winner") or "unknown")
        winners[winner] = winners.get(winner, 0) + 1
        reason = str(r.get("reason") or "unknown")
        reasons[reason] = reasons.get(reason, 0) + 1
        d = r.get("durationSeconds")
        if isinstance(d, (int, float)):
            durations.append(float(d))
        np = r.get("numPlayers")
        if isinstance(np, int):
            num_players.append(np)
        m = r.get("meetingsCalled")
        if isinstance(m, int):
            meetings.append(m)
        fb = r.get("forceReboots")
        if isinstance(fb, int):
            force_reboots.append(fb)
        for role, count in (r.get("tasksByRole") or {}).items():
            tasks_by_role[str(role)] = tasks_by_role.get(str(role), 0) + int(count)
        sabotages_total += int(r.get("sabotagesTriggeredTotal") or 0)
        repairs_total += int(r.get("repairsCompleted") or 0)
        ce = r.get("coffeeEnergyAvgAtEnd")
        if isinstance(ce, (int, float)):
            coffee_end.append(float(ce))
        pae = r.get("playersAliveAtEnd")
        if isinstance(pae, int):
            players_alive_end.append(pae)

    def avg(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 2) if xs else None

    def avg_int(xs: list[int]) -> float | None:
        return round(sum(xs) / len(xs), 2) if xs else None

    return {
        "metricsAvailable": True,
        "totalRounds": n,
        "since": since.isoformat() if since else None,
        "winners": winners,
        "winRateRelease": round(winners.get("release_team", 0) / n, 3),
        "winRateChaos": round(winners.get("chaos_agents", 0) / n, 3),
        "winReasons": reasons,
        "avgDurationSeconds": avg(durations),
        "avgNumPlayers": avg_int(num_players),
        "avgMeetingsCalled": avg_int(meetings),
        "avgForceReboots": avg_int(force_reboots),
        "avgPlayersAliveAtEnd": avg_int(players_alive_end),
        "avgCoffeeAtEnd": avg(coffee_end),
        "tasksByRoleTotal": tasks_by_role,
        "sabotagesTriggeredTotal": sabotages_total,
        "repairsCompletedTotal": repairs_total,
    }
