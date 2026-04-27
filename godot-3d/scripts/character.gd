class_name Character
extends Node3D

# A renderable player character. Wraps the KayKit Dummy mesh + animations,
# applies a color tint via material override, and animates between Idle/Walking
# based on movement.
#
# The world.gd is responsible for:
#   - Calling push_target(server_x, server_y) when game_state arrives
#   - Calling set_player_data(name, color_hex, is_alive) on lobby_state
#   - Setting `is_self = true` for the local player so we can highlight it.

const DUMMY_SCENE: PackedScene = preload("res://assets/character/Dummy.glb")
const ANIM_SCENE: PackedScene = preload("res://assets/character/Rig_Medium_MovementBasic.glb")

# Movement smoothing — target is updated at 20 Hz, we lerp every frame.
const POSITION_LERP_SPEED: float = 14.0
const ROTATION_LERP_SPEED: float = 10.0
const MOVE_DEADZONE: float = 0.04
const NAMEPLATE_HEIGHT: float = 2.4

const COLOR_SELF_RING: Color = Color(0.30, 0.95, 0.50)

# Animation names tried in order; first match wins.
const ANIM_WALK_PRIORITY: Array = ["Walking_A", "Walking_B", "Walking_C", "Running_A", "Running_B"]
const ANIM_IDLE_PRIORITY: Array = ["T-Pose"]

@export var is_self: bool = false

var _player_id: String = ""
var _player_name: String = "?"
var _color_hex: String = "#888888"
var _is_alive: bool = true
var _target_pos: Vector3 = Vector3.ZERO
var _last_pos: Vector3 = Vector3.ZERO

var _dummy: Node3D
var _anim_player: AnimationPlayer
var _walk_anim: String = ""
var _idle_anim: String = ""
var _current_anim: String = ""
var _facing: float = 0.0
var _nameplate: Label3D
var _self_ring: MeshInstance3D

func setup(player_id: String, player_name: String, color_hex: String, is_alive: bool, is_self_: bool) -> void:
	_player_id = player_id
	_player_name = player_name
	_color_hex = color_hex
	_is_alive = is_alive
	is_self = is_self_

func _ready() -> void:
	_dummy = DUMMY_SCENE.instantiate() as Node3D
	add_child(_dummy)
	_dummy.scale = Vector3(0.55, 0.55, 0.55)  # KayKit characters scale nicely at ~0.55

	_anim_player = _dummy.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if _anim_player != null:
		_setup_animations(_anim_player)
		_idle_anim = _pick_animation(ANIM_IDLE_PRIORITY)
		_walk_anim = _pick_animation(ANIM_WALK_PRIORITY)
		if _idle_anim != "":
			_play_anim(_idle_anim)

	_apply_color_tint()
	_build_nameplate()
	_build_self_ring()
	# Start at target so we don't slide in from origin
	_dummy.position = Vector3.ZERO
	_last_pos = global_position

func push_target(server_x: float, server_y: float) -> void:
	_target_pos = Protocol.server_to_world(server_x, server_y)

func set_player_data(player_name: String, color_hex: String, is_alive: bool) -> void:
	var name_changed := player_name != _player_name
	var color_changed := color_hex != _color_hex
	var alive_changed := is_alive != _is_alive
	_player_name = player_name
	_color_hex = color_hex
	_is_alive = is_alive
	if name_changed:
		_update_nameplate_text()
	if color_changed and is_inside_tree():
		_apply_color_tint()
	if alive_changed and is_inside_tree():
		_apply_alive_state()

func _process(delta: float) -> void:
	# Position lerp
	var current := global_position
	var t = clamp(POSITION_LERP_SPEED * delta, 0.0, 1.0)
	global_position = current.lerp(_target_pos, t)

	# Movement detection (in world units / second)
	var moved := global_position - _last_pos
	var horiz := Vector2(moved.x, moved.z)
	_last_pos = global_position
	var moving: bool = horiz.length() > MOVE_DEADZONE * delta * POSITION_LERP_SPEED

	if moving:
		_facing = atan2(horiz.x, horiz.y)
		_dummy.rotation.y = lerp_angle(_dummy.rotation.y, _facing, ROTATION_LERP_SPEED * delta)
		if _walk_anim != "" and _current_anim != _walk_anim:
			_play_anim(_walk_anim)
	else:
		if _idle_anim != "" and _current_anim != _idle_anim:
			_play_anim(_idle_anim)

	if _self_ring != null:
		# Floating ring pulse
		var pulse: float = 1.0 + 0.1 * sin(Time.get_ticks_msec() / 250.0)
		_self_ring.scale = Vector3(pulse, 1.0, pulse)

