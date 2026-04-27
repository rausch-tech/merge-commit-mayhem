extends Node3D

# Game world. Spawned from main.gd after the server moves the room into PLAYING.
# Owns the WSClient handed over by main.gd and drives game-state syncing,
# multi-player rendering, camera-follow, HUD updates, and the pause menu.

const CHARACTER_SCENE: PackedScene = preload("res://scenes/character.tscn")
const HUD_SCENE: PackedScene = preload("res://scenes/hud.tscn")
const PAUSE_SCENE: PackedScene = preload("res://scenes/pause_menu.tscn")
const MAIN_SCENE: String = "res://scenes/main.tscn"

# Camera placement (Godot units, relative to player).
const CAMERA_OFFSET: Vector3 = Vector3(0, 28, 22)
const CAMERA_LERP_SPEED: float = 6.0

# State (set by main.gd before scene is added to the tree)
var ws_client: WSClient
var player_id: String = ""
var is_host: bool = false
var map_data: Dictionary = {}
var role_info: Dictionary = {}
var initial_state: Dictionary = {}

# Runtime
var _world_root: Node3D
var _input_sender: InputSender
var _camera: Camera3D
var _camera_rig: Node3D
var _hud: CanvasLayer
var _pause_menu: CanvasLayer
var _players_by_id: Dictionary = {}
var _world_initialized: bool = false
var _last_state: Dictionary = {}

func _ready() -> void:
	if ws_client == null:
		push_error("world.gd: ws_client must be set before _ready()")
		_return_to_main()
		return

	_world_root = MapBuilder.build(map_data)
	add_child(_world_root)

	_camera_rig = Node3D.new()
	_camera_rig.name = "CameraRig"
	add_child(_camera_rig)
	_camera = Camera3D.new()
	_camera.projection = Camera3D.PROJECTION_PERSPECTIVE
	_camera.fov = 38
	_camera.position = CAMERA_OFFSET
	_camera.look_at(Vector3.ZERO, Vector3.UP)
	_camera.current = true
	_camera_rig.add_child(_camera)

	_input_sender = InputSender.new()
	_input_sender.name = "InputSender"
	add_child(_input_sender)
	_input_sender.attach(ws_client)
	_input_sender.set_enabled(true)

	# WSClient may already be attached to us (main.gd reparented it).
	if ws_client.get_parent() != self and ws_client.get_parent() != null:
		ws_client.get_parent().remove_child(ws_client)
		add_child(ws_client)
	elif ws_client.get_parent() == null:
		add_child(ws_client)
	if not ws_client.message_received.is_connected(_on_message):
		ws_client.message_received.connect(_on_message)
	if not ws_client.disconnected.is_connected(_on_disconnected):
		ws_client.disconnected.connect(_on_disconnected)

	_hud = HUD_SCENE.instantiate() as CanvasLayer
	add_child(_hud)
	if _hud.has_method("set_player_id"):
		_hud.call("set_player_id", player_id)
	if _hud.has_method("set_role_info"):
		_hud.call("set_role_info", role_info)
	if _hud.has_method("set_map_name"):
		_hud.call("set_map_name", str(map_data.get("name", "?")))

	# Apply initial game state if provided
	if not initial_state.is_empty():
		_apply_state(initial_state)

func _process(delta: float) -> void:
	# Camera follow: aim CameraRig at the local player's position.
	var anchor: Vector3 = _local_player_position()
	var current := _camera_rig.position
	var t = clamp(CAMERA_LERP_SPEED * delta, 0.0, 1.0)
	_camera_rig.position = current.lerp(anchor, t)

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var key_event := event as InputEventKey
		if key_event.keycode == KEY_ESCAPE:
			_toggle_pause_menu()

