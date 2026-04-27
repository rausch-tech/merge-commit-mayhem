extends CanvasLayer

# Game HUD — overlays the 3D world with stat bars, timer, role chip, and a
# right-side player roster. Pure UI; updates come from world.gd via:
#   - apply_game_state(state)
#   - set_role_info(payload)
#   - set_player_id(id)
#   - set_map_name(name)

const COLOR_PANEL_BG: Color = Color(0.06, 0.08, 0.12, 0.88)
const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_DANGER: Color = Color(0.95, 0.35, 0.35)
const COLOR_WARN: Color = Color(0.95, 0.70, 0.30)

# Stat bar colors
const COLOR_STAT_RELEASE: Color = Color(0.30, 0.85, 0.45)
const COLOR_STAT_PIPELINE: Color = Color(0.45, 0.65, 0.95)
const COLOR_STAT_COFFEE: Color = Color(0.85, 0.60, 0.30)
const COLOR_STAT_INCIDENTS: Color = Color(0.95, 0.40, 0.40)

var _player_id: String = ""
var _map_name: String = ""
var _role_info: Dictionary = {}

# UI nodes
var _top_bar: PanelContainer
var _stat_labels: Dictionary = {}        # name → Label (value)
var _stat_bars: Dictionary = {}          # name → ColorRect (fill)
var _stat_bar_max_width: float = 140.0
var _timer_label: Label
var _phase_label: Label
var _role_chip: Label
var _team_chip: Label
var _map_label: Label
var _roster: VBoxContainer

func _ready() -> void:
	_build_top_bar()
	_build_role_chip()
	_build_roster_panel()
	_build_map_label()
	apply_game_state({})

# Public API ----------------------------------------------------------------

func set_player_id(id: String) -> void:
	_player_id = id

func set_map_name(name: String) -> void:
	_map_name = name
	if _map_label != null:
		_map_label.text = "Map: %s" % name

func set_role_info(role_info: Dictionary) -> void:
	_role_info = role_info
	if _role_chip == null:
		return
	var role := str(role_info.get("role", "")).replace("_", " ").capitalize()
	var team := str(role_info.get("team", ""))
	_role_chip.text = role if role != "" else "—"
	if team == "chaos_agents":
		_team_chip.text = "CHAOS-AGENT"
		_team_chip.add_theme_color_override("font_color", COLOR_DANGER)
	elif team == "release_team":
		_team_chip.text = "RELEASE-TEAM"
		_team_chip.add_theme_color_override("font_color", COLOR_ACCENT)
	else:
		_team_chip.text = "—"
		_team_chip.add_theme_color_override("font_color", COLOR_TEXT_DIM)

func apply_game_state(state: Dictionary) -> void:
	# Stats
	_set_stat("release", int(state.get("releaseProgress", 0)))
	_set_stat("pipeline", int(state.get("pipelineStability", 100)))
	_set_stat("coffee", int(state.get("coffeeLevel", 100)))
	_set_stat("incidents", int(state.get("incidents", 0)))

	# Timer
	var seconds: int = int(state.get("remainingSeconds", 0))
	if _timer_label != null:
		_timer_label.text = _format_timer(seconds)

	# Phase chip
	if _phase_label != null:
		var phase := str(state.get("phase", ""))
		match phase:
			"playing":
				_phase_label.text = "PLAYING"
				_phase_label.add_theme_color_override("font_color", COLOR_ACCENT)
			"meeting":
				_phase_label.text = "MEETING"
				_phase_label.add_theme_color_override("font_color", COLOR_WARN)
			"ended":
				_phase_label.text = "ENDED"
				_phase_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
			_:
				_phase_label.text = "—"

	# Roster
	_update_roster(state.get("players", []))

# Build helpers --------------------------------------------------------------

func _build_top_bar() -> void:
	_top_bar = PanelContainer.new()
	_top_bar.anchor_left = 0.0
	_top_bar.anchor_right = 1.0
	_top_bar.anchor_top = 0.0
	_top_bar.offset_left = 16
	_top_bar.offset_right = -16
	_top_bar.offset_top = 16
	_top_bar.offset_bottom = 86
	add_child(_top_bar)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_PANEL_BG
	style.set_corner_radius_all(10)
	style.set_border_width_all(1)
	style.border_color = Color(1, 1, 1, 0.08)
	style.set_content_margin_all(12)
	_top_bar.add_theme_stylebox_override("panel", style)

	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 28)
	_top_bar.add_child(hbox)

	hbox.add_child(_build_stat_block("release", "RELEASE", COLOR_STAT_RELEASE))
	hbox.add_child(_build_stat_block("pipeline", "PIPELINE", COLOR_STAT_PIPELINE))
	hbox.add_child(_build_stat_block("coffee", "COFFEE", COLOR_STAT_COFFEE))
	hbox.add_child(_build_stat_block("incidents", "INCIDENTS", COLOR_STAT_INCIDENTS))

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hbox.add_child(spacer)

	var timer_block := VBoxContainer.new()
	timer_block.alignment = BoxContainer.ALIGNMENT_END
	hbox.add_child(timer_block)

	_phase_label = Label.new()
	_phase_label.text = "—"
	_phase_label.add_theme_color_override("font_color", COLOR_ACCENT)
	_phase_label.add_theme_font_size_override("font_size", 12)
	_phase_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	timer_block.add_child(_phase_label)

	_timer_label = Label.new()
	_timer_label.text = "00:00"
	_timer_label.add_theme_color_override("font_color", COLOR_TEXT)
	_timer_label.add_theme_font_size_override("font_size", 32)
	_timer_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	timer_block.add_child(_timer_label)

