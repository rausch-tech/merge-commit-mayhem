"""Tier 0.x — Performance baseline (synthetic 12-player load).

Measures the in-memory cost of the server's hot path before we port to a
second client (Godot, Tier 4). Skips the WebSocket layer entirely; the
relevant bottleneck is tick computation + per-viewer payload assembly,
which is independent of socket I/O.

Usage:
    uv run python scripts/perf_baseline.py [--players N] [--seconds S]

Defaults: 12 players, 20 seconds (= 400 ticks at 20 Hz).
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

# Allow running directly without PYTHONPATH=. — script lives under scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.game.game_room import GameRoom  # noqa: E402

TICK_DT = 1.0 / 20  # mirrors app.main.TICK_DT


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = int(round((len(s) - 1) * pct / 100))
    return s[k]


def _payload_bytes(state: dict) -> int:
    return len(json.dumps(state, separators=(",", ":")).encode("utf-8"))


def run_baseline(num_players: int, seconds: float) -> dict:
    rng = random.Random(20260426)
    room = GameRoom(code="PERF")
    for i in range(num_players):
        room.add_player(f"p{i:02d}")
    host = next(iter(room.players))
    room.start(requesting_player_id=host, rng=rng)
    player_ids = list(room.players.keys())

    chaos_ids = [pid for pid, p in room.players.items() if p.team == "chaos_agents"]
    if not chaos_ids:
        raise RuntimeError("No chaos agent assigned — cannot exercise sabotage path.")

    # Random walk inputs so movement code does real work each tick.
    from app.game.models import InputState  # noqa: PLC0415

    def _random_axis() -> InputState:
        return InputState(
            up=rng.random() < 0.4,
            down=rng.random() < 0.4,
            left=rng.random() < 0.4,
            right=rng.random() < 0.4,
        )

    for pid in player_ids:
        room.apply_input(pid, _random_axis())

    tick_durations: list[float] = []
    payload_sizes: list[int] = []
    bytes_per_tick: list[int] = []
    total_ticks = int(seconds / TICK_DT)
    sabotage_at_tick = total_ticks // 4
    sabotage_repaired_at_tick = total_ticks // 2

    sabotage_id = None
    sabotage_options = room.sabotages.keys()
    if sabotage_options:
        sabotage_id = next(iter(sabotage_options))

    for t in range(total_ticks):
        # Refresh random inputs every ~1 s so movement keeps changing.
        if t % 20 == 0:
            for pid in player_ids:
                room.apply_input(pid, _random_axis())
        # Stage one sabotage to measure payload with active state.
        if sabotage_id and t == sabotage_at_tick:
            try:
                room.trigger_sabotage(chaos_ids[0], sabotage_id)
            except Exception:  # noqa: BLE001
                pass
        # And repair it (if a panel exists) to flex the lights/comms branches.
        if sabotage_id and t == sabotage_repaired_at_tick:
            try:
                room.repair_sabotage(player_ids[1], sabotage_id)
            except Exception:  # noqa: BLE001
                pass

        t0 = time.perf_counter()
        room.tick(TICK_DT)
        base = room._public_state_base()
        tick_total_bytes = 0
        for viewer_id in player_ids:
            personalized = room.public_state_for(viewer_id, base=base)
            size = _payload_bytes(personalized)
            payload_sizes.append(size)
            tick_total_bytes += size
        bytes_per_tick.append(tick_total_bytes)
        tick_durations.append((time.perf_counter() - t0) * 1000.0)  # ms

    return {
        "players": num_players,
        "ticks": total_ticks,
        "tick_ms_mean": statistics.mean(tick_durations),
        "tick_ms_p50": _percentile(tick_durations, 50),
        "tick_ms_p95": _percentile(tick_durations, 95),
        "tick_ms_p99": _percentile(tick_durations, 99),
        "tick_ms_max": max(tick_durations),
        "payload_bytes_mean": statistics.mean(payload_sizes),
        "payload_bytes_p95": _percentile(payload_sizes, 95),
        "payload_bytes_p99": _percentile(payload_sizes, 99),
        "tick_total_bytes_mean": statistics.mean(bytes_per_tick),
        "tick_total_bytes_p95": _percentile(bytes_per_tick, 95),
        "throughput_KB_per_s": (statistics.mean(bytes_per_tick) / 1024) / TICK_DT,
        "headroom_factor": TICK_DT * 1000 / max(_percentile(tick_durations, 99), 0.001),
    }


def _print_report(r: dict) -> None:
    print("\n--- MCM Performance Baseline ---")
    print(f"Players:                  {r['players']}")
    print(f"Ticks measured:           {r['ticks']} (~{r['ticks'] / 20:.0f} s wall)")
    print()
    print("Tick duration (ms):")
    print(
        f"  mean / p50 / p95 / p99 / max: "
        f"{r['tick_ms_mean']:.2f} / {r['tick_ms_p50']:.2f} / "
        f"{r['tick_ms_p95']:.2f} / {r['tick_ms_p99']:.2f} / {r['tick_ms_max']:.2f}"
    )
    print(f"  Tick budget (50 ms @ 20 Hz)   headroom factor at p99: {r['headroom_factor']:.1f}x")
    print()
    print("Per-viewer payload bytes (single game_state JSON):")
    print(
        f"  mean / p95 / p99: "
        f"{r['payload_bytes_mean']:.0f} / "
        f"{r['payload_bytes_p95']:.0f} / {r['payload_bytes_p99']:.0f}"
    )
    print()
    print("Total bytes broadcast per tick (sum over all viewers):")
    print(f"  mean / p95: {r['tick_total_bytes_mean']:.0f} / {r['tick_total_bytes_p95']:.0f}")
    print(f"  -> {r['throughput_KB_per_s']:.1f} KB/s aggregate at 20 Hz")
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--players", type=int, default=12)
    parser.add_argument("--seconds", type=float, default=20.0)
    args = parser.parse_args()
    report = run_baseline(args.players, args.seconds)
    _print_report(report)


if __name__ == "__main__":
    main()
