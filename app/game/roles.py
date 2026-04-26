"""
Rollen-System (Tier 3.5).

Jeder Spieler bekommt zu Rundenstart genau eine Rolle. Release-Rollen haben
Stärken (schnellere Tasks in passenden Kategorien), Schwächen, ein eigenes
Kaffee-Profil und optional eine aktive Fähigkeit. Chaos-Rollen unterscheiden
sich darin, welche Sabotagen sie auslösen können — Vibe Coder ist
AI-/Code-fokussiert, Rogue Consultant macht Meeting-/Scope-Chaos, Shadow Admin
greift Infrastruktur an.

Das alte 2-Rollen-Modell (developer + vibe_coder) ist hier weiter als
„Default-Rolle" verfügbar; assign() füllt nicht-präferierte Slots mit
Developer auf.
"""

import random
from dataclasses import dataclass, field
from typing import Final

_MIN_PLAYERS = 2
_MAX_PLAYERS = 12

# Task categories (referenced by RoleDefinition.strength_categories etc.)
# Map task_id → category in tasks.py via TaskDefinition.category. Keep this
# list curated and small — every category needs a clear "who's good at it".
TASK_CATEGORY_CODE: Final[str] = "code"
TASK_CATEGORY_INFRA: Final[str] = "infra"
TASK_CATEGORY_LEGACY: Final[str] = "legacy"
TASK_CATEGORY_SCOPE: Final[str] = "scope"
TASK_CATEGORY_SUPPORT: Final[str] = "support"

ALL_CATEGORIES: Final[tuple[str, ...]] = (
    TASK_CATEGORY_CODE,
    TASK_CATEGORY_INFRA,
    TASK_CATEGORY_LEGACY,
    TASK_CATEGORY_SCOPE,
    TASK_CATEGORY_SUPPORT,
)


@dataclass(frozen=True)
class RoleDefinition:
    """Static definition of a role. Lives in code (not the map JSON) — these
    drive every per-role mechanic: task speed, coffee decay, ability gates."""

    id: str
    title: str
    team: str  # "release_team" | "chaos_agents"
    description: str
    short_blurb: str  # one-line role-card subtitle
    strength_categories: tuple[str, ...] = field(default_factory=tuple)
    weak_categories: tuple[str, ...] = field(default_factory=tuple)
    # Coffee profile. decay_modifier 1.0 = normal, 1.5 = drains fast,
    # 0.5 = sips slowly. max_coffee may exceed 100 (Caffeine Collector).
    coffee_decay_modifier: float = 1.0
    max_coffee: float = 100.0
    coffee_full_speed_bonus: float = 0.10  # +x% task/move speed at >=80 coffee
    coffee_low_speed_penalty: float = 0.10  # -x% at <15 coffee
    # Active ability (one per role, single-use per round). None = no ability.
    ability_id: str | None = None
    ability_label: str = ""
    ability_hint: str = ""
    # Chaos-only: which sabotages this role can trigger. Empty for release.
    available_sabotages: tuple[str, ...] = field(default_factory=tuple)
    # Singleton roles: server enforces at most one of these per round even if
    # multiple players prefer it (Caffeine Collector, Scrum Master, etc.).
    singleton: bool = False


# --- Release Team Roles ----------------------------------------------------

DEVELOPER = RoleDefinition(
    id="developer",
    title="Developer",
    team="release_team",
    description=(
        "Du bist Developer. PRs, Unit-Tests, Release-Notes — du bringst Code über die Linie."
    ),
    short_blurb="Code-Spezialist • PRs & Tests",
    strength_categories=(TASK_CATEGORY_CODE,),
    weak_categories=(TASK_CATEGORY_SUPPORT,),
)

DEVOPS_ENGINEER = RoleDefinition(
    id="devops_engineer",
    title="DevOps Engineer",
    team="release_team",
    description=(
        "Du bist DevOps Engineer. CI/CD, Deployments, Logs — die Pipeline "
        "läuft, weil du läufst. Aber ohne Kaffee bist du fast nichts wert."
    ),
    short_blurb="Infra-Spezialist • Pipeline & Deploys",
    strength_categories=(TASK_CATEGORY_INFRA,),
    weak_categories=(TASK_CATEGORY_SCOPE, TASK_CATEGORY_CODE),
    coffee_decay_modifier=1.5,
    coffee_full_speed_bonus=0.20,
    coffee_low_speed_penalty=0.25,
    ability_id="rollback",
    ability_label="Rollback",
    ability_hint="Stelle einmal pro Runde +18 Pipeline-Stability her.",
    singleton=True,
)

