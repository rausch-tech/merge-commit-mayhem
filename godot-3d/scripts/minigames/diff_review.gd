extends Control

# Mini-Game „diff_review" UI (review_pr task). Mirror von
# static/minigames/diff_review.js — Spieler markiert die zwei kritischen
# Bug-Zeilen in einem 6-Zeilen-Diff. Falscher Klick = Soft-Reset.
#
# View-Schema (server public_view):
#   { lines: [{id, text, marked}], totalBugs, markedBugs }
#
# Input zurueck:
#   action="click", params={lineId}

const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_DANGER: Color = Color(0.95, 0.40, 0.40)
const COLOR_LINE_BG: Color = Color(0.10, 0.12, 0.16, 1.0)
const COLOR_LINE_MARKED: Color = Color(0.07, 0.20, 0.10, 1.0)

var _input_callback: Callable = Callable()
var _progress_label: Label
var _list_container: VBoxContainer


func _ready() -> void:
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	vbox.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(vbox)

	var hint := Label.new()
	hint.text = "Finde die zwei kritischen Code-Zeilen im PR. Falscher Klick setzt zurueck."
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
	var marked: int = int(view.get("markedBugs", 0))
	var total: int = int(view.get("totalBugs", 0))
	_progress_label.text = "%d / %d Bugs markiert" % [marked, total]

	for child in _list_container.get_children():
		child.queue_free()
	for line in view.get("lines", []):
		_list_container.add_child(_build_line_button(line))


func _build_line_button(line: Dictionary) -> Button:
	var btn := Button.new()
	var text: String = str(line.get("text", ""))
	var marked: bool = bool(line.get("marked", false))
	btn.text = ("✓ " if marked else "  ") + text
	btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	btn.add_theme_font_size_override("font_size", 12)
	btn.add_theme_color_override("font_color", COLOR_TEXT)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_LINE_MARKED if marked else COLOR_LINE_BG
	style.set_corner_radius_all(3)
	style.set_content_margin_all(6)
	style.set_border_width_all(1)
	style.border_color = COLOR_ACCENT if marked else Color(1, 1, 1, 0.10)
	btn.add_theme_stylebox_override("normal", style)
	btn.add_theme_stylebox_override("hover", style)
	btn.add_theme_stylebox_override("pressed", style)

	var line_id: String = str(line.get("id", ""))
	btn.disabled = marked
	btn.pressed.connect(func(): _on_line_pressed(line_id))
	return btn


func _on_line_pressed(line_id: String) -> void:
	if _input_callback.is_valid():
		_input_callback.call("click", {"lineId": line_id})


func on_complete(_success: bool, _reason: String) -> void:
	pass
