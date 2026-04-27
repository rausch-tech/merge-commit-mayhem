"""Tier 3.7 — Mini-Game „PR reviewen" (review_pr task).

Mechanik (Multi-Select-by-Criterion, mirror of log_filter): Sechs
Code-Zeilen aus einem fiktiven Pull-Request. Genau zwei davon sind
Bugs (hardcoded API key, leerer ``catch``-Block, Debug-Statement, …),
vier sind harmloser Code. Spieler markiert die zwei Bugs.

Klick auf eine Bug-Zeile  → Mark bleibt.
Klick auf eine Non-Bug    → Soft-Reset (alle Marks weg).
Mini-Game complete         → genau zwei Bugs sind markiert.

Templates sind absichtlich kurz und plakativ; bei einer spaeteren
LLM-Erweiterung produziert ``init_state`` realistischere Diff-Hunks.
"""

import random

from app.game.minigames.base import MiniGamePlugin, MiniGamePluginError

NUM_LINES = 6
NUM_BUGS = 2
NUM_BENIGN = NUM_LINES - NUM_BUGS

_BUG_TEMPLATES: list[str] = [
    "API_KEY = 'sk-prod-1234abcd'  # TODO move to env",
    "except Exception: pass  # swallow + move on",
    "console.log('user', userId, 'token', sessionToken);",
    "query = 'SELECT * FROM users WHERE name=' + name + ';'",
    "if user.role == 'admin' or DEBUG: bypass_auth(user)",
    "subprocess.run(cmd, shell=True)  # cmd built from request body",
    "Math.random() < 0.0001 // good enough for crypto",
    "// FIXME: payment goes through even on declined card",
]

_BENIGN_TEMPLATES: list[str] = [
    "logger.info(f'user {user.id} signed in via {provider}')",
    "return jsonify({'ok': True, 'count': len(items)})",
    "with open(path, 'r', encoding='utf-8') as f: data = json.load(f)",
    "results = sorted(rows, key=lambda r: r.created_at, reverse=True)",
    "if cache.get(key) is not None: return cache.get(key)",
    "for item in batch: queue.put(item)  # backpressure handled by put()",
    "assert response.status_code == 200, response.text",
    "settings = SettingsModel.model_validate(raw)",
    "session.commit()",
    "return user.role in {'admin', 'maintainer'}",
]


class DiffReview(MiniGamePlugin):
    id = "diff_review"
    title = "PR reviewen"

    def init_state(self, seed: int) -> dict:
        rng = random.Random(seed)
        bugs = rng.sample(_BUG_TEMPLATES, NUM_BUGS)
        benign = rng.sample(_BENIGN_TEMPLATES, NUM_BENIGN)
        lines: list[tuple[str, str]] = [("bug", text) for text in bugs] + [
            ("benign", text) for text in benign
        ]
        rng.shuffle(lines)
        return {
            "lines": [
                {"id": f"l{i}", "kind": kind, "text": text, "marked": False}
                for i, (kind, text) in enumerate(lines)
            ],
            "marked_bugs": 0,
        }

    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        if action != "click":
            raise MiniGamePluginError(code="UNKNOWN_ACTION", message=f"Unknown action {action!r}.")
        if not isinstance(params, dict):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Params must be an object.")
        line_id = params.get("lineId")
        if not isinstance(line_id, str):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Missing lineId.")
        line = next((row for row in state["lines"] if row["id"] == line_id), None)
        if line is None:
            raise MiniGamePluginError(code="UNKNOWN_LINE", message=f"Unknown line_id {line_id!r}.")
        if line["marked"]:
            return state  # idempotent
        if line["kind"] == "bug":
            line["marked"] = True
            state["marked_bugs"] += 1
        else:
            # Soft reset: drop every mark.
            for other in state["lines"]:
                other["marked"] = False
            state["marked_bugs"] = 0
        return state

    def is_complete(self, state: dict) -> bool:
        return state["marked_bugs"] >= NUM_BUGS

    def public_view(self, state: dict) -> dict:
        # Note: ``kind`` is intentionally NOT leaked — the client only sees
        # the ``text`` and the ``marked`` flag. Knowing which line is the
        # bug ahead of time would defeat the puzzle.
        return {
            "lines": [
                {"id": row["id"], "text": row["text"], "marked": row["marked"]}
                for row in state["lines"]
            ],
            "totalBugs": NUM_BUGS,
            "markedBugs": state["marked_bugs"],
        }
