import random

import pytest

from app.game.roles import assign, chaos_count_for


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
    player_ids = [f"p{i}" for i in range(n)]
    result = assign(player_ids, rng=random.Random(42))
    chaos = [pid for pid, info in result.items() if info.role == "vibe_coder"]
    devs = [pid for pid, info in result.items() if info.role == "developer"]
    assert len(chaos) == expected_chaos
    assert len(devs) == n - expected_chaos


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
        if info.role == "vibe_coder":
            assert info.team == "chaos_agents"
        elif info.role == "developer":
            assert info.team == "release_team"
        else:
            pytest.fail(f"Unexpected role {info.role!r}")


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
