class_name InputSender
extends Node

# WASD + arrow-key sampling at 20 Hz. Sends player_input on change, with a
# 50ms throttle to avoid spam.

const SEND_INTERVAL: float = 0.05  # 50 ms = 20 Hz

var _ws: WSClient = null
var _accum: float = 0.0
var _last_state: Dictionary = {"up": false, "down": false, "left": false, "right": false}
var _dirty: bool = true
var _enabled: bool = false

func attach(ws: WSClient) -> void:
	_ws = ws

func set_enabled(value: bool) -> void:
	_enabled = value
	if value:
		# Flush a fresh "all-released" baseline when disabled (avoid stuck input).
		_dirty = true
		_accum = SEND_INTERVAL

func _process(delta: float) -> void:
	if _ws == null or not _enabled:
		return
	var current := {
		"up": Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP),
		"down": Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN),
		"left": Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT),
		"right": Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT),
	}
	if current.hash() != _last_state.hash():
		_dirty = true
		_last_state = current
	_accum += delta
	if _dirty and _accum >= SEND_INTERVAL:
		_ws.send(Protocol.TYPE_PLAYER_INPUT, current)
		_accum = 0.0
		_dirty = false
