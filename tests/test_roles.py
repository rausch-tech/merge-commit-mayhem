import random

import pytest

from app.game.roles import RoleInfo, assign


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6])
def test_assigns_exactly_one_chaos_agent(n: int):
    player_ids = [f"p{i}" for i in range(n)]
    result = assign(player_ids, rng=random.Random(42))
    chaos = [pid for pid, info in result.items() if info.role == "vibe_coder"]
    devs = [pid for pid, info in result.items() if info.role == "developer"]
    assert len(chaos) == 1
    assert len(devs) == n - 1


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
        assign([f"p{i}" for i in range(7)], rng=random.Random(0))


def test_role_info_exposes_description():
    result = assign(["a", "b"], rng=random.Random(0))
    for info in result.values():
        assert isinstance(info.description, str)
        assert info.description  # non-empty
