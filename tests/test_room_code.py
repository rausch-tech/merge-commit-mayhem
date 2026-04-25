import pytest

from app.game.room_code import ALPHABET, generate, generate_unique


def test_alphabet_excludes_confusing_chars():
    assert "I" not in ALPHABET
    assert "O" not in ALPHABET
    assert "0" not in ALPHABET
    assert "1" not in ALPHABET
    assert len(ALPHABET) == 24


def test_generate_returns_four_chars_from_alphabet():
    for _ in range(50):
        code = generate()
        assert len(code) == 4
        assert all(ch in ALPHABET for ch in code)


def test_generate_unique_avoids_collisions():
    existing = {"ABCD", "EFGH"}
    code = generate_unique(existing)
    assert code not in existing
    assert len(code) == 4


def test_generate_unique_eventually_raises_when_saturated():
    # Saturate with all possible codes → generate_unique must give up.
    all_codes = {
        a + b + c + d for a in ALPHABET for b in ALPHABET for c in ALPHABET for d in ALPHABET
    }
    with pytest.raises(RuntimeError):
        generate_unique(all_codes)