QA_LEAD = RoleDefinition(
    id="qa_lead",
    title="QA Lead",
    team="release_team",
    description=(
        "Du bist QA Lead. Du findest Bugs, validierst Logs und merkst, wenn "
        "etwas Komisches passiert. Du brauchst weniger Kaffee als die anderen."
    ),
    short_blurb="Test-Spezialistin • Logs & Repro",
    strength_categories=(TASK_CATEGORY_CODE, TASK_CATEGORY_LEGACY),
    weak_categories=(TASK_CATEGORY_INFRA,),
    coffee_decay_modifier=0.6,
    ability_id="reproduce_bug",
    ability_label="Reproduce Bug",
    ability_hint='Markiert eine kürzliche Aktion als "plausibel/verdächtig".',
    singleton=True,
)

SCRUM_MASTER = RoleDefinition(
    id="scrum_master",
    title="Scrum Master",
    team="release_team",
    description=(
        "Du bist Scrum Master. Sprint-Board, Scope, Release-Notes — und "
        "im Notfall rufst du ein Standup."
    ),
    short_blurb="Process-Lead • Scope & Standup",
    strength_categories=(TASK_CATEGORY_SCOPE,),
    weak_categories=(TASK_CATEGORY_INFRA,),
    coffee_decay_modifier=0.8,
    ability_id="standup",
    ability_label="Standup ansetzen",
    ability_hint="Ruft einmal pro Runde ein zusätzliches Emergency Meeting.",
    singleton=True,
)

CAFFEINE_COLLECTOR = RoleDefinition(
    id="caffeine_collector",
    title="Caffeine Collector",
    team="release_team",
    description=(
        "Du bist Caffeine Collector. Du hältst das Team koffein-positiv. "
        "Deine Tasse fasst mehr und du kannst andere boosten."
    ),
    short_blurb="Support • Coffee Run",
    strength_categories=(TASK_CATEGORY_SUPPORT,),
    weak_categories=(TASK_CATEGORY_INFRA, TASK_CATEGORY_CODE),
    coffee_decay_modifier=0.5,
    max_coffee=130.0,
    coffee_full_speed_bonus=0.15,
    ability_id="coffee_run",
    ability_label="Coffee Run",
    ability_hint="Buffe alle Spieler in 220 px um dich mit +35 Coffee.",
    singleton=True,
)

# --- Chaos Roles -----------------------------------------------------------

VIBE_CODER = RoleDefinition(
    id="vibe_coder",
    title="Vibe Coder",
    team="chaos_agents",
    description=(
        "Du bist der Vibe Coder. Du committest direkt auf main, schmückst "
        "Tests mit Hallucinations und lässt die Pipeline atmen — auf deine "
        "Art. Sabotiere, ohne entdeckt zu werden."
    ),
    short_blurb="AI-Chaos • Code, CI, Vibe",
    available_sabotages=(
        "ci_cd_red",
        "flaky_tests",
        "merge_conflict_storm",
        "fake_customer_request",
    ),
)

ROGUE_CONSULTANT = RoleDefinition(
    id="rogue_consultant",
    title="Rogue Consultant",
    team="chaos_agents",
    description=(
        "Du bist Rogue Consultant. Du erfindest Customer Requests, ziehst "
        "Leute in unnötige Meetings und wirst dafür bezahlt, alles zu "
        "blockieren. Sabotiere, ohne entdeckt zu werden."
    ),
    short_blurb="Process-Chaos • Meetings, Scope",
    available_sabotages=(
        "mandatory_meeting",
        "fake_customer_request",
        "coffee_outage",
        "merge_conflict_storm",
    ),
)

SHADOW_ADMIN = RoleDefinition(
    id="shadow_admin",
    title="Shadow Admin",
    team="chaos_agents",
    description=(
        "Du bist Shadow Admin. Du hast root, kappst Slack, killst die "
        "Beleuchtung und lässt das Pager-System brennen. Sabotiere, ohne "
        "entdeckt zu werden."
    ),
    short_blurb="Infra-Chaos • Outages",
    available_sabotages=(
        "lights_out",
        "comms_outage",
        "ci_cd_red",
        "mandatory_meeting",
    ),
)


ROLE_DEFINITIONS: Final[tuple[RoleDefinition, ...]] = (
    DEVELOPER,
    DEVOPS_ENGINEER,
    QA_LEAD,
    SCRUM_MASTER,
    CAFFEINE_COLLECTOR,
    VIBE_CODER,
    ROGUE_CONSULTANT,
    SHADOW_ADMIN,
)

_BY_ID: Final[dict[str, RoleDefinition]] = {r.id: r for r in ROLE_DEFINITIONS}

RELEASE_ROLES: Final[tuple[str, ...]] = tuple(
    r.id for r in ROLE_DEFINITIONS if r.team == "release_team"
)
CHAOS_ROLES: Final[tuple[str, ...]] = tuple(
    r.id for r in ROLE_DEFINITIONS if r.team == "chaos_agents"
)


def role_by_id(role_id: str) -> RoleDefinition:
    """Lookup helper. Falls back to Developer for unknown ids so a stale
    client/save can never crash the round."""
    return _BY_ID.get(role_id, DEVELOPER)


