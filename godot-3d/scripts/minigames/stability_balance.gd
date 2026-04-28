extends Control

# Mini-Game „stability_balance" UI (calm_legacy_service task). Mirror von
# static/minigames/stability_balance.js — drei horizontale Bars (CPU, Mem,
# Queue) muessen alle im gruenen Band [40, 60] gehalten werden. Pro Metrik
# zwei Buttons (- / +). Server rotated jede Korrektur (cpu→mem→queue→cpu)
# und schickt das neue public_view ueber mini_game_state.
#
# View-Schema (server public_view):
#   { cpu, mem, queue, greenLow, greenHigh }
#
# Input zurueck:
#   action="adjust", params={metric, direction}
#     metric: "cpu" / "mem" / "queue"
#     direction: "up" / "down"

const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_DANGER: Color = Color(0.95, 0.35, 0.35)
const COLOR_BAR_BG: Color = Color(0.06, 0.08, 0.12)
const COLOR_GREEN_BAND: Color = Color(0.30, 0.85, 0.45, 0.30)
const COLOR_FILL: Color = Color(0.45, 0.65, 0.95)
const COLOR_FILL_GREEN: Color = Color(0.30, 0.85, 0.45)

const METRICS: Array = [
	{"key": "cpu", "label": "CPU"},
	{"key": "mem", "label": "Memory"},
	{"key": "queue", "label": "Queue"},
]

var _input_callback: Callable = Callable()
var _bar_nodes: Dictionary = {}  # metric_key -> {fill, value_label, green_band, bar_inner}


func _ready() -> void:
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	vbox.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(vbox)

	var hint := Label.new()
	hint.text = "Halte alle drei Metriken im gruenen Band [40, 60]. Jede Korrektur drueckt die naechste Metrik leicht weg."
	hint.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	hint.add_theme_font_size_override("font_size", 12)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(hint)

	for m in METRICS:
		vbox.add_child(_build_metric_row(m))


func set_input_callback(cb: Callable) -> void:
	_input_callback = cb


func apply_view(view: Dictionary) -> void:
	var green_low: float = float(view.get("greenLow", 40))
	var green_high: float = float(view.get("greenHigh", 60))
	for m in METRICS:
		var key: String = m["key"]
		if not _bar_nodes.has(key):
			continue
		var nodes: Dictionary = _bar_nodes[key]
		var v: float = float(view.get(key, 0.0))
		var ratio: float = clampf(v / 100.0, 0.0, 1.0)
		var bar_inner: Control = nodes["bar_inner"]
		var fill: ColorRect = nodes["fill"]
		var value_label: Label = nodes["value_label"]
		var green_band: ColorRect = nodes["green_band"]
		# Bar-Innen-Width ist die effektive Spannweite. Wir setzen Anchor
		# fuer Fill (von links bis ratio) + GreenBand (greenLow..greenHigh).
		fill.anchor_left = 0.0
		fill.anchor_right = ratio
		fill.offset_left = 0
		fill.offset_right = 0
		var in_green: bool = v >= green_low and v <= green_high
		fill.color = COLOR_FILL_GREEN if in_green else COLOR_FILL
		value_label.text = "%d" % int(round(v))
		value_label.add_theme_color_override("font_color", COLOR_ACCENT if in_green else COLOR_TEXT_DIM)
		green_band.anchor_left = green_low / 100.0
		green_band.anchor_right = green_high / 100.0
		green_band.offset_left = 0
		green_band.offset_right = 0


func _build_metric_row(m: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var minus_btn := Button.new()
	minus_btn.text = "-"
	minus_btn.custom_minimum_size = Vector2(40, 32)
	minus_btn.pressed.connect(func(): _send_adjust(str(m["key"]), "down"))
	row.add_child(minus_btn)

	# Label + Value im Wrapper.
	var label_wrap := VBoxContainer.new()
	label_wrap.custom_minimum_size = Vector2(80, 0)
	var label := Label.new()
	label.text = str(m["label"])
	label.add_theme_color_override("font_color", COLOR_TEXT)
	label.add_theme_font_size_override("font_size", 14)
	label_wrap.add_child(label)
	var value_label := Label.new()
	value_label.text = "—"
	value_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	value_label.add_theme_font_size_override("font_size", 12)
	label_wrap.add_child(value_label)
	row.add_child(label_wrap)

	# Bar mit GreenBand + Fill.
	var bar_outer := PanelContainer.new()
	bar_outer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar_outer.custom_minimum_size = Vector2(0, 32)
	var outer_style := StyleBoxFlat.new()
	outer_style.bg_color = COLOR_BAR_BG
	outer_style.set_corner_radius_all(4)
	outer_style.set_border_width_all(1)
	outer_style.border_color = Color(1, 1, 1, 0.10)
	bar_outer.add_theme_stylebox_override("panel", outer_style)
	row.add_child(bar_outer)

	var bar_inner := Control.new()
	bar_outer.add_child(bar_inner)

	var green_band := ColorRect.new()
	green_band.color = COLOR_GREEN_BAND
	green_band.anchor_top = 0.0
	green_band.anchor_bottom = 1.0
	bar_inner.add_child(green_band)

	var fill := ColorRect.new()
	fill.color = COLOR_FILL
	fill.anchor_top = 0.0
	fill.anchor_bottom = 1.0
	bar_inner.add_child(fill)

	var plus_btn := Button.new()
	plus_btn.text = "+"
	plus_btn.custom_minimum_size = Vector2(40, 32)
	plus_btn.pressed.connect(func(): _send_adjust(str(m["key"]), "up"))
	row.add_child(plus_btn)

	_bar_nodes[str(m["key"])] = {
		"fill": fill,
		"value_label": value_label,
		"green_band": green_band,
		"bar_inner": bar_inner,
	}
	return row


func _send_adjust(metric: String, direction: String) -> void:
	if _input_callback.is_valid():
		_input_callback.call("adjust", {"metric": metric, "direction": direction})


func on_complete(_success: bool, _reason: String) -> void:
	pass
