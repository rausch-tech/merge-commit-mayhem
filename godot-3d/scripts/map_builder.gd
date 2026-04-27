class_name MapBuilder
extends RefCounted

# Builds the 3D office geometry from a server-shipped Map JSON.
#
# Server-side coords are 2D pixels: (x, y) where x∈[0,map_width], y∈[0,map_height].
# We map them to Godot world units via Protocol.WORLD_SCALE: server (x,y) → Godot (x*S, 0, y*S).
#
# Output: a Node3D called "World" containing:
#   Floors/<room_id>     — flat plane per room with tinted material
#   Walls/<segment_n>    — extruded box-mesh per wall segment (between doors)
#   SpawnPoints/<i>      — invisible Marker3D per spawn (used by world.gd)
#   TaskAnchors/<task_id>— invisible Marker3D per task anchor
#   Furniture            — placed Office decor (KayKit Bits)

const WALL_HEIGHT: float = 2.6
const WALL_THICKNESS: float = 0.18
const FLOOR_THICKNESS: float = 0.05
const WORLD_SCALE: float = Protocol.WORLD_SCALE

# Asset references — shared furniture pool used to decorate rooms heuristically.
const DESK_SCENE: PackedScene = preload("res://assets/furniture/desk.gltf")
const CHAIR_SCENE: PackedScene = preload("res://assets/furniture/chair_desk_A.gltf")
const MONITOR_SCENE: PackedScene = preload("res://assets/furniture/monitor.gltf")

# Visual tone per room id — falls back to room.color from JSON.
const ROOM_TINT_OVERRIDE: Dictionary = {
	"open_space":      Color(0.42, 0.50, 0.62),
	"meeting_room":    Color(0.50, 0.40, 0.60),
	"kitchen":         Color(0.62, 0.50, 0.34),
	"server_room":     Color(0.30, 0.42, 0.58),
	"war_room":        Color(0.30, 0.52, 0.60),
	"legacy_basement": Color(0.38, 0.55, 0.40),
}

const COLOR_WALL: Color = Color(0.92, 0.93, 0.96)
const COLOR_FLOOR_FALLBACK: Color = Color(0.30, 0.34, 0.40)
const COLOR_SPAWN_MARKER: Color = Color(0.30, 0.95, 0.50, 0.6)
const COLOR_TASK_MARKER: Color = Color(0.95, 0.85, 0.20, 0.8)

static func build(map: Dictionary) -> Node3D:
	var root := Node3D.new()
	root.name = "World"

	var size_dict: Dictionary = map.get("size", {})
	var map_w: float = float(size_dict.get("width", 4800.0))
	var map_h: float = float(size_dict.get("height", 3200.0))

	root.add_child(_build_environment(map_w, map_h))

	var floors := Node3D.new()
	floors.name = "Floors"
	root.add_child(floors)
	for room_data in map.get("rooms", []):
		floors.add_child(_build_room_floor(room_data))

	var walls := Node3D.new()
	walls.name = "Walls"
	root.add_child(walls)
	_build_walls(walls, map.get("wallLines", []), map_w, map_h)

	var perimeter := Node3D.new()
	perimeter.name = "Perimeter"
	root.add_child(perimeter)
	_build_perimeter(perimeter, map_w, map_h)

	var spawns := Node3D.new()
	spawns.name = "SpawnPoints"
	root.add_child(spawns)
	for i in range(map.get("spawnPoints", []).size()):
		var sp = map.get("spawnPoints", [])[i]
		var marker := Marker3D.new()
		marker.name = "Spawn_%d" % i
		marker.position = Protocol.server_to_world(float(sp.get("x", 0)), float(sp.get("y", 0)))
		spawns.add_child(marker)

	var task_anchors := Node3D.new()
	task_anchors.name = "TaskAnchors"
	root.add_child(task_anchors)
	for ta in map.get("taskAnchors", []):
		var marker := Marker3D.new()
		marker.name = str(ta.get("taskId", "task"))
		marker.position = Protocol.server_to_world(float(ta.get("x", 0)), float(ta.get("y", 0)))
		task_anchors.add_child(marker)
		# Subtle visual marker — small floating diamond.
		var diamond := MeshInstance3D.new()
		var mesh := SphereMesh.new()
		mesh.radius = 0.18
		mesh.height = 0.36
		mesh.radial_segments = 6
		mesh.rings = 3
		diamond.mesh = mesh
		var mat := StandardMaterial3D.new()
		mat.albedo_color = COLOR_TASK_MARKER
		mat.emission_enabled = true
		mat.emission = COLOR_TASK_MARKER
		mat.emission_energy_multiplier = 0.6
		diamond.material_override = mat
		diamond.position.y = 1.2
		marker.add_child(diamond)

	var furniture := Node3D.new()
	furniture.name = "Furniture"
	root.add_child(furniture)
	_decorate_rooms(furniture, map.get("rooms", []))

	return root

# -- Environment + lighting --------------------------------------------------

