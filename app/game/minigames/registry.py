"""Tier 3.1 — Plugin registry.

A new mini-game plugin is registered by adding an entry here. The id must
match ``MiniGamePlugin.id`` and the value used in TaskDefinition.mini_game.
"""

from app.game.minigames.base import MiniGamePlugin
from app.game.minigames.cable_pairing import CablePairing
from app.game.minigames.coffee_pour import CoffeePour
from app.game.minigames.diff_review import DiffReview
from app.game.minigames.log_filter import LogFilter
from app.game.minigames.sprint_trim import SprintTrim
from app.game.minigames.stability_balance import StabilityBalance
from app.game.minigames.test_suite_repair import TestSuiteRepair

MINI_GAME_PLUGINS: dict[str, MiniGamePlugin] = {
    "test_suite_repair": TestSuiteRepair(),
    "cable_pairing": CablePairing(),
    "coffee_pour": CoffeePour(),
    "log_filter": LogFilter(),
    "sprint_trim": SprintTrim(),
    "diff_review": DiffReview(),
    "stability_balance": StabilityBalance(),
}


def get_plugin(mini_game_id: str) -> MiniGamePlugin:
    """Resolve a mini-game plugin by id. Raises KeyError if unknown so the
    caller can translate into a domain-appropriate error."""
    return MINI_GAME_PLUGINS[mini_game_id]


def is_known(mini_game_id: str) -> bool:
    return mini_game_id in MINI_GAME_PLUGINS
