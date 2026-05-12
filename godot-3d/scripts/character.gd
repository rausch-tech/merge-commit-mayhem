class_name Character
extends Node3D

# A renderable player character. Picks one of six Kenney Mini Character meshes
# based on player.color (mirrors COLOR_TO_CHAR_INDEX in static/render.js so
# Godot and the HTML client show the same character per color), animates
# between idle/walk based on movement, and shows a player-colored ground disc
# for identity (since we no longer tint the body).
#
# The world.gd is responsible for:
#   - Calling push_target(server_x, server_y) when game_state arrives
#   - Calling set_player_data(name, color_hex, is_alive) on lobby_state
#   - Setting `is_self = true` for the local player so we can highlight it.

# Six characters, one per color in _COLOR_PALETTE order. Spielers 7-12 fall
# through to index 0 (default) — same fallback as the HTML render.
const CHARACTER_SCENES: Array[PackedScene] = [
	preload("res://assets/character/kenney_mini/character-male-a.glb"),    # 0 green
	preload("res://assets/character/kenney_mini/character-female-c.glb"),  # 1 blue
	preload("res://assets/character/kenney_mini/character-female-e.glb"),  # 2 orange
	preload("res://assets/character/kenney_mini/character-female-a.glb"),  # 3 purple
	preload("res://assets/character/kenney_mini/character-female-b.glb"),  # 4 yellow
	preload("res://assets/character/kenney_mini/character-male-c.glb"),    # 5 red
]
# Mirrors static/render.js COLOR_TO_CHAR_INDEX and game_room.py _COLOR_PALETTE.
const COLOR_TO_INDEX: Dictionary = {
	"#4ade80": 0,  # green
	"#60a5fa": 1,  # blue
	"#fb923c": 2,  # orange
	"#c084fc": 3,  # purple
	"#facc15": 4,  # yellow
	"#f87171": 5,  # red
}

# Movement smoothing — target is updated at 20 Hz, we lerp every frame.
# 35.0 ergibt ~20 ms zum Erreichen von 50 % Distanz. Hoeher als 22.0 weil
# Lerp-Oszillation zwischen Server-Ticks (50 ms Spacing) sonst als
# "hakelig" sichtbar wird — bei niedrigerem Lerp-Speed schwankt die
# Render-Velocity stark zwischen Ticks (schneller direkt nach Tick,
# asymptotisch langsam vor naechstem Tick). 35.0 schliesst die meiste
# Distanz innerhalb eines Tick-Intervalls und stabilisiert die Geschwindigkeit.
const POSITION_LERP_SPEED: float = 35.0
const ROTATION_LERP_SPEED: float = 10.0
const MOVE_DEADZONE: float = 0.04
# Wenn der Server-Snapshot weit weg vom gerenderten Char ist UND ein echter
# Pushback (oder Idle-Stuck) vorliegt, snappen wir hart statt zu lerpen.
# Schwellwert: 0.12 World-Units (= 12 Server-Pixel) — knapp ueber dem max
# Lerp-Lag bei Speed-35 (~10 px) und unter typischen Wall-Pushbacks (>= 20 px),
# damit Snap nur bei echten Server-Korrekturen feuert, nicht bei normalen
# Tick-Sprueengen.
const SNAP_PUSHBACK_DISTANCE: float = 0.12
const NAMEPLATE_HEIGHT: float = 2.4
const CHARACTER_SCALE: float = 2.2  # Kenney Mini chars are tiny raw, scale up

const COLOR_SELF_RING: Color = Color(0.30, 0.95, 0.30)
const DISC_OUTER_RADIUS: float = 0.42
const DISC_INNER_RADIUS: float = 0.28

# Footstep sounds — 5 carpet variants, randomized per step.
const FOOTSTEP_SOUNDS: Array[AudioStream] = [
	preload("res://assets/audio/footsteps/footstep_carpet_000.ogg"),
	preload("res://assets/audio/footsteps/footstep_carpet_001.ogg"),
	preload("res://assets/audio/footsteps/footstep_carpet_002.ogg"),
	preload("res://assets/audio/footsteps/footstep_carpet_003.ogg"),
	preload("res://assets/audio/footsteps/footstep_carpet_004.ogg"),
]
const FOOTSTEP_INTERVAL: float = 0.38
const FOOTSTEP_VOLUME_DB: float = -14.0
const FOOTSTEP_MAX_DISTANCE: float = 12.0