static func _build_environment(map_w: float, map_h: float) -> Node3D:
	var holder := Node3D.new()
	holder.name = "Environment"

	var env_node := WorldEnvironment.new()
	env_node.name = "WorldEnvironment"
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.06, 0.09, 0.14)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.65, 0.72, 0.85)
	env.ambient_light_energy = 0.45
	env_node.environment = env
	holder.add_child(env_node)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	sun.transform = Transform3D(Basis().rotated(Vector3(1, 0, 0), -1.05).rotated(Vector3(0, 1, 0), 0.6), Vector3.ZERO)
	sun.light_energy = 1.0
	sun.light_color = Color(1.0, 0.97, 0.92)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 100.0
	sun.shadow_bias = 0.05
	holder.add_child(sun)

	var fill := DirectionalLight3D.new()
	fill.name = "Fill"
	fill.transform = Transform3D(Basis().rotated(Vector3(1, 0, 0), -0.5).rotated(Vector3(0, 1, 0), -2.0), Vector3.ZERO)
	fill.light_energy = 0.35
	fill.light_color = Color(0.7, 0.85, 1.0)
	fill.shadow_enabled = false
	holder.add_child(fill)

	return holder

# -- Rooms -------------------------------------------------------------------

static func _build_room_floor(room_data: Dictionary) -> Node3D:
	var holder := Node3D.new()
	holder.name = "Floor_%s" % str(room_data.get("id", "room"))

	var rx: float = float(room_data.get("x", 0))
	var ry: float = float(room_data.get("y", 0))
	var rw: float = float(room_data.get("width", 0))
	var rh: float = float(room_data.get("height", 0))

	var plane := MeshInstance3D.new()
	plane.name = "Plane"
	var mesh := PlaneMesh.new()
	mesh.size = Vector2(rw * WORLD_SCALE, rh * WORLD_SCALE)
	plane.mesh = mesh
	plane.position = Vector3(
		(rx + rw * 0.5) * WORLD_SCALE,
		0.0,
		(ry + rh * 0.5) * WORLD_SCALE
	)

	var mat := StandardMaterial3D.new()
	var room_id := str(room_data.get("id", ""))
	if ROOM_TINT_OVERRIDE.has(room_id):
		mat.albedo_color = ROOM_TINT_OVERRIDE[room_id]
	else:
		var hex := str(room_data.get("color", ""))
		mat.albedo_color = Color(hex) if hex.begins_with("#") and hex.length() == 7 else COLOR_FLOOR_FALLBACK
	mat.metallic = 0.05
	mat.roughness = 0.85
	plane.material_override = mat
	holder.add_child(plane)

	# Room title floats just above the floor edge.
	var title_text := str(room_data.get("title", room_id))
	var label := Label3D.new()
	label.text = title_text
	label.position = Vector3(
		(rx + 60) * WORLD_SCALE,
		0.05,
		(ry + 110) * WORLD_SCALE
	)
	label.rotate_x(deg_to_rad(-90.0))
	label.font_size = 64
	label.outline_size = 8
	label.modulate = Color(1.0, 1.0, 1.0, 0.65)
	label.no_depth_test = true
	holder.add_child(label)

	return holder

# -- Walls -------------------------------------------------------------------

static func _build_walls(parent: Node3D, lines: Array, map_w: float, map_h: float) -> void:
	var idx: int = 0
	for line in lines:
		var axis := str(line.get("axis", "x"))
		var pos: float = float(line.get("position", 0))
		var doors_raw: Array = line.get("doors", [])
		var max_pos: float = map_h if axis == "x" else map_w
		var segments := _wall_segments(doors_raw, max_pos)
		for seg in segments:
			var seg_start: float = seg[0]
			var seg_end: float = seg[1]
			if seg_end <= seg_start:
				continue
			var wall := _make_wall_box(axis, pos, seg_start, seg_end)
			wall.name = "Wall_%d" % idx
			parent.add_child(wall)
			idx += 1

# Computes wall segments between doors along a single wall line.
# Doors are sorted by center; segments cover the gaps.
static func _wall_segments(doors_raw: Array, max_pos: float) -> Array:
	var doors: Array = []
	for d in doors_raw:
		var center: float = float(d.get("center", 0))
		var width: float = float(d.get("width", 120))
		doors.append({"start": center - width * 0.5, "end": center + width * 0.5})
	doors.sort_custom(func(a, b): return a.start < b.start)
	var segments: Array = []
	var cursor: float = 0.0
	for door in doors:
		if door.start > cursor:
			segments.append([cursor, door.start])
		cursor = max(cursor, door.end)
	if cursor < max_pos:
		segments.append([cursor, max_pos])
	return segments

