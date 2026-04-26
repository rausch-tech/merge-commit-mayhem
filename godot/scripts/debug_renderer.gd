class_name DebugRenderer
extends Node2D

const COLOR_ROOM_OUTLINE: Color = Color(0.9, 0.9, 0.95, 0.6)
const COLOR_ROOM_FILL: Color = Color(0.2, 0.2, 0.28, 0.4)
const COLOR_WALL: Color = Color(0.95, 0.3, 0.3, 0.95)
const COLOR_DOOR: Color = Color(0.3, 0.85, 0.7, 1.0)
const COLOR_SPAWN: Color = Color(0.3, 0.95, 0.4, 0.9)
const COLOR_TASK: Color = Color(0.95, 0.85, 0.2, 0.9)
const PLAYER_BOX_SIZE: Vector2 = Vector2(80, 80)
const COLOR_SELF_OUTLINE: Color = Color(1, 1, 1, 1)

# World-pixel sizes — tuned to be readable at the default fit-to-viewport zoom
# (~0.225 for 1280x720, larger for bigger windows). Lines/markers are thick in
# world pixels so they survive the zoom-out.
const WALL_THICKNESS: float = 24.0
const ROOM_OUTLINE_THICKNESS: float = 6.0
const DOOR_DOT_RADIUS: float = 28.0
const SPAWN_ARM: float = 30.0
const SPAWN_THICKNESS: float = 8.0
const TASK_RADIUS: float = 28.0
const PLAYER_OUTLINE_THICKNESS: float = 8.0
const ROOM_LABEL_SIZE: int = 96
const TASK_LABEL_SIZE: int = 56
const PLAYER_LABEL_SIZE: int = 56

var _map: Dictionary = {}
var _self_player_id: String = ""
var _players: Array = []
var _snap_prev: Dictionary = {}
var _snap_curr: Dictionary = {}
var _snap_prev_t: float = 0.0
var _snap_curr_t: float = 0.0
var _interp_render: Array = []

func _ready() -> void:
	set_process(true)

func set_map(map: Dictionary) -> void:
	_map = map
	_fit_camera_to_map()
	queue_redraw()

func _fit_camera_to_map() -> void:
	if not is_inside_tree():
		print("[fit-camera] not in tree, skip")
		return
	var parent_node := get_parent()
	if parent_node == null:
		print("[fit-camera] no parent, skip")
		return
	var camera_node: Camera2D = parent_node.get_node_or_null("Camera") as Camera2D
	if camera_node == null:
		print("[fit-camera] camera node not found under parent ", parent_node.name)
		return
	var size_dict: Dictionary = _map.get("size", {})
	var map_w: float = float(size_dict.get("width", 4800))
	var map_h: float = float(size_dict.get("height", 3200))
	if map_w <= 0 or map_h <= 0:
		print("[fit-camera] invalid map size %sx%s, skip" % [map_w, map_h])
		return
	# stretch_mode=viewport: Render-Area ist immer die konfigurierte Viewport-Groesse
	# (1280x720), unabhaengig vom OS-Window. Die Camera muss auf diese fitten.
	# get_viewport_rect() liefert genau diese Groesse zurueck.
	var viewport_size: Vector2 = get_viewport_rect().size
	if viewport_size.x <= 0 or viewport_size.y <= 0:
		print("[fit-camera] viewport size 0x0, skip")
		return
	var fit_x: float = viewport_size.x / map_w
	var fit_y: float = viewport_size.y / map_h
	# Margin = 1.0 → keine kuenstliche Verkleinerung. Whitespace links/rechts kommt
	# nur durch Aspect-Mismatch (Map 1.5:1 vs Viewport 1.78:1).
	var zoom_factor: float = minf(fit_x, fit_y)
	camera_node.zoom = Vector2(zoom_factor, zoom_factor)
	camera_node.position = Vector2(map_w * 0.5, map_h * 0.5)
	print("[fit-camera] viewport=%s map=%sx%s zoom=%.4f" % [
		viewport_size, map_w, map_h, zoom_factor
	])

func set_self_player_id(id: String) -> void:
	_self_player_id = id

func set_players(players: Array) -> void:
	_players = players
	queue_redraw()

func push_snapshot(players: Array, now_msec: float) -> void:
	var by_id := {}
	for p in players:
		by_id[str(p.get("id", ""))] = p
	_snap_prev = _snap_curr
	_snap_prev_t = _snap_curr_t
	_snap_curr = by_id
	_snap_curr_t = now_msec

func _process(_delta: float) -> void:
	if _snap_curr.is_empty():
		return
	var now := float(Time.get_ticks_msec())
	var dt := _snap_curr_t - _snap_prev_t
	var alpha: float = 1.0
	if dt > 0.0:
		alpha = clamp((now - _snap_curr_t) / dt + 1.0, 0.0, 1.0)
	var rendered: Array = []
	for id in _snap_curr.keys():
		var curr: Dictionary = _snap_curr[id]
		var p := curr.duplicate()
		if _snap_prev.has(id):
			var prev: Dictionary = _snap_prev[id]
			var px: float = lerp(float(prev.get("x", 0)), float(curr.get("x", 0)), alpha)
			var py: float = lerp(float(prev.get("y", 0)), float(curr.get("y", 0)), alpha)
			p["x"] = px
			p["y"] = py
		rendered.append(p)
	_interp_render = rendered
	queue_redraw()

