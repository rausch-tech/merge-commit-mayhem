"""Tier 3.2 — Beispiel-Mini-Game „Test-Suite reparieren".

Mechanik: 5 fehlerhafte Tests, gemischte Reihenfolge. Spieler muss in
numerischer Reihenfolge (1 → 5) klicken. Falscher Klick = Soft-Reset (alle
wieder rot, next_order zurück auf 1). Bei 5/5 ist der Mini-Game complete.

Die Test-Templates sind absichtlich Pseudo-Tests — bei einer späteren
LLM-Erweiterung wird ``init_state`` echte Stack-Traces erzeugen, und der
Spieler muss aus dem Stack-Trace die Reihenfolge ableiten statt sie an einer
sichtbaren Nummer abzulesen.
"""

import random

from app.game.minigames.base import MiniGamePlugin, MiniGamePluginError

NUM_TESTS = 5

_TEMPLATES = [
    "test_user_can_login",
    "test_password_is_hashed",
    "test_session_expires_after_logout",
    "test_login_locks_after_5_attempts",
    "test_password_reset_email_sent",
    "test_csrf_token_validated",
    "test_admin_can_impersonate",
    "test_audit_log_records_login",
]


class TestSuiteRepair(MiniGamePlugin):
    id = "test_suite_repair"
    title = "Test-Suite reparieren"

    def init_state(self, seed: int) -> dict:
        rng = random.Random(seed)
        chosen = rng.sample(_TEMPLATES, NUM_TESTS)
        # Assign orders 1..NUM_TESTS, then shuffle the visible row order so
        # the player has to scan to find each next number.
        rows = [
            {"id": f"t{i}", "label": label, "order": i + 1, "status": "broken"}
            for i, label in enumerate(chosen)
        ]
        rng.shuffle(rows)
        return {"tests": rows, "next_order": 1}

    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        if action != "click":
            raise MiniGamePluginError(code="UNKNOWN_ACTION", message=f"Unknown action {action!r}.")
        test_id = params.get("testId") if isinstance(params, dict) else None
        if not isinstance(test_id, str):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Missing testId.")
        target = next((t for t in state["tests"] if t["id"] == test_id), None)
        if target is None:
            raise MiniGamePluginError(code="UNKNOWN_TEST", message=f"Unknown test_id {test_id!r}.")
        if target["status"] == "fixed":
            # Already fixed — silently ignore; not a cheat, the client may
            # double-click before the state echo arrives.
            return state
        if target["order"] == state["next_order"]:
            target["status"] = "fixed"
            state["next_order"] += 1
        else:
            # Soft reset.
            for t in state["tests"]:
                t["status"] = "broken"
            state["next_order"] = 1
        return state

    def is_complete(self, state: dict) -> bool:
        return state["next_order"] > NUM_TESTS

    def public_view(self, state: dict) -> dict:
        return {
            "tests": [
                {"id": t["id"], "label": t["label"], "order": t["order"], "status": t["status"]}
                for t in state["tests"]
            ],
            "nextOrder": state["next_order"],
            "totalTests": NUM_TESTS,
        }
