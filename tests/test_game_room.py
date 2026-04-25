import random

import pytest

from app.game.game_room import GameRoom, GameRoomError, MAX_PLAYERS
from app.game.models import InputState, Phase


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


# --- start() ---------------------------------------------------------------


def _make_started_room(player_count: int = 3) -> GameRoom:
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


def test_start_requires_min_two_players():
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
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
    room = _make_started_room(player_count=3)
    assert room.phase is Phase.PLAYING
    roles = [p.role for p in room.players.values()]
    assert roles.count("vibe_coder") == 1
    assert roles.count("developer") == 2
    assert all(p.team in {"release_team", "chaos_agents"} for p in room.players.values())


def test_start_sets_timer_to_720():
    room = _make_started_room(player_count=2)
    assert room.remaining_seconds == 720.0


def test_start_places_players_on_map():
    room = _make_started_room(player_count=4)
    for p in room.players.values():
        assert 0 <= p.x <= 2400
        assert 0 <= p.y <= 1600


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
    room.tick(0.1)  # 15 px bei 150 px/s
    assert p.x == pytest.approx(115.0)


def test_tick_clamps_at_map_borders():
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x = 2395.0
    room.apply_input(p.id, InputState(right=True))
    room.tick(1.0)  # Versucht 150 px rechts → wird auf 2400 geclampt.
    assert p.x == 2400.0

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
    assert speed == pytest.approx(15.0, abs=0.01)


def test_tick_decrements_timer():
    room = _make_started_room(player_count=2)
    room.tick(0.5)
    assert room.remaining_seconds == pytest.approx(719.5)


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
    assert room.incident_count == 0
    assert room.meeting_active_for == 0.0
    assert room.winner is None
    assert room.win_reason is None
    assert room.completed_tasks_by_player == {}
    assert room.triggered_sabotages_by_player == {}


def test_start_initializes_per_player_counters_and_stats():
    room = _make_started_room(player_count=3)
    assert room.release_progress == 0
    assert room.pipeline_stability == 100
    assert room.coffee_level == 100
    assert len(room.completed_tasks_by_player) == 3
    assert all(v == 0 for v in room.completed_tasks_by_player.values())
    assert set(room.completed_tasks_by_player.keys()) == set(room.players.keys())
    assert len(room.triggered_sabotages_by_player) == 3


def test_public_state_exposes_stats():
    room = _make_started_room(player_count=2)
    state = room.public_state()
    assert state["releaseProgress"] == 0
    assert state["pipelineStability"] == 100
    assert state["coffeeLevel"] == 100
    assert state["incidentCount"] == 0


def test_reset_for_new_round_returns_to_lobby():
    room = _make_started_room(player_count=3)
    host_id = next(p.id for p in room.players.values() if p.is_host)

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
    first_role_map = {p.id: p.role for p in room.players.values()}

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
    from app.game.sabotages import COFFEE_SLOW_SPEED
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x, p.y = 400.0, 100.0
    room.apply_input(p.id, InputState(right=True))
    room.coffee_level = 0  # slow
    room.tick(0.1)
    # 80 px/s * 0.1 s = 8 px, not 15 px.
    assert p.x == pytest.approx(408.0)


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
    room = GameRoom(code="DEMO")
    a = room.add_player("Alice")
    b = room.add_player("Bob")
    room.start(requesting_player_id=a.id, rng=random.Random(0), demo=True)
    roles = sorted(p.role for p in room.players.values())
    assert roles == ["developer", "vibe_coder"]


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
