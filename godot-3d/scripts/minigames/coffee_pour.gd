extends Control

# Mini-Game „coffee_pour" UI (refill_coffee task). Mirror von
# static/minigames/coffee_pour.js — eine Tasse fuellt sich linear in
# cycleSeconds Sekunden, der Spieler tippt einmal STOP. Server validiert
# ob der Tap im sweetMin..sweetMax-Band liegt; bei Daneben kommt ein neuer
# Frame mit elapsed≈0. Wir extrapolieren lokal aus elapsed +
# Date.now()-Diff.
#
# View-Schema (server public_view):
#   { elapsed, cycleSeconds, sweetMin, sweetMax, attempts,
#     lastAttemptFill, complete }
#
# Input zurueck:
#   action="stop", params={}

const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_DANGER: Color = Color(0.95, 0.35, 0.35)
const COLOR_CUP_BG: Color = Color(0.10, 0.13, 0.18, 1.0)
const COLOR_FILL: Color = Color(0.65, 0.45, 0.20, 0.95)
const COLOR_SWEET: Color = Color(0.30, 0.95, 0.55, 0.30)

var _input_callback: Callable = Callable()
var _hint_label: Label
var _status_label: Label
var _cup_panel: PanelContainer
var _fill_rect: ColorRect
var _sweet_rect: ColorRect
var _stop_btn: Button

var _cycle_seconds: float = 3.0
var _sweet_min: float = 0.7
var _sweet_max: float = 1.0
var _local_t0: float = 0.0  # OS.get_ticks_msec()/1000 - elapsed_at_last_view
var _last_view: Dictionary = {}


func _ready() -> void:
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 12)
	vbox.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(vbox)

	_hint_label = Label.new()
	_hint_label.text = "Tippe STOP, wenn die Tasse im gruenen Bereich ist."
	_hint_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	_hint_label.add_theme_font_size_override("font_size", 12)
	_hint_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(_hint_label)

	_status_label = Label.new()
	_status_label.text = "—"
	_status_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	_status_label.add_theme_font_size_override("font_size", 13)
	vbox.add_child(_status_label)

	# Cup-Stage: 200x300 zentriert. Sweet-Band sichtbar als helleres Overlay,
	# Fill-Rect waechst von unten hoch.
	var stage := CenterContainer.new()
	stage.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(stage)

	_cup_panel = PanelContainer.new()
	_cup_panel.custom_minimum_size = Vector2(200, 300)
	var cup_style := StyleBoxFlat.new()
	cup_style.bg_color = COLOR_CUP_BG
	cup_style.set_corner_radius_all(8)
	cup_style.set_border_width_all(2)
	cup_style.border_color = COLOR_TEXT_DIM
	_cup_panel.add_theme_stylebox_override("panel", cup_style)
	stage.add_child(_cup_panel)

	# Inner: zwei ColorRects, sweet (passiv) hinten, fill (animiert) vorne.
	var inner := Control.new()
	inner.set_anchors_preset(Control.PRESET_FULL_RECT)
	_cup_panel.add_child(inner)

	_sweet_rect = ColorRect.new()
	_sweet_rect.color = COLOR_SWEET
	_sweet_rect.anchor_left = 0.0
	_sweet_rect.anchor_right = 1.0
	inner.add_child(_sweet_rect)

	_fill_rect = ColorRect.new()
	_fill_rect.color = COLOR_FILL
	_fill_rect.anchor_left = 0.0
	_fill_rect.anchor_right = 1.0
	inner.add_child(_fill_rect)

	_stop_btn = Button.new()
	_stop_btn.text = "STOP"
	_stop_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_stop_btn.add_theme_font_size_override("font_size", 18)
	_stop_btn.pressed.connect(_on_stop_pressed)
	vbox.add_child(_stop_btn)


func set_input_callback(cb: Callable) -> void:
	_input_callback = cb


func apply_view(view: Dictionary) -> void:
	_cycle_seconds = float(view.get("cycleSeconds", _cycle_seconds))
	_sweet_min = float(view.get("sweetMin", _sweet_min))
	_sweet_max = float(view.get("sweetMax", _sweet_max))
	_local_t0 = _now() - float(view.get("elapsed", 0.0))
	_last_view = view

	# Sweet-Band positionieren: bottom = sweetMin*height, height = (max-min)*height.
	# Wir setzen Anchors so dass der Rect den richtigen Bereich abdeckt.
	if _sweet_rect != null:
		_sweet_rect.anchor_top = 1.0 - _sweet_max
		_sweet_rect.anchor_bottom = 1.0 - _sweet_min
		_sweet_rect.offset_top = 0
		_sweet_rect.offset_bottom = 0

	# Status-Text update
	if bool(view.get("complete", false)):
		_status_label.text = "Volltreffer!"
		_status_label.add_theme_color_override("font_color", COLOR_ACCENT)
	elif int(view.get("attempts", 0)) > 0:
		var pct: int = int(round(float(view.get("lastAttemptFill", 0.0)) * 100.0))
		_status_label.text = "Daneben (%d%%) — nochmal!" % pct
		_status_label.add_theme_color_override("font_color", COLOR_DANGER)
	else:
		_status_label.text = "Bereit."
		_status_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)


func _process(_delta: float) -> void:
	if _last_view.is_empty() or _fill_rect == null:
		return
	if bool(_last_view.get("complete", false)):
		# Volltreffer: Fill bleibt voll, kein animierter Reset.
		_fill_rect.anchor_top = 1.0 - _sweet_max
		_fill_rect.offset_top = 0
		return
	var elapsed: float = _now() - _local_t0
	# Modulo cycle: nach Vollfuellung beginnt der naechste Versuch.
	var t: float = fmod(elapsed, _cycle_seconds) / _cycle_seconds
	t = clamp(t, 0.0, 1.0)
	# Fill von unten: anchor_top = 1 - t (oben am Cup), bottom bleibt 1.
	_fill_rect.anchor_top = 1.0 - t
	_fill_rect.anchor_bottom = 1.0
	_fill_rect.offset_top = 0
	_fill_rect.offset_bottom = 0


func _on_stop_pressed() -> void:
	if _input_callback.is_valid():
		_input_callback.call("stop", {})


func _now() -> float:
	return Time.get_ticks_msec() / 1000.0


func on_complete(_success: bool, _reason: String) -> void:
	pass