# Kenney Mini Characters animation library — names are lowercase shorts.
const ANIM_WALK_PRIORITY: Array = ["walk", "sprint"]
const ANIM_IDLE_PRIORITY: Array = ["idle", "static"]

@export var is_self: bool = false

var _player_id: String = ""
var _player_name: String = "?"
var _color_hex: String = "#888888"
var _is_alive: bool = true
var _target_pos: Vector3 = Vector3.ZERO
var _last_pos: Vector3 = Vector3.ZERO
# Pre-lerp Position vom letzten Frame — fuer korrektes "moved_last_frame".
# `_last_pos` wird am Frame-Ende post-lerp gesetzt, also waere im naechsten
# Frame `current - _last_pos` immer 0. `_pre_lerp_pos` schliesst diese Luecke.
var _pre_lerp_pos: Vector3 = Vector3.ZERO

var _dummy: Node3D
var _anim_player: AnimationPlayer
var _walk_anim: String = ""
var _idle_anim: String = ""
var _current_anim: String = ""
var _facing: float = 0.0
var _nameplate: Label3D
var _self_ring: MeshInstance3D
var _color_disc: MeshInstance3D
var _disc_material: StandardMaterial3D
var _footstep_player: AudioStreamPlayer3D
var _footstep_timer: float = 0.0
var _rng: RandomNumberGenerator = RandomNumberGenerator.new()

func setup(player_id: String, player_name: String, color_hex: String, is_alive: bool, is_self_: bool) -> void:
	_player_id = player_id
	_player_name = player_name
	_color_hex = color_hex
	_is_alive = is_alive
	is_self = is_self_

func _ready() -> void:
	# Pick mesh based on player color — fall through to index 0 if unknown.
	var idx: int = int(COLOR_TO_INDEX.get(_color_hex, 0))
	_dummy = CHARACTER_SCENES[idx].instantiate() as Node3D
	add_child(_dummy)
	_dummy.scale = Vector3(CHARACTER_SCALE, CHARACTER_SCALE, CHARACTER_SCALE)

	# Kenney Mini Characters ship with their own AnimationPlayer + walk/idle.
	# Their default loop_mode is "none" though — force LOOP_LINEAR so the
	# clip keeps repeating instead of freezing after one cycle.
	_anim_player = _dummy.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if _anim_player != null:
		_walk_anim = _pick_animation(ANIM_WALK_PRIORITY)
		_idle_anim = _pick_animation(ANIM_IDLE_PRIORITY)
		_force_loop(_walk_anim)
		_force_loop(_idle_anim)
		if _idle_anim != "":
			_play_anim(_idle_anim)

	_build_color_disc()
	_apply_alive_state()
	_build_nameplate()
	_build_self_ring()
	_build_footstep_player()
	_rng.randomize()
	_dummy.position = Vector3.ZERO
	_last_pos = global_position
	_pre_lerp_pos = global_position

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
		# Color is fixed at spawn — if it ever changes mid-game we'd have to
		# swap the mesh too. Just refresh the disc tint for now.
		_refresh_disc_color()
	if alive_changed and is_inside_tree():
		_apply_alive_state()

