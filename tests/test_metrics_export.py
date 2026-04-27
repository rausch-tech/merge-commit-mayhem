"""Tier 3.7.6 — JSONL metrics export per finished round."""

from __future__ import annotations

import json
import random
from pathlib import Path

from app.game.game_room import GameRoom
from app.game.metrics_export import (
    export_round,
    round_metrics_payload,
)


def _started_room(player_count: int = 4) -> GameRoom:
    if player_count < 4:
        player_count = 4
    room = GameRoom(code="MTRC")
    for i in range(player_count):
        room.add_player(f"p{i}")
    host = next(iter(room.players))
    room.start(requesting_player_id=host, rng=random.Random(0))
    return room


def _force_finish_without_export(room: GameRoom, winner: str, reason: str) -> None:
    """Set the post-finish room fields directly so export_round() has the
    right state to read, but don't go through _finish_round() (which would
    itself call export_round and flip the idempotency flag)."""
    from app.game.models import Phase

    room.winner = winner
    room.win_reason = reason
    room.phase = Phase.ENDED


# --- payload shape ---------------------------------------------------------


def test_round_metrics_payload_has_required_camel_case_fields():
    """The JSONL schema lives on the Wire-side as camelCase. Pin the
    minimum field set so future analysis scripts have a stable contract."""
    room = _started_room()
    room._finish_round("release_team", "Release deployed.")
    payload = round_metrics_payload(room)
    expected = {
        "timestamp",
        "roomCode",
        "winner",
        "reason",
        "durationSeconds",
        "numPlayers",
        "meetingsCalled",
        "forceReboots",
        "tasksByRole",
        "sabotagesTriggeredTotal",
        "repairsCompleted",
        "coffeeEnergyAvgAtEnd",
        "playersAliveAtEnd",
    }
    assert expected.issubset(payload.keys())


def test_round_metrics_payload_winner_and_reason():
    room = _started_room()
    room._finish_round("chaos_agents", "Pipeline tot.")
    payload = round_metrics_payload(room)
    assert payload["winner"] == "chaos_agents"
    assert payload["reason"] == "Pipeline tot."
    assert payload["roomCode"] == "MTRC"


def test_round_metrics_payload_num_players_and_alive_at_end():
    room = _started_room(player_count=4)
    # Eliminate one player.
    pid = next(iter(room.players))
    room.players[pid].is_alive = False
    payload = round_metrics_payload(room)
    assert payload["numPlayers"] == 4
    assert payload["playersAliveAtEnd"] == 3


def test_tasks_by_role_aggregates_per_role():
    room = _started_room()
    pid_a, pid_b = list(room.players.keys())[:2]
    room.players[pid_a].role = "developer"
    room.players[pid_b].role = "developer"
    room.completed_tasks_by_player[pid_a] = 3
    room.completed_tasks_by_player[pid_b] = 2
    payload = round_metrics_payload(room)
    assert payload["tasksByRole"]["developer"] == 5


def test_coffee_energy_avg_only_counts_alive_players():
    room = _started_room()
    pids = list(room.players.keys())
    for i, pid in enumerate(pids):
        room.players[pid].coffee_energy = 60.0 + i * 10
    # Eliminate the one with the highest energy so the avg drops.
    room.players[pids[-1]].is_alive = False
    payload = round_metrics_payload(room)
    alive_energies = [60.0 + i * 10 for i in range(len(pids) - 1)]
    expected_avg = round(sum(alive_energies) / len(alive_energies), 2)
    assert payload["coffeeEnergyAvgAtEnd"] == expected_avg


# --- file I/O --------------------------------------------------------------


def test_export_round_writes_one_jsonl_line(tmp_path: Path):
    """With ``metrics_dir`` configured, ``export_round`` appends exactly
    one JSON line to today's file."""
    room = _started_room()
    _force_finish_without_export(room, "release_team", "Test win")

    written = export_round(room, metrics_dir=tmp_path)
    assert written is not None
    assert written.parent == tmp_path
    assert written.suffix == ".jsonl"
    # File contains exactly one line, parseable as JSON.
    lines = written.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["winner"] == "release_team"


def test_export_round_appends_to_existing_file(tmp_path: Path):
    """Two rounds on the same day land as two lines in the same file."""
    room1 = _started_room()
    _force_finish_without_export(room1, "release_team", "Win 1")
    written1 = export_round(room1, metrics_dir=tmp_path)

    room2 = GameRoom(code="MTR2")
    for i in range(4):
        room2.add_player(f"q{i}")
    room2.start(
        requesting_player_id=next(iter(room2.players)),
        rng=random.Random(1),
    )
    _force_finish_without_export(room2, "chaos_agents", "Loss 1")
    written2 = export_round(room2, metrics_dir=tmp_path)

    assert written1 == written2  # same filename — same date
    lines = written1.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rooms = {json.loads(line)["roomCode"] for line in lines}
    assert rooms == {"MTRC", "MTR2"}


def test_export_round_is_idempotent_for_one_room(tmp_path: Path):
    """Defensive: a second ``export_round`` call on the same room
    instance does NOT add another line. Prevents double-logging if
    ``_finish_round`` is somehow re-invoked."""
    room = _started_room()
    _force_finish_without_export(room, "release_team", "Win")
    export_round(room, metrics_dir=tmp_path)
    export_round(room, metrics_dir=tmp_path)
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    assert len(files[0].read_text(encoding="utf-8").splitlines()) == 1


def test_export_round_no_op_when_no_dir_configured(monkeypatch):
    """Default behaviour: without MCM_METRICS_DIR, the export is silent."""
    monkeypatch.delenv("MCM_METRICS_DIR", raising=False)
    room = _started_room()
    _force_finish_without_export(room, "release_team", "Win")
    written = export_round(room)
    assert written is None


def test_export_round_uses_env_var_when_set(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MCM_METRICS_DIR", str(tmp_path))
    room = _started_room()
    _force_finish_without_export(room, "release_team", "Win")
    written = export_round(room)
    assert written is not None
    assert written.parent == tmp_path


# --- _finish_round integration --------------------------------------------


def test_finish_round_writes_when_env_var_set(tmp_path: Path, monkeypatch):
    """End-to-end: the ``_finish_round`` hook calls export_round and a
    JSONL line lands in the configured directory."""
    monkeypatch.setenv("MCM_METRICS_DIR", str(tmp_path))
    room = _started_room()
    room._finish_round("release_team", "End-to-end test")
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    parsed = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
    assert parsed["reason"] == "End-to-end test"


def test_finish_round_does_not_double_write_on_back_to_back_calls(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MCM_METRICS_DIR", str(tmp_path))
    room = _started_room()
    room._finish_round("release_team", "Win")
    room._finish_round("release_team", "Win again")  # defensive double-call
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    assert len(files[0].read_text(encoding="utf-8").splitlines()) == 1
