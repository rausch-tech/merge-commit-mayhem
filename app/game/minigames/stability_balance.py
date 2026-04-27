"""Tier 3.7 — Mini-Game „Legacy-Service beruhigen" (calm_legacy_service task).

Mechanik (Closed-loop Balancing): Drei Metriken — CPU, Memory, Queue —
beginnen alle ausserhalb der grünen Zone. Spieler hat sechs Buttons
(+/- pro Metrik). Jede Aktion bewegt die Ziel-Metrik um ±10, drückt
aber die *naechste* Metrik um ∓5 in die Gegenrichtung (Rotation:
cpu→mem, mem→queue, queue→cpu). Mini-Game complete, sobald alle drei
Metriken gleichzeitig im Range [40, 60] liegen.

Initial-Werte sind absichtlich asymmetrisch (CPU hoch, Memory tief,
Queue hoch), damit der Spieler ueberlegen muss in welcher Reihenfolge
er korrigiert. Der Soft-Failure-Modus ist „weiter klicken bis alles
green" — kein Hard-Reset, keine Sackgassen, da alle Werte in [0, 100]
clamping. Sven's playtest soll zeigen ob der Schwierigkeitsgrad passt.
"""

import random

from app.game.minigames.base import MiniGamePlugin, MiniGamePluginError

GREEN_LOW = 40
GREEN_HIGH = 60
SCALE_MIN = 0
SCALE_MAX = 100
PRIMARY_DELTA = 10
CROSS_DELTA = 5

# Rotation: adjusting metric N moves N+1 in the opposite direction.
# This makes the system tightly coupled but always solvable.
_NEXT_METRIC = {"cpu": "mem", "mem": "queue", "queue": "cpu"}

# Initial-Werte fuer drei Schwierigkeits-Buckets (vom seed gewaehlt).
_INITIAL_PRESETS: list[tuple[int, int, int]] = [
    (85, 20, 70),  # CPU melt, memory free, queue clogged
    (30, 80, 25),  # CPU idle, memory full, queue empty
    (75, 75, 30),  # both compute hot, queue empty
]


def _clamp(value: int) -> int:
    if value < SCALE_MIN:
        return SCALE_MIN
    if value > SCALE_MAX:
        return SCALE_MAX
    return value


class StabilityBalance(MiniGamePlugin):
    id = "stability_balance"
    title = "Legacy-Service beruhigen"

    def init_state(self, seed: int) -> dict:
        rng = random.Random(seed)
        cpu, mem, queue = rng.choice(_INITIAL_PRESETS)
        return {"cpu": cpu, "mem": mem, "queue": queue}

    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        if action != "adjust":
            raise MiniGamePluginError(code="UNKNOWN_ACTION", message=f"Unknown action {action!r}.")
        if not isinstance(params, dict):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Params must be an object.")
        metric = params.get("metric")
        if metric not in ("cpu", "mem", "queue"):
            raise MiniGamePluginError(
                code="INVALID_PARAMS", message="metric must be cpu/mem/queue."
            )
        direction = params.get("direction")
        if direction not in ("up", "down"):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="direction must be up/down.")
        sign = 1 if direction == "up" else -1
        # Primary delta on the target metric.
        state[metric] = _clamp(state[metric] + sign * PRIMARY_DELTA)
        # Cross-effect on the next metric (opposite direction).
        cross = _NEXT_METRIC[metric]
        state[cross] = _clamp(state[cross] - sign * CROSS_DELTA)
        return state

    def is_complete(self, state: dict) -> bool:
        return all(GREEN_LOW <= state[m] <= GREEN_HIGH for m in ("cpu", "mem", "queue"))

    def public_view(self, state: dict) -> dict:
        return {
            "cpu": state["cpu"],
            "mem": state["mem"],
            "queue": state["queue"],
            "greenLow": GREEN_LOW,
            "greenHigh": GREEN_HIGH,
        }
