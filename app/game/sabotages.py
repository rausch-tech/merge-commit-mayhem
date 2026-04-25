"""
Statische Sabotage-Definitionen und global gültige Balancing-Konstanten
für Meeting / Coffee-Slow-Effekte.
"""

from dataclasses import dataclass
from typing import Final

NORMAL_SPEED: Final[float] = 150.0  # px/s, default movement
COFFEE_SLOW_SPEED: Final[float] = 80.0  # px/s, while coffee_level == 0
MEETING_DURATION: Final[float] = 5.0  # s that mandatory_meeting keeps everyone slowed


@dataclass(frozen=True)
class SabotageDefinition:
    id: str
    title: str
    cooldown_seconds: float


SABOTAGE_DEFINITIONS: Final[list[SabotageDefinition]] = [
    SabotageDefinition(id="ci_cd_red", title="CI/CD Rot", cooldown_seconds=60.0),
    SabotageDefinition(id="coffee_outage", title="Kaffee leer", cooldown_seconds=75.0),
    SabotageDefinition(id="mandatory_meeting", title="Mandatory Meeting", cooldown_seconds=90.0),
]


def sabotage_by_id(sabotage_id: str) -> SabotageDefinition:
    """Lookup helper; raises KeyError if the id is unknown."""
    for sab in SABOTAGE_DEFINITIONS:
        if sab.id == sabotage_id:
            return sab
    raise KeyError(sabotage_id)
