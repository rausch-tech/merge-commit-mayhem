"""
Reine Tally-Helfer fuers Voting. Trennt Pure-Logic vom GameRoom-State,
damit Tests einfacher werden.
"""

from typing import Final

SKIP_TARGET: Final[str] = ""


def tally(votes: dict[str, str]) -> str | None:
    """
    Returns the player_id of the eliminated player, or None if nobody is removed.

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
    # Find max.
    max_count = max(counts.values())
    winners = [t for t, c in counts.items() if c == max_count]
    if len(winners) > 1:
        return None  # tie → no removal
    winner = winners[0]
    if winner == SKIP_TARGET:
        return None
    return winner


def all_chaos_eliminated(players: list, team_field: str = "team", alive_field: str = "is_alive") -> bool:
    """
    True if every player on team 'chaos_agents' has is_alive=False.
    Returns False if no chaos players exist (vacuous-truth would mislead).
    """
    chaos = [p for p in players if getattr(p, team_field) == "chaos_agents"]
    if not chaos:
        return False
    return all(not getattr(p, alive_field) for p in chaos)
