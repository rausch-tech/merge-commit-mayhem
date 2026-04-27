extends Node3D

# Game world. Spawned from main.gd after the server moves the room into PLAYING.
# Owns the WSClient handed over by main.gd and drives game-state syncing,
# multi-player rendering, camera-follow, HUD updates, and the pause menu.

const CHARACTER_SCENE: PackedScene = preload("res://scenes/character.tscn")
const HUD_SCENE: PackedScene = preload("res://scenes/hud.tscn")
const PAUSE_SCENE: PackedScene = preload("res://scenes/pause_menu.tscn")
const MAIN_SCENE: String = "res://scenes/main.tscn"

# Audio — stings are one-shot 2D players for game-wide events. Footsteps
# live on each Character (3D positional). No ambient loop — Kenney's
# computer-noise loop was too "dülülüut" to keep running during play.
const STING_ROLE_REVEAL: AudioStream = preload("res://assets/audio/sting/role_reveal.ogg")
const STING_MEETING: AudioStream = preload("res://assets/audio/sting/meeting.ogg")
const STING_KILL: AudioStream = preload("res://assets/audio/sting/kill.ogg")
const STING_TASK_COMPLETE: AudioStream = preload("res://assets/audio/sting/task_complete.ogg")
const STING_VOLUME_DB: float = -10.0

# Camera placement (Godot units, relative to player). Tuned so the player
# fills a noticeable chunk of the screen and only ~one room is visible at a
# time — matches the close-up feel of the 2D online client.
const CAMERA_OFFSET: Vector3 = Vector3(0, 10, 8)
const CAMERA_LERP_SPEED: float = 6.0
# Pitch from horizontal: atan2(offset.y, offset.z) = atan2(10, 8) ≈ 51.34°.
const CAMERA_PITCH_RAD: float = -0.8961  # = -deg_to_rad(51.34)

# Demo mode: when true, camera is parked above the map center, orthographic,
# showing all rooms at once (screenshots / team presentations). When false,
# camera follows the local player. Toggleable via set_camera_mode().
@export var aerial_demo_camera: bool = false

# State (set by main.gd before scene is added to the tree)
var ws_client: WSClient
var player_id: String = ""
var is_host: bool = false
var map_data: Dictionary = {}
var role_info: Dictionary = {}
var initial_state: Dictionary = {}
# Per-Owner-Stream (coffeeEnergy, coffeeMax, abilityUsed, takedownCooldownRemaining).
# Tickt nicht jeden Frame, sondern nur wenn sich was aendert. Cached fuers HUD
# zwischen den Updates.
var private_state: Dictionary = {}

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
var _sting_player: AudioStreamPlayer
var _last_phase: String = ""
var _alive_state: Dictionary = {}  # pid → bool, tracks transitions for kill sting
var _role_sting_played: bool = false

func _ready() -> void:
	if ws_client == null:
		push_error("world.gd: ws_client must be set before _ready()")
		_return_to_main()
		return

	print("[world] _ready map=", map_data.get("name", "?"), " rooms=", map_data.get("rooms", []).size())
	_world_root = MapBuilder.build(map_data)
	print("[world] map built, child count=", _world_root.get_child_count())
	add_child(_world_root)

	_camera_rig = Node3D.new()
	_camera_rig.name = "CameraRig"
	add_child(_camera_rig)
	_camera = Camera3D.new()
	_setup_camera()
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

	_sting_player = AudioStreamPlayer.new()
	_sting_player.name = "StingPlayer"
	_sting_player.volume_db = STING_VOLUME_DB
	add_child(_sting_player)
	if _hud.has_method("set_player_id"):
		_hud.call("set_player_id", player_id)
	if _hud.has_method("set_role_info"):
		_hud.call("set_role_info", role_info)
	if _hud.has_method("set_map_name"):
		_hud.call("set_map_name", str(map_data.get("name", "?")))
	# Initial private_state (coffee-Bar) wenn Demo-Mode oder Reconnect schon
	# einen mitgegeben hat. Live-Server pusht spaeter via TYPE_PRIVATE_STATE.
	if not private_state.is_empty() and _hud.has_method("apply_private_state"):
		_hud.call("apply_private_state", private_state)

	# Apply initial game state if provided
	if not initial_state.is_empty():
		_apply_state(initial_state)
		print("[world] applied initial state, players=", _players_by_id.size())
		for pid in _players_by_id:
			var ch: Node3D = _players_by_id[pid]
			print("[world]   player ", pid, " at ", ch.global_position)

