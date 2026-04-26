import random
from dataclasses import dataclass

_MIN_PLAYERS = 2
_MAX_PLAYERS = 12

_DESCRIPTIONS = {
    "developer": "Du bist ein Developer. Bring das Release über die Linie.",
    "vibe_coder": ("Du bist der Vibe Coder. Sabotiere das Release, ohne entdeckt zu werden."),
}
_TEAMS = {
    "developer": "release_team",
    "vibe_coder": "chaos_agents",
}


@dataclass(frozen=True)
class RoleInfo:
    role: str
    team: str
    description: str


def chaos_count_for(n_players: int) -> int:
    """Returns number of chaos agents for a given player count.

    Tier 1.5 mapping: 2..6 -> 1, 7..9 -> 2, 10..12 -> 3.
    Formula: max(1, (n - 1) // 3) — fits the table exactly.
    """
    return max(1, (n_players - 1) // 3)


def assign(
    player_ids: list[str],
    rng: random.Random | None = None,
) -> dict[str, RoleInfo]:
    """Weist Rollen zufällig zu: 1..3 Vibe Coder (je nach Spielerzahl), Rest Developer.

    Gilt für 2..12 Spieler. Anzahl Chaos-Agenten siehe `chaos_count_for`.
    rng injizierbar für deterministische Tests.
    """
    n = len(player_ids)
    if n < _MIN_PLAYERS or n > _MAX_PLAYERS:
        raise ValueError(f"assign() erwartet {_MIN_PLAYERS}..{_MAX_PLAYERS} Spieler, bekam {n}.")

    r = rng or random.SystemRandom()
    shuffled = list(player_ids)
    r.shuffle(shuffled)

    chaos_n = chaos_count_for(n)
    chaos_ids = shuffled[:chaos_n]
    dev_ids = shuffled[chaos_n:]
    out: dict[str, RoleInfo] = {}
    for chaos_id in chaos_ids:
        out[chaos_id] = RoleInfo(
            role="vibe_coder",
            team=_TEAMS["vibe_coder"],
            description=_DESCRIPTIONS["vibe_coder"],
        )
    for dev_id in dev_ids:
        out[dev_id] = RoleInfo(
            role="developer",
            team=_TEAMS["developer"],
            description=_DESCRIPTIONS["developer"],
        )
    return out


def description_for(role: str) -> str:
    """Public helper so other modules don't reach into a private dict."""
    return _DESCRIPTIONS.get(role, "")
