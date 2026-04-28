class_name WSClient
extends Node

# WebSocket-Wrapper, ported from slice/godot-spike, plus close()-before-reconnect
# safety so successive connect_to_server calls don't pile up state on the same peer.

signal connected
signal disconnected
signal message_received(type: String, payload: Dictionary)
signal connection_error(reason: String)

var _socket: WebSocketPeer = WebSocketPeer.new()
var _state: int = WebSocketPeer.STATE_CLOSED
var _previous_state: int = WebSocketPeer.STATE_CLOSED

# Letzte URL die wir connect_to_server() uebergeben haben. Wird vom World-Loader
# gelesen um die HTTP-Base (fuer /api/kinds, /api/maps/<id>) abzuleiten — gleicher
# Host wie die WS-Verbindung, damit Lokal-Dev und Production beide automatisch
# stimmen ohne extra Config.
var connected_url: String = ""

func connect_to_server(url: String) -> void:
	connected_url = url
	if _state != WebSocketPeer.STATE_CLOSED:
		_socket.close()
		# Force a fresh peer; the old socket might be in a half-open state.
		_socket = WebSocketPeer.new()
		_state = WebSocketPeer.STATE_CLOSED
		_previous_state = WebSocketPeer.STATE_CLOSED
	var err := _socket.connect_to_url(url)
	if err != OK:
		connection_error.emit("connect_to_url returned error %d" % err)

# Convert connected_url ("ws[s]://host[/path]") into the matching HTTP base
# ("http[s]://host"). Returns "" if we never connected. Used by KindsLoader to
# fetch /api/kinds + /api/maps/<id> from the same backend the WS talks to.
func http_base_url() -> String:
	if connected_url == "":
		return ""
	var u := connected_url
	var scheme := ""
	if u.begins_with("wss://"):
		scheme = "https://"
		u = u.substr(6)
	elif u.begins_with("ws://"):
		scheme = "http://"
		u = u.substr(5)
	else:
		return ""
	var slash := u.find("/")
	if slash >= 0:
		u = u.substr(0, slash)
	return scheme + u

func send(type_: String, payload: Dictionary = {}) -> void:
	if _state != WebSocketPeer.STATE_OPEN:
		push_warning("WSClient.send while not OPEN — drop %s" % type_)
		return
	_socket.send_text(Protocol.envelope(type_, payload))

func close() -> void:
	_socket.close()

func is_connected_open() -> bool:
	return _state == WebSocketPeer.STATE_OPEN

func _process(_delta: float) -> void:
	_socket.poll()
	var current := _socket.get_ready_state()
	if current != _state:
		_previous_state = _state
		_state = current
		_on_state_change(current)
	while _state == WebSocketPeer.STATE_OPEN and _socket.get_available_packet_count() > 0:
		var raw := _socket.get_packet().get_string_from_utf8()
		_handle_packet(raw)

func _on_state_change(new_state: int) -> void:
	match new_state:
		WebSocketPeer.STATE_OPEN:
			connected.emit()
		WebSocketPeer.STATE_CLOSED:
			if _previous_state == WebSocketPeer.STATE_OPEN:
				disconnected.emit()
			else:
				var code := _socket.get_close_code()
				connection_error.emit("connection closed (code=%d)" % code)

func _handle_packet(raw: String) -> void:
	var parsed = JSON.parse_string(raw)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("WSClient: non-dict packet — %s" % raw)
		return
	var type_ := str(parsed.get("type", ""))
	var payload_raw = parsed.get("payload", {})
	var payload: Dictionary = payload_raw if typeof(payload_raw) == TYPE_DICTIONARY else {}
	if type_ == "":
		push_warning("WSClient: packet without type — %s" % raw)
		return
	message_received.emit(type_, payload)