func _process(delta: float) -> void:
	# In aerial demo-camera mode the rig stays parked at map center.
	if aerial_demo_camera:
		return
	# Camera follow: prefer local player, fall back to any player so we
	# never sit at (0,0,0) staring into the void if our id is missing.
	var ch_anchor: Node3D = null
	if _players_by_id.has(player_id):
		ch_anchor = _players_by_id[player_id]
	elif not _players_by_id.is_empty():
		ch_anchor = _players_by_id[_players_by_id.keys()[0]]
	if ch_anchor == null:
		return
	var anchor: Vector3 = ch_anchor.global_position
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
			# After state apply, ensure camera reaches local player even if first
			# few states arrived without our id (spectator/late-join recovery).
			if not _world_initialized and not aerial_demo_camera and _players_by_id.has(player_id):
				var ch_local: Node3D = _players_by_id[player_id]
				_camera_rig.position = ch_local.global_position
				_world_initialized = true
				print("[world] late camera-snap to local player at ", ch_local.global_position)
		Protocol.TYPE_LOBBY_STATE:
			# Could happen on return-to-lobby; bounce back to main.
			_return_to_main()
		Protocol.TYPE_PRIVATE_ROLE:
			role_info = payload.duplicate()
			if _hud and _hud.has_method("set_role_info"):
				_hud.call("set_role_info", role_info)
			# Server may resend role on reconnect — only sting once.
			if not _role_sting_played:
				_play_sting(STING_ROLE_REVEAL)
				_role_sting_played = true
		Protocol.TYPE_PRIVATE_STATE:
			# Per-Owner-Stream — Coffee-Energy + Cooldowns. HUD zeigt aktuell
			# nur die Coffee-Bar; Ability/Takedown-UI kommen in Tier 4.7/4.10.
			private_state = payload.duplicate()
			if _hud and _hud.has_method("apply_private_state"):
				_hud.call("apply_private_state", private_state)
		_:
			# Voting/meeting/mini-game etc. — Tier 4.6+ rendert sie, vorher
			# fallen sie hier durch. Logs auf Debugging-Bedarf nicht hier
			# anwerfen, sonst flutet das die Konsole bei 20 Hz.
			pass

func _on_disconnected() -> void:
	push_warning("world: disconnected — returning to main")
	_return_to_main()

func _apply_state(state: Dictionary) -> void:
	_last_state = state
	var phase := str(state.get("phase", ""))
	# Phase-transition stings — meeting and kill detection happen here so
	# we react in lockstep with the authoritative server state.
	if phase != _last_phase:
		if phase == Protocol.PHASE_MEETING and _last_phase != "":
			_play_sting(STING_MEETING)
		_last_phase = phase
	if phase == Protocol.PHASE_ENDED:
		_return_to_main()
		return

	# Players
	var seen_ids: Dictionary = {}
	var players_array: Array = state.get("players", [])
	var any_kill: bool = false
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
		# Death transition — sting once (collected, plays after the loop).
		if _alive_state.has(pid) and _alive_state[pid] and not is_alive:
			any_kill = true
		_alive_state[pid] = is_alive
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

	if any_kill:
		_play_sting(STING_KILL)

	# HUD update
	if _hud and _hud.has_method("apply_game_state"):
		_hud.call("apply_game_state", state)

	# On first state apply: snap camera onto local player so we don't drift in.
	# Only mark "initialized" once we actually found the local player — otherwise
	# we'd skip the snap forever if the first state arrived without a positioned
	# local player (e.g. spectator/late-join scenarios).
	if aerial_demo_camera:
		_world_initialized = true
	elif not _world_initialized:
		if _players_by_id.has(player_id):
			var ch_local: Node3D = _players_by_id[player_id]
			_camera_rig.position = ch_local.global_position
			_world_initialized = true
			print("[world] camera snapped to local player ", player_id, " at ", ch_local.global_position)
		else:
			print("[world] WARN: no local player ", player_id, " in players=", _players_by_id.keys())

func _local_player_position() -> Vector3:
	if _players_by_id.has(player_id):
		var ch: Node3D = _players_by_id[player_id]
		return ch.global_position
	return Vector3.ZERO

func _setup_camera() -> void:
	if aerial_demo_camera:
		# Aerial demo view — orthographic top-down at map center.
		var size_dict: Dictionary = map_data.get("size", {})
		var map_w: float = float(size_dict.get("width", 4800)) * Protocol.WORLD_SCALE
		var map_h: float = float(size_dict.get("height", 3200)) * Protocol.WORLD_SCALE
		_camera_rig.position = Vector3(map_w * 0.5, 0.0, map_h * 0.5)
		_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
		# size is the vertical extent. No padding — frame the map exactly so we
		# don't see the void beyond the perimeter walls.
		_camera.size = map_h
		_camera.position = Vector3(0, 50, 0)
		_camera.rotation = Vector3(-PI * 0.5, 0.0, 0.0)  # straight down
		_camera.near = 0.1
		_camera.far = 200.0
	else:
		_camera.projection = Camera3D.PROJECTION_PERSPECTIVE
		_camera.fov = 55
		_camera.position = CAMERA_OFFSET
		_camera.rotation = Vector3(CAMERA_PITCH_RAD, 0.0, 0.0)
	_camera.current = true

func set_camera_mode(aerial: bool) -> void:
	aerial_demo_camera = aerial
	if _camera != null:
		_setup_camera()

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

func _play_sting(stream: AudioStream) -> void:
	if _sting_player == null or stream == null:
		return
	_sting_player.stream = stream
	_sting_player.play()
