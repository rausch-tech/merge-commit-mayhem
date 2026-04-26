"""Tier 3.1 — Mini-Game plugin base class.

Server-authoritative pattern: each mini-game is a class implementing four
required methods. The framework calls these in response to WS messages; the
plugin is pure logic, never touches WS or GameRoom directly. That keeps the
plugin surface small enough that an LLM can generate one from a schema
without halluzinating side-effects.
"""

from abc import ABC, abstractmethod


class MiniGamePluginError(Exception):
    """Raised by a plugin to signal an invalid input. The framework catches
    this and emits an error frame to the offending client without ending
    the mini-game session — the plugin is asserting that the input was
    malformed/cheaty, not that the player failed.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class MiniGamePlugin(ABC):
    """Server-side mini-game plugin.

    All four methods are required. ``tick`` is optional (default no-op) for
    time-pressure mini-games. State and view dicts are plugin-specific JSON
    payloads — the framework only validates the WS wrapper, not the inner
    schema. Plugins must reject malformed inputs by raising
    ``MiniGamePluginError``.
    """

    id: str  # stable identifier, must match registry key
    title: str  # human-readable label

    @abstractmethod
    def init_state(self, seed: int) -> dict:
        """Build the initial server-side state. Must be deterministic given
        the seed so server restarts / re-runs are reproducible."""

    @abstractmethod
    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        """Apply a player input. Returns the new state (mutating in place is
        also fine — caller treats the return value as authoritative).

        Raise MiniGamePluginError(code=..., message=...) on cheating /
        malformed input; the framework will surface the error to the client
        without ending the session.
        """

    @abstractmethod
    def is_complete(self, state: dict) -> bool:
        """Return True iff the player has solved the mini-game and the
        framework should reward + close the session."""

    @abstractmethod
    def public_view(self, state: dict) -> dict:
        """Return the subset of state that the client may see. The
        framework forwards this verbatim in mini_game_started /
        mini_game_state messages.
        """

    def tick(self, state: dict, dt: float) -> dict:
        """Optional: advance state by ``dt`` seconds. Default is a no-op for
        input-driven mini-games. Override for time-pressure mechanics."""
        return state