# -- Animation setup ---------------------------------------------------------

func _setup_animations(player: AnimationPlayer) -> void:
	var src := ANIM_SCENE.instantiate() as Node3D
	add_child(src)
	var src_player := src.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if src_player == null:
		push_warning("character: animation source has no AnimationPlayer")
		src.queue_free()
		return
	for lib_name in src_player.get_animation_library_list():
		var src_lib: AnimationLibrary = src_player.get_animation_library(lib_name)
		if src_lib == null:
			continue
		# Merge into our player. If a library with same name exists, replace it.
		if player.has_animation_library(lib_name):
			player.remove_animation_library(lib_name)
		# Make a deep copy so the source can be freed safely.
		var copy := AnimationLibrary.new()
		for anim_name in src_lib.get_animation_list():
			copy.add_animation(anim_name, src_lib.get_animation(anim_name))
		player.add_animation_library(lib_name, copy)
	src.queue_free()

func _pick_animation(candidates: Array) -> String:
	if _anim_player == null:
		return ""
	for name in candidates:
		var qualified := _qualified_anim(name)
		if qualified != "":
			return qualified
	return ""

# Animations may live in the "" or any other library. Look up the first match.
func _qualified_anim(short_name: String) -> String:
	if _anim_player.has_animation(short_name):
		return short_name
	for lib_name in _anim_player.get_animation_library_list():
		var lib: AnimationLibrary = _anim_player.get_animation_library(lib_name)
		if lib == null:
			continue
		if lib.has_animation(short_name):
			return "%s/%s" % [lib_name, short_name] if lib_name != "" else short_name
	return ""

func _play_anim(name: String) -> void:
	if _anim_player == null:
		return
	if not _anim_player.has_animation(name):
		return
	_anim_player.play(name, 0.2)
	_current_anim = name

# -- Visual decoration -------------------------------------------------------

func _apply_color_tint() -> void:
	if _dummy == null:
		return
	var col := _parse_color(_color_hex)
	for mesh in _find_mesh_instances(_dummy):
		var mat_override := StandardMaterial3D.new()
		var existing_mat: Material = mesh.get_active_material(0)
		if existing_mat is StandardMaterial3D:
			var existing := existing_mat as StandardMaterial3D
			# Preserve KayKit's albedo texture, multiply via modulate.
			mat_override.albedo_texture = existing.albedo_texture
			mat_override.albedo_color = col
		else:
			mat_override.albedo_color = col
		mat_override.metallic = 0.05
		mat_override.roughness = 0.55
		if not _is_alive:
			mat_override.albedo_color.a = 0.45
		mesh.material_override = mat_override

func _apply_alive_state() -> void:
	for mesh in _find_mesh_instances(_dummy):
		var mat: Material = mesh.material_override
		if mat is StandardMaterial3D:
			var sm := mat as StandardMaterial3D
			sm.albedo_color.a = 1.0 if _is_alive else 0.45

func _build_nameplate() -> void:
	_nameplate = Label3D.new()
	_nameplate.position = Vector3(0, NAMEPLATE_HEIGHT, 0)
	_nameplate.font_size = 56
	_nameplate.outline_size = 8
	_nameplate.modulate = Color(1, 1, 1, 1)
	_nameplate.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_nameplate.no_depth_test = true
	_update_nameplate_text()
	add_child(_nameplate)

func _update_nameplate_text() -> void:
	if _nameplate != null:
		_nameplate.text = _player_name

func _build_self_ring() -> void:
	if not is_self:
		return
	_self_ring = MeshInstance3D.new()
	_self_ring.name = "SelfRing"
	var torus := TorusMesh.new()
	torus.inner_radius = 0.55
	torus.outer_radius = 0.65
	torus.rings = 24
	torus.ring_segments = 8
	_self_ring.mesh = torus
	var mat := StandardMaterial3D.new()
	mat.albedo_color = COLOR_SELF_RING
	mat.emission_enabled = true
	mat.emission = COLOR_SELF_RING
	mat.emission_energy_multiplier = 0.6
	_self_ring.material_override = mat
	_self_ring.position.y = 0.05
	add_child(_self_ring)

func _find_mesh_instances(root: Node) -> Array:
	var result: Array = []
	if root is MeshInstance3D:
		result.append(root)
	for child in root.get_children():
		result.append_array(_find_mesh_instances(child))
	return result

func _parse_color(hex: String) -> Color:
	if hex.begins_with("#") and hex.length() == 7:
		return Color(hex)
	return Color(0.5, 0.5, 0.5)
