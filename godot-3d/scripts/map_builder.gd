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
#   MapObjects/<kind_n>  — Tier-4 props (desks, chairs, monitors, …) gerendert
#                          aus map.mapObjects[]. Kinds mit echten KayKit-Assets
#                          → instanced asset; sonst → Fallback-Box mit Kind-
#                          Label (sieht hässlich aus, aber zeigt klar wo Assets
#                          fehlen — Asset-Pipeline ist Tier 4.0.x).

const WALL_HEIGHT: float = 2.6
const WALL_THICKNESS: float = 0.12
const FLOOR_THICKNESS: float = 0.05
const WORLD_SCALE: float = Protocol.WORLD_SCALE

# kind → PackedScene mapping. Kinds, die hier nicht aufgelistet sind, fallen
# auf einen grauen Fallback-Box mit Kind-Label zurück (siehe _make_map_object).
# Wenn neue Assets dazukommen: hier registrieren, Eintrag aus `docs/maps.md`
# Kind-Catalogue als Wahrheits-Source nutzen.
const KIND_ASSETS: Dictionary = {
	"desk":       preload("res://assets/furniture/desk.gltf"),
	"chair_desk": preload("res://assets/furniture/chair_desk_A.gltf"),
	"monitor":    preload("res://assets/furniture/monitor.gltf"),
}

# Fallback-Box-Farbe + Höhe für Kinds ohne Asset. Höhe ist absichtlich klein
# damit er nicht visuell mit Wänden konkurriert.
const COLOR_PROP_FALLBACK: Color = Color(0.55, 0.55, 0.58)
const PROP_FALLBACK_HEIGHT: float = 0.6
const PROP_LABEL_HEIGHT: float = 0.95

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
	_build_walls(walls, map.get("rooms", []), map.get("doors", []), map.get("size", {}))

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

	var props := Node3D.new()
	props.name = "MapObjects"
	root.add_child(props)
	_build_map_objects(props, map.get("mapObjects", []))

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
#
# Walls werden aus Room-Edges + Door-Cutouts abgeleitet — Mirror von
# app/game/game_map.compute_walls() (Slice 3, "Wand-Modell C").
#
# Pro Room-Edge: shared portion mit Nachbarn → Wand minus matching Doors
# (Pair-dedup); non-shared portion → Wand, außer auf Map-Boundary. Outer-
# Map-Perimeter wird separat in _build_perimeter() gerendert, damit die
# Welt in 3D geschlossen wirkt (Server clamped Movement an der Boundary).
# Map-Objects (blocks_movement) werden hier NICHT als Walls gerendert —
# die kommen als eigene 3D-Meshes in einem späteren Slice.

static func _build_walls(parent: Node3D, rooms: Array, doors: Array, map_size: Dictionary) -> void:
	var segments := _compute_wall_segments(rooms, doors, map_size)
	var idx: int = 0
	for seg in segments:
		if seg.end <= seg.start:
			continue
		var wall := _make_wall_box(seg.axis, seg.pos, seg.start, seg.end)
		wall.name = "Wall_%d" % idx
		parent.add_child(wall)
		idx += 1

static func _compute_wall_segments(rooms: Array, doors: Array, map_size: Dictionary) -> Array:
	var out: Array = []
	# Dedup: each shared edge (room_a ↔ room_b at axis/edge_pos/overlap)
	# darf nur einmal in Segmente umgesetzt werden — sonst doppelte Box-Meshes.
	var processed: Dictionary = {}

	for room in rooms:
		var rid: String = str(room.get("id", ""))
		var rx: float = float(room.get("x", 0))
		var ry: float = float(room.get("y", 0))
		var rw: float = float(room.get("width", 0))
		var rh: float = float(room.get("height", 0))

		var edges: Array = [
			{"axis": "y", "edge_pos": ry, "start": rx, "end": rx + rw},        # top
			{"axis": "y", "edge_pos": ry + rh, "start": rx, "end": rx + rw},   # bottom
			{"axis": "x", "edge_pos": rx, "start": ry, "end": ry + rh},        # left
			{"axis": "x", "edge_pos": rx + rw, "start": ry, "end": ry + rh},   # right
		]

		for edge in edges:
			var axis: String = edge.axis
			var edge_pos: float = edge.edge_pos
			var start: float = edge.start
			var end: float = edge.end

			var shared: Array = []
			for other in rooms:
				if str(other.get("id", "")) == rid:
					continue
				var ovl = _edge_overlap(other, axis, edge_pos, start, end)
				if ovl != null:
					shared.append({"other_id": str(other.get("id", "")), "ovl": ovl})

			# Shared portions: walls minus door cutouts (dedup pro Pair).
			for s in shared:
				var pair_key: Array = [rid, s.other_id]
				pair_key.sort()
				var key: String = "%s|%s|%s|%s|%s|%s" % [axis, edge_pos, pair_key[0], pair_key[1], s.ovl[0], s.ovl[1]]
				if processed.has(key):
					continue
				processed[key] = true

				var cutouts: Array = []
				for door in doors:
					var door_pair: Array = [str(door.get("betweenRoomA", "")), str(door.get("betweenRoomB", ""))]
					door_pair.sort()
					if door_pair[0] != pair_key[0] or door_pair[1] != pair_key[1]:
						continue
					var dpos: float = float(door.get("position", 0))
					if dpos < s.ovl[0] or dpos > s.ovl[1]:
						continue
					var dwidth: float = float(door.get("width", 120))
					var half: float = dwidth * 0.5
					cutouts.append([dpos - half, dpos + half])

				for seg_pair in _interval_subtract(s.ovl[0], s.ovl[1], cutouts):
					out.append({"axis": axis, "pos": edge_pos, "start": seg_pair[0], "end": seg_pair[1]})

			# Perimeter portions (kein Nachbar) — nur wenn Edge nicht auf Map-Boundary.
			if not _is_map_edge(axis, edge_pos, map_size):
				var shared_cuts: Array = []
				for s in shared:
					shared_cuts.append(s.ovl)
				for seg_pair in _interval_subtract(start, end, shared_cuts):
					out.append({"axis": axis, "pos": edge_pos, "start": seg_pair[0], "end": seg_pair[1]})

	return out

