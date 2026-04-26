from typing import (  # noqa: UP035 (Union needed for 3.9 compat via Pydantic)
    Annotated,
    Any,
    Literal,
)

from pydantic import BaseModel, ConfigDict, Discriminator, Field
from pydantic.alias_generators import to_camel


def _camel_config() -> ConfigDict:
    return ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


# --- incoming payloads ------------------------------------------------------


class JoinRoomPayload(BaseModel):
    model_config = _camel_config()
    room_code: str
    player_name: str


class StartGamePayload(BaseModel):
    model_config = _camel_config()
    demo: bool = False


class PlayerInputPayload(BaseModel):
    model_config = _camel_config()
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False


class JoinRoom(BaseModel):
    model_config = _camel_config()
    type: Literal["join_room"]
    payload: JoinRoomPayload


class StartGame(BaseModel):
    model_config = _camel_config()
    type: Literal["start_game"]
    payload: StartGamePayload = Field(default_factory=StartGamePayload)


class PlayerInput(BaseModel):
    model_config = _camel_config()
    type: Literal["player_input"]
    payload: PlayerInputPayload


class TaskHoldStartPayload(BaseModel):
    model_config = _camel_config()
    task_id: str


class TaskHoldStopPayload(BaseModel):
    model_config = _camel_config()
    task_id: str


class TriggerSabotagePayload(BaseModel):
    model_config = _camel_config()
    sabotage_id: str


class ReturnToLobbyPayload(BaseModel):
    model_config = _camel_config()


class TaskHoldStart(BaseModel):
    model_config = _camel_config()
    type: Literal["task_hold_start"]
    payload: TaskHoldStartPayload


class TaskHoldStop(BaseModel):
    model_config = _camel_config()
    type: Literal["task_hold_stop"]
    payload: TaskHoldStopPayload


class TriggerSabotage(BaseModel):
    model_config = _camel_config()
    type: Literal["trigger_sabotage"]
    payload: TriggerSabotagePayload


class ReturnToLobby(BaseModel):
    model_config = _camel_config()
    type: Literal["return_to_lobby"]
    payload: ReturnToLobbyPayload = Field(default_factory=ReturnToLobbyPayload)


class CallEmergencyMeetingPayload(BaseModel):
    model_config = _camel_config()


class CastVotePayload(BaseModel):
    model_config = _camel_config()
    target_player_id: str


class SkipVotePayload(BaseModel):
    model_config = _camel_config()


class CallEmergencyMeeting(BaseModel):
    model_config = _camel_config()
    type: Literal["call_emergency_meeting"]
    payload: CallEmergencyMeetingPayload = Field(default_factory=CallEmergencyMeetingPayload)


class CastVote(BaseModel):
    model_config = _camel_config()
    type: Literal["cast_vote"]
    payload: CastVotePayload


class SkipVote(BaseModel):
    model_config = _camel_config()
    type: Literal["skip_vote"]
    payload: SkipVotePayload = Field(default_factory=SkipVotePayload)


class RejoinPayload(BaseModel):
    model_config = _camel_config()
    room_code: str
    player_id: str


class Rejoin(BaseModel):
    model_config = _camel_config()
    type: Literal["rejoin"]
    payload: RejoinPayload


class TriggerTakedownPayload(BaseModel):
    model_config = _camel_config()
    target_player_id: str


class TriggerTakedown(BaseModel):
    model_config = _camel_config()
    type: Literal["trigger_takedown"]
    payload: TriggerTakedownPayload


class ReportBodyPayload(BaseModel):
    model_config = _camel_config()
    body_id: str


class ReportBody(BaseModel):
    model_config = _camel_config()
    type: Literal["report_body"]
    payload: ReportBodyPayload


class SelectMapPayload(BaseModel):
    model_config = _camel_config()
    map_id: str


class SelectMap(BaseModel):
    model_config = _camel_config()
    type: Literal["select_map"]
    payload: SelectMapPayload


class LeaveRoomPayload(BaseModel):
    model_config = _camel_config()


class LeaveRoom(BaseModel):
    model_config = _camel_config()
    type: Literal["leave_room"]
    payload: LeaveRoomPayload = Field(default_factory=LeaveRoomPayload)


class AbortRoundPayload(BaseModel):
    model_config = _camel_config()


class AbortRound(BaseModel):
    model_config = _camel_config()
    type: Literal["abort_round"]
    payload: AbortRoundPayload = Field(default_factory=AbortRoundPayload)


IncomingMessage = Annotated[
    JoinRoom
    | Rejoin
    | StartGame
    | PlayerInput
    | TaskHoldStart
    | TaskHoldStop
    | TriggerSabotage
    | ReturnToLobby
    | CallEmergencyMeeting
    | CastVote
    | SkipVote
    | TriggerTakedown
    | ReportBody
    | SelectMap
    | LeaveRoom
    | AbortRound,
    Discriminator("type"),
]


class _IncomingEnvelope(BaseModel):
    """Wrapper to trigger Pydantic's discriminated-union validation."""

    model_config = _camel_config()
    root: IncomingMessage


def parse_incoming(raw: dict[str, Any]) -> IncomingMessage:
    return _IncomingEnvelope(root=raw).root


# --- outgoing messages ------------------------------------------------------


class RoomJoinedMsg(BaseModel):
    model_config = _camel_config()
    room_code: str
    player_id: str
    is_host: bool
    map: dict[str, Any] = Field(default_factory=dict)


class LobbyStateMsg(BaseModel):
    model_config = _camel_config()
    room_code: str
    players: list[dict[str, Any]]
    available_maps: list[dict[str, Any]] = Field(default_factory=list)
    selected_map_id: str = ""
    map: dict[str, Any] = Field(default_factory=dict)


class GameStateMsg(BaseModel):
    model_config = _camel_config()
    phase: str
    remaining_seconds: int
    release_progress: int = 0
    pipeline_stability: int = 100
    coffee_level: int = 100
    incidents: int = 0
    players: list[dict[str, Any]]
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    sabotages: list[dict[str, Any]] = Field(default_factory=list)
    meeting: dict[str, Any] | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    bodies: list[dict[str, Any]] = Field(default_factory=list)


class PrivateRoleMsg(BaseModel):
    model_config = _camel_config()
    role: str
    team: str
    description: str
    available_sabotages: list[str] = Field(default_factory=list)


class PrivateStateMsg(BaseModel):
    model_config = _camel_config()
    takedown_cooldown_remaining: float = 0.0


class ErrorMsg(BaseModel):
    model_config = _camel_config()
    code: str
    message: str


class GameEndedMsg(BaseModel):
    model_config = _camel_config()
    winner: str
    reason: str
    players: list[
        dict[str, Any]
    ]  # each: {id, name, role, team, completedTasks, triggeredSabotages}


class VotingResultMsg(BaseModel):
    model_config = _camel_config()
    removed_player_id: str = ""
    removed_player_name: str = ""
    was_chaos_agent: bool = False
    tie: bool = False
    skipped: bool = False


def envelope(type_: str, payload: BaseModel) -> dict[str, Any]:
    """Wrap a payload model into the {type, payload} wire format."""
    return {"type": type_, "payload": payload.model_dump(by_alias=True)}
