"""Tier 3.5 — Mini-Game „Logs analysieren".

Mechanik (Multi-Select-by-Criterion): Acht Log-Zeilen in zufaelliger
Reihenfolge mit gemischtem Severity-Level (drei `error`, zwei `warn`, drei
`info`). Spieler markiert die `error`-Zeilen. Klick auf `warn` oder `info`
ist Soft-Reset (alle Markierungen weg). Mini-Game ist complete sobald alle
drei `error`-Zeilen markiert sind.
"""

import random

from app.game.minigames.base import MiniGamePlugin, MiniGamePluginError

NUM_LINES = 8
NUM_ERRORS = 3
NUM_WARNS = 2
NUM_INFOS = NUM_LINES - NUM_ERRORS - NUM_WARNS

_ERROR_TEMPLATES: list[str] = [
    "ConnectionError: timeout connecting to db.cluster.internal",
    "FATAL: panic in worker pool: nil pointer dereference",
    "OutOfMemory: heap exhausted at GC root, evicting cache",
    "AuthenticationFailed: invalid signature for token tk_4781",
    "DiskFull: cannot write to /var/log/app.log",
    "PaymentDeclined: gateway returned 502 for txn_a8f2c1",
    "DeploymentFailed: rollback triggered for build #4823",
    "DataLoss: replication lag exceeded threshold by 12 minutes",
]

_WARN_TEMPLATES: list[str] = [
    "Slow query: SELECT * FROM events took 2.4s (limit 1.5s)",
    "Deprecated API call from client v1.7 — switch to v2",
    "Retry attempt 3/5 for upstream service billing-svc",
    "Disk usage at 85% on /var (alert above 90%)",
    "TLS certificate for *.internal renews in 14 days",
    "Cache miss rate 18% over last hour (target: <10%)",
]

_INFO_TEMPLATES: list[str] = [
    "User u_481 signed in via SSO (provider: okta)",
    "Cron 'rollup_daily' completed in 12.3s",
    "Cache warmed: 4823 entries loaded from snapshot",
    "Health check passed: 200 OK in 24ms",
    "Worker pool started with 8 processes (pid 1247-1254)",
    "Feature flag 'new_dashboard' enabled for cohort B",
    "Backup snapshot s_4982 archived to cold storage",
]


class LogFilter(MiniGamePlugin):
    id = "log_filter"
    title = "Logs analysieren"

    def init_state(self, seed: int) -> dict:
        rng = random.Random(seed)
        errors = rng.sample(_ERROR_TEMPLATES, NUM_ERRORS)
        warns = rng.sample(_WARN_TEMPLATES, NUM_WARNS)
        infos = rng.sample(_INFO_TEMPLATES, NUM_INFOS)
        lines: list[tuple[str, str]] = (
            [("error", m) for m in errors]
            + [("warn", m) for m in warns]
            + [("info", m) for m in infos]
        )
        rng.shuffle(lines)
        return {
            "lines": [
                {"id": f"l{i}", "level": level, "message": message, "marked": False}
                for i, (level, message) in enumerate(lines)
            ],
            "marked_errors": 0,
        }

    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        if action != "click":
            raise MiniGamePluginError(code="UNKNOWN_ACTION", message=f"Unknown action {action!r}.")
        if not isinstance(params, dict):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Params must be an object.")
        line_id = params.get("lineId")
        if not isinstance(line_id, str):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Missing lineId.")
        line = next((line_ for line_ in state["lines"] if line_["id"] == line_id), None)
        if line is None:
            raise MiniGamePluginError(code="UNKNOWN_LINE", message=f"Unknown line_id {line_id!r}.")
        if line["marked"]:
            return state  # idempotent
        if line["level"] == "error":
            line["marked"] = True
            state["marked_errors"] += 1
        else:
            # Soft reset: drop every mark.
            for line_ in state["lines"]:
                line_["marked"] = False
            state["marked_errors"] = 0
        return state

    def is_complete(self, state: dict) -> bool:
        return state["marked_errors"] >= NUM_ERRORS

    def public_view(self, state: dict) -> dict:
        return {
            "lines": [
                {
                    "id": line_["id"],
                    "level": line_["level"],
                    "message": line_["message"],
                    "marked": line_["marked"],
                }
                for line_ in state["lines"]
            ],
            "totalErrors": NUM_ERRORS,
            "markedErrors": state["marked_errors"],
        }
