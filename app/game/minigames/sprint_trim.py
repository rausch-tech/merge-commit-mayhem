"""Tier 3.6 — Mini-Game „Scope reduzieren / Sprint-Trim".

Mechanik (Subset-Selection unter Constraint): Sechs Tickets im Sprint, jedes
mit Story-Points; Gesamtsumme uebersteigt das Sprint-Budget. Spieler entfernt
Tickets, bis die Restsumme <= Budget ist. Manche Tickets sind Priority und
duerfen NICHT entfernt werden (klick auf Priority = Soft-Reset, alles wieder
in den Sprint). Done sobald `remaining_points <= budget` und kein Priority
entfernt wurde.
"""

import random

from app.game.minigames.base import MiniGamePlugin, MiniGamePluginError

NUM_TICKETS = 6
SPRINT_BUDGET = 18

_TICKET_TEMPLATES: list[str] = [
    "Refactor billing service",
    "Migrate auth to OIDC",
    "Add dark mode",
    "Fix flaky test_login_locks",
    "Implement audit log export",
    "Upgrade Postgres 14 -> 16",
    "Cache analytics dashboard",
    "Replace cron with scheduler",
    "Add 2FA recovery flow",
    "Document deployment runbook",
    "Reduce Docker image size",
    "Investigate memory leak in worker",
]

# Story-point distribution: chosen so subsets of size >=2 can hit <= budget
# while priority-only subsets cannot. Total of 30 with mix of small/large.
_POINT_POOL: list[int] = [3, 5, 8, 2, 8, 13, 5, 3, 8, 2, 5, 13]


class SprintTrim(MiniGamePlugin):
    id = "sprint_trim"
    title = "Scope reduzieren"

    def init_state(self, seed: int) -> dict:
        rng = random.Random(seed)
        # Pick six unique titles + their associated points (zip-paired so the
        # pool order stays meaningful across seeds).
        indices = rng.sample(range(len(_TICKET_TEMPLATES)), NUM_TICKETS)
        tickets = [
            {
                "id": f"t{i}",
                "title": _TICKET_TEMPLATES[idx],
                "points": _POINT_POOL[idx],
                "priority": False,
                "removed": False,
            }
            for i, idx in enumerate(indices)
        ]
        # Mark exactly two as priority (cannot be removed).
        priority_indices = rng.sample(range(NUM_TICKETS), 2)
        for pi in priority_indices:
            tickets[pi]["priority"] = True
        # Ensure the puzzle is solvable: sum of priority tickets must already
        # fit under budget; if not, swap their points down.
        priority_sum = sum(t["points"] for t in tickets if t["priority"])
        if priority_sum > SPRINT_BUDGET:
            # Reassign the two priority tickets the lowest-point templates
            # to guarantee solvability while keeping titles intact.
            low_points = sorted(p for p in _POINT_POOL)[:2]
            for j, t in enumerate(tickets):
                if t["priority"]:
                    t["points"] = low_points.pop(0)
        return {
            "tickets": tickets,
            "budget": SPRINT_BUDGET,
        }

    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        if action != "toggle":
            raise MiniGamePluginError(code="UNKNOWN_ACTION", message=f"Unknown action {action!r}.")
        if not isinstance(params, dict):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Params must be an object.")
        ticket_id = params.get("ticketId")
        if not isinstance(ticket_id, str):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Missing ticketId.")
        ticket = next((t for t in state["tickets"] if t["id"] == ticket_id), None)
        if ticket is None:
            raise MiniGamePluginError(
                code="UNKNOWN_TICKET", message=f"Unknown ticket_id {ticket_id!r}."
            )
        if ticket["priority"]:
            # Soft reset — touching priority drops every removal.
            for t in state["tickets"]:
                t["removed"] = False
            return state
        # Toggle removal — re-tap unremoves it (restores the ticket to sprint).
        ticket["removed"] = not ticket["removed"]
        return state

    def is_complete(self, state: dict) -> bool:
        remaining = sum(t["points"] for t in state["tickets"] if not t["removed"])
        return remaining <= state["budget"]

    def public_view(self, state: dict) -> dict:
        remaining = sum(t["points"] for t in state["tickets"] if not t["removed"])
        return {
            "tickets": [
                {
                    "id": t["id"],
                    "title": t["title"],
                    "points": t["points"],
                    "priority": t["priority"],
                    "removed": t["removed"],
                }
                for t in state["tickets"]
            ],
            "budget": state["budget"],
            "remainingPoints": remaining,
        }
