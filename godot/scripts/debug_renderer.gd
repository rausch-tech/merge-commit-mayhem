class_name DebugRenderer
extends Node2D

const COLOR_ROOM_OUTLINE: Color = Color(0.9, 0.9, 0.95, 0.6)
const COLOR_ROOM_FILL: Color = Color(0.2, 0.2, 0.28, 0.4)
const COLOR_WALL: Color = Color(0.95, 0.3, 0.3, 0.85)
const COLOR_DOOR: Color = Color(0.3, 0.7, 0.95, 0.9)
const COLOR_SPAWN: Color = Color(0.3, 0.95, 0.4, 0.9)
const COLOR_TASK: Color = Color(0.95, 0.85, 0.2, 0.9)
const PLAYER_BOX_SIZE: Vector2 = Vector2(40, 40)
const COLOR_SELF_OUTLINE: Color = Color(1, 1, 1, 1)

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
	queue_redraw()

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
		draw_rect(rect, COLOR_ROOM_OUTLINE, false, 2.0)
		var label := str(room.get("title", room.get("id", "?")))
		draw_string(ThemeDB.fallback_font, rect.position + Vector2(12, 32), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 28, COLOR_ROOM_OUTLINE)

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
			draw_line(Vector2(pos, 0), Vector2(pos, map_h), COLOR_WALL, 4.0)
			for door in doors:
				var c := float(door.get("center", 0))
				var w := float(door.get("width", 120))
				draw_circle(Vector2(pos, c), w * 0.5, COLOR_DOOR)
		elif axis == "y":
			draw_line(Vector2(0, pos), Vector2(map_w, pos), COLOR_WALL, 4.0)
			for door in doors:
				var c := float(door.get("center", 0))
				var w := float(door.get("width", 120))
				draw_circle(Vector2(c, pos), w * 0.5, COLOR_DOOR)

func _draw_spawns() -> void:
	var spawns: Array = _map.get("spawnPoints", [])
	for sp in spawns:
		var p := Vector2(float(sp.get("x", 0)), float(sp.get("y", 0)))
		draw_line(p + Vector2(-12, -12), p + Vector2(12, 12), COLOR_SPAWN, 3.0)
		draw_line(p + Vector2(-12, 12), p + Vector2(12, -12), COLOR_SPAWN, 3.0)

func _draw_task_anchors() -> void:
	var tasks: Array = _map.get("taskAnchors", [])
	for ta in tasks:
		var p := Vector2(float(ta.get("x", 0)), float(ta.get("y", 0)))
		draw_circle(p, 16.0, COLOR_TASK)
		draw_string(ThemeDB.fallback_font, p + Vector2(20, 6), str(ta.get("taskId", "?")), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, COLOR_TASK)

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
			draw_rect(rect, COLOR_SELF_OUTLINE, false, 4.0)
		var name_ := str(p.get("name", "?"))
		draw_string(ThemeDB.fallback_font, pos + Vector2(-30, -28), name_, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color(1, 1, 1, 0.95))
