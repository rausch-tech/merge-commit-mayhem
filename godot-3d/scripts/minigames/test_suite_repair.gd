extends Control

# Mini-Game „test_suite_repair" UI (fix_unit_tests task). Mirror von
# static/minigames/test_suite_repair.js — Spieler klickt fehlerhafte Tests
# in numerischer Reihenfolge. Falscher Klick = Soft-Reset.
#
# View-Schema (server public_view):
#   { tests: [{id, label, order, status}], nextOrder, totalTests }
#
# Input zurueck:
#   action="click", params={testId}

const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_DANGER: Color = Color(0.95, 0.40, 0.40)
const COLOR_LINE_BG: Color = Color(0.10, 0.12, 0.16, 1.0)
const COLOR_LINE_FIXED: Color = Color(0.07, 0.20, 0.10, 0.6)

var _input_callback: Callable = Callable()
var _progress_label: Label
var _list_container: VBoxContainer


func _ready() -> void:
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	vbox.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(vbox)

	var hint := Label.new()
	hint.text = "Klicke die fehlerhaften Tests in numerischer Reihenfolge."
	hint.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	hint.add_theme_font_size_override("font_size", 12)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(hint)

	_progress_label = Label.new()
	_progress_label.text = "—"
	_progress_label.add_theme_color_override("font_color", COLOR_ACCENT)
	_progress_label.add_theme_font_size_override("font_size", 14)
	vbox.add_child(_progress_label)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	vbox.add_child(scroll)

	_list_container = VBoxContainer.new()
	_list_container.add_theme_constant_override("separation", 4)
	_list_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_list_container)


func set_input_callback(cb: Callable) -> void:
	_input_callback = cb


func apply_view(view: Dictionary) -> void:
	if _progress_label == null:
		return
	var next_order: int = int(view.get("nextOrder", 1))
	var total: int = int(view.get("totalTests", 0))
	_progress_label.text = "Als nächstes: #%d (%d / %d fertig)" % [next_order, next_order - 1, total]

	for child in _list_container.get_children():
		child.queue_free()
	for t in view.get("tests", []):
		_list_container.add_child(_build_test_button(t))


func _build_test_button(t: Dictionary) -> Button:
	var btn := Button.new()
	var order: int = int(t.get("order", 0))
	var label: String = str(t.get("label", "?"))
	var fixed: bool = str(t.get("status", "")) == "fixed"
	btn.text = "#%d  %s%s" % [order, label, "  ✓" if fixed else ""]
	btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	btn.add_theme_font_size_override("font_size", 13)
	btn.add_theme_color_override("font_color", COLOR_TEXT_DIM if fixed else COLOR_TEXT)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_LINE_FIXED if fixed else COLOR_LINE_BG
	style.set_corner_radius_all(3)
	style.set_content_margin_all(6)
	style.set_border_width_all(1)
	style.border_color = COLOR_ACCENT if fixed else Color(1, 1, 1, 0.10)
	btn.add_theme_stylebox_override("normal", style)
	btn.add_theme_stylebox_override("hover", style)
	btn.add_theme_stylebox_override("pressed", style)

	var test_id: String = str(t.get("id", ""))
	btn.disabled = fixed
	btn.pressed.connect(func(): _on_test_pressed(test_id))
	return btn


func _on_test_pressed(test_id: String) -> void:
	if _input_callback.is_valid():
		_input_callback.call("click", {"testId": test_id})


func on_complete(_success: bool, _reason: String) -> void:
	pass