# Returns [a, b] overlap-interval entlang der perpendikulären Achse, oder
# null wenn other keine Edge an (axis, edge_pos) hat oder kein Overlap.
static func _edge_overlap(other: Dictionary, axis: String, edge_pos: float, start: float, end: float):
	var ox: float = float(other.get("x", 0))
	var oy: float = float(other.get("y", 0))
	var ow: float = float(other.get("width", 0))
	var oh: float = float(other.get("height", 0))
	var a: float
	var b: float
	if axis == "x":
		if ox != edge_pos and ox + ow != edge_pos:
			return null
		a = max(start, oy)
		b = min(end, oy + oh)
	else:
		if oy != edge_pos and oy + oh != edge_pos:
			return null
		a = max(start, ox)
		b = min(end, ox + ow)
	if a < b:
		return [a, b]
	return null

# [start, end] minus union der cutouts. Sortiertes Ergebnis.
static func _interval_subtract(start: float, end: float, cutouts: Array) -> Array:
	if cutouts.is_empty():
		return [[start, end]] if start < end else []
	var clipped: Array = []
	for c in cutouts:
		var sa: float = max(c[0], start)
		var sb: float = min(c[1], end)
		if sa < sb:
			clipped.append([sa, sb])
	clipped.sort_custom(func(a, b): return a[0] < b[0])
	var out: Array = []
	var cursor: float = start
	for c in clipped:
		if c[0] > cursor:
			out.append([cursor, c[0]])
		cursor = max(cursor, c[1])
	if cursor < end:
		out.append([cursor, end])
	return out

static func _is_map_edge(axis: String, edge_pos: float, map_size: Dictionary) -> bool:
	var w: float = float(map_size.get("width", 4800))
	var h: float = float(map_size.get("height", 3200))
	if axis == "x":
		return edge_pos == 0.0 or edge_pos == w
	return edge_pos == 0.0 or edge_pos == h

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

# -- MapObjects rendering ----------------------------------------------------
#
# Map-JSON ist single source of truth für alle Furniture/Props (jeder Eintrag
# in mapObjects[] = ein 3D-Objekt). Heuristische Furniture-Platzierung pro
# Room-Id (vor Slice A1) ist gedroppt — Map-Editor und Schema beschreiben
# jetzt vollständig was wo steht.
#
# object.x/y ist CENTER (nicht top-left). object.rotation ∈ {0, 90, 180, 270}
# rotiert das Mesh um die Y-Achse. Die object.width/height beziehen sich auf
# die UN-rotierte Form — Rotation 90/270 swapped den AABB-Footprint, aber
# da wir das Mesh selbst rotieren, brauchen wir den Swap visuell nicht.
# (Server-side Collision macht das Swap für blocks_movement, siehe
# game_map.map_object_aabb().)

static func _build_map_objects(parent: Node3D, map_objects: Array) -> void:
	for i in map_objects.size():
		var obj: Dictionary = map_objects[i]
		var kind := str(obj.get("kind", ""))
		var node := _make_map_object(kind, obj)
		node.name = "%s_%d" % [kind if kind != "" else "obj", i]
		parent.add_child(node)

static func _make_map_object(kind: String, obj: Dictionary) -> Node3D:
	var holder := Node3D.new()
	var ox: float = float(obj.get("x", 0))
	var oy: float = float(obj.get("y", 0))
	var rot_deg: int = int(obj.get("rotation", 0))

	holder.position = Protocol.server_to_world(ox, oy)
	holder.rotation.y = deg_to_rad(float(rot_deg))

	if KIND_ASSETS.has(kind):
		var asset := (KIND_ASSETS[kind] as PackedScene).instantiate() as Node3D
		holder.add_child(asset)
	else:
		holder.add_child(_make_fallback_prop(kind, obj))

	return holder

# Fallback-Visual für Kinds ohne registriertes Asset: graue Box mit Kind-Label.
# Bewusst hässlich, damit man auf einen Blick sieht, welche Assets noch
# fehlen. Lange Liste pro Map = Asset-Pipeline-Slice ist überfällig.
static func _make_fallback_prop(kind: String, obj: Dictionary) -> Node3D:
	var holder := Node3D.new()
	var ow: float = float(obj.get("width", 0))
	var oh: float = float(obj.get("height", 0))

	var box := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3(ow * WORLD_SCALE, PROP_FALLBACK_HEIGHT, oh * WORLD_SCALE)
	box.mesh = mesh
	box.position.y = PROP_FALLBACK_HEIGHT * 0.5

	var mat := StandardMaterial3D.new()
	mat.albedo_color = COLOR_PROP_FALLBACK
	mat.metallic = 0.05
	mat.roughness = 0.85
	box.material_override = mat
	holder.add_child(box)

	if kind != "":
		var label := Label3D.new()
		label.text = kind
		label.position.y = PROP_LABEL_HEIGHT
		label.font_size = 28
		label.outline_size = 4
		label.modulate = Color(1.0, 1.0, 1.0, 0.85)
		label.no_depth_test = true
		holder.add_child(label)

	return holder
