extends Control

# Mini-Game „sprint_trim" UI. Mirror der Browser-Implementierung in
# static/minigames/sprint_trim.js — Spieler tippt 6 Tickets an um sie aus
# dem Sprint zu nehmen, bis remainingPoints <= budget. Priority-Tickets
# (rot) duerfen NICHT entfernt werden — Klick darauf ist Soft-Reset.
#
# View-Schema (vom Server, public_view):
#   { tickets: [{id, title, points, priority, removed}], budget, remainingPoints }
#
# Input zurueck:
#   action="toggle", params={ticketId: "t0"..."t5"}

const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_DANGER: Color = Color(0.95, 0.35, 0.35)
const COLOR_TICKET_BG: Color = Color(0.14, 0.17, 0.22, 1.0)
const COLOR_TICKET_REMOVED: Color = Color(0.10, 0.12, 0.16, 1.0)
const COLOR_TICKET_PRIORITY: Color = Color(0.30, 0.10, 0.10, 1.0)

var _input_callback: Callable = Callable()
var _hint_label: Label
var _progress_label: Label
var _list_container: VBoxContainer

func _ready() -> void:
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	vbox.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(vbox)

	_hint_label = Label.new()
	_hint_label.text = "Tippe Tickets an um sie aus dem Sprint zu nehmen. Rote Priority-Tickets nicht anfassen."
	_hint_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	_hint_label.add_theme_font_size_override("font_size", 12)
	_hint_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(_hint_label)

	_progress_label = Label.new()
	_progress_label.text = "—"
	_progress_label.add_theme_color_override("font_color", COLOR_DANGER)
	_progress_label.add_theme_font_size_override("font_size", 16)
	vbox.add_child(_progress_label)

	_list_container = VBoxContainer.new()
	_list_container.add_theme_constant_override("separation", 4)
	_list_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(_list_container)

func set_input_callback(cb: Callable) -> void:
	_input_callback = cb

func apply_view(view: Dictionary) -> void:
	if _progress_label == null:
		return
	var remaining: int = int(view.get("remainingPoints", 0))
	var budget: int = int(view.get("budget", 0))
	var over: bool = remaining > budget
	_progress_label.text = "Restpunkte: %d / Sprint-Budget %d" % [remaining, budget]
	_progress_label.add_theme_color_override(
		"font_color", COLOR_DANGER if over else COLOR_ACCENT
	)

	for child in _list_container.get_children():
		child.queue_free()

	for t in view.get("tickets", []):
		_list_container.add_child(_build_ticket_button(t))

func _build_ticket_button(t: Dictionary) -> Button:
	var btn := Button.new()
	var points: int = int(t.get("points", 0))
	var title: String = str(t.get("title", "?"))
	var priority: bool = bool(t.get("priority", false))
	var removed: bool = bool(t.get("removed", false))
	var tag: String = "PRIORITY" if priority else ("OUT" if removed else "IN")
	btn.text = "%2d SP   %-32s   [%s]" % [points, title, tag]
	btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	btn.add_theme_font_size_override("font_size", 13)
	btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var style := StyleBoxFlat.new()
	if priority:
		style.bg_color = COLOR_TICKET_PRIORITY
		style.border_color = COLOR_DANGER
	elif removed:
		style.bg_color = COLOR_TICKET_REMOVED
		style.border_color = Color(1, 1, 1, 0.10)
	else:
		style.bg_color = COLOR_TICKET_BG
		style.border_color = COLOR_ACCENT
	style.set_border_width_all(1)
	style.set_corner_radius_all(4)
	style.set_content_margin_all(8)
	btn.add_theme_stylebox_override("normal", style)
	btn.add_theme_stylebox_override("hover", style)
	btn.add_theme_stylebox_override("pressed", style)

	var ticket_id: String = str(t.get("id", ""))
	btn.pressed.connect(func(): _on_ticket_pressed(ticket_id))
	return btn

func _on_ticket_pressed(ticket_id: String) -> void:
	if _input_callback.is_valid():
		_input_callback.call("toggle", {"ticketId": ticket_id})

func on_complete(_success: bool, _reason: String) -> void:
	pass