static func _make_wall_box(axis: String, pos: float, seg_start: float, seg_end: float) -> Node3D:
	var node := MeshInstance3D.new()
	var length_world: float = (seg_end - seg_start) * WORLD_SCALE
	var box := BoxMesh.new()
	if axis == "x":
		# Vertical wall in 2D = wall along Z in 3D, at fixed X.
		box.size = Vector3(WALL_THICKNESS, WALL_HEIGHT, length_world)
		node.position = Vector3(
			pos * WORLD_SCALE,
			WALL_HEIGHT * 0.5,
			(seg_start + seg_end) * 0.5 * WORLD_SCALE
		)
	else:
		# Horizontal wall in 2D = wall along X in 3D, at fixed Z.
		box.size = Vector3(length_world, WALL_HEIGHT, WALL_THICKNESS)
		node.position = Vector3(
			(seg_start + seg_end) * 0.5 * WORLD_SCALE,
			WALL_HEIGHT * 0.5,
			pos * WORLD_SCALE
		)
	node.mesh = box
	var mat := StandardMaterial3D.new()
	mat.albedo_color = COLOR_WALL
	mat.metallic = 0.05
	mat.roughness = 0.7
	node.material_override = mat
	return node

# Outer perimeter walls so the room edges close cleanly.
static func _build_perimeter(parent: Node3D, map_w: float, map_h: float) -> void:
	var sides := [
		{"axis": "x", "pos": 0.0, "start": 0.0, "end": map_h},
		{"axis": "x", "pos": map_w, "start": 0.0, "end": map_h},
		{"axis": "y", "pos": 0.0, "start": 0.0, "end": map_w},
		{"axis": "y", "pos": map_h, "start": 0.0, "end": map_w},
	]
	var idx := 0
	for side in sides:
		var wall := _make_wall_box(side.axis, side.pos, side.start, side.end)
		wall.name = "Perimeter_%d" % idx
		parent.add_child(wall)
		idx += 1

# -- Furniture decoration ---------------------------------------------------

static func _decorate_rooms(parent: Node3D, rooms: Array) -> void:
	for room in rooms:
		var room_id := str(room.get("id", ""))
		var rx: float = float(room.get("x", 0))
		var ry: float = float(room.get("y", 0))
		var rw: float = float(room.get("width", 0))
		var rh: float = float(room.get("height", 0))
		var cx: float = rx + rw * 0.5
		var cz: float = ry + rh * 0.5
		match room_id:
			"open_space":
				_place_desk_row(parent, rx + 200, ry + 250, 3, 0)
				_place_desk_row(parent, rx + 200, ry + 600, 3, 0)
			"meeting_room":
				_place_meeting_table(parent, cx, cz)
			"server_room":
				_place_server_racks(parent, rx, ry, rw, rh)
			"war_room":
				_place_meeting_table(parent, cx, cz)
			"kitchen":
				_place_desk_row(parent, rx + 250, ry + 200, 2, 0)
			"legacy_basement":
				_place_desk_row(parent, rx + 200, ry + 250, 2, 0)
				_place_desk_row(parent, rx + 200, ry + 600, 2, 0)
			_:
				pass

static func _place_desk_row(parent: Node3D, start_x: float, start_z: float, count: int, _rotation: float) -> void:
	var spacing_world: float = 1.8
	for i in count:
		var pos_world := Protocol.server_to_world(start_x, start_z)
		pos_world.x += i * spacing_world
		var desk := DESK_SCENE.instantiate() as Node3D
		desk.position = pos_world
		parent.add_child(desk)
		var monitor := MONITOR_SCENE.instantiate() as Node3D
		monitor.position = pos_world + Vector3(0, 0.78, -0.25)
		parent.add_child(monitor)
		var chair := CHAIR_SCENE.instantiate() as Node3D
		chair.position = pos_world + Vector3(0, 0, 0.9)
		chair.rotation.y = PI
		parent.add_child(chair)

static func _place_meeting_table(parent: Node3D, server_x: float, server_z: float) -> void:
	var table_pos := Protocol.server_to_world(server_x, server_z)
	# Use desk as a long table proxy; KayKit doesn't ship a dedicated meeting table here.
	for i in range(-1, 2):
		var t := DESK_SCENE.instantiate() as Node3D
		t.position = table_pos + Vector3(i * 1.8, 0, 0)
		parent.add_child(t)
	for i in range(-2, 3):
		var c := CHAIR_SCENE.instantiate() as Node3D
		c.position = table_pos + Vector3(i * 0.9, 0, 1.0)
		c.rotation.y = PI
		parent.add_child(c)
		var c2 := CHAIR_SCENE.instantiate() as Node3D
		c2.position = table_pos + Vector3(i * 0.9, 0, -1.0)
		parent.add_child(c2)

static func _place_server_racks(parent: Node3D, rx: float, ry: float, rw: float, rh: float) -> void:
	# Stack monitors as makeshift "server racks" along the room edges.
	for i in 4:
		var pos_world := Protocol.server_to_world(rx + 200 + i * 250.0, ry + 200)
		var rack := MONITOR_SCENE.instantiate() as Node3D
		rack.position = pos_world + Vector3(0, 1.2, 0)
		rack.scale = Vector3(0.8, 1.6, 0.8)
		parent.add_child(rack)
		var stand := DESK_SCENE.instantiate() as Node3D
		stand.position = pos_world
		stand.scale = Vector3(0.7, 0.5, 0.7)
		parent.add_child(stand)
