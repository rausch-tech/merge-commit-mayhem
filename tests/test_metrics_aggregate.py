"""Tests for the /api/metrics aggregator (Tier 3.7.6 → /api/metrics).

Reads JSONL files written by metrics_export.py and rolls them into win-
rates / averages / totals. Tests cover the empty/no-config paths, a
mixed-rounds happy path, the ``since`` filter, and resilience against
malformed lines + non-ISO filenames.
"""

import json
from datetime import date, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.game.metrics_aggregate import aggregate_metrics
from app.main import app


@pytest.fixture
def tmp_metrics(tmp_path: Path) -> Path:
    target = tmp_path / "playtest"
    target.mkdir()
    return target


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _line(**overrides) -> str:
    """Write one round-payload line in the metrics_export schema."""
    base = {
        "timestamp": "2026-04-27T15:00:00+00:00",
        "roomCode": "TEST",
        "winner": "release_team",
        "reason": "release_complete",
        "durationSeconds": 600.0,
        "numPlayers": 7,
        "meetingsCalled": 2,
        "forceReboots": 1,
        "tasksByRole": {"developer": 4, "qa_lead": 2},
        "sabotagesTriggeredTotal": 3,
        "repairsCompleted": 2,
        "coffeeEnergyAvgAtEnd": 60.0,
        "playersAliveAtEnd": 6,
    }
    base.update(overrides)
    return json.dumps(base) + "\n"


def _write(target: Path, name: str, lines: list[str]) -> None:
    (target / name).write_text("".join(lines), encoding="utf-8")


# --- aggregator pure logic --------------------------------------------------


def test_no_metrics_dir_configured_is_loud_but_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCM_METRICS_DIR", raising=False)
    out = aggregate_metrics()
    assert out["metricsAvailable"] is False


def test_empty_dir_returns_zero_rounds(tmp_metrics: Path) -> None:
    out = aggregate_metrics(metrics_dir=tmp_metrics)
    assert out == {
        "metricsAvailable": True,
        "totalRounds": 0,
        "since": None,
        "message": "No rounds in the requested window.",
    }


def test_aggregates_winners_durations_and_per_role(tmp_metrics: Path) -> None:
    _write(
        tmp_metrics,
        "2026-04-27.jsonl",
        [
            _line(winner="release_team", durationSeconds=600.0, numPlayers=7),
            _line(winner="chaos_agents", durationSeconds=400.0, numPlayers=8),
            _line(winner="release_team", durationSeconds=500.0, numPlayers=6),
        ],
    )
    out = aggregate_metrics(metrics_dir=tmp_metrics)
    assert out["totalRounds"] == 3
    assert out["winners"] == {"release_team": 2, "chaos_agents": 1}
    assert out["winRateRelease"] == 0.667
    assert out["winRateChaos"] == 0.333
    assert out["avgDurationSeconds"] == 500.0
    assert out["avgNumPlayers"] == 7.0
    # Each round's tasks summed across roles
    assert out["tasksByRoleTotal"] == {"developer": 12, "qa_lead": 6}
    assert out["sabotagesTriggeredTotal"] == 9
    assert out["repairsCompletedTotal"] == 6


def test_since_filter_skips_older_files(tmp_metrics: Path) -> None:
    _write(tmp_metrics, "2026-04-25.jsonl", [_line(winner="release_team")])
    _write(tmp_metrics, "2026-04-27.jsonl", [_line(winner="chaos_agents")])
    out = aggregate_metrics(since=date(2026, 4, 26), metrics_dir=tmp_metrics)
    assert out["totalRounds"] == 1
    assert out["winners"] == {"chaos_agents": 1}
    assert out["since"] == "2026-04-26"


def test_malformed_lines_are_skipped(tmp_metrics: Path) -> None:
    _write(
        tmp_metrics,
        "2026-04-27.jsonl",
        [
            _line(winner="release_team"),
            "{ this is not json\n",
            "\n",
            _line(winner="chaos_agents"),
        ],
    )
    out = aggregate_metrics(metrics_dir=tmp_metrics)
    assert out["totalRounds"] == 2


def test_non_iso_filenames_are_skipped(tmp_metrics: Path) -> None:
    """A backup or rotated file with a non-ISO name shouldn't kill the run."""
    _write(tmp_metrics, "2026-04-27.jsonl", [_line(winner="release_team")])
    _write(tmp_metrics, "rotated.jsonl", [_line(winner="chaos_agents")])
    out = aggregate_metrics(metrics_dir=tmp_metrics)
    assert out["totalRounds"] == 1


def test_win_reasons_are_counted(tmp_metrics: Path) -> None:
    _write(
        tmp_metrics,
        "2026-04-27.jsonl",
        [
            _line(reason="release_complete"),
            _line(reason="all_chaos_voted_out"),
            _line(reason="release_complete"),
            _line(reason="pipeline_zero"),
        ],
    )
    out = aggregate_metrics(metrics_dir=tmp_metrics)
    assert out["winReasons"] == {
        "release_complete": 2,
        "all_chaos_voted_out": 1,
        "pipeline_zero": 1,
    }


# --- /api/metrics endpoint --------------------------------------------------


def test_endpoint_metrics_unconfigured_returns_available_false(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.delenv("MCM_METRICS_DIR", raising=False)
    r = client.get("/api/metrics")
    assert r.status_code == 200
    assert r.json()["metricsAvailable"] is False


def test_endpoint_metrics_invalid_since_returns_400(client: TestClient) -> None:
    r = client.get("/api/metrics", params={"since": "yesterday"})
    assert r.status_code == 400
    assert "YYYY-MM-DD" in r.json()["detail"]


def test_endpoint_metrics_with_data(
    tmp_metrics: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setenv("MCM_METRICS_DIR", str(tmp_metrics))
    _write(
        tmp_metrics,
        "2026-04-27.jsonl",
        [_line(winner="release_team"), _line(winner="chaos_agents")],
    )
    r = client.get("/api/metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["metricsAvailable"] is True
    assert body["totalRounds"] == 2
    assert body["winners"] == {"release_team": 1, "chaos_agents": 1}
    # silence: keep the timezone import referenced (linters notice it
    # otherwise once metrics_export grows real-time semantics).
    _ = timezone
