import random

import pytest

from app.game.game_room import MAX_PLAYERS, GameRoom, GameRoomError
from app.game.models import InputState, Phase
from app.game.sabotages import NORMAL_SPEED


def test_first_player_becomes_host():
    room = GameRoom(code="ABCD")
    player = room.add_player("Sven")
    assert player.is_host is True
    assert player.name == "Sven"
    assert len(room.players) == 1
    assert room.phase is Phase.LOBBY


def test_second_player_is_not_host():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    second = room.add_player("Max")
    assert second.is_host is False


def test_add_player_rejects_duplicate_name():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.add_player("Sven")
    assert exc.value.code == "NAME_TAKEN"


def test_add_player_rejects_when_full():
    room = GameRoom(code="ABCD")
    for i in range(MAX_PLAYERS):
        room.add_player(f"player_{i}")
    with pytest.raises(GameRoomError) as exc:
        room.add_player("overflow")
    assert exc.value.code == "ROOM_FULL"


def test_remove_host_promotes_oldest_remaining():
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    second = room.add_player("Max")
    third = room.add_player("Lea")

    room.remove_player(host.id)
    assert host.id not in room.players
    # Max joined second → should become host.
    assert room.players[second.id].is_host is True
    assert room.players[third.id].is_host is False


def test_remove_last_player_marks_empty():
    room = GameRoom(code="ABCD")
    player = room.add_player("Sven")
    room.remove_player(player.id)
    assert room.is_empty() is True


def test_unique_colors_assigned():
    room = GameRoom(code="ABCD")
    colors = set()
    for i in range(MAX_PLAYERS):
        p = room.add_player(f"player_{i}")
        colors.add(p.color)
    assert len(colors) == MAX_PLAYERS


def test_max_twelve_players_can_join():
    """Tier 1.5: cap is 12, every player gets a unique color from the palette."""
    room = GameRoom(code="ABCD")
    for i in range(12):
        room.add_player(f"player_{i}")
    assert len(room.players) == 12
    assert len({p.color for p in room.players.values()}) == 12
    with pytest.raises(GameRoomError) as exc:
        room.add_player("overflow")
    assert exc.value.code == "ROOM_FULL"


# --- start() ---------------------------------------------------------------


def _make_started_room(player_count: int = 4) -> GameRoom:
    """Spawn a started GameRoom with at least MIN_PLAYERS_TO_START players.

    Tier 1.5 raised MIN_PLAYERS_TO_START to 4. Tier 2.1's chaos-parity win
    condition also fires on tick when chaos_alive >= release_alive — with
    4 players (1 chaos + 3 release) parity is not triggered at start.
    Bumps any caller-supplied count below 4 silently up to 4. The first
    two ids stay in deterministic join order so callers indexing into them
    still get the expected pair.
    """
    if player_count < 4:
        player_count = 4
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    for i in range(player_count - 1):
        room.add_player(f"p{i}")
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    return room


def test_start_requires_host():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    second = room.add_player("Max")
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=second.id, rng=random.Random(0))
    assert exc.value.code == "NOT_HOST"


def test_start_requires_min_players():
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=host.id, rng=random.Random(0))
    assert exc.value.code == "NOT_ENOUGH_PLAYERS"


def test_start_below_min_players_rejected():
    """Tier 1.5: MIN_PLAYERS_TO_START is 4, so 3 players is not enough."""
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    room.add_player("Max")
    room.add_player("Lea")
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=host.id, rng=random.Random(0))
    assert exc.value.code == "NOT_ENOUGH_PLAYERS"


def test_start_requires_lobby_phase():
    room = _make_started_room(player_count=2)
    host_id = next(p.id for p in room.players.values() if p.is_host)
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=host_id, rng=random.Random(0))
    assert exc.value.code == "WRONG_PHASE"


