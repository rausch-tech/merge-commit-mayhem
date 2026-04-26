"""Tier 3.3 — Mini-Game „Server-Racks neu verkabeln".

Mechanik (Among-Us-Cables im DevOps-Re-Skin): vier farbige Source-Stecker
links, vier Destination-Buchsen rechts in zufaelliger Reihenfolge. Spieler
verbindet jede Source mit der gleichfarbigen Destination, indem er beide
nacheinander tippt (Pairing-Mechanik). Der Client haelt nur die UI-Selektion;
der Server bekommt jeden Versuch als ``connect``-Action mit beiden Ids und
entscheidet authoritativ, ob die Farben passen. Bei Mismatch wird die
Verbindungs-Map komplett geleert (Soft-Reset). Bei vier korrekten
Verbindungen ist das Mini-Game complete.
"""

import random

from app.game.minigames.base import MiniGamePlugin, MiniGamePluginError

NUM_PAIRS = 4
COLORS: list[str] = ["#f87171", "#4ade80", "#60a5fa", "#facc15"]


class CablePairing(MiniGamePlugin):
    id = "cable_pairing"
    title = "Server-Racks neu verkabeln"

    def init_state(self, seed: int) -> dict:
        rng = random.Random(seed)
        # Sources keep their color order top-to-bottom; destinations shuffle
        # so the player must visually scan to find each match.
        sources = [{"id": f"s{i}", "color": c} for i, c in enumerate(COLORS)]
        dest_colors = COLORS.copy()
        rng.shuffle(dest_colors)
        destinations = [{"id": f"d{i}", "color": c} for i, c in enumerate(dest_colors)]
        return {
            "sources": sources,
            "destinations": destinations,
            "connections": {},  # source_id -> destination_id
        }

    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        if action != "connect":
            raise MiniGamePluginError(code="UNKNOWN_ACTION", message=f"Unknown action {action!r}.")
        if not isinstance(params, dict):
            raise MiniGamePluginError(code="INVALID_PARAMS", message="Params must be an object.")
        source_id = params.get("sourceId")
        dest_id = params.get("destinationId")
        if not isinstance(source_id, str) or not isinstance(dest_id, str):
            raise MiniGamePluginError(
                code="INVALID_PARAMS", message="Missing sourceId/destinationId."
            )

        source = next((s for s in state["sources"] if s["id"] == source_id), None)
        dest = next((d for d in state["destinations"] if d["id"] == dest_id), None)
        if source is None or dest is None:
            raise MiniGamePluginError(code="UNKNOWN_NODE", message="Unknown source/destination id.")

        # Idempotent re-tap: if this source is already wired the same way,
        # silently accept (the client may double-tap before the echo arrives).
        if state["connections"].get(source_id) == dest_id:
            return state
        # Either side already in use? Reject silently — player must clear the
        # board with a deliberate mismatch if they want to retry.
        if source_id in state["connections"]:
            return state
        if dest_id in state["connections"].values():
            return state

        if source["color"] == dest["color"]:
            state["connections"][source_id] = dest_id
        else:
            # Soft reset: drop everything so the player starts over.
            state["connections"] = {}
        return state

    def is_complete(self, state: dict) -> bool:
        return len(state["connections"]) >= NUM_PAIRS

    def public_view(self, state: dict) -> dict:
        return {
            "sources": [{"id": s["id"], "color": s["color"]} for s in state["sources"]],
            "destinations": [
                {"id": d["id"], "color": d["color"]} for d in state["destinations"]
            ],
            "connections": dict(state["connections"]),
            "totalPairs": NUM_PAIRS,
        }
