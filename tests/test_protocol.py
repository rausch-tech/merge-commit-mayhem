import pytest
from pydantic import ValidationError

from app.protocol import (
    CallEmergencyMeeting,
    CastVote,
    ErrorMsg,
    GameEndedMsg,
    GameStateMsg,
    JoinRoom,
    LobbyStateMsg,
    PlayerInput,
    PrivateRoleMsg,
    PrivateStateMsg,
    ReportBody,
    ReturnToLobby,
    RoomJoinedMsg,
    SkipVote,
    StartGame,
    TaskHoldStart,
    TaskHoldStop,
    TriggerSabotage,
    TriggerTakedown,
    VotingResultMsg,
    parse_incoming,
)

# --- incoming parsing -------------------------------------------------------


def test_parse_join_room():
    raw = {"type": "join_room", "payload": {"roomCode": "ABCD", "playerName": "Sven"}}
    msg = parse_incoming(raw)
    assert isinstance(msg, JoinRoom)
    assert msg.payload.room_code == "ABCD"
    assert msg.payload.player_name == "Sven"


def test_parse_start_game():
    raw = {"type": "start_game", "payload": {}}
    msg = parse_incoming(raw)
    assert isinstance(msg, StartGame)


def test_parse_player_input():
    raw = {
        "type": "player_input",
        "payload": {"up": True, "down": False, "left": False, "right": True},
    }
    msg = parse_incoming(raw)
    assert isinstance(msg, PlayerInput)
    assert msg.payload.up is True
    assert msg.payload.right is True


def test_parse_rejects_unknown_type():
    with pytest.raises(ValidationError):
        parse_incoming({"type": "unknown_event", "payload": {}})


def test_parse_rejects_missing_type():
    with pytest.raises(ValidationError):
        parse_incoming({"payload": {}})


# --- outgoing serialization ------------------------------------------------


def test_room_joined_serializes_to_camel_case():
    msg = RoomJoinedMsg(room_code="ABCD", player_id="abc123", is_host=True)
    dumped = msg.model_dump(by_alias=True)
    assert dumped["roomCode"] == "ABCD"
    assert dumped["playerId"] == "abc123"
    assert dumped["isHost"] is True
    assert "map" in dumped  # map field is present (empty by default)


