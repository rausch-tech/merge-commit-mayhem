"""Tier 3.6.5 — voting_result.lastWords flavor pass.

flavor_last_words is a tiny pure helper, but two contracts matter for
callers:

1. **Pool selection follows team**: chaos players get troll-flavored
   exits, release-team players get aggrieved exits. We don't assert on
   exact strings — those drift — but the two pools must be disjoint so
   the team intent stays readable.
2. **No empty strings**: every flavor entry is a non-empty line; the
   default ``""`` only fires for skipped/tied votes (handled in the
   meeting-controller call-site).
"""

import random

from app.game.ai_flavor import (
    _LAST_WORDS_CHAOS,
    _LAST_WORDS_RELEASE,
    flavor_last_words,
)


def test_last_words_returns_a_chaos_line_for_chaos_players():
    rng = random.Random(0)
    for _ in range(20):
        line = flavor_last_words(was_chaos=True, rng=rng)
        assert line in _LAST_WORDS_CHAOS


def test_last_words_returns_a_release_line_for_release_players():
    rng = random.Random(0)
    for _ in range(20):
        line = flavor_last_words(was_chaos=False, rng=rng)
        assert line in _LAST_WORDS_RELEASE


def test_pools_are_disjoint():
    """Pool overlap would muddy the team-flavor intent. Catch it now."""
    overlap = set(_LAST_WORDS_CHAOS) & set(_LAST_WORDS_RELEASE)
    assert not overlap, f"chaos and release pools share lines: {overlap}"


def test_pools_have_no_empty_lines():
    for line in (*_LAST_WORDS_CHAOS, *_LAST_WORDS_RELEASE):
        assert line.strip(), "empty flavor line would render as a blank quote"
