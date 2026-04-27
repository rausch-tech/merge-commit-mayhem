"""Tier 3.7 — Mini-Game „Release Notes schreiben" (write_release_notes task).

Mechanik (Click-to-Cycle Sort): Sechs Commit-Messages aus einem
fiktiven PR-Backlog. Jeder Commit gehoert in eine von vier Kategorien:
Feature / Bugfix / Breaking Change / Should-Not-Be-Mentioned-Publicly.

Klick auf einen Commit cycelt seine Kategorie:
    unassigned → feature → bugfix → breaking → noprod → unassigned → ...

Submit-Button ist erst aktiv wenn alle sechs Commits zugewiesen sind.
Submit prueft alle Zuweisungen:
    - Alle korrekt  → Mini-Game complete.
    - Mindestens eine falsch → Soft-Reset (alles back auf unassigned).

Drag-and-Drop wurde bewusst verworfen — Mobile-Tricky und auf
Touch-Screens fummelig. Click-to-Cycle funktioniert auf jedem Gerät.
"""

import random

from app.game.minigames.base import MiniGamePlugin, MiniGamePluginError

NUM_COMMITS = 6
CATEGORIES: tuple[str, ...] = ("feature", "bugfix", "breaking", "noprod")
_CYCLE: tuple[str | None, ...] = (None,) + CATEGORIES  # unassigned + 4 buckets

# Pool: jeder Eintrag (category, message). init_state pickt
# zwei aus jeder Kategorie sodass alle vier Buckets vertreten sind und
# der Spieler nicht durch Häufigkeit alleine die richtige Antwort
# raten kann.
_POOL: dict[str, list[str]] = {
    "feature": [
        "Add SAML SSO via Okta provider",
        "Implement /api/v3/users (paginated)",
        "Per-tenant rate limiting for write endpoints",
        "New retention-policy UI in admin console",
        "Server-side filters for the report builder",
    ],
    "bugfix": [
        "Fix off-by-one in pagination cursor",
        "Handle empty payload in /webhook receivers",
        "Resolve race in token-refresh middleware",
        "Repair flaky e2e for billing checkout flow",
        "Stop swallowing 502s in the upstream client",
    ],
    "breaking": [
        "Drop /api/v1 (returns 410 Gone)",
        "Rename `userId` -> `user_id` across all responses",
        "DB migration: NOT NULL constraint on users.email",
        "Remove deprecated `legacy_token` cookie",
        "Bump minimum supported browser to ES2022",
    ],
    "noprod": [
        "Hardcoded admin override removed (was THERE for 3 years)",
        "Telemetry now respects DNT - finally",
        "API key rotated after the leak in incident-4781",
        "Dropped Russian-timezone support due to compliance",
        "Reverted shipping a build with the staging DB url",
    ],
}


class ReleaseNotes(MiniGamePlugin):
    id = "release_notes"
    title = "Release Notes schreiben"

    def init_state(self, seed: int) -> dict:
        rng = random.Random(seed)
        commits: list[dict] = []
        # Pick: 2 features, 2 bugfixes, 1 breaking, 1 noprod — 6 total.
        # Distribution makes the four-bucket choice meaningful even with
        # only six commits.
        per_cat = {"feature": 2, "bugfix": 2, "breaking": 1, "noprod": 1}
        idx = 0
        for cat, count in per_cat.items():
            picks = rng.sample(_POOL[cat], count)
            for text in picks:
                commits.append(
                    {
                        "id": f"c{idx}",
                        "message": text,
                        "correct": cat,
                        "assigned": None,
                    }
                )
                idx += 1
        rng.shuffle(commits)
        return {"commits": commits}

    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        if action == "cycle":
            return self._cycle(state, params)
        if action == "submit":
            return self._submit(state)
        raise MiniGamePluginError(code="UNKNOWN_ACTION", message=f"Unknown action {action!r}.")

    def _cycle(self, state: dict, params: dict) -> dict:
        if not isinstance(params, dict):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Params must be an object.")
        commit_id = params.get("commitId")
        if not isinstance(commit_id, str):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Missing commitId.")
        commit = next((c for c in state["commits"] if c["id"] == commit_id), None)
        if commit is None:
            raise MiniGamePluginError(
                code="UNKNOWN_COMMIT", message=f"Unknown commit {commit_id!r}."
            )
        # Cycle: None → feature → bugfix → breaking → noprod → None.
        current = commit["assigned"]
        next_idx = (_CYCLE.index(current) + 1) % len(_CYCLE)
        commit["assigned"] = _CYCLE[next_idx]
        return state

    def _submit(self, state: dict) -> dict:
        if any(c["assigned"] is None for c in state["commits"]):
            raise MiniGamePluginError(
                code="NOT_READY", message="Bitte jeden Commit zuerst einsortieren."
            )
        all_correct = all(c["assigned"] == c["correct"] for c in state["commits"])
        if all_correct:
            state["solved"] = True
        else:
            # Soft reset — drop all assignments, player tries again.
            for c in state["commits"]:
                c["assigned"] = None
        return state

    def is_complete(self, state: dict) -> bool:
        return state.get("solved", False)

    def public_view(self, state: dict) -> dict:
        # ``correct`` is intentionally NOT leaked — the client never sees
        # the answer until they submit. Knowing the correct category up
        # front would defeat the puzzle.
        return {
            "commits": [
                {"id": c["id"], "message": c["message"], "assigned": c["assigned"]}
                for c in state["commits"]
            ],
            "categories": list(CATEGORIES),
            "totalCommits": NUM_COMMITS,
            "assignedCount": sum(1 for c in state["commits"] if c["assigned"] is not None),
        }
