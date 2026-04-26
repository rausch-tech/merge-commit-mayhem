"""Shared pytest helpers."""

from app.game.game_room import GameRoom
from app.game.sabotages import sabotage_by_id


def snap_to_object_for_sabotage(room: GameRoom, player_id: str, sabotage_id: str) -> None:
    """Tier 2.7 rework: position the player on the first task anchor whose
    object_type matches one of the sabotage's allowed trigger types. No-op for
    maps without typed anchors (legacy "from anywhere" path stays open).

    Tests that need apply_sabotage to succeed should call this on the chaos
    player; tests that intentionally exercise the proximity gate should NOT
    call it and assert ``NOT_NEAR_OBJECT`` instead.
    """
    sab = sabotage_by_id(sabotage_id)
    allowed = set(sab.trigger_object_types)
    if not allowed:
        return
    for anchor in room.map.task_anchors:
        if anchor.object_type and anchor.object_type in allowed:
            player = room.players[player_id]
            player.x = anchor.x
            player.y = anchor.y
            return


def snap_to_any_object(room: GameRoom, player_id: str) -> None:
    """Position the player on the first typed task anchor (any object_type).
    Useful when the test triggers many sabotages and just wants to satisfy
    *some* proximity check without caring which one."""
    for anchor in room.map.task_anchors:
        if anchor.object_type:
            player = room.players[player_id]
            player.x = anchor.x
            player.y = anchor.y
            return
