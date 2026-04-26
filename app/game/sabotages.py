"""
Statische Sabotage-Definitionen und global gültige Balancing-Konstanten
für Meeting / Coffee-Slow-Effekte.

Tier 2.7 (rework): Jede Sabotage listet ``trigger_object_types`` — Chaos kann
sie nur auslösen, wenn er an einem Task-Anchor steht, dessen ``object_type``
matched. Same anchor = Same physical spot wie release-Tasks → Ambiguität, weil
Beobachter nicht sehen, ob da gearbeitet oder sabotiert wird.
"""

from dataclasses import dataclass, field
from typing import Final

NORMAL_SPEED: Final[float] = 300.0  # px/s, default movement (scaled to 4800×3200 map)
COFFEE_SLOW_SPEED: Final[float] = 160.0  # px/s, while coffee_level == 0
MEETING_DURATION: Final[float] = 5.0  # s that mandatory_meeting keeps everyone slowed


@dataclass(frozen=True)
class SabotageDefinition:
    id: str
    title: str
    cooldown_seconds: float
    incidents_increase: int = 0  # added to incidents when triggered
    # Tier 2.7: object_type values (matching TaskAnchor.object_type) where chaos
    # may stand to trigger this sabotage. Empty list = legacy "from anywhere"
    # (only used as fallback when a map has zero typed anchors).
    trigger_object_types: tuple[str, ...] = field(default_factory=tuple)
    # Human-friendly hint shown next to the sabotage button when out of range.
    object_hint: str = ""


SABOTAGE_DEFINITIONS: Final[list[SabotageDefinition]] = [
    SabotageDefinition(
        id="ci_cd_red",
        title="CI/CD Rot",
        cooldown_seconds=60.0,
        trigger_object_types=("ci_console",),
        object_hint="CI-Konsole im Server Room",
    ),
    SabotageDefinition(
        id="coffee_outage",
        title="Kaffee leer",
        cooldown_seconds=75.0,
        trigger_object_types=("coffee_machine",),
        object_hint="Kaffeemaschine in der Kitchen",
    ),
    SabotageDefinition(
        id="mandatory_meeting",
        title="Mandatory Meeting",
        cooldown_seconds=90.0,
        trigger_object_types=("meeting_screen",),
        object_hint="Meeting-Screen im Meeting Room",
    ),
    SabotageDefinition(
        id="merge_conflict_storm",
        title="Merge Conflict Storm",
        cooldown_seconds=70.0,
        incidents_increase=25,
        trigger_object_types=("git_terminal",),
        object_hint="Git-Terminal im Open Space",
    ),
    SabotageDefinition(
        id="fake_customer_request",
        title="Fake Customer Request",
        cooldown_seconds=90.0,
        trigger_object_types=("release_console", "meeting_screen"),
        object_hint="Release-Console oder Meeting-Screen",
    ),
    SabotageDefinition(
        id="flaky_tests",
        title="Flaky Tests",
        cooldown_seconds=60.0,
        incidents_increase=30,
        trigger_object_types=("qa_terminal",),
        object_hint="QA-Terminal im Open Space",
    ),
    SabotageDefinition(
        id="lights_out",
        title="PagerDuty-Storm",
        cooldown_seconds=70.0,
        trigger_object_types=("monitoring_panel",),
        object_hint="Monitoring-Konsole im Server Room",
    ),
    SabotageDefinition(
        id="comms_outage",
        title="Slack-Down",
        cooldown_seconds=80.0,
        trigger_object_types=("monitoring_panel", "ci_console"),
        object_hint="Server-Room-Konsolen",
    ),
]


def sabotage_by_id(sabotage_id: str) -> SabotageDefinition:
    """Lookup helper; raises KeyError if the id is unknown."""
    for sab in SABOTAGE_DEFINITIONS:
        if sab.id == sabotage_id:
            return sab
    raise KeyError(sabotage_id)