func _draw() -> void:
	if _map.is_empty():
		return
	_draw_rooms()
	_draw_wall_lines()
	_draw_spawns()
	_draw_task_anchors()
	_draw_players()

func _draw_rooms() -> void:
	var rooms: Array = _map.get("rooms", [])
	for room in rooms:
		var rect := Rect2(
			float(room.get("x", 0)), float(room.get("y", 0)),
			float(room.get("width", 0)), float(room.get("height", 0))
		)
		var fill := COLOR_ROOM_FILL
		var hex := str(room.get("color", ""))
		if hex.begins_with("#") and hex.length() == 7:
			fill = Color(hex)
			fill.a = 0.35
		draw_rect(rect, fill, true)
		draw_rect(rect, COLOR_ROOM_OUTLINE, false, ROOM_OUTLINE_THICKNESS)
		var label := str(room.get("title", room.get("id", "?")))
		draw_string(ThemeDB.fallback_font, rect.position + Vector2(40, 110), label, HORIZONTAL_ALIGNMENT_LEFT, -1, ROOM_LABEL_SIZE, COLOR_ROOM_OUTLINE)

func _draw_wall_lines() -> void:
	var size: Dictionary = _map.get("size", {})
	var map_w := float(size.get("width", 4800))
	var map_h := float(size.get("height", 3200))
	var lines: Array = _map.get("wallLines", [])
	for line in lines:
		var axis := str(line.get("axis", "x"))
		var pos := float(line.get("position", 0))
		var doors: Array = line.get("doors", [])
		if axis == "x":
			draw_line(Vector2(pos, 0), Vector2(pos, map_h), COLOR_WALL, WALL_THICKNESS)
			for door in doors:
				var c := float(door.get("center", 0))
				draw_circle(Vector2(pos, c), DOOR_DOT_RADIUS, COLOR_DOOR)
		elif axis == "y":
			draw_line(Vector2(0, pos), Vector2(map_w, pos), COLOR_WALL, WALL_THICKNESS)
			for door in doors:
				var c := float(door.get("center", 0))
				draw_circle(Vector2(c, pos), DOOR_DOT_RADIUS, COLOR_DOOR)

func _draw_spawns() -> void:
	var spawns: Array = _map.get("spawnPoints", [])
	for sp in spawns:
		var p := Vector2(float(sp.get("x", 0)), float(sp.get("y", 0)))
		draw_line(p + Vector2(-SPAWN_ARM, -SPAWN_ARM), p + Vector2(SPAWN_ARM, SPAWN_ARM), COLOR_SPAWN, SPAWN_THICKNESS)
		draw_line(p + Vector2(-SPAWN_ARM, SPAWN_ARM), p + Vector2(SPAWN_ARM, -SPAWN_ARM), COLOR_SPAWN, SPAWN_THICKNESS)

func _draw_task_anchors() -> void:
	var tasks: Array = _map.get("taskAnchors", [])
	for ta in tasks:
		var p := Vector2(float(ta.get("x", 0)), float(ta.get("y", 0)))
		draw_circle(p, TASK_RADIUS, COLOR_TASK)
		draw_string(ThemeDB.fallback_font, p + Vector2(40, 18), str(ta.get("taskId", "?")), HORIZONTAL_ALIGNMENT_LEFT, -1, TASK_LABEL_SIZE, COLOR_TASK)

func _draw_players() -> void:
	var source: Array = _interp_render if not _interp_render.is_empty() else _players
	for p in source:
		var pos := Vector2(float(p.get("x", 0)), float(p.get("y", 0)))
		var hex := str(p.get("color", "#888888"))
		var col := Color(hex) if hex.begins_with("#") and hex.length() == 7 else Color(0.5, 0.5, 0.5)
		if not bool(p.get("isAlive", true)):
			col.a = 0.3
		var rect := Rect2(pos - PLAYER_BOX_SIZE * 0.5, PLAYER_BOX_SIZE)
		draw_rect(rect, col, true)
		if str(p.get("id", "")) == _self_player_id:
			draw_rect(rect, COLOR_SELF_OUTLINE, false, PLAYER_OUTLINE_THICKNESS)
		var name_ := str(p.get("name", "?"))
		draw_string(ThemeDB.fallback_font, pos + Vector2(-PLAYER_BOX_SIZE.x, -PLAYER_BOX_SIZE.y), name_, HORIZONTAL_ALIGNMENT_LEFT, -1, PLAYER_LABEL_SIZE, Color(1, 1, 1, 0.95))
