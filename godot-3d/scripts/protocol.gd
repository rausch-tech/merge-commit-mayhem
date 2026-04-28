class_name Protocol
extends RefCounted

# Mirror der wichtigsten Werte aus app/protocol.py und docs/PROTOCOL.md.

const TICK_HZ: int = 20
const TICK_INTERVAL_MS: int = 50
const PLAYER_COLLISION_RADIUS: float = 20.0
const TASK_INTERACTION_RADIUS: float = 40.0

# Server world is 4800x3200 server-pixels. Godot world units scale down for nicer
# camera handling and physics. 1 server-pixel = WORLD_SCALE Godot-units.
const WORLD_SCALE: float = 0.01
const SERVER_MAP_DEFAULT_WIDTH: float = 4800.0
const SERVER_MAP_DEFAULT_HEIGHT: float = 3200.0

# Outgoing message types
const TYPE_JOIN_ROOM: String = "join_room"
const TYPE_REJOIN: String = "rejoin"
const TYPE_START_GAME: String = "start_game"
const TYPE_PLAYER_INPUT: String = "player_input"
const TYPE_TASK_HOLD_START: String = "task_hold_start"
const TYPE_TASK_HOLD_STOP: String = "task_hold_stop"
const TYPE_MINI_GAME_INPUT: String = "mini_game_input"
const TYPE_RETURN_TO_LOBBY: String = "return_to_lobby"
const TYPE_SELECT_MAP: String = "select_map"
const TYPE_SET_PREFERRED_ROLE: String = "set_preferred_role"
const TYPE_ADD_BOT: String = "add_bot"
const TYPE_REMOVE_BOT: String = "remove_bot"
const TYPE_USE_ABILITY: String = "use_ability"
const TYPE_TRIGGER_SABOTAGE: String = "trigger_sabotage"
const TYPE_REPAIR_SABOTAGE: String = "repair_sabotage"
const TYPE_TRIGGER_TAKEDOWN: String = "trigger_takedown"
const TYPE_REPORT_BODY: String = "report_body"
const TYPE_USE_VENT: String = "use_vent"
const TYPE_CALL_EMERGENCY_MEETING: String = "call_emergency_meeting"
const TYPE_CAST_VOTE: String = "cast_vote"
const TYPE_SKIP_VOTE: String = "skip_vote"

# Incoming message types
const TYPE_ROOM_JOINED: String = "room_joined"
const TYPE_LOBBY_STATE: String = "lobby_state"
const TYPE_GAME_STATE: String = "game_state"
const TYPE_PRIVATE_ROLE: String = "private_role"
const TYPE_PRIVATE_STATE: String = "private_state"
const TYPE_VOTING_RESULT: String = "voting_result"
const TYPE_GAME_ENDED: String = "game_ended"
const TYPE_MINI_GAME_STARTED: String = "mini_game_started"
const TYPE_MINI_GAME_STATE: String = "mini_game_state"
const TYPE_MINI_GAME_COMPLETED: String = "mini_game_completed"
const TYPE_ERROR: String = "error"

# Phases (mirror server's Phase enum)
const PHASE_LOBBY: String = "lobby"
const PHASE_PLAYING: String = "playing"
const PHASE_MEETING: String = "meeting"
const PHASE_ENDED: String = "ended"

static func envelope(type_: String, payload: Dictionary) -> String:
	return JSON.stringify({"type": type_, "payload": payload})

static func server_to_world(server_x: float, server_y: float) -> Vector3:
	# Map server (x,y) on a 2D world plane → Godot (x, 0, z). Y axis depth = server-Y.
	return Vector3(server_x * WORLD_SCALE, 0.0, server_y * WORLD_SCALE)
