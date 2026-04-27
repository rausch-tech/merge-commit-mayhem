"""Pure tally helpers for voting. Decoupled from GameRoom state so the
unit tests stay tiny — they pass dict literals and tiny ad-hoc structs
instead of standing up a full game room.
"""

from typing import Final, Protocol

SKIP_TARGET: Final[str] = ""


class _PlayerLike(Protocol):
    """Structural type for ``all_chaos_eliminated``: anything with the two
    fields the function needs. Player satisfies it; the test doubles in
    test_voting.py do too. Avoids ``getattr`` indirection without coupling
    voting.py to the full ``Player`` model. ``team`` is Optional because
    ``Player.team`` is None until assign() runs at round start."""

    team: str | None
    is_alive: bool


def tally(votes: dict[str, str]) -> str | None:
    """Returns the player_id of the eliminated player, or None if nobody is
    removed.

    Rules:
    - Empty dict → None.
    - Skip votes count toward the skip pile.
    - The "winner" is whichever target (player_id OR skip) got the most votes.
    - If skip wins (or ties for the highest), nobody is removed → return None.
    - If a player wins outright, return their id.
    - If two or more named targets tie at the top, return None (no removal).
    """
    if not votes:
        return None
    counts: dict[str, int] = {}
    for target in votes.values():
        counts[target] = counts.get(target, 0) + 1
    max_count = max(counts.values())
    winners = [t for t, c in counts.items() if c == max_count]
    if len(winners) > 1:
        return None  # tie → no removal
    winner = winners[0]
    if winner == SKIP_TARGET:
        return None
    return winner


def all_chaos_eliminated(players: list[_PlayerLike]) -> bool:
    """True if every player on team 'chaos_agents' has is_alive=False.
    Returns False if no chaos players exist (vacuous-truth would mislead)."""
    chaos = [p for p in players if p.team == "chaos_agents"]
    if not chaos:
        return False
    return all(not p.is_alive for p in chaos)
