import random
from dataclasses import dataclass

_MIN_PLAYERS = 2
_MAX_PLAYERS = 6

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


def assign(
    player_ids: list[str],
    rng: random.Random | None = None,
) -> dict[str, RoleInfo]:
    """Weist Rollen zufällig zu: genau 1 Vibe Coder, Rest Developer.

    Gilt für 2..6 Spieler.
    rng injizierbar für deterministische Tests.
    """
    n = len(player_ids)
    if n < _MIN_PLAYERS or n > _MAX_PLAYERS:
        raise ValueError(f"assign() erwartet {_MIN_PLAYERS}..{_MAX_PLAYERS} Spieler, bekam {n}.")

    r = rng or random.SystemRandom()
    shuffled = list(player_ids)
    r.shuffle(shuffled)

    chaos_id, *dev_ids = shuffled
    out: dict[str, RoleInfo] = {
        chaos_id: RoleInfo(
            role="vibe_coder",
            team=_TEAMS["vibe_coder"],
            description=_DESCRIPTIONS["vibe_coder"],
        ),
    }
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