def test_start_transitions_to_playing_and_assigns_roles():
    """Tier 3.5: chaos role can be Vibe Coder / Rogue Consultant / Shadow
    Admin; release roles can be Developer / DevOps / QA / Scrum / CC."""
    room = _make_started_room(player_count=4)
    assert room.phase is Phase.PLAYING
    teams = [p.team for p in room.players.values()]
    assert teams.count("chaos_agents") == 1
    assert teams.count("release_team") == 3
    assert all(p.team in {"release_team", "chaos_agents"} for p in room.players.values())


def test_start_with_twelve_players_assigns_three_chaos():
    """Tier 1.5: 12-player rooms have exactly 3 chaos agents."""
    room = _make_started_room(player_count=12)
    teams = [p.team for p in room.players.values()]
    assert teams.count("chaos_agents") == 3
    assert teams.count("release_team") == 9


def test_start_with_seven_players_assigns_two_chaos():
    """Tier 1.5: 7..9 players -> 2 chaos."""
    room = _make_started_room(player_count=7)
    teams = [p.team for p in room.players.values()]
    assert teams.count("chaos_agents") == 2
    assert teams.count("release_team") == 5


def test_start_sets_timer_to_900():
    room = _make_started_room(player_count=2)
    assert room.remaining_seconds == 900.0


def test_start_places_players_on_map():
    room = _make_started_room(player_count=4)
    for p in room.players.values():
        assert 0 <= p.x <= 4800
        assert 0 <= p.y <= 3200


# --- apply_input + tick ----------------------------------------------------


def test_apply_input_updates_state():
    room = _make_started_room(player_count=2)
    any_player = next(iter(room.players.values()))
    room.apply_input(any_player.id, InputState(right=True))
    assert room.players[any_player.id].input_state.right is True


def test_tick_moves_player_right():
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x = 100.0
    room.apply_input(p.id, InputState(right=True))
    room.tick(0.1)  # NORMAL_SPEED * dt
    assert p.x == pytest.approx(100.0 + NORMAL_SPEED * 0.1)


def test_tick_clamps_at_map_borders():
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x = 4795.0
    room.apply_input(p.id, InputState(right=True))
    room.tick(1.0)  # tries NORMAL_SPEED px right → clamps at map edge 4800.
    assert p.x == 4800.0

    p.y = 5.0
    room.apply_input(p.id, InputState(right=False, up=True))
    room.tick(1.0)
    assert p.y == 0.0


def test_tick_diagonal_is_not_faster_than_axis():
    # Normalisierte Bewegung: Diagonal ≈ gleiche Geschwindigkeit wie axial.
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x, p.y = 400.0, 100.0
    room.apply_input(p.id, InputState(right=True, down=True))
    room.tick(0.1)
    dx, dy = p.x - 400.0, p.y - 100.0
    speed = (dx**2 + dy**2) ** 0.5
    assert speed == pytest.approx(NORMAL_SPEED * 0.1, abs=0.01)


def test_tick_decrements_timer():
    room = _make_started_room(player_count=2)
    room.tick(0.5)
    assert room.remaining_seconds == pytest.approx(899.5)


def test_tick_is_noop_in_lobby():
    room = GameRoom(code="ABCD")
    p1 = room.add_player("Sven")
    room.add_player("Max")
    room.apply_input(p1.id, InputState(right=True))
    start_x = p1.x
    room.tick(0.1)
    assert p1.x == start_x


# --- serialization accessors ----------------------------------------------


def test_public_state_excludes_secrets():
    room = _make_started_room(player_count=3)
    state = room.public_state()
    for player in state["players"]:
        assert "role" not in player
        assert "team" not in player
        assert "inputState" not in player
        assert "input_state" not in player


def test_private_role_returns_tuple():
    room = _make_started_room(player_count=2)
    any_id = next(iter(room.players))
    info = room.private_role_for(any_id)
    assert info.role in {"vibe_coder", "developer"}
    assert info.team in {"release_team", "chaos_agents"}
    assert info.description


# --- B2 additions: ENDED phase + reset + counters ------------------------


def test_phase_enum_has_ended():
    from app.game.models import Phase as _Phase

    assert _Phase.ENDED.value == "ended"


