"""Tier 3.4 — Mini-Game „Kaffee einschenken".

Mechanik (Skill-Stop / Timing): die Tasse fuellt sich linear in einem Zyklus
von ``CYCLE_SECONDS`` Sekunden von 0% auf 100% und beginnt dann von vorne.
Der Spieler tippt einmal auf STOP. Liegt die Fuellung im Sweet-Spot
(``SWEET_MIN`` .. ``SWEET_MAX``), ist das Mini-Game gewonnen. Sonst wird der
Zyklus zurueckgesetzt und der Spieler kann erneut versuchen.

Server haelt die Wahrheit: ``cycle_started_at`` als monotonic-Zeitstempel,
``handle_input("stop")`` rechnet selbst die Fuellung und entscheidet. Der
Client extrapoliert zwischen ``mini_game_state``-Frames lokal — das ist nur
fuer die Animation, die Validierung passiert immer serverseitig.
"""

import time

from app.game.minigames.base import MiniGamePlugin, MiniGamePluginError

CYCLE_SECONDS = 3.0
SWEET_MIN = 0.70  # 70%
SWEET_MAX = 1.00  # 100%


def _now() -> float:
    """Indirection so tests can monkeypatch the clock without faking time."""
    return time.monotonic()


class CoffeePour(MiniGamePlugin):
    id = "coffee_pour"
    title = "Kaffee einschenken"

    def init_state(self, seed: int) -> dict:
        # seed is ignored — the cup-fill mini-game has no per-session
        # randomization. The signature stays consistent with the base class.
        del seed
        return {
            "cycle_started_at": _now(),
            "complete": False,
            "attempts": 0,
            "last_attempt_fill": None,
        }

    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        del params  # stop carries no payload
        if action != "stop":
            raise MiniGamePluginError(code="UNKNOWN_ACTION", message=f"Unknown action {action!r}.")
        if state["complete"]:
            return state
        elapsed = _now() - state["cycle_started_at"]
        # Repeated cycles wrap modulo cycle_seconds — players who wait through
        # one full overflow get another shot without spamming stop.
        fill = (elapsed / CYCLE_SECONDS) % 1.0
        state["attempts"] += 1
        state["last_attempt_fill"] = round(fill, 3)
        if SWEET_MIN <= fill <= SWEET_MAX:
            state["complete"] = True
        else:
            state["cycle_started_at"] = _now()
        return state

    def is_complete(self, state: dict) -> bool:
        return bool(state["complete"])

    def public_view(self, state: dict) -> dict:
        elapsed = _now() - state["cycle_started_at"]
        return {
            "elapsed": elapsed,
            "cycleSeconds": CYCLE_SECONDS,
            "sweetMin": SWEET_MIN,
            "sweetMax": SWEET_MAX,
            "attempts": state["attempts"],
            "lastAttemptFill": state["last_attempt_fill"],
            "complete": state["complete"],
        }