def test_lobby_state_serializes_to_camel_case():
    msg = LobbyStateMsg(
        room_code="ABCD",
        players=[
            {"id": "p1", "name": "Sven", "color": "#4ade80", "isHost": True},
        ],
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["roomCode"] == "ABCD"
    assert dumped["players"][0]["isHost"] is True


def test_game_state_serializes_to_camel_case():
    msg = GameStateMsg(
        phase="playing",
        remaining_seconds=598,
        players=[
            {"id": "p1", "name": "Sven", "x": 120.5, "y": 99.0, "color": "#4ade80", "isHost": True},
        ],
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["remainingSeconds"] == 598
    assert "phase" in dumped
    # `events` is part of the public envelope and defaults to an empty list.
    assert dumped["events"] == []


def test_game_state_carries_events_when_present():
    msg = GameStateMsg(
        phase="playing",
        remaining_seconds=598,
        players=[],
        events=[{"seq": 1, "severity": "info", "message": "Los geht's."}],
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["events"] == [{"seq": 1, "severity": "info", "message": "Los geht's."}]


def test_private_role_serializes_as_expected():
    msg = PrivateRoleMsg(
        role="vibe_coder",
        team="chaos_agents",
        description="Sabotier das Release.",
    )
    dumped = msg.model_dump(by_alias=True)
    # Tier 3.5: PrivateRoleMsg now carries role-card metadata too. Asserting
    # the core 4 fields keeps the contract test focused on what's wired.
    assert dumped["role"] == "vibe_coder"
    assert dumped["team"] == "chaos_agents"
    assert dumped["description"] == "Sabotier das Release."
    assert dumped["availableSabotages"] == []


def test_error_msg_serializes_correctly():
    msg = ErrorMsg(code="NOT_HOST", message="Only host can start.")
    dumped = msg.model_dump(by_alias=True)
    assert dumped == {"code": "NOT_HOST", "message": "Only host can start."}


# --- B7 additions: new incoming types + GameEndedMsg + PrivateRole extension


def test_parse_task_hold_start():
    raw = {"type": "task_hold_start", "payload": {"taskId": "fix_unit_tests"}}
    msg = parse_incoming(raw)
    assert isinstance(msg, TaskHoldStart)
    assert msg.payload.task_id == "fix_unit_tests"


def test_parse_task_hold_stop():
    raw = {"type": "task_hold_stop", "payload": {"taskId": "review_pr"}}
    msg = parse_incoming(raw)
    assert isinstance(msg, TaskHoldStop)
    assert msg.payload.task_id == "review_pr"


def test_parse_trigger_sabotage():
    raw = {"type": "trigger_sabotage", "payload": {"sabotageId": "ci_cd_red"}}
    msg = parse_incoming(raw)
    assert isinstance(msg, TriggerSabotage)
    assert msg.payload.sabotage_id == "ci_cd_red"


def test_parse_return_to_lobby_with_empty_payload():
    raw = {"type": "return_to_lobby", "payload": {}}
    msg = parse_incoming(raw)
    assert isinstance(msg, ReturnToLobby)


def test_private_role_default_available_sabotages_empty():
    msg = PrivateRoleMsg(role="developer", team="release_team", description="x")
    dumped = msg.model_dump(by_alias=True)
    assert dumped["availableSabotages"] == []


def test_private_role_with_available_sabotages():
    msg = PrivateRoleMsg(
        role="vibe_coder",
        team="chaos_agents",
        description="Sabotier.",
        available_sabotages=["ci_cd_red", "coffee_outage", "mandatory_meeting"],
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["availableSabotages"] == ["ci_cd_red", "coffee_outage", "mandatory_meeting"]


def test_game_ended_msg_serializes_to_camel():
    msg = GameEndedMsg(
        winner="release_team",
        reason="Release deployed.",
        players=[
            {
                "id": "p1",
                "name": "Sven",
                "role": "developer",
                "team": "release_team",
                "completedTasks": 5,
                "triggeredSabotages": 0,
            }
        ],
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["winner"] == "release_team"
    assert dumped["reason"] == "Release deployed."
    assert dumped["players"][0]["completedTasks"] == 5
    assert dumped["players"][0]["triggeredSabotages"] == 0


# --- VB additions: voting protocol models -----------------------------------


def test_parse_call_emergency_meeting():
    raw = {"type": "call_emergency_meeting", "payload": {}}
    msg = parse_incoming(raw)
    assert isinstance(msg, CallEmergencyMeeting)


def test_parse_cast_vote():
    raw = {"type": "cast_vote", "payload": {"targetPlayerId": "abc"}}
    msg = parse_incoming(raw)
    assert isinstance(msg, CastVote)
    assert msg.payload.target_player_id == "abc"


def test_parse_skip_vote_with_empty_payload():
    raw = {"type": "skip_vote", "payload": {}}
    msg = parse_incoming(raw)
    assert isinstance(msg, SkipVote)


def test_voting_result_default_dump():
    msg = VotingResultMsg()
    dumped = msg.model_dump(by_alias=True)
    assert dumped == {
        "removedPlayerId": "",
        "removedPlayerName": "",
        "wasChaosAgent": False,
        "tie": False,
        "skipped": False,
        "lastWords": "",
    }


def test_voting_result_with_eliminated_player():
    msg = VotingResultMsg(
        removed_player_id="p123",
        removed_player_name="Max",
        was_chaos_agent=True,
        tie=False,
        skipped=False,
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["removedPlayerId"] == "p123"
    assert dumped["wasChaosAgent"] is True


# --- Reconnect protocol ---


def test_parse_rejoin():
    raw = {"type": "rejoin", "payload": {"roomCode": "ABCD", "playerId": "abc"}}
    msg = parse_incoming(raw)
    from app.protocol import Rejoin

    assert isinstance(msg, Rejoin)
    assert msg.payload.room_code == "ABCD"
    assert msg.payload.player_id == "abc"


# --- Tier 2.1: Take-Down + Body-Report protocol -----------------------------


def test_parse_trigger_takedown_camel_case():
    raw = {"type": "trigger_takedown", "payload": {"targetPlayerId": "abc"}}
    msg = parse_incoming(raw)
    assert isinstance(msg, TriggerTakedown)
    assert msg.payload.target_player_id == "abc"


def test_parse_report_body_camel_case():
    raw = {"type": "report_body", "payload": {"bodyId": "deadbeef"}}
    msg = parse_incoming(raw)
    assert isinstance(msg, ReportBody)
    assert msg.payload.body_id == "deadbeef"


def test_private_state_msg_serializes_camel_case():
    msg = PrivateStateMsg(takedown_cooldown_remaining=12.5)
    dumped = msg.model_dump(by_alias=True)
    assert dumped["takedownCooldownRemaining"] == 12.5
    # Tier 3.5: per-viewer coffee + ability gating.
    assert "coffeeEnergy" in dumped
    assert "coffeeMax" in dumped
    assert "abilityUsed" in dumped


def test_private_state_msg_default_zero():
    msg = PrivateStateMsg()
    dumped = msg.model_dump(by_alias=True)
    assert dumped["takedownCooldownRemaining"] == 0.0
    assert dumped["coffeeEnergy"] == 100.0
    assert dumped["abilityUsed"] is False


def test_game_state_msg_bodies_default_empty_and_round_trip():
    msg = GameStateMsg(phase="playing", remaining_seconds=300, players=[])
    dumped = msg.model_dump(by_alias=True)
    assert "bodies" in dumped
    assert dumped["bodies"] == []

    body_payload = {
        "id": "bid",
        "x": 100.0,
        "y": 200.0,
        "color": "#facc15",
        "victimName": "Ada",
    }
    msg2 = GameStateMsg(
        phase="playing",
        remaining_seconds=300,
        players=[],
        bodies=[body_payload],
    )
    dumped2 = msg2.model_dump(by_alias=True)
    assert dumped2["bodies"] == [body_payload]


# --- Tier 1.2: incidents stat on the wire ----------------------------------


def test_game_state_msg_incidents_defaults_to_zero():
    msg = GameStateMsg(phase="playing", remaining_seconds=300, players=[])
    dumped = msg.model_dump(by_alias=True)
    assert "incidents" in dumped
    assert dumped["incidents"] == 0


def test_game_state_msg_incidents_round_trips_camel_case():
    msg = GameStateMsg(phase="playing", remaining_seconds=300, players=[], incidents=42)
    dumped = msg.model_dump(by_alias=True)
    assert dumped["incidents"] == 42

    # Re-parse via aliases (camelCase) to confirm the wire field name.
    rehydrated = GameStateMsg.model_validate(dumped)
    assert rehydrated.incidents == 42