def test_new_room_has_default_stats():
    room = GameRoom(code="ABCD")
    assert room.release_progress == 0
    assert room.pipeline_stability == 100
    assert room.coffee_level == 100
    assert room.meeting_active_for == 0.0
    assert room.winner is None
    assert room.win_reason is None
    assert room.completed_tasks_by_player == {}
    assert room.triggered_sabotages_by_player == {}


def test_start_initializes_per_player_counters_and_stats():
    room = _make_started_room(player_count=4)
    assert room.release_progress == 0
    assert room.pipeline_stability == 100
    assert room.coffee_level == 100
    assert len(room.completed_tasks_by_player) == 4
    assert all(v == 0 for v in room.completed_tasks_by_player.values())
    assert set(room.completed_tasks_by_player.keys()) == set(room.players.keys())
    assert len(room.triggered_sabotages_by_player) == 4


def test_public_state_exposes_stats():
    room = _make_started_room(player_count=2)
    state = room.public_state()
    assert state["releaseProgress"] == 0
    assert state["pipelineStability"] == 100
    assert state["coffeeLevel"] == 100


def test_reset_for_new_round_returns_to_lobby():
    room = _make_started_room(player_count=3)
    # mess with some state to make sure reset clears it
    room.release_progress = 50
    room.pipeline_stability = 30
    room.coffee_level = 0
    room.meeting_active_for = 3.0
    room.winner = "chaos_agents"
    room.win_reason = "Die Pipeline ist tot."

    room.reset_for_new_round()

    assert room.phase is Phase.LOBBY
    assert room.release_progress == 0
    assert room.pipeline_stability == 100
    assert room.coffee_level == 100
    assert room.meeting_active_for == 0.0
    assert room.winner is None
    assert room.win_reason is None
    assert room.completed_tasks_by_player == {}
    assert room.triggered_sabotages_by_player == {}
    for p in room.players.values():
        assert p.role is None
        assert p.team is None
        assert p.x == 0.0
        assert p.y == 0.0


def test_reset_keeps_host_and_player_identities():
    room = _make_started_room(player_count=3)
    host_id_before = next(p.id for p in room.players.values() if p.is_host)
    all_ids_before = set(room.players.keys())

    room.reset_for_new_round()

    host_id_after = next(p.id for p in room.players.values() if p.is_host)
    assert host_id_after == host_id_before
    assert set(room.players.keys()) == all_ids_before


def test_reset_is_noop_in_lobby():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    room.reset_for_new_round()  # should not blow up
    assert room.phase is Phase.LOBBY


def test_start_after_reset_assigns_new_roles():
    room = _make_started_room(player_count=3)
    host_id = next(p.id for p in room.players.values() if p.is_host)
    room.reset_for_new_round()
    room.start(requesting_player_id=host_id, rng=random.Random(99))

    assert room.phase is Phase.PLAYING
    second_role_map = {p.id: p.role for p in room.players.values()}
    # New assignment happened (might by chance equal — allow either; but at least no Nones left).
    assert all(r is not None for r in second_role_map.values())


# --- B5 additions: movement speed modifiers -----------------------------


def test_default_speed_is_normal():
    from app.game.sabotages import NORMAL_SPEED

    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    assert room._current_speed_for(pid) == NORMAL_SPEED


def test_coffee_zero_applies_slow_speed():
    from app.game.sabotages import COFFEE_SLOW_SPEED

    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    room.coffee_level = 0
    assert room._current_speed_for(pid) == COFFEE_SLOW_SPEED


def test_meeting_active_applies_slow_speed():
    from app.game.sabotages import COFFEE_SLOW_SPEED

    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    room.meeting_active_for = 3.0
    assert room._current_speed_for(pid) == COFFEE_SLOW_SPEED


def test_both_effects_do_not_stack():
    from app.game.sabotages import COFFEE_SLOW_SPEED

    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    room.coffee_level = 0
    room.meeting_active_for = 3.0
    # Still exactly the same slow-speed, not lower.
    assert room._current_speed_for(pid) == COFFEE_SLOW_SPEED


