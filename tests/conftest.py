"""Shared pytest helpers."""

from app.game.game_room import GameRoom


def snap_to_first_console(room: GameRoom, player_id: str) -> None:
    """Tier 2.7: position the player at the map's first sabotage console so
    `apply_sabotage` clears the proximity gate. No-op for maps without
    consoles (those keep the legacy "trigger from anywhere" behaviour).

    Tests that need to assert sabotage effects can call this on the chaos
    player; tests that intentionally exercise the proximity gate should NOT
    call it and assert ``NOT_NEAR_CONSOLE`` instead.
    """
    if not room.map.sabotage_consoles:
        return
    console = room.map.sabotage_consoles[0]
    player = room.players[player_id]
    player.x = console.x
    player.y = console.y
