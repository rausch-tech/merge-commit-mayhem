import random

from app.game.game_room import GameRoom
from app.game.models import Phase


def _started_room(n: int = 4) -> GameRoom:
    """Tier 1.5 raised MIN_PLAYERS_TO_START to 4 — bump any caller below 4."""
    if n < 4:
        n = 4
    room = GameRoom(code="ABCD")
    for i in range(n):
        room.add_player(f"p{i}")
    host_id = next(iter(room.players))
    room.start(requesting_player_id=host_id, rng=random.Random(0))
    return room


# --- individual conditions ------------------------------------------------


def test_pipeline_zero_ends_with_chaos_win():
    room = _started_room()
    room.pipeline_stability = 0
    room.tick(0.05)
    assert room.phase is Phase.ENDED
    assert room.winner == "chaos_agents"
    assert room.win_reason == "Die Pipeline ist tot."


def test_pipeline_below_zero_also_triggers_win():
    room = _started_room()
    # Cannot drop below 0 in practice (clamped), but defensively test <= 0 path.
    room.pipeline_stability = -5
    room.tick(0.05)
    assert room.phase is Phase.ENDED
    assert room.winner == "chaos_agents"


def test_release_hundred_ends_with_release_team_win():
    room = _started_room()
    room.release_progress = 100
    room.tick(0.05)
    assert room.phase is Phase.ENDED
    assert room.winner == "release_team"
    assert room.win_reason == "Release deployed."


def test_release_over_hundred_also_triggers_win():
    room = _started_room()
    room.release_progress = 110
    room.tick(0.05)
    assert room.phase is Phase.ENDED
    assert room.winner == "release_team"


def test_timer_expired_ends_with_chaos_win():
    room = _started_room()
    room.remaining_seconds = 0.01
    room.tick(0.1)
    assert room.phase is Phase.ENDED
    assert room.winner == "chaos_agents"
    assert room.win_reason == "Das Release-Fenster ist geschlossen."


# --- priority order -------------------------------------------------------


def test_pipeline_wins_over_release_on_simultaneous_trigger():
    room = _started_room()
    room.pipeline_stability = 0
    room.release_progress = 100
    room.tick(0.05)
    assert room.winner == "chaos_agents"
    assert room.win_reason == "Die Pipeline ist tot."


def test_release_wins_over_timer_on_simultaneous_trigger():
    room = _started_room()
    room.release_progress = 100
    room.remaining_seconds = 0
    room.tick(0.05)
    assert room.winner == "release_team"


# --- frozen state ---------------------------------------------------------


def test_ticks_after_end_are_noops():
    room = _started_room()
    room.pipeline_stability = 0
    room.tick(0.05)
    assert room.phase is Phase.ENDED
    # Snapshot state.
    rp = room.release_progress
    rs = room.remaining_seconds
    # Force a bunch of ticks — nothing should change.
    for _ in range(100):
        room.tick(0.1)
    assert room.release_progress == rp
    assert room.remaining_seconds == rs
    assert room.phase is Phase.ENDED


def test_win_check_is_idempotent():
    """A condition satisfied for several ticks must not change winner/reason."""
    room = _started_room()
    room.pipeline_stability = 0
    room.tick(0.05)
    first_winner = room.winner
    first_reason = room.win_reason
    room.tick(0.05)
    assert room.winner == first_winner
    assert room.win_reason == first_reason


def test_playing_state_is_untouched_without_condition():
    room = _started_room()
    # Standard tick with no extreme values.
    room.tick(0.05)
    assert room.phase is Phase.PLAYING
    assert room.winner is None
    assert room.win_reason is None


# --- Tier 2.1: chaos parity ------------------------------------------------


def test_chaos_parity_one_each_chaos_wins():
    """1 chaos + 1 release alive → chaos wins via parity."""
    room = _started_room(n=4)  # 1 chaos + 3 release
    # Eliminate enough release players to leave parity: 1 chaos + 1 release.
    release_alive = [p for p in room.players.values() if p.team == "release_team" and p.is_alive]
    assert len(release_alive) >= 2
    release_alive[0].is_alive = False
    release_alive[1].is_alive = False
    room.tick(0.05)
    assert room.phase is Phase.ENDED
    assert room.winner == "chaos_agents"
    assert room.win_reason == "Chaos hat die Mehrheit."


def test_no_chaos_parity_when_release_majority():
    """1 chaos + 2 release alive → no chaos parity yet, round continues."""
    room = _started_room(n=4)  # 1 chaos + 3 release
    # Eliminate one release so we have 1 chaos + 2 release (release majority).
    release_alive = [p for p in room.players.values() if p.team == "release_team" and p.is_alive]
    release_alive[0].is_alive = False
    chaos_alive = [p for p in room.players.values() if p.team == "chaos_agents" and p.is_alive]
    release_alive = [p for p in room.players.values() if p.team == "release_team" and p.is_alive]
    assert len(chaos_alive) == 1
    assert len(release_alive) == 2
    room.tick(0.05)
    assert room.phase is Phase.PLAYING


def test_no_chaos_parity_when_zero_chaos_alive():
    """0 chaos + 1 release alive: the existing all_chaos_eliminated win takes
    precedence over chaos parity (which requires chaos_alive > 0)."""
    room = _started_room(n=4)  # 1 chaos + 3 release
    # Eliminate the chaos player and all but one release.
    for p in room.players.values():
        if p.team == "chaos_agents":
            p.is_alive = False
    release_alive = [p for p in room.players.values() if p.team == "release_team" and p.is_alive]
    for p in release_alive[1:]:
        p.is_alive = False
    room.tick(0.05)
    assert room.phase is Phase.ENDED
    assert room.winner == "release_team"
    assert room.win_reason == "Alle Chaos-Agenten wurden enttarnt."


def test_demo_mode_solo_player_does_not_immediately_win_chaos():
    """Regression: a solo demo round (1 chaos, 0 release) used to trigger the
    chaos-parity win on the very first tick because chaos_alive (1) >= release_alive
    (0). The parity rule must only fire if a release team existed at all."""
    room = GameRoom(code="DEMO")
    room.add_player("Solo")
    host_id = next(iter(room.players))
    room.start(requesting_player_id=host_id, rng=random.Random(0), demo=True)
    # Solo demo forces vibe_coder.
    assert room.players[host_id].team == "chaos_agents"
    assert sum(1 for p in room.players.values() if p.team == "release_team") == 0
    room.tick(0.05)
    assert room.phase is Phase.PLAYING
    assert room.winner is None


# --- reset recovers --------------------------------------------------------


def test_reset_after_end_returns_to_lobby():
    room = _started_room()
    room.release_progress = 100
    room.tick(0.05)
    assert room.phase is Phase.ENDED
    room.reset_for_new_round()
    assert room.phase is Phase.LOBBY
    assert room.winner is None
    assert room.win_reason is None