func _on_message(type_: String, payload: Dictionary) -> void:
	match type_:
		Protocol.TYPE_GAME_STATE:
			_apply_state(payload)
		Protocol.TYPE_LOBBY_STATE:
			# Could happen on return-to-lobby; bounce back to main.
			_return_to_main()
		Protocol.TYPE_PRIVATE_ROLE:
			role_info = payload.duplicate()
			if _hud and _hud.has_method("set_role_info"):
				_hud.call("set_role_info", role_info)
		_:
			# Many other message types (private_state, voting_result, etc.) —
			# the demo doesn't render them but logs help debugging.
			pass

func _on_disconnected() -> void:
	push_warning("world: disconnected — returning to main")
	_return_to_main()

func _apply_state(state: Dictionary) -> void:
	_last_state = state
	var phase := str(state.get("phase", ""))
	if phase == Protocol.PHASE_ENDED:
		_return_to_main()
		return

	# Players
	var seen_ids: Dictionary = {}
	var players_array: Array = state.get("players", [])
	for p in players_array:
		var pid := str(p.get("id", ""))
		if pid == "":
			continue
		seen_ids[pid] = true
		var x: float = float(p.get("x", 0))
		var y: float = float(p.get("y", 0))
		var name_str: String = str(p.get("name", "?"))
		var color_hex: String = str(p.get("color", "#888888"))
		var is_alive: bool = bool(p.get("isAlive", true))
		if _players_by_id.has(pid):
			var existing: Node3D = _players_by_id[pid]
			existing.call("set_player_data", name_str, color_hex, is_alive)
			existing.call("push_target", x, y)
		else:
			var ch: Node3D = CHARACTER_SCENE.instantiate() as Node3D
			ch.call("setup", pid, name_str, color_hex, is_alive, pid == player_id)
			# Set initial position before adding so we don't slide in from origin.
			ch.position = Protocol.server_to_world(x, y)
			add_child(ch)
			ch.global_position = Protocol.server_to_world(x, y)
			ch.call("push_target", x, y)
			_players_by_id[pid] = ch

	# Despawn any players that are no longer in the snapshot
	for old_id in _players_by_id.keys():
		if not seen_ids.has(old_id):
			var ch: Node3D = _players_by_id[old_id]
			ch.queue_free()
			_players_by_id.erase(old_id)

	# HUD update
	if _hud and _hud.has_method("apply_game_state"):
		_hud.call("apply_game_state", state)

	# On first state apply: snap camera onto local player so we don't drift in.
	if not _world_initialized:
		var anchor := _local_player_position()
		_camera_rig.position = anchor
		_world_initialized = true

func _local_player_position() -> Vector3:
	if _players_by_id.has(player_id):
		var ch: Node3D = _players_by_id[player_id]
		return ch.global_position
	return Vector3.ZERO

func _toggle_pause_menu() -> void:
	if _pause_menu == null:
		_pause_menu = PAUSE_SCENE.instantiate() as CanvasLayer
		_pause_menu.set("is_host", is_host)
		add_child(_pause_menu)
		if _pause_menu.has_signal("leave_requested"):
			_pause_menu.connect("leave_requested", _on_leave_requested)
		if _pause_menu.has_signal("close_requested"):
			_pause_menu.connect("close_requested", _on_pause_close)
		if _pause_menu.has_signal("end_round_requested"):
			_pause_menu.connect("end_round_requested", _on_end_round_requested)
	else:
		_on_pause_close()

func _on_pause_close() -> void:
	if _pause_menu != null:
		_pause_menu.queue_free()
		_pause_menu = null

func _on_leave_requested() -> void:
	if ws_client != null:
		ws_client.close()
	_return_to_main()

func _on_end_round_requested() -> void:
	if ws_client != null and is_host:
		ws_client.send(Protocol.TYPE_RETURN_TO_LOBBY, {})
	# Server will eventually send lobby_state — we then return to main on its trigger.

func _return_to_main() -> void:
	# Tear down the world cleanly and load main.tscn fresh.
	get_tree().change_scene_to_file(MAIN_SCENE)