def test_coffee_refill_restores_normal_speed():
    from app.game.sabotages import NORMAL_SPEED

    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    room.coffee_level = 0
    room.coffee_level = 100  # refilled
    assert room._current_speed_for(pid) == NORMAL_SPEED


def test_tick_movement_respects_slow_speed():

    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    from app.game.sabotages import COFFEE_SLOW_SPEED

    p.x, p.y = 400.0, 100.0
    room.apply_input(p.id, InputState(right=True))
    room.coffee_level = 0  # slow
    room.tick(0.1)
    assert p.x == pytest.approx(400.0 + COFFEE_SLOW_SPEED * 0.1)


# --- Demo mode -----------------------------------------------------------


def test_demo_mode_allows_single_player_start():
    room = GameRoom(code="DEMO")
    only = room.add_player("Sven")
    room.start(requesting_player_id=only.id, rng=random.Random(0), demo=True)
    assert room.phase is Phase.PLAYING


def test_demo_mode_assigns_vibe_coder_to_solo_player():
    room = GameRoom(code="DEMO")
    only = room.add_player("Sven")
    room.start(requesting_player_id=only.id, rng=random.Random(0), demo=True)
    assert room.players[only.id].role == "vibe_coder"
    assert room.players[only.id].team == "chaos_agents"


def test_demo_mode_with_two_players_uses_normal_role_assignment():
    """Tier 3.5: with 2 players, normal assignment kicks in — exactly one
    chaos (any chaos role variant) and one release (any release role)."""
    room = GameRoom(code="DEMO")
    a = room.add_player("Alice")
    room.add_player("Bob")
    room.start(requesting_player_id=a.id, rng=random.Random(0), demo=True)
    teams = sorted(p.team for p in room.players.values())
    assert teams == ["chaos_agents", "release_team"]


def test_non_demo_still_requires_two_players():
    room = GameRoom(code="DEMO")
    only = room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=only.id, rng=random.Random(0))
    assert exc.value.code == "NOT_ENOUGH_PLAYERS"


def test_demo_mode_with_zero_players_still_errors():
    """Edge case: a host who somehow starts after everyone left."""
    room = GameRoom(code="DEMO")
    # Manually craft an impossible state for the test.
    with pytest.raises(GameRoomError):
        room.start(requesting_player_id="nope", rng=random.Random(0), demo=True)


# --- Reconnect ---


def test_mark_disconnected_keeps_player_in_room():
    room = _make_started_room(player_count=3)
    pid = next(iter(room.players))
    room.mark_disconnected(pid)
    assert pid in room.players
    assert room.players[pid].is_connected is False
    assert room.players[pid].disconnected_at_monotonic is not None


def test_mark_disconnected_releases_task_holds():
    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    p = room.players[pid]
    # Move player onto the task so hold_start succeeds.
    task_x, task_y = room.task_position("review_pr")
    p.x, p.y = task_x, task_y
    room.apply_task_hold_start(pid, "review_pr")
    assert pid in room.tasks["review_pr"].per_player_progress
    room.mark_disconnected(pid)
    assert pid not in room.tasks["review_pr"].per_player_progress


def test_mark_disconnected_transfers_host():
    room = _make_started_room(player_count=3)
    host = next(p for p in room.players.values() if p.is_host)
    room.mark_disconnected(host.id)
    assert room.players[host.id].is_host is False
    other_hosts = [p for p in room.players.values() if p.is_host and p.id != host.id]
    assert len(other_hosts) == 1


def test_mark_reconnected_within_grace_restores():
    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    room.mark_disconnected(pid)
    p = room.mark_reconnected(pid)
    assert p.is_connected is True
    assert p.disconnected_at_monotonic is None


def test_mark_reconnected_after_grace_raises():
    import time

    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    room.mark_disconnected(pid)
    # Force disconnect timestamp into the past.
    room.players[pid].disconnected_at_monotonic = time.monotonic() - 60
    with pytest.raises(GameRoomError) as exc:
        room.mark_reconnected(pid)
    assert exc.value.code == "REJOIN_NOT_AVAILABLE"


