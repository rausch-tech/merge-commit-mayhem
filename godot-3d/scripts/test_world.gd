extends Node3D

# Spike-2: statisches Office mit Floor-Tiles + Furniture, Dummy als Spieler,
# Camera von schraeg oben (Among-Us-Style via Orthographic). WASD bewegt den
# Spieler in X-Z-Ebene; Camera folgt.
#
# KEINE Animations (Dummy.glb hat keine eingebakenen, AnimLibrary-Setup ist
# Editor-Klickerei und kommt mit Tier 4). Spieler "gleitet" als T-Pose.

const FLOOR_SCENE: PackedScene = preload("res://assets/floor/floor_kitchen.gltf")
const DUMMY_SCENE: PackedScene = preload("res://assets/character/Dummy.glb")
const DESK_SCENE: PackedScene = preload("res://assets/furniture/desk.gltf")
const CHAIR_SCENE: PackedScene = preload("res://assets/furniture/chair_desk_A.gltf")
const MONITOR_SCENE: PackedScene = preload("res://assets/furniture/monitor.gltf")

const FLOOR_TILE_SIZE: float = 1.0  # KayKit Bits Standard
const FLOOR_GRID: int = 12          # 12x12 Tiles = 12x12 Welt-Units
const PLAYER_SPEED: float = 5.0     # Welt-Units/Sekunde
const CAMERA_OFFSET: Vector3 = Vector3(0, 14, 10)

var _player: Node3D = null
@onready var _camera: Camera3D = $Camera

func _ready() -> void:
	_build_floor()
	_place_furniture()
	_spawn_player()
	_update_camera()

func _build_floor() -> void:
	var container := Node3D.new()
	container.name = "Floor"
	add_child(container)
	var origin := -float(FLOOR_GRID) * 0.5 * FLOOR_TILE_SIZE
	for x in FLOOR_GRID:
		for z in FLOOR_GRID:
			var tile := FLOOR_SCENE.instantiate() as Node3D
			tile.position = Vector3(origin + x * FLOOR_TILE_SIZE, 0, origin + z * FLOOR_TILE_SIZE)
			container.add_child(tile)

func _place_furniture() -> void:
	var container := Node3D.new()
	container.name = "Furniture"
	add_child(container)
	# Drei Desk-Setups in einer Reihe (-3, -1, +1) entlang Z=-3
	for i in range(-1, 2):
		var desk := DESK_SCENE.instantiate() as Node3D
		desk.position = Vector3(i * 2.0, 0, -3)
		container.add_child(desk)
		var chair := CHAIR_SCENE.instantiate() as Node3D
		chair.position = Vector3(i * 2.0, 0, -2)
		chair.rotation.y = PI  # zum Desk hin schauen
		container.add_child(chair)
		var monitor := MONITOR_SCENE.instantiate() as Node3D
		monitor.position = Vector3(i * 2.0, 0.8, -3.3)
		container.add_child(monitor)

func _spawn_player() -> void:
	_player = DUMMY_SCENE.instantiate() as Node3D
	_player.name = "Player"
	_player.position = Vector3.ZERO
	add_child(_player)

func _process(delta: float) -> void:
	var direction := Vector3.ZERO
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		direction.z -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		direction.z += 1.0
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		direction.x -= 1.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		direction.x += 1.0
	if direction.length() > 0.0:
		direction = direction.normalized()
		_player.position += direction * PLAYER_SPEED * delta
		# Charakter dreht sich in Bewegungsrichtung
		_player.rotation.y = atan2(-direction.x, -direction.z)
	_update_camera()

func _update_camera() -> void:
	if _player == null:
		return
	_camera.position = _player.position + CAMERA_OFFSET
	_camera.look_at(_player.position, Vector3.UP)