func _process(delta: float) -> void:
	# Position lerp
	var current := global_position
	var to_target := _target_pos - current
	# moved_last_frame = Lerp-Delta des LETZTEN Frames (post_N-1 - pre_N-1).
	# Dafuer brauchen wir die pre-lerp-pos von letztem Frame separat —
	# `_last_pos` wird unten post-lerp gesetzt und waere hier identisch zu
	# `current`, also Diff = 0 (latenter Bug aus Tier 4.3.1).
	var moved_last_frame := current - _pre_lerp_pos
	_pre_lerp_pos = current
	# Snap-Trigger in zwei Faellen:
	#  1. Aktiver Pushback: wir laufen, Server schiebt uns entgegen (Wall-Clamp).
	#  2. Idle-Stuck: wir stehen visuell still, der Server-Target ist aber weit
	#     weg. Tritt auf wenn man in einen Tisch reingerannt ist und gestoppt
	#     hat — Lerp braucht sonst ~500 ms zum asymptotischen Aufholen, und
	#     der Char rendert solange visuell im Tisch.
	var pushback := (
		to_target.length() > SNAP_PUSHBACK_DISTANCE
		and (
			moved_last_frame.length_squared() <= 0.0001
			or to_target.dot(moved_last_frame) < 0.0
		)
	)
	if pushback:
		global_position = _target_pos
	else:
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
		_footstep_timer -= delta
		if _footstep_timer <= 0.0 and _is_alive:
			_play_footstep()
			_footstep_timer = FOOTSTEP_INTERVAL
	else:
		if _idle_anim != "" and _current_anim != _idle_anim:
			_play_anim(_idle_anim)
		_footstep_timer = 0.0

	if _self_ring != null:
		var pulse: float = 1.0 + 0.1 * sin(Time.get_ticks_msec() / 250.0)
		_self_ring.scale = Vector3(pulse, 1.0, pulse)

# -- Animation lookup --------------------------------------------------------

func _pick_animation(candidates: Array) -> String:
	if _anim_player == null:
		return ""
	for name in candidates:
		var qualified := _qualified_anim(name)
		if qualified != "":
			return qualified
	return ""

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

func _force_loop(qualified_name: String) -> void:
	if qualified_name == "" or _anim_player == null:
		return
	var anim: Animation = _anim_player.get_animation(qualified_name)
	if anim != null:
		anim.loop_mode = Animation.LOOP_LINEAR

# -- Visual decoration -------------------------------------------------------

func _build_color_disc() -> void:
	_color_disc = MeshInstance3D.new()
	_color_disc.name = "ColorDisc"
	var torus := TorusMesh.new()
	torus.inner_radius = DISC_INNER_RADIUS
	torus.outer_radius = DISC_OUTER_RADIUS
	torus.rings = 24
	torus.ring_segments = 6
	_color_disc.mesh = torus
	_disc_material = StandardMaterial3D.new()
	_disc_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_disc_material.emission_enabled = true
	_color_disc.material_override = _disc_material
	_color_disc.position.y = 0.04
	add_child(_color_disc)
	_refresh_disc_color()

func _refresh_disc_color() -> void:
	if _disc_material == null:
		return
	var col := _parse_color(_color_hex)
	col.a = 0.85
	_disc_material.albedo_color = col
	_disc_material.emission = col
	_disc_material.emission_energy_multiplier = 0.4

func _apply_alive_state() -> void:
	# Dead = ghost: every mesh-instance turns translucent. Live = full opacity.
	var transparency: float = 0.0 if _is_alive else 0.55
	for mesh in _find_mesh_instances(_dummy):
		mesh.transparency = transparency

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
	torus.inner_radius = DISC_OUTER_RADIUS + 0.03
	torus.outer_radius = DISC_OUTER_RADIUS + 0.10
	torus.rings = 24
	torus.ring_segments = 6
	_self_ring.mesh = torus
	var mat := StandardMaterial3D.new()
	mat.albedo_color = COLOR_SELF_RING
	mat.emission_enabled = true
	mat.emission = COLOR_SELF_RING
	mat.emission_energy_multiplier = 0.7
	_self_ring.material_override = mat
	_self_ring.position.y = 0.06
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

func _build_footstep_player() -> void:
	_footstep_player = AudioStreamPlayer3D.new()
	_footstep_player.name = "FootstepPlayer"
	_footstep_player.volume_db = FOOTSTEP_VOLUME_DB
	_footstep_player.max_distance = FOOTSTEP_MAX_DISTANCE
	_footstep_player.pitch_scale = 0.95 + 0.10 * _rng.randf()
	add_child(_footstep_player)

func _play_footstep() -> void:
	if _footstep_player == null or FOOTSTEP_SOUNDS.is_empty():
		return
	var idx: int = _rng.randi_range(0, FOOTSTEP_SOUNDS.size() - 1)
	_footstep_player.stream = FOOTSTEP_SOUNDS[idx]
	_footstep_player.pitch_scale = 0.92 + 0.12 * _rng.randf()
	_footstep_player.play()
