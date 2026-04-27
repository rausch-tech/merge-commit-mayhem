"""Tier 3.7 — Per-Runde Metrik-Export als JSONL.

Bei jedem ``_finish_round`` schreibt der Server eine einzelne JSON-Line
in ``<metrics_dir>/<YYYY-MM-DD>.jsonl``. Eine Datei pro Tag, eine
Zeile pro abgeschlossener Runde. Fuer einfache Analyse via ``jq`` /
``pandas`` / SQLite.

Aktivierung: ``MCM_METRICS_DIR=data/playtest/`` als Env-Var setzen
(typischerweise im Deploy-Script). Bleibt der Pfad ungesetzt, ist die
Funktion ein No-Op — Tests koennen die runden-completion-Pfade
durchspielen ohne lokal Files zu erzeugen, Production sammelt die
Daten ohne Code-Aenderung.

Schema (camelCase auf der Wire-Seite, snake_case in Python):
    {
        "timestamp": ISO-8601 UTC,
        "roomCode": str,
        "winner": "release_team" | "chaos_agents",
        "reason": str,
        "durationSeconds": float,
        "numPlayers": int,
        "meetingsCalled": int,
        "forceReboots": int,            # = takedowns
        "tasksByRole": {role_id: count},
        "sabotagesTriggeredTotal": int,
        "repairsCompleted": int,
        "coffeeEnergyAvgAtEnd": float,  # Durchschnitt ueber Lebende, oder 0
        "playersAliveAtEnd": int,
    }
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.game.game_room import GameRoom


_log = logging.getLogger("mcm.metrics")
_METRICS_DIR_ENV = "MCM_METRICS_DIR"


def _resolve_metrics_dir() -> Path | None:
    """Return the configured metrics directory, or None when unset."""
    raw = os.environ.get(_METRICS_DIR_ENV)
    if not raw or not raw.strip():
        return None
    return Path(raw)


def round_metrics_payload(room: GameRoom) -> dict:
    """Build the JSON payload for a finished room. Pure — no side effects.
    Public so tests can assert on the shape without writing to disk."""
    duration = max(0.0, _round_duration(room))
    tasks_by_role: dict[str, int] = {}
    for pid, count in room.completed_tasks_by_player.items():
        player = room.players.get(pid)
        role = player.role if player else "unknown"
        tasks_by_role[role or "unknown"] = tasks_by_role.get(role or "unknown", 0) + int(count)
    sabotages_total = int(sum(room.triggered_sabotages_by_player.values()))
    repairs_completed = int(
        sum(1 for sab in room.sabotages.values() if sab.cooldown_remaining == 0 and not sab.active)
    )
    alive = [p for p in room.players.values() if p.is_alive]
    coffee_avg = round(sum(p.coffee_energy for p in alive) / len(alive), 2) if alive else 0.0
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "roomCode": room.code,
        "winner": room.winner or "",
        "reason": room.win_reason or "",
        "durationSeconds": round(duration, 2),
        "numPlayers": len(room.players),
        "meetingsCalled": int(_meetings_called(room)),
        "forceReboots": int(_force_reboots(room)),
        "tasksByRole": tasks_by_role,
        "sabotagesTriggeredTotal": sabotages_total,
        "repairsCompleted": repairs_completed,
        "coffeeEnergyAvgAtEnd": coffee_avg,
        "playersAliveAtEnd": len(alive),
    }


def export_round(room: GameRoom, metrics_dir: Path | None = None) -> Path | None:
    """Append a JSON line for ``room`` to today's JSONL file. Returns the
    file path when a write happened, or None if metrics are disabled.
    Idempotent guard: writes once per finished round, marked via
    ``room._metrics_exported``."""
    if getattr(room, "_metrics_exported", False):
        return None
    target_dir = metrics_dir if metrics_dir is not None else _resolve_metrics_dir()
    if target_dir is None:
        # don't retry on subsequent ticks; flag is set ad-hoc via setattr
        # so mypy doesn't need GameRoom to declare the attribute.
        room._metrics_exported = True  # type: ignore[attr-defined]
        return None
    payload = round_metrics_payload(room)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.now(UTC).strftime("%Y-%m-%d") + ".jsonl"
    target_file = target_dir / filename
    line = json.dumps(payload, ensure_ascii=False)
    try:
        with target_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        _log.exception("Failed to append metrics line to %s", target_file)
        return None
    room._metrics_exported = True  # type: ignore[attr-defined]
    return target_file


# --- helpers ---------------------------------------------------------------


def _round_duration(room: GameRoom) -> float:
    """ROUND_SECONDS minus what's left when the round ends. Defensive against
    ``remaining_seconds`` already being clamped to 0 on time-out."""
    from app.game.game_room import ROUND_SECONDS

    return max(0.0, ROUND_SECONDS - float(room.remaining_seconds))


def _meetings_called(room: GameRoom) -> int:
    """Count meetings via the ``players_with_meeting_left`` flag: every
    player started with True; whoever's now False used theirs. Body-reports
    + Scrum-Master-standups don't consume the quota, but they're still
    metric-relevant — we leave that detail to room-level event counters in
    a future slice. For now this is the simplest source of truth."""
    return sum(1 for v in room.players_with_meeting_left.values() if v is False)


def _force_reboots(room: GameRoom) -> int:
    """A force-reboot leaves a body behind PLUS the chaos cooldown ticked.
    Count chaos agents whose takedown cooldown was set this round at any
    point — but the room only stores the *current* cooldown, not the
    history. Approximate: dead release-team players is a tight upper bound
    (every chaos take-down kills one release player)."""
    return sum(1 for p in room.players.values() if p.team == "release_team" and not p.is_alive)
