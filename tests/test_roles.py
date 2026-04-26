import random

import pytest

from app.game.roles import CHAOS_ROLES, RELEASE_ROLES, assign, chaos_count_for


@pytest.mark.parametrize(
    "n,expected_chaos",
    [
        (2, 1),
        (3, 1),
        (4, 1),
        (5, 1),
        (6, 1),
        (7, 2),
        (8, 2),
        (9, 2),
        (10, 3),
        (11, 3),
        (12, 3),
    ],
)
def test_assigns_expected_chaos_count(n: int, expected_chaos: int):
    """Tier 3.5: chaos can be any of the chaos role variants (Vibe Coder /
    Rogue Consultant / Shadow Admin); release can be any release role."""
    player_ids = [f"p{i}" for i in range(n)]
    result = assign(player_ids, rng=random.Random(42))
    chaos = [pid for pid, info in result.items() if info.team == "chaos_agents"]
    release = [pid for pid, info in result.items() if info.team == "release_team"]
    assert len(chaos) == expected_chaos
    assert len(release) == n - expected_chaos
    for info in result.values():
        if info.team == "chaos_agents":
            assert info.role in CHAOS_ROLES
        else:
            assert info.role in RELEASE_ROLES


@pytest.mark.parametrize(
    "n,expected_chaos",
    [
        (2, 1),
        (3, 1),
        (4, 1),
        (5, 1),
        (6, 1),
        (7, 2),
        (8, 2),
        (9, 2),
        (10, 3),
        (11, 3),
        (12, 3),
    ],
)
def test_chaos_count_for_matches_spec(n: int, expected_chaos: int):
    assert chaos_count_for(n) == expected_chaos


def test_roles_have_correct_teams():
    player_ids = ["a", "b", "c"]
    result = assign(player_ids, rng=random.Random(7))
    for info in result.values():
        if info.role in CHAOS_ROLES:
            assert info.team == "chaos_agents"
        elif info.role in RELEASE_ROLES:
            assert info.team == "release_team"
        else:
            pytest.fail(f"Unexpected role {info.role!r}")


def test_lobby_preference_honored_for_release_role():
    """Tier 3.5: a player who prefs DevOps gets DevOps when there's a free
    slot. Singleton roles (DevOps, QA, Scrum Master, Caffeine Collector) are
    capped at 1 per round."""
    player_ids = ["a", "b", "c", "d"]
    result = assign(
        player_ids,
        rng=random.Random(0),
        preferences={"a": "devops_engineer", "b": "qa_lead"},
    )
    # The two preference slots got honored if those players landed on release.
    for pid, pref in [("a", "devops_engineer"), ("b", "qa_lead")]:
        if result[pid].team == "release_team":
            assert result[pid].role == pref


def test_chaos_preferences_silently_ignored():
    """Preferences for chaos roles never assign chaos — chaos stays random.
    'a' may or may not be chaos (picked randomly), but their preference was
    not the deciding factor — verify across many seeds."""
    seeds_chaos = 0
    seeds_release = 0
    for seed in range(20):
        r = assign(
            ["a", "b", "c", "d"],
            rng=random.Random(seed),
            preferences={"a": "vibe_coder"},
        )
        if r["a"].team == "chaos_agents":
            seeds_chaos += 1
        else:
            seeds_release += 1
    # Expect roughly chaos_count_for(4)/4 = 1/4 of seeds — preference didn't
    # bias the outcome (would be 100% chaos if it did).
    assert seeds_release > 0  # not always chaos


def test_all_input_ids_present_in_output():
    player_ids = ["alpha", "beta", "gamma", "delta"]
    result = assign(player_ids, rng=random.Random(0))
    assert set(result.keys()) == set(player_ids)


def test_deterministic_with_seeded_rng():
    ids = ["a", "b", "c", "d"]
    first = assign(ids, rng=random.Random(123))
    second = assign(ids, rng=random.Random(123))
    assert {k: v.role for k, v in first.items()} == {k: v.role for k, v in second.items()}


def test_raises_for_too_few_players():
    with pytest.raises(ValueError):
        assign(["only_one"], rng=random.Random(0))


def test_raises_for_too_many_players():
    with pytest.raises(ValueError):
        assign([f"p{i}" for i in range(13)], rng=random.Random(0))


def test_role_info_exposes_description():
    result = assign(["a", "b"], rng=random.Random(0))
    for info in result.values():
        assert isinstance(info.description, str)
        assert info.description  # non-empty
