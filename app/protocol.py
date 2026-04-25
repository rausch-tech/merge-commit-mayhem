from typing import Annotated, Any, Literal, Union

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


IncomingMessage = Annotated[
    Union[
        JoinRoom,
        StartGame,
        PlayerInput,
        TaskHoldStart,
        TaskHoldStop,
        TriggerSabotage,
        ReturnToLobby,
    ],
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


class LobbyStateMsg(BaseModel):
    model_config = _camel_config()
    room_code: str
    players: list[dict[str, Any]]


class GameStateMsg(BaseModel):
    model_config = _camel_config()
    phase: str
    remaining_seconds: int
    release_progress: int = 0
    pipeline_stability: int = 100
    coffee_level: int = 100
    incident_count: int = 0
    players: list[dict[str, Any]]
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    sabotages: list[dict[str, Any]] = Field(default_factory=list)


class PrivateRoleMsg(BaseModel):
    model_config = _camel_config()
    role: str
    team: str
    description: str
    available_sabotages: list[str] = Field(default_factory=list)


class ErrorMsg(BaseModel):
    model_config = _camel_config()
    code: str
    message: str


class GameEndedMsg(BaseModel):
    model_config = _camel_config()
    winner: str
    reason: str
    players: list[dict[str, Any]]  # each: {id, name, role, team, completedTasks, triggeredSabotages}


def envelope(type_: str, payload: BaseModel) -> dict[str, Any]:
    """Wrap a payload model into the {type, payload} wire format."""
    return {"type": type_, "payload": payload.model_dump(by_alias=True)}
