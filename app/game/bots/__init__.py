"""AI-NPCs (Tier 3.9.2).

Bot lifecycle + movement/work loop. The high-level intent layer
(LLM-driven) lives in `decision.py` (Slice 3.9.2 follow-up — task 54).

Public surface is `BotManager`. The wandering / pathfinding helpers in
`pathfinding.py` are intentionally pure (no GameRoom dependency) so
they're trivially testable.
"""

from app.game.bots.manager import BOT_NAMES, BotManager

__all__ = ["BotManager", "BOT_NAMES"]