def test_mark_reconnected_unknown_player_raises():
    room = _make_started_room(player_count=2)
    with pytest.raises(GameRoomError):
        room.mark_reconnected("nonexistent")


def test_mark_reconnected_already_connected_raises():
    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    with pytest.raises(GameRoomError) as exc:
        room.mark_reconnected(pid)
    assert exc.value.code == "REJOIN_NOT_AVAILABLE"


def test_disconnected_player_input_ignored():
    room = _make_started_room(player_count=2)
    pid = next(iter(room.players))
    p = room.players[pid]
    initial_x = p.x
    room.mark_disconnected(pid)
    room.apply_input(pid, InputState(right=True))
    room.tick(0.5)
    assert p.x == initial_x  # didn't move


def test_sweep_removes_after_grace():
    import time

    room = _make_started_room(player_count=3)
    pid = next(iter(room.players))
    room.mark_disconnected(pid)
    # Force timestamp into past.
    room.players[pid].disconnected_at_monotonic = time.monotonic() - 60
    room.tick(0.05)
    assert pid not in room.players


def test_public_state_includes_isconnected():
    room = _make_started_room(player_count=2)
    state = room.public_state()
    for p in state["players"]:
        assert p["isConnected"] is True


def test_reset_restores_isconnected():
    room = _make_started_room(player_count=3)
    pid = next(iter(room.players))
    room.mark_disconnected(pid)
    room.reset_for_new_round()
    assert room.players[pid].is_connected is True
    assert room.players[pid].disconnected_at_monotonic is None


# --- Multi-map: set_map + map_id ----------------------------------------


def test_new_room_uses_default_map_id():
    room = GameRoom(code="MAPS")
    assert room.map_id == "default"


def test_new_room_with_small_map_id_uses_small_map():
    from app.game.game_map import discover_maps

    registry = discover_maps()
    small = registry["small"]
    room = GameRoom(code="MAPS", game_map=small, map_id="small")
    assert room.map_id == "small"
    assert room.map.name == "small-arena"
    # War-room bounds reflect the small map (2400x1600 world, war_room at
    # (1200, 800)..(2400, 1600)).
    x_min, y_min, x_max, y_max = room._war_room_bounds
    assert (x_min, y_min, x_max, y_max) == (1200, 800, 2400, 1600)


def test_set_map_happy_path_swaps_walls_and_anchors():
    from app.game.game_map import discover_maps

    registry = discover_maps()
    room = GameRoom(code="MAPS")
    host = room.add_player("Sven")
    walls_before = list(room._walls)
    anchors_before = dict(room._task_position)

    room.set_map(requesting_player_id=host.id, map_id="small", registry=registry)

    assert room.map_id == "small"
    assert room.map.name == "small-arena"
    assert room._walls != walls_before
    assert room._task_position != anchors_before
    # War-room bounds switched to the small map's war_room.
    assert room._war_room_bounds == (1200, 800, 2400, 1600)


def test_set_map_rejects_non_host():
    from app.game.game_map import discover_maps

    registry = discover_maps()
    room = GameRoom(code="MAPS")
    room.add_player("Sven")
    second = room.add_player("Max")
    with pytest.raises(GameRoomError) as exc:
        room.set_map(requesting_player_id=second.id, map_id="small", registry=registry)
    assert exc.value.code == "NOT_HOST"


def test_set_map_rejects_outside_lobby():
    from app.game.game_map import discover_maps

    registry = discover_maps()
    room = _make_started_room(player_count=4)
    host_id = next(p.id for p in room.players.values() if p.is_host)
    with pytest.raises(GameRoomError) as exc:
        room.set_map(requesting_player_id=host_id, map_id="small", registry=registry)
    assert exc.value.code == "WRONG_PHASE"


def test_set_map_rejects_unknown_id():
    from app.game.game_map import discover_maps

    registry = discover_maps()
    room = GameRoom(code="MAPS")
    host = room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.set_map(requesting_player_id=host.id, map_id="ghost-town", registry=registry)
    assert exc.value.code == "UNKNOWN_MAP"
