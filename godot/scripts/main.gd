extends Control

@onready var _url_field: LineEdit = $Panel/VBox/UrlField
@onready var _room_field: LineEdit = $Panel/VBox/RoomField
@onready var _name_field: LineEdit = $Panel/VBox/NameField
@onready var _connect_btn: Button = $Panel/VBox/ConnectBtn
@onready var _log: TextEdit = $Panel/VBox/Log

var _ws: WSClient
var _player_id: String = ""
var _map: Dictionary = {}
var _renderer: DebugRenderer = null

func _ready() -> void:
	_ws = WSClient.new()
	add_child(_ws)
	_ws.connected.connect(_on_connected)
	_ws.disconnected.connect(_on_disconnected)
	_ws.connection_error.connect(_on_error)
	_ws.message_received.connect(_on_message)
	_connect_btn.pressed.connect(_on_connect_pressed)

func _on_connect_pressed() -> void:
	var url := _url_field.text.strip_edges()
	var room := _room_field.text.strip_edges()
	var name_ := _name_field.text.strip_edges()
	if url == "" or room == "" or name_ == "":
		_append_log("[input] please fill all three fields")
		return
	_append_log("[ws] connecting to %s" % url)
	set_meta("pending_room", room)
	set_meta("pending_name", name_)
	_ws.connect_to_server(url)

func _on_connected() -> void:
	_append_log("[ws] connected")
	var room := str(get_meta("pending_room"))
	var name_ := str(get_meta("pending_name"))
	_ws.send(Protocol.TYPE_JOIN_ROOM, {"roomCode": room, "playerName": name_})
	_append_log("[ws] sent join_room room=%s name=%s" % [room, name_])

func _on_disconnected() -> void:
	_append_log("[ws] disconnected")

func _on_error(reason: String) -> void:
	_append_log("[ws] error: %s" % reason)

func _on_message(type_: String, payload: Dictionary) -> void:
	match type_:
		Protocol.TYPE_ROOM_JOINED:
			_player_id = str(payload.get("playerId", ""))
			_map = payload.get("map", {})
			var is_host := bool(payload.get("isHost", false))
			_append_log("[room_joined] playerId=%s isHost=%s mapName=%s" % [
				_player_id, is_host, _map.get("name", "?")
			])
			_switch_to_world()
		Protocol.TYPE_LOBBY_STATE:
			var players: Array = payload.get("players", [])
			var names: Array = []
			for p in players:
				names.append(str(p.get("name", "?")))
			_append_log("[lobby_state] players=[%s]" % ", ".join(names))
			if _renderer != null:
				_renderer.set_players(players)
		Protocol.TYPE_GAME_STATE:
			if _renderer != null:
				_renderer.push_snapshot(payload.get("players", []), float(Time.get_ticks_msec()))
		Protocol.TYPE_ERROR:
			_append_log("[server_error] code=%s message=%s" % [
				payload.get("code", "?"), payload.get("message", "?")
			])
		_:
			_append_log("[%s] %s" % [type_, JSON.stringify(payload)])

func _switch_to_world() -> void:
	if _renderer != null:
		return  # already switched
	var world_scene := load("res://scenes/debug_world.tscn") as PackedScene
	if world_scene == null:
		_append_log("[error] debug_world.tscn not found")
		return
	var world := world_scene.instantiate()
	get_tree().root.add_child.call_deferred(world)
	await get_tree().process_frame
	_renderer = world.get_node("Renderer") as DebugRenderer
	_renderer.set_map(_map)
	_renderer.set_self_player_id(_player_id)
	var sender := world.get_node("InputSender") as InputSender
	if sender != null:
		sender.attach(_ws)
	# Connect-Form ausblenden, Log als Overlay sichtbar lassen.
	$Panel/VBox/Title.visible = false
	$Panel/VBox/UrlLabel.visible = false
	$Panel/VBox/UrlField.visible = false
	$Panel/VBox/RoomLabel.visible = false
	$Panel/VBox/RoomField.visible = false
	$Panel/VBox/NameLabel.visible = false
	$Panel/VBox/NameField.visible = false
	$Panel/VBox/ConnectBtn.visible = false
	$Panel.modulate = Color(1, 1, 1, 0.55)
	$Panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	$Panel/VBox.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_log.mouse_filter = Control.MOUSE_FILTER_IGNORE

func _append_log(line: String) -> void:
	print(line)
	_log.text += line + "\n"
	_log.scroll_vertical = _log.get_line_count()