func _build_stat_block(name: String, title: String, color: Color) -> Control:
	var block := VBoxContainer.new()
	block.add_theme_constant_override("separation", 4)

	var title_label := Label.new()
	title_label.text = title
	title_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	title_label.add_theme_font_size_override("font_size", 10)
	block.add_child(title_label)

	var value_row := HBoxContainer.new()
	value_row.add_theme_constant_override("separation", 8)
	block.add_child(value_row)

	var value_label := Label.new()
	value_label.text = "0"
	value_label.add_theme_color_override("font_color", COLOR_TEXT)
	value_label.add_theme_font_size_override("font_size", 26)
	value_label.custom_minimum_size = Vector2(48, 0)
	value_row.add_child(value_label)
	_stat_labels[name] = value_label

	var bar_container := PanelContainer.new()
	bar_container.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var bar_bg := StyleBoxFlat.new()
	bar_bg.bg_color = Color(0.08, 0.10, 0.14, 0.8)
	bar_bg.set_corner_radius_all(4)
	bar_bg.set_content_margin_all(2)
	bar_container.add_theme_stylebox_override("panel", bar_bg)
	value_row.add_child(bar_container)

	var bar_inner := Control.new()
	bar_inner.custom_minimum_size = Vector2(_stat_bar_max_width, 16)
	bar_container.add_child(bar_inner)

	var fill := ColorRect.new()
	fill.color = color
	fill.anchor_top = 0.0
	fill.anchor_bottom = 1.0
	fill.anchor_left = 0.0
	fill.size = Vector2(0, 16)
	bar_inner.add_child(fill)
	_stat_bars[name] = fill

	return block

func _set_stat(name: String, value: int) -> void:
	var clamped: int = clampi(value, 0, 100)
	if _stat_labels.has(name):
		_stat_labels[name].text = str(clamped)
	if _stat_bars.has(name):
		var fill: ColorRect = _stat_bars[name]
		fill.size = Vector2(_stat_bar_max_width * float(clamped) / 100.0, 16)

func _build_role_chip() -> void:
	var panel := PanelContainer.new()
	panel.anchor_left = 0.0
	panel.anchor_top = 1.0
	panel.anchor_bottom = 1.0
	panel.offset_left = 16
	panel.offset_right = 280
	panel.offset_top = -88
	panel.offset_bottom = -16
	add_child(panel)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_PANEL_BG
	style.set_corner_radius_all(10)
	style.set_border_width_all(1)
	style.border_color = Color(1, 1, 1, 0.08)
	style.set_content_margin_all(14)
	panel.add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 4)
	panel.add_child(vbox)

	_team_chip = Label.new()
	_team_chip.text = "—"
	_team_chip.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	_team_chip.add_theme_font_size_override("font_size", 12)
	vbox.add_child(_team_chip)

	_role_chip = Label.new()
	_role_chip.text = "—"
	_role_chip.add_theme_color_override("font_color", COLOR_TEXT)
	_role_chip.add_theme_font_size_override("font_size", 22)
	vbox.add_child(_role_chip)

	var hint := Label.new()
	hint.text = "ESC = Menü"
	hint.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	hint.add_theme_font_size_override("font_size", 11)
	vbox.add_child(hint)

func _build_roster_panel() -> void:
	var panel := PanelContainer.new()
	panel.anchor_right = 1.0
	panel.anchor_top = 0.0
	panel.anchor_bottom = 1.0
	panel.offset_left = -260
	panel.offset_right = -16
	panel.offset_top = 110
	panel.offset_bottom = -110
	add_child(panel)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_PANEL_BG
	style.set_corner_radius_all(10)
	style.set_border_width_all(1)
	style.border_color = Color(1, 1, 1, 0.08)
	style.set_content_margin_all(14)
	panel.add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	panel.add_child(vbox)

	var title := Label.new()
	title.text = "SPIELER"
	title.add_theme_color_override("font_color", COLOR_ACCENT)
	title.add_theme_font_size_override("font_size", 12)
	vbox.add_child(title)

	_roster = VBoxContainer.new()
	_roster.add_theme_constant_override("separation", 6)
	vbox.add_child(_roster)

func _build_map_label() -> void:
	_map_label = Label.new()
	_map_label.anchor_left = 0.5
	_map_label.anchor_right = 0.5
	_map_label.anchor_bottom = 1.0
	_map_label.offset_left = -150
	_map_label.offset_right = 150
	_map_label.offset_top = -28
	_map_label.offset_bottom = -8
	_map_label.text = "Map: %s" % _map_name
	_map_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_map_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	_map_label.add_theme_font_size_override("font_size", 12)
	add_child(_map_label)

func _update_roster(players: Array) -> void:
	if _roster == null:
		return
	for child in _roster.get_children():
		child.queue_free()
	for p in players:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		var dot := ColorRect.new()
		var color_hex := str(p.get("color", "#888888"))
		dot.color = Color(color_hex) if color_hex.begins_with("#") else Color(0.5, 0.5, 0.5)
		if not bool(p.get("isAlive", true)):
			dot.color.a = 0.35
		dot.custom_minimum_size = Vector2(12, 12)
		row.add_child(dot)
		var name_label := Label.new()
		var name_str := str(p.get("name", "?"))
		if str(p.get("id", "")) == _player_id:
			name_str += "  (du)"
		name_label.text = name_str
		name_label.add_theme_color_override(
			"font_color",
			COLOR_TEXT if bool(p.get("isAlive", true)) else COLOR_TEXT_DIM
		)
		name_label.add_theme_font_size_override("font_size", 14)
		row.add_child(name_label)
		_roster.add_child(row)

func _format_timer(seconds: int) -> String:
	var s: int = maxi(0, seconds)
	var m: int = s / 60
	var sec: int = s % 60
	return "%02d:%02d" % [m, sec]