@dataclass(frozen=True)
class RoleInfo:
    """Wire-friendly snapshot used by the legacy `private_role` message and
    private_role_for(). Includes ability + role-card metadata so the client
    can render the intro modal without hardcoding role data."""

    role: str
    team: str
    description: str
    title: str = ""
    short_blurb: str = ""
    strength_categories: tuple[str, ...] = field(default_factory=tuple)
    weak_categories: tuple[str, ...] = field(default_factory=tuple)
    ability_id: str | None = None
    ability_label: str = ""
    ability_hint: str = ""
    max_coffee: float = 100.0
    available_sabotages: tuple[str, ...] = field(default_factory=tuple)


def info_for(role_id: str) -> RoleInfo:
    """Build the wire-shaped RoleInfo from the static RoleDefinition."""
    rd = role_by_id(role_id)
    return RoleInfo(
        role=rd.id,
        team=rd.team,
        description=rd.description,
        title=rd.title,
        short_blurb=rd.short_blurb,
        strength_categories=rd.strength_categories,
        weak_categories=rd.weak_categories,
        ability_id=rd.ability_id,
        ability_label=rd.ability_label,
        ability_hint=rd.ability_hint,
        max_coffee=rd.max_coffee,
        available_sabotages=rd.available_sabotages,
    )


def chaos_count_for(n_players: int) -> int:
    """Returns number of chaos agents for a given player count.
    Tier 1.5 mapping: 2..6 -> 1, 7..9 -> 2, 10..12 -> 3.
    """
    return max(1, (n_players - 1) // 3)


def _pick_chaos_role(rng: random.Random) -> str:
    """Pick a chaos variant uniformly (Vibe Coder / Rogue Consultant /
    Shadow Admin)."""
    return rng.choice(CHAOS_ROLES)


def assign(
    player_ids: list[str],
    rng: random.Random | None = None,
    preferences: dict[str, str | None] | None = None,
) -> dict[str, RoleInfo]:
    """Tier 3.5: assign release + chaos roles, honoring lobby preferences.

    Algorithm:
    1. Pick chaos players (deterministic count via chaos_count_for) → assign
       each a random chaos variant (Vibe / Consultant / Admin).
    2. For release players: honor preferred_role if it exists and the role
       slot is still available (singleton roles capped at 1).
    3. Fill remaining release players with Developer.

    Preferences for chaos players are silently ignored — secrecy demands
    server-side override.
    """
    n = len(player_ids)
    if n < _MIN_PLAYERS or n > _MAX_PLAYERS:
        raise ValueError(f"assign() erwartet {_MIN_PLAYERS}..{_MAX_PLAYERS} Spieler, bekam {n}.")

    r = rng or random.SystemRandom()
    prefs = preferences or {}
    shuffled = list(player_ids)
    r.shuffle(shuffled)

    chaos_n = chaos_count_for(n)
    chaos_ids = shuffled[:chaos_n]
    release_ids = shuffled[chaos_n:]

    out: dict[str, RoleInfo] = {}

    # Chaos: random variant per agent, silent override of any preference.
    for cid in chaos_ids:
        out[cid] = info_for(_pick_chaos_role(r))

    # Release: honor preference if singleton slot still open.
    used_singletons: set[str] = set()
    for pid in release_ids:
        pref = prefs.get(pid)
        chosen = None
        if pref and pref in RELEASE_ROLES and pref != "developer":
            rd = _BY_ID[pref]
            if not rd.singleton or pref not in used_singletons:
                chosen = pref
                if rd.singleton:
                    used_singletons.add(pref)
        out[pid] = info_for(chosen or "developer")

    return out


def description_for(role: str) -> str:
    """Public helper so other modules don't reach into a private dict."""
    return role_by_id(role).description


# --- gameplay multipliers --------------------------------------------------


def task_speed_multiplier(
    role_id: str | None,
    task_category: str | None,
    coffee_energy: float,
) -> float:
    """Returns a multiplier on task progress speed (1.0 = normal). Larger =
    faster. Combines role strength/weakness with coffee energy."""
    rd = role_by_id(role_id) if role_id else DEVELOPER
    mult = 1.0
    if task_category and task_category in rd.strength_categories:
        mult *= 1.35
    if task_category and task_category in rd.weak_categories:
        mult *= 0.75
    # Coffee curve: <15 = penalty, ≥80 = bonus, in between = normal.
    if coffee_energy >= 80:
        mult *= 1.0 + rd.coffee_full_speed_bonus
    elif coffee_energy < 15:
        mult *= 1.0 - rd.coffee_low_speed_penalty
    return mult


def movement_speed_multiplier(role_id: str | None, coffee_energy: float) -> float:
    """Returns a multiplier on movement speed. Baseline is 1.0 at full
    coffee — no role gets a movement *bonus*; coffee only matters when it
    runs critically low (penalty kicks in <15)."""
    rd = role_by_id(role_id) if role_id else DEVELOPER
    if coffee_energy < 15:
        return 1.0 - rd.coffee_low_speed_penalty * 0.5
    return 1.0
