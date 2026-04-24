import random
import string

# A–Z ohne I und O (Verwechslung mit 1/0).
ALPHABET = "".join(ch for ch in string.ascii_uppercase if ch not in {"I", "O"})

_MAX_ATTEMPTS = 32


def generate(rng: random.Random | None = None) -> str:
    """Return a 4-char code from the allowed alphabet."""
    r = rng or random
    return "".join(r.choices(ALPHABET, k=4))


def generate_unique(
    existing: set[str],
    rng: random.Random | None = None,
) -> str:
    """Return a code that is not in `existing`. Raises after 32 collisions."""
    for _ in range(_MAX_ATTEMPTS):
        code = generate(rng)
        if code not in existing:
            return code
    raise RuntimeError(
        f"Could not generate unique room code after {_MAX_ATTEMPTS} attempts."
    )
