extends CanvasLayer

# ESC overlay. Lets the player resume, leave the room, and (if host) end the
# round via return_to_lobby.
#
# Signals:
#   close_requested        — user clicked WEITER or pressed ESC again
#   leave_requested        — user clicked RAUM VERLASSEN
#   end_round_requested    — host clicked RUNDE BEENDEN

signal close_requested
signal leave_requested
signal end_round_requested

const COLOR_PANEL_BG: Color = Color(0.10, 0.13, 0.18, 0.96)
const COLOR_BACKDROP: Color = Color(0, 0, 0, 0.55)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_DANGER: Color = Color(0.95, 0.35, 0.35)

@export var is_host: bool = false

func _ready() -> void:
	layer = 50
	_build_ui()
	# Allow ESC to close
	process_mode = Node.PROCESS_MODE_ALWAYS

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var k := event as InputEventKey
		if k.keycode == KEY_ESCAPE:
			close_requested.emit()
			get_viewport().set_input_as_handled()

func _build_ui() -> void:
	var backdrop := ColorRect.new()
	backdrop.color = COLOR_BACKDROP
	backdrop.anchor_right = 1.0
	backdrop.anchor_bottom = 1.0
	backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(backdrop)

	var card := PanelContainer.new()
	card.anchor_left = 0.5
	card.anchor_right = 0.5
	card.anchor_top = 0.5
	card.anchor_bottom = 0.5
	card.offset_left = -200
	card.offset_right = 200
	card.offset_top = -180
	card.offset_bottom = 200
	add_child(card)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_PANEL_BG
	style.set_corner_radius_all(12)
	style.set_border_width_all(2)
	style.border_color = Color(0.30, 0.95, 0.55, 0.4)
	style.set_content_margin_all(28)
	card.add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 16)
	card.add_child(vbox)

	var title := Label.new()
	title.text = "PAUSE"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", COLOR_ACCENT)
	title.add_theme_font_size_override("font_size", 36)
	vbox.add_child(title)

	var hint := Label.new()
	hint.text = "ESC zum Schliessen"
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	hint.add_theme_font_size_override("font_size", 12)
	vbox.add_child(hint)

	vbox.add_child(_make_separator())

	var continue_btn := _make_button("WEITER", COLOR_ACCENT, false)
	continue_btn.pressed.connect(func(): close_requested.emit())
	vbox.add_child(continue_btn)

	if is_host:
		var end_btn := _make_button("RUNDE BEENDEN (Host)", COLOR_TEXT, false)
		end_btn.pressed.connect(func(): end_round_requested.emit())
		vbox.add_child(end_btn)

	var leave_btn := _make_button("RAUM VERLASSEN", COLOR_DANGER, true)
	leave_btn.pressed.connect(func(): leave_requested.emit())
	vbox.add_child(leave_btn)

func _make_button(text: String, color: Color, danger: bool) -> Button:
	var btn := Button.new()
	btn.text = text
	btn.custom_minimum_size = Vector2(0, 44)
	btn.add_theme_font_size_override("font_size", 16)
	btn.add_theme_color_override(
		"font_color", Color(0.04, 0.06, 0.10) if not danger else COLOR_TEXT
	)
	for state in ["normal", "hover", "pressed"]:
		var style := StyleBoxFlat.new()
		var base := color if not danger else Color(0.06, 0.08, 0.12)
		style.bg_color = base
		if state == "hover":
			style.bg_color = base.lightened(0.1)
		elif state == "pressed":
			style.bg_color = base.darkened(0.15)
		style.set_corner_radius_all(8)
		style.set_border_width_all(1 if danger else 0)
		if danger:
			style.border_color = COLOR_DANGER
		style.set_content_margin_all(10)
		btn.add_theme_stylebox_override(state, style)
	return btn

func _make_separator() -> HSeparator:
	var sep := HSeparator.new()
	sep.add_theme_constant_override("separation", 8)
	return sep
