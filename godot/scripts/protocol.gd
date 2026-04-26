class_name Protocol
extends RefCounted

const TICK_HZ: int = 20
const TICK_INTERVAL_MS: int = 50
const PLAYER_COLLISION_RADIUS: float = 20.0
const TASK_INTERACTION_RADIUS: float = 40.0

const TYPE_JOIN_ROOM: String = "join_room"
const TYPE_REJOIN: String = "rejoin"
const TYPE_PLAYER_INPUT: String = "player_input"

const TYPE_ROOM_JOINED: String = "room_joined"
const TYPE_LOBBY_STATE: String = "lobby_state"
const TYPE_GAME_STATE: String = "game_state"
const TYPE_PRIVATE_ROLE: String = "private_role"
const TYPE_PRIVATE_STATE: String = "private_state"
const TYPE_ERROR: String = "error"

static func envelope(type_: String, payload: Dictionary) -> String:
	return JSON.stringify({"type": type_, "payload": payload})
