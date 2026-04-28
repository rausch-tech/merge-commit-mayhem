extends CanvasLayer

# Signals: HUD-Buttons schicken Signals statt direkt WS — world.gd haengt
# sich dran und sendet die richtige Message. So bleibt das HUD WS-frei und
# testbar.
signal ability_pressed
signal sabotage_pressed(sabotage_id: String)
# vote_pressed(target_id) — "" target_id = skip-vote.
signal vote_pressed(target_id: String)
# Tier 4.10 — Proximity-Action-Buttons.
signal takedown_pressed(target_player_id: String)
signal report_pressed(body_id: String)
signal vent_pressed(vent_id: String)

# Game HUD — overlays the 3D world with stat bars, timer, role chip, and a
# right-side player roster. Pure UI; updates come from world.gd via:
#   - apply_game_state(state)         — team-level stats (release, pipeline,
#                                       team-coffee-Mittelwert, incidents)
#   - apply_private_state(state)      — per-Owner: persoenliche Coffee-Energie,
#                                       Cooldowns. Separat von apply_game_state
#                                       weil das Wire-Format zwei Coffee-Werte
#                                       hat (game_state.coffeeLevel = team,
#                                       private_state.coffeeEnergy = self).
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
var _personal_coffee_fill: ColorRect
var _personal_coffee_max_width: float = 180.0
var _task_prompt_panel: PanelContainer
var _task_prompt_label: Label
var _task_prompt_fill: ColorRect
var _task_prompt_fill_max_width: float = 220.0
var _eventfeed: RichTextLabel
# Hoechste seq die wir schon ausgegeben haben — verhindert doppelte Lines
# wenn der gleiche game_state mehrfach kommt (Reconnect, Throttling).
var _eventfeed_last_seq: int = -1
# Role-Intro-Modal — zeigt sich einmalig pro private_role-Payload.
var _role_intro_panel: PanelContainer
var _role_intro_dismiss_timer: Timer
var _role_intro_shown_for: String = ""  # "<role>:<team>" Dedupe-Key
# Personal-Task-Panel (4.5.1) — links, listet alle Tasks mit Stern fuer eigene.
var _personal_task_panel: PanelContainer
var _personal_task_list: VBoxContainer
# Ability-Button (4.5.3) — sendet use_ability via Signal an world.gd.
var _ability_btn: Button
var _ability_hint_label: Label
var _ability_used: bool = false
var _phase: String = ""
# Coffee-Pulse (4.5.2) — Sinus-Modulation der Personal-Coffee-Bar wenn
# Energie < 15 (Speed-Penalty-Threshold).
var _coffee_ratio: float = 1.0
var _pulse_clock: float = 0.0
const COFFEE_PULSE_THRESHOLD: float = 0.15
# Sabotage-Strip (4.7) — bottom-center, nur sichtbar fuer Chaos-Rollen.
var _sabotage_strip: PanelContainer
var _sabotage_buttons_box: HBoxContainer
var _sabotage_button_nodes: Dictionary = {}  # id -> {btn, cd_label}
var _sabotage_states: Dictionary = {}        # id -> {cooldown, active}
var _available_sabotages: Array = []
var _is_chaos: bool = false
# Meeting + Voting (4.8) — Modal-Overlay, sichtbar wenn phase=meeting.
var _meeting_modal: PanelContainer
var _meeting_title: Label
var _meeting_context_label: RichTextLabel
var _meeting_vote_box: VBoxContainer
var _voting_already_cast: bool = false
# Voting-Result-Toast.
var _voting_toast: PanelContainer
var _voting_toast_label: RichTextLabel
var _voting_toast_timer: Timer
# Endscreen-Modal (4.9) — sichtbar wenn phase=ended + game_state.finalSummary.
var _endscreen_modal: PanelContainer
var _endscreen_built: bool = false
# Signal: Host klickt "Zurueck zur Lobby" — world.gd routet zu return_to_lobby.
signal return_to_lobby_pressed
# Proximity-Action-Buttons (4.10) — bottom-left ueber dem Role-Chip.
var _action_buttons_panel: PanelContainer
var _takedown_btn: Button
var _report_btn: Button
var _vent_btn: Button
var _last_takedown_target: String = ""
var _last_report_body: String = ""
var _last_vent_id: String = ""
# Sabotage-VFX (4.10.y) — Lights-Out-Vignette + Comms-Down-State.
var _lights_overlay: ColorRect
var _comms_down: bool = false
# Ghost-Banner (4.10.z) — sichtbar wenn local player isAlive=false.
var _ghost_banner: Label
var _is_ghost: bool = false
# Kill-Flash (4.10 Polish) — voller Screen-Edge-Tint beim Kill-Event.
var _kill_flash: ColorRect
var _kill_flash_tween: Tween
# Phase-Transition-Banner (4.11/Demo) — kurzer Mid-Screen-Text beim Wechsel.
var _phase_banner_label: Label
var _phase_banner_tween: Tween
var _last_phase_for_banner: String = ""
# Confetti-Particles auf dem Endscreen (4.11/Demo) — CPUParticles2D.
var _confetti: CPUParticles2D

func _ready() -> void:
	_build_top_bar()
	_build_role_chip()
	_build_personal_task_panel()
	_build_roster_panel()
	_build_eventfeed_panel()
	_build_role_intro_modal()
	_build_sabotage_strip()
	_build_meeting_modal()
	_build_voting_toast()
	_build_action_buttons_panel()
	_build_lights_overlay()
	_build_ghost_banner()
	_build_kill_flash()
	_build_phase_banner()
	_build_confetti()
	_build_map_label()
	_build_task_prompt()
	apply_game_state({})


func _process(delta: float) -> void:
	# Coffee-Pulse: sinus-moduliert die Helligkeit der Personal-Coffee-Bar
	# wenn die Energie unter dem Speed-Penalty-Threshold liegt. Zieht
	# Aufmerksamkeit ohne den Spieler aus dem Game-Flow zu reissen.
	if _personal_coffee_fill == null:
		return
	if _coffee_ratio < COFFEE_PULSE_THRESHOLD:
		_pulse_clock += delta
		var pulse: float = 0.6 + 0.4 * sin(_pulse_clock * 6.0)  # 0.2..1.0 hin und her
		_personal_coffee_fill.modulate = Color(1.0, 0.4, 0.3, pulse)
	else:
		_pulse_clock = 0.0
		_personal_coffee_fill.modulate = Color(1.0, 1.0, 1.0, 1.0)

# Public API ----------------------------------------------------------------

func set_player_id(id: String) -> void:
	_player_id = id

func set_map_name(name: String) -> void:
	_map_name = name
	if _map_label != null:
		_map_label.text = "Map: %s" % name

func set_role_info(role_info: Dictionary) -> void:
	_role_info = role_info
	var role_id := str(role_info.get("role", ""))
	var team := str(role_info.get("team", ""))
	# Modal nur einmal pro role+team-Kombination zeigen — wenn Server uns
	# erneut die gleiche Rolle schickt (Reconnect, Round-Restart), nicht
	# nochmal ueberblenden. Bei Wechsel der Rolle (z.B. neuer Round mit
	# anderer Verteilung) erneut zeigen.
	if role_id != "":
		var key := "%s:%s" % [role_id, team]
		if key != _role_intro_shown_for:
			_role_intro_shown_for = key
			_show_role_intro(role_info)
	if _role_chip == null:
		return
	var role_label := role_id.replace("_", " ").capitalize()
	_role_chip.text = role_label if role_label != "" else "—"
	if team == "chaos_agents":
		_team_chip.text = "CHAOS-AGENT"
		_team_chip.add_theme_color_override("font_color", COLOR_DANGER)
	elif team == "release_team":
		_team_chip.text = "RELEASE-TEAM"
		_team_chip.add_theme_color_override("font_color", COLOR_ACCENT)
	else:
		_team_chip.text = "—"
		_team_chip.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	# Ability-Button-Label aus role_info ableiten + neu evaluieren.
	_refresh_ability_button()
	# Sabotage-Strip: Liste der verfuegbaren Sabotagen aus role_info auslesen,
	# Buttons im Strip rebuilden. Sichtbarkeit (Chaos-only) wird drin
	# entschieden — set_role_info ist die einzige Quelle fuer "bin ich Chaos".
	_is_chaos = team == "chaos_agents"
	_available_sabotages = role_info.get("availableSabotages", [])
	_rebuild_sabotage_buttons()
	# Personal-Tasks rendern beim naechsten game_state-Tick mit den neuen
	# assignedTaskIds — Server-Tickrate ist 20 Hz, das ist <50 ms verzoegert.

func set_task_prompt(task_id: String, progress: float, holding: bool) -> void:
	# task_id == "" = nichts in Reichweite, Prompt verstecken.
	# holding == true = Spieler haelt gerade E auf diesem Task; zeig den
	# Progress-Balken statt nur "[E] HALTEN".
	if _task_prompt_panel == null:
		return
	if task_id == "":
		_task_prompt_panel.visible = false
		return
	_task_prompt_panel.visible = true
	if holding:
		_task_prompt_label.text = "%s · halten ..." % task_id
		_task_prompt_label.add_theme_color_override("font_color", COLOR_ACCENT)
	else:
		_task_prompt_label.text = "[E] halten — %s" % task_id
		_task_prompt_label.add_theme_color_override("font_color", COLOR_TEXT)
	if _task_prompt_fill != null:
		_task_prompt_fill.size = Vector2(_task_prompt_fill_max_width * clampf(progress, 0.0, 1.0), 6)

func apply_private_state(state: Dictionary) -> void:
	var energy: float = float(state.get("coffeeEnergy", 100.0))
	var max_e: float = float(state.get("coffeeMax", 100.0))
	if max_e <= 0.0:
		max_e = 100.0
	var ratio: float = clampf(energy / max_e, 0.0, 1.0)
	_coffee_ratio = ratio  # _process liest das fuer den Pulse
	if _personal_coffee_fill != null:
		_personal_coffee_fill.size = Vector2(_personal_coffee_max_width * ratio, 8)
	# Ability-Button: nach jedem private_state-Tick refreshen (used-Flag).
	_ability_used = bool(state.get("abilityUsed", false))
	_refresh_ability_button()

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
		var phase_now: String = str(state.get("phase", ""))
		# 4.11/Demo: Timer rot wenn unter 60 s waehrend playing.
		if seconds <= 60 and phase_now == "playing":
			_timer_label.add_theme_color_override("font_color", COLOR_DANGER)
		else:
			_timer_label.add_theme_color_override("font_color", COLOR_TEXT)

	# Phase chip + transition banner
	var prev_phase: String = _phase
	_phase = str(state.get("phase", ""))
	if _phase != prev_phase and _phase != "":
		_show_phase_banner_for(_phase)
	if _phase_label != null:
		match _phase:
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

	# Ghost-Banner: lokaler Spieler in players[]-Liste suchen.
	_apply_ghost_banner(state.get("players", []))

	# Eventfeed: append nur die neuen Events seit dem letzten Tick.
	_update_eventfeed(state.get("events", []))

	# Personal-Task-Panel: aktualisieren mit aktuellen Task-Status.
	_update_personal_tasks(state.get("tasks", []))

	# Ability-Button neu evaluieren (phase wechselt = Sichtbarkeit wechselt).
	_refresh_ability_button()

	# Sabotage-Strip: Cooldowns aus dem game_state.sabotages cachen.
	_cache_sabotage_states(state.get("sabotages", []))
	_refresh_sabotage_buttons()
	# Sabotage-VFX (Tier 4.10.y): lights_out -> Vignette, comms_outage -> tasks-blank.
	_apply_sabotage_vfx(state.get("sabotages", []))

	# Meeting-Modal: zeigt sich nur waehrend phase=meeting, schliesst sich beim
	# naechsten phase=playing/ended automatisch.
	_update_meeting_modal(state.get("meeting", null), int(state.get("remainingSeconds", 0)))

	# Endscreen: zeigt sich wenn phase=ended UND finalSummary mitgekommen ist.
	# game_ended-Message ist nur Trigger; Awards/Postmortem leben in
	# game_state.finalSummary (Tier 3.7).
	if _phase == "ended":
		var summary: Variant = state.get("finalSummary", null)
		if typeof(summary) == TYPE_DICTIONARY:
			show_endscreen(summary)
		_set_confetti_active(true)
	else:
		hide_endscreen()
		_set_confetti_active(false)

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

	# Persoenliche Coffee-Energie (private_state.coffeeEnergy / coffeeMax) —
	# bewusst optisch klar getrennt vom Team-Coffee-Stat-Pill oben (anderer
	# Akzent + thinner). Default voll, wird via apply_private_state geupdated.
	var coffee_row := HBoxContainer.new()
	coffee_row.add_theme_constant_override("separation", 6)
	vbox.add_child(coffee_row)

	var coffee_label := Label.new()
	coffee_label.text = "ENERGIE"
	coffee_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	coffee_label.add_theme_font_size_override("font_size", 10)
	coffee_label.custom_minimum_size = Vector2(58, 0)
	coffee_row.add_child(coffee_label)

	var bar_container := PanelContainer.new()
	bar_container.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var bar_bg := StyleBoxFlat.new()
	bar_bg.bg_color = Color(0.08, 0.10, 0.14, 0.8)
	bar_bg.set_corner_radius_all(3)
	bar_bg.set_content_margin_all(2)
	bar_container.add_theme_stylebox_override("panel", bar_bg)
	coffee_row.add_child(bar_container)

	var bar_inner := Control.new()
	bar_inner.custom_minimum_size = Vector2(_personal_coffee_max_width, 8)
	bar_container.add_child(bar_inner)

	_personal_coffee_fill = ColorRect.new()
	_personal_coffee_fill.color = COLOR_ACCENT
	_personal_coffee_fill.anchor_top = 0.0
	_personal_coffee_fill.anchor_bottom = 1.0
	_personal_coffee_fill.anchor_left = 0.0
	_personal_coffee_fill.size = Vector2(_personal_coffee_max_width, 8)
	bar_inner.add_child(_personal_coffee_fill)

	var hint := Label.new()
	hint.text = "ESC = Menü"
	hint.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	hint.add_theme_font_size_override("font_size", 11)
	vbox.add_child(hint)

func _build_roster_panel() -> void:
	var panel := PanelContainer.new()
	# Anchor right edge: both left and right anchors must be 1.0 so the panel
	# stays a fixed 244px wide on the right (offset_left = -260, offset_right = -16).
	# Without anchor_left = 1.0 the panel stretches from x=-260 to x=screen_width-16
	# and looks like a giant semi-transparent overlay covering the playfield.
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.anchor_top = 0.0
	# Top-Half der rechten Seite (Roster). Bottom-Half ist der Eventfeed
	# (siehe _build_eventfeed_panel) — beide teilen sich die ~500 px hoehe.
	panel.anchor_bottom = 0.0
	panel.offset_left = -260
	panel.offset_right = -16
	panel.offset_top = 110
	panel.offset_bottom = 320
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
	# Anchor bottom-center: both top and bottom anchors at 1.0 so the label
	# stays a thin strip just above the bottom edge instead of stretching
	# from y=-28 to y=712 (which it does without anchor_top set).
	_map_label.anchor_left = 0.5
	_map_label.anchor_right = 0.5
	_map_label.anchor_top = 1.0
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

func _build_eventfeed_panel() -> void:
	# Rechte Seite, unter dem Roster. Live-Log: Tasks, Sabotagen, Kills,
	# Phase-Wechsel, AI-Flavor-Texte vom Server. RichTextLabel mit BBCode
	# fuer Severity-Farben (info/warn/error). Auto-scroll zum neuesten.
	var panel := PanelContainer.new()
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.anchor_top = 0.0
	panel.anchor_bottom = 1.0
	panel.offset_left = -260
	panel.offset_right = -16
	panel.offset_top = 332
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
	title.text = "EVENTS"
	title.add_theme_color_override("font_color", COLOR_ACCENT)
	title.add_theme_font_size_override("font_size", 12)
	vbox.add_child(title)

	_eventfeed = RichTextLabel.new()
	_eventfeed.bbcode_enabled = true
	_eventfeed.scroll_following = true  # auto-scroll zur neuesten Zeile
	_eventfeed.fit_content = false
	_eventfeed.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_eventfeed.add_theme_color_override("default_color", COLOR_TEXT_DIM)
	_eventfeed.add_theme_font_size_override("normal_font_size", 12)
	_eventfeed.text = "[i]Noch nichts passiert.[/i]"
	vbox.add_child(_eventfeed)


func _update_eventfeed(events: Array) -> void:
	if _eventfeed == null:
		return
	var newest_seq := _eventfeed_last_seq
	for e in events:
		var seq := int(e.get("seq", 0))
		if seq <= _eventfeed_last_seq:
			continue
		if seq > newest_seq:
			newest_seq = seq
		var severity := str(e.get("severity", "info"))
		var message := str(e.get("message", "?"))
		var color: String = "888d96"  # default grey
		match severity:
			"warn":
				color = "f5b042"
			"error":
				color = "ef6464"
			"info":
				color = "9ea4ad"
		# Bei der allerersten neuen Line den "Noch nichts"-Placeholder ersetzen.
		if _eventfeed_last_seq < 0 and _eventfeed.text.find("Noch nichts") != -1:
			_eventfeed.text = ""
		_eventfeed.append_text("[color=#%s]%s[/color]\n" % [color, message])
	_eventfeed_last_seq = newest_seq


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

func _build_task_prompt() -> void:
	# Bottom-center Prompt fuer Task-Interaction. Sichtbar wenn Spieler in
	# Reichweite eines Tasks ist; zeigt entweder "[E] halten — TASK_ID" oder
	# (waehrend Hold) den Task-Progress.
	_task_prompt_panel = PanelContainer.new()
	_task_prompt_panel.anchor_left = 0.5
	_task_prompt_panel.anchor_right = 0.5
	_task_prompt_panel.anchor_bottom = 1.0
	_task_prompt_panel.anchor_top = 1.0
	_task_prompt_panel.offset_left = -160
	_task_prompt_panel.offset_right = 160
	_task_prompt_panel.offset_top = -100
	_task_prompt_panel.offset_bottom = -50
	_task_prompt_panel.visible = false
	add_child(_task_prompt_panel)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_PANEL_BG
	style.set_corner_radius_all(8)
	style.set_border_width_all(1)
	style.border_color = Color(1, 1, 1, 0.10)
	style.set_content_margin_all(10)
	_task_prompt_panel.add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 4)
	_task_prompt_panel.add_child(vbox)

	_task_prompt_label = Label.new()
	_task_prompt_label.text = ""
	_task_prompt_label.add_theme_color_override("font_color", COLOR_TEXT)
	_task_prompt_label.add_theme_font_size_override("font_size", 13)
	_task_prompt_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(_task_prompt_label)

	# Progress-Bar — Server-driven (game_state.tasks[].progress).
	var bar_container := PanelContainer.new()
	bar_container.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var bar_bg := StyleBoxFlat.new()
	bar_bg.bg_color = Color(0.08, 0.10, 0.14, 0.8)
	bar_bg.set_corner_radius_all(2)
	bar_bg.set_content_margin_all(1)
	bar_container.add_theme_stylebox_override("panel", bar_bg)
	vbox.add_child(bar_container)

	var bar_inner := Control.new()
	bar_inner.custom_minimum_size = Vector2(_task_prompt_fill_max_width, 6)
	bar_container.add_child(bar_inner)

	_task_prompt_fill = ColorRect.new()
	_task_prompt_fill.color = COLOR_ACCENT
	_task_prompt_fill.anchor_top = 0.0
	_task_prompt_fill.anchor_bottom = 1.0
	_task_prompt_fill.anchor_left = 0.0
	_task_prompt_fill.size = Vector2(0, 6)
	bar_inner.add_child(_task_prompt_fill)


# Role-Intro-Modal — beim ersten private_role-Payload pro Round, 30 s Auto-Dismiss
# oder Click-to-close. Zeigt Rolle + Team + Description + Strengths + Ability +
# AssignedTasks. Mirror des JS-Clients (static/role_intro.js).

const ROLE_INTRO_AUTO_DISMISS_SECONDS: float = 30.0
const COLOR_TEAM_RELEASE: Color = Color(0.30, 0.85, 0.45)
const COLOR_TEAM_CHAOS: Color = Color(0.95, 0.40, 0.40)


func _build_role_intro_modal() -> void:
	# Vollflaechige semi-transparente Overlay — fangs Clicks ab und schliesst
	# das Modal beim Click anywhere (analog zu JS-Client).
	_role_intro_panel = PanelContainer.new()
	_role_intro_panel.anchor_left = 0.5
	_role_intro_panel.anchor_top = 0.5
	_role_intro_panel.anchor_right = 0.5
	_role_intro_panel.anchor_bottom = 0.5
	_role_intro_panel.offset_left = -260
	_role_intro_panel.offset_top = -200
	_role_intro_panel.offset_right = 260
	_role_intro_panel.offset_bottom = 200
	_role_intro_panel.visible = false

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.06, 0.09, 0.13, 0.97)
	style.set_corner_radius_all(14)
	style.set_border_width_all(2)
	style.border_color = COLOR_ACCENT
	style.shadow_color = Color(0, 0, 0, 0.6)
	style.shadow_size = 32
	style.set_content_margin_all(28)
	_role_intro_panel.add_theme_stylebox_override("panel", style)
	add_child(_role_intro_panel)

	_role_intro_dismiss_timer = Timer.new()
	_role_intro_dismiss_timer.one_shot = true
	_role_intro_dismiss_timer.timeout.connect(_hide_role_intro)
	add_child(_role_intro_dismiss_timer)

	_role_intro_panel.gui_input.connect(_on_role_intro_clicked)


func _on_role_intro_clicked(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		_hide_role_intro()


func _show_role_intro(role_info: Dictionary) -> void:
	if _role_intro_panel == null:
		return
	# Children leeren und neu aufbauen — einmaliger Build pro Show-Call.
	for child in _role_intro_panel.get_children():
		child.queue_free()

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 14)
	_role_intro_panel.add_child(vbox)

	# Team-Badge
	var team := str(role_info.get("team", ""))
	var team_label := Label.new()
	if team == "release_team":
		team_label.text = "RELEASE-TEAM"
		team_label.add_theme_color_override("font_color", COLOR_TEAM_RELEASE)
	elif team == "chaos_agents":
		team_label.text = "CHAOS-AGENT"
		team_label.add_theme_color_override("font_color", COLOR_TEAM_CHAOS)
	else:
		team_label.text = team.to_upper()
		team_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	team_label.add_theme_font_size_override("font_size", 14)
	vbox.add_child(team_label)

	# Role title
	var title_text := str(role_info.get("title", ""))
	if title_text == "":
		title_text = str(role_info.get("role", "?")).replace("_", " ").capitalize()
	var title := Label.new()
	title.text = title_text
	title.add_theme_color_override("font_color", COLOR_TEXT)
	title.add_theme_font_size_override("font_size", 28)
	vbox.add_child(title)

	# Short blurb (1 line)
	var blurb := str(role_info.get("shortBlurb", ""))
	if blurb != "":
		var blurb_label := Label.new()
		blurb_label.text = blurb
		blurb_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
		blurb_label.add_theme_font_size_override("font_size", 14)
		blurb_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(blurb_label)

	# Full description (multi-line)
	var description := str(role_info.get("description", ""))
	if description != "":
		var desc_label := Label.new()
		desc_label.text = description
		desc_label.add_theme_color_override("font_color", COLOR_TEXT)
		desc_label.add_theme_font_size_override("font_size", 13)
		desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(desc_label)

	# Strengths — wo die Rolle 1.35x schneller ist
	var strengths: Array = role_info.get("strengthCategories", [])
	if strengths.size() > 0:
		var s_label := Label.new()
		s_label.text = "Stark in: %s" % ", ".join(strengths)
		s_label.add_theme_color_override("font_color", COLOR_ACCENT)
		s_label.add_theme_font_size_override("font_size", 13)
		s_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(s_label)

	# Ability
	var ability_label_text := str(role_info.get("abilityLabel", ""))
	var ability_hint := str(role_info.get("abilityHint", ""))
	if ability_label_text != "":
		var a_block := VBoxContainer.new()
		a_block.add_theme_constant_override("separation", 2)
		var a_title := Label.new()
		a_title.text = "Faehigkeit: %s" % ability_label_text
		a_title.add_theme_color_override("font_color", COLOR_STAT_PIPELINE)
		a_title.add_theme_font_size_override("font_size", 13)
		a_block.add_child(a_title)
		if ability_hint != "":
			var a_hint := Label.new()
			a_hint.text = ability_hint
			a_hint.add_theme_color_override("font_color", COLOR_TEXT_DIM)
			a_hint.add_theme_font_size_override("font_size", 12)
			a_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			a_block.add_child(a_hint)
		vbox.add_child(a_block)

	# Assigned tasks
	var task_ids: Array = role_info.get("assignedTaskIds", [])
	if task_ids.size() > 0:
		var t_label := Label.new()
		t_label.text = "Persoenliche Tasks: %s" % ", ".join(task_ids)
		t_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
		t_label.add_theme_font_size_override("font_size", 12)
		t_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(t_label)

	# Hint: click anywhere
	var hint := Label.new()
	hint.text = "Klick irgendwo, um zu schliessen (Auto in 30 s)"
	hint.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	hint.add_theme_font_size_override("font_size", 11)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(hint)

	_role_intro_panel.visible = true
	_role_intro_dismiss_timer.start(ROLE_INTRO_AUTO_DISMISS_SECONDS)


func _hide_role_intro() -> void:
	if _role_intro_panel != null:
		_role_intro_panel.visible = false
	if _role_intro_dismiss_timer != null:
		_role_intro_dismiss_timer.stop()


# Personal-Task-Panel (4.5.1) — links, listet alle Tasks aus game_state.tasks.
# Eigene Tasks (in role_info.assignedTaskIds) bekommen einen gelben Stern und
# eine accent-coloured Border. Status pro Task: available / in_progress (X%) /
# cooldown (Ns).

const COLOR_PERSONAL_STAR: Color = Color(1.0, 0.84, 0.22)


func _build_personal_task_panel() -> void:
	var panel := PanelContainer.new()
	panel.anchor_left = 0.0
	panel.anchor_right = 0.0
	panel.anchor_top = 0.0
	panel.anchor_bottom = 1.0
	panel.offset_left = 16
	panel.offset_right = 260
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
	title.text = "AUFGABEN"
	title.add_theme_color_override("font_color", COLOR_ACCENT)
	title.add_theme_font_size_override("font_size", 12)
	vbox.add_child(title)

	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(scroll)

	_personal_task_list = VBoxContainer.new()
	_personal_task_list.add_theme_constant_override("separation", 4)
	_personal_task_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_personal_task_list)

	_personal_task_panel = panel


func _update_personal_tasks(tasks: Array) -> void:
	if _personal_task_list == null:
		return
	for child in _personal_task_list.get_children():
		child.queue_free()
	# Comms-Outage Sabotage (4.10.y) — Release-Team kann keine Tasks mehr
	# sehen. Chaos sieht weiter (sie haben Fake-Tasks, die ueberhaupt nicht
	# entry).
	if _comms_down and not _is_chaos:
		var blocked := Label.new()
		blocked.text = "[ COMMS DOWN — Tasks gesperrt ]"
		blocked.add_theme_color_override("font_color", COLOR_DANGER)
		blocked.add_theme_font_size_override("font_size", 12)
		_personal_task_list.add_child(blocked)
		return
	if tasks.is_empty():
		var empty := Label.new()
		empty.text = "Keine Tasks aktiv."
		empty.add_theme_color_override("font_color", COLOR_TEXT_DIM)
		empty.add_theme_font_size_override("font_size", 12)
		_personal_task_list.add_child(empty)
		return
	var assigned: Array = _role_info.get("assignedTaskIds", [])
	# Zuerst eigene Tasks (sortiert nach Anchor-Order), dann der Rest.
	var personal: Array = []
	var rest: Array = []
	for t in tasks:
		if str(t.get("id", "")) in assigned:
			personal.append(t)
		else:
			rest.append(t)
	for t in personal:
		_personal_task_list.add_child(_make_task_row(t, true))
	for t in rest:
		_personal_task_list.add_child(_make_task_row(t, false))


func _make_task_row(task: Dictionary, is_mine: bool) -> Control:
	var row := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.05, 0.07, 0.10, 0.7)
	style.set_corner_radius_all(4)
	style.set_content_margin_all(6)
	if is_mine:
		style.set_border_width_all(1)
		style.border_color = COLOR_PERSONAL_STAR
	row.add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 2)
	row.add_child(vbox)

	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 6)
	vbox.add_child(top)

	if is_mine:
		var star := Label.new()
		star.text = "★"
		star.add_theme_color_override("font_color", COLOR_PERSONAL_STAR)
		star.add_theme_font_size_override("font_size", 13)
		top.add_child(star)

	var title := Label.new()
	title.text = str(task.get("title", task.get("id", "?")))
	title.add_theme_color_override("font_color", COLOR_TEXT)
	title.add_theme_font_size_override("font_size", 12)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(title)

	var status_str := str(task.get("status", "available"))
	var status_label := Label.new()
	match status_str:
		"in_progress":
			var pct: int = int(round(float(task.get("progress", 0.0)) * 100.0))
			status_label.text = "%d%%" % pct
			status_label.add_theme_color_override("font_color", COLOR_WARN)
		"cooldown":
			var cd: float = float(task.get("cooldownRemaining", 0.0))
			status_label.text = "%ds" % int(round(cd))
			status_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
		_:
			status_label.text = "ok"
			status_label.add_theme_color_override("font_color", COLOR_ACCENT)
	status_label.add_theme_font_size_override("font_size", 11)
	top.add_child(status_label)

	var room := str(task.get("room", ""))
	if room != "":
		var room_label := Label.new()
		room_label.text = room.replace("_", " ")
		room_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
		room_label.add_theme_font_size_override("font_size", 10)
		vbox.add_child(room_label)

	return row


# Active-Ability-Button (4.5.3) — sitzt unter dem Role-Chip-Block. Sichtbar
# nur wenn role_info eine ability_id hat, disabled bei abilityUsed=true oder
# phase!=playing. Click sendet das ability_pressed-Signal an world.gd, der
# damit `use_ability` ueber WS rausschickt.


func _ensure_ability_button_built() -> void:
	if _ability_btn != null:
		return
	# Wir haengen das Button an das role-chip-Panel — gleicher Footer-Block.
	# Suche das role-chip-panel ueber _role_chip's Parent.
	if _role_chip == null:
		return
	var role_vbox := _role_chip.get_parent()
	if role_vbox == null:
		return
	_ability_btn = Button.new()
	_ability_btn.text = "—"
	_ability_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_ability_btn.pressed.connect(_on_ability_button_pressed)
	role_vbox.add_child(_ability_btn)

	_ability_hint_label = Label.new()
	_ability_hint_label.text = ""
	_ability_hint_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	_ability_hint_label.add_theme_font_size_override("font_size", 10)
	_ability_hint_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	role_vbox.add_child(_ability_hint_label)


func _refresh_ability_button() -> void:
	var ability_id := str(_role_info.get("abilityId", ""))
	var label := str(_role_info.get("abilityLabel", ""))
	var hint := str(_role_info.get("abilityHint", ""))
	# Kein abilityId = keine Faehigkeit (Chaos-Rollen oder nicht-konfigurierte
	# Release-Rollen). Button wird gar nicht gebaut.
	if ability_id == "" or label == "":
		if _ability_btn != null:
			_ability_btn.visible = false
			if _ability_hint_label != null:
				_ability_hint_label.visible = false
		return
	_ensure_ability_button_built()
	_ability_btn.visible = true
	if _ability_hint_label != null:
		_ability_hint_label.visible = true
		_ability_hint_label.text = hint
	if _ability_used:
		_ability_btn.text = "%s (verbraucht)" % label
		_ability_btn.disabled = true
	elif _phase != "playing":
		_ability_btn.text = "%s (warte)" % label
		_ability_btn.disabled = true
	else:
		_ability_btn.text = label
		_ability_btn.disabled = false


func _on_ability_button_pressed() -> void:
	if _ability_used or _phase != "playing":
		return
	emit_signal("ability_pressed")


# Sabotage-Strip (4.7) — bottom-center, nur fuer Chaos-Rollen sichtbar.
# Pro verfuegbarer Sabotage ein Button mit Title + Cooldown-Sekunden.
# Click → emit_signal sabotage_pressed(id) → world.gd sendet trigger_sabotage.
# Server prueft Object-Binding-Reichweite + ob comms-down die Buttons disabled.

const COLOR_SABOTAGE_BG: Color = Color(0.10, 0.05, 0.05, 0.92)


func _build_sabotage_strip() -> void:
	_sabotage_strip = PanelContainer.new()
	_sabotage_strip.anchor_left = 0.5
	_sabotage_strip.anchor_right = 0.5
	_sabotage_strip.anchor_top = 1.0
	_sabotage_strip.anchor_bottom = 1.0
	_sabotage_strip.offset_left = -340
	_sabotage_strip.offset_right = 340
	_sabotage_strip.offset_top = -100
	_sabotage_strip.offset_bottom = -42
	_sabotage_strip.visible = false  # bis Role bekannt + Chaos
	add_child(_sabotage_strip)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_SABOTAGE_BG
	style.set_corner_radius_all(8)
	style.set_border_width_all(1)
	style.border_color = Color(0.95, 0.40, 0.40, 0.55)
	style.set_content_margin_all(8)
	_sabotage_strip.add_theme_stylebox_override("panel", style)

	_sabotage_buttons_box = HBoxContainer.new()
	_sabotage_buttons_box.add_theme_constant_override("separation", 6)
	_sabotage_buttons_box.alignment = BoxContainer.ALIGNMENT_CENTER
	_sabotage_strip.add_child(_sabotage_buttons_box)


func _rebuild_sabotage_buttons() -> void:
	if _sabotage_buttons_box == null:
		return
	# Visibility: nur Chaos sieht den Strip ueberhaupt. Bei Role-Reset auf
	# release_team / leer wird der Strip versteckt + leer gemacht.
	if not _is_chaos or _available_sabotages.is_empty():
		_sabotage_strip.visible = false
		for child in _sabotage_buttons_box.get_children():
			child.queue_free()
		_sabotage_button_nodes.clear()
		return
	# Wenn die gleiche Sabotage-Liste schon gerendert ist, nicht rebuilden —
	# sonst flackert der Strip auf jedem Role-Re-Send.
	var existing_ids: Array = []
	for c in _sabotage_buttons_box.get_children():
		if c.has_meta("sab_id"):
			existing_ids.append(str(c.get_meta("sab_id")))
	if existing_ids == _available_sabotages:
		_refresh_sabotage_buttons()
		return
	for child in _sabotage_buttons_box.get_children():
		child.queue_free()
	_sabotage_button_nodes.clear()
	_sabotage_strip.visible = true
	for sab_id in _available_sabotages:
		var sid := str(sab_id)
		var col := VBoxContainer.new()
		col.add_theme_constant_override("separation", 2)
		col.set_meta("sab_id", sid)
		var btn := Button.new()
		btn.text = _sabotage_label(sid)
		btn.custom_minimum_size = Vector2(110, 38)
		btn.pressed.connect(func(): emit_signal("sabotage_pressed", sid))
		col.add_child(btn)
		var cd_label := Label.new()
		cd_label.text = ""
		cd_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
		cd_label.add_theme_font_size_override("font_size", 10)
		cd_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		col.add_child(cd_label)
		_sabotage_buttons_box.add_child(col)
		_sabotage_button_nodes[sid] = {"btn": btn, "cd": cd_label}
	_refresh_sabotage_buttons()


func _cache_sabotage_states(sabotages: Array) -> void:
	# Wir cachen pro Sabotage-ID den letzten Cooldown + active-Flag aus dem
	# game_state. Per-Tick aufgerufen in apply_game_state.
	_sabotage_states.clear()
	for s in sabotages:
		var sid := str(s.get("id", ""))
		if sid == "":
			continue
		_sabotage_states[sid] = {
			"cooldown": float(s.get("cooldownRemaining", 0.0)),
			"active": bool(s.get("active", false)),
		}


func _refresh_sabotage_buttons() -> void:
	if not _is_chaos:
		return
	for sid_v in _sabotage_button_nodes.keys():
		var sid := str(sid_v)
		var nodes: Dictionary = _sabotage_button_nodes[sid]
		var btn: Button = nodes["btn"]
		var cd_label: Label = nodes["cd"]
		var st: Dictionary = _sabotage_states.get(sid, {})
		var cooldown: float = float(st.get("cooldown", 0.0))
		var active: bool = bool(st.get("active", false))
		if _phase != "playing":
			btn.disabled = true
			cd_label.text = "off"
		elif active:
			btn.disabled = true
			cd_label.text = "active"
		elif cooldown > 0.0:
			btn.disabled = true
			cd_label.text = "%ds" % int(round(cooldown))
		else:
			btn.disabled = false
			cd_label.text = ""


func _sabotage_label(sab_id: String) -> String:
	# Kurze Labels — Server-Title ist oft zu lang fuer 110px-Buttons.
	# Mirror der haeufigsten Sabotage-IDs aus app/game/sabotages.py.
	match sab_id:
		"ci_cd_red":              return "CI/CD Red"
		"coffee_outage":          return "Coffee Out"
		"mandatory_meeting":      return "Forced Meeting"
		"merge_conflict_storm":   return "Merge Storm"
		"fake_customer_request":  return "Fake CR"
		"flaky_tests":            return "Flaky Tests"
		"lights_out":             return "PagerDuty"
		"comms_outage":           return "Slack Down"
	return sab_id.replace("_", " ").capitalize()


# Meeting + Voting (4.8) — Modal-Overlay waehrend phase=meeting.
# Zeigt Reporter, Body-Location, RecentEvents als AI-flavored Stimmungs-
# Block, und Voting-Buttons pro lebendigem Spieler + Skip. Sendet
# vote_pressed(target_id) ueber Signal — world.gd routet zu cast_vote /
# skip_vote.

const COLOR_MEETING_BG: Color = Color(0.04, 0.06, 0.10, 0.96)
const COLOR_MEETING_BORDER: Color = Color(0.95, 0.70, 0.30, 0.85)
const COLOR_VOTING_TOAST_BG: Color = Color(0.06, 0.10, 0.06, 0.95)


func _build_meeting_modal() -> void:
	_meeting_modal = PanelContainer.new()
	_meeting_modal.anchor_left = 0.5
	_meeting_modal.anchor_top = 0.5
	_meeting_modal.anchor_right = 0.5
	_meeting_modal.anchor_bottom = 0.5
	_meeting_modal.offset_left = -300
	_meeting_modal.offset_top = -240
	_meeting_modal.offset_right = 300
	_meeting_modal.offset_bottom = 240
	_meeting_modal.visible = false

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_MEETING_BG
	style.set_corner_radius_all(14)
	style.set_border_width_all(2)
	style.border_color = COLOR_MEETING_BORDER
	style.shadow_color = Color(0, 0, 0, 0.7)
	style.shadow_size = 30
	style.set_content_margin_all(24)
	_meeting_modal.add_theme_stylebox_override("panel", style)
	add_child(_meeting_modal)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 12)
	_meeting_modal.add_child(vbox)

	_meeting_title = Label.new()
	_meeting_title.text = "EMERGENCY MEETING"
	_meeting_title.add_theme_color_override("font_color", COLOR_WARN)
	_meeting_title.add_theme_font_size_override("font_size", 24)
	vbox.add_child(_meeting_title)

	_meeting_context_label = RichTextLabel.new()
	_meeting_context_label.bbcode_enabled = true
	_meeting_context_label.fit_content = true
	_meeting_context_label.scroll_active = false
	_meeting_context_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_meeting_context_label.add_theme_color_override("default_color", COLOR_TEXT_DIM)
	_meeting_context_label.add_theme_font_size_override("normal_font_size", 12)
	vbox.add_child(_meeting_context_label)

	var vote_title := Label.new()
	vote_title.text = "Wer soll geremoved werden?"
	vote_title.add_theme_color_override("font_color", COLOR_ACCENT)
	vote_title.add_theme_font_size_override("font_size", 14)
	vbox.add_child(vote_title)

	_meeting_vote_box = VBoxContainer.new()
	_meeting_vote_box.add_theme_constant_override("separation", 4)
	_meeting_vote_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(_meeting_vote_box)


func _update_meeting_modal(meeting_data: Variant, remaining_seconds: int) -> void:
	if _meeting_modal == null:
		return
	if _phase != "meeting" or meeting_data == null:
		_meeting_modal.visible = false
		_voting_already_cast = false  # reset fuer naechstes Meeting
		return
	if not (typeof(meeting_data) == TYPE_DICTIONARY):
		return
	_meeting_modal.visible = true
	var ctx: Dictionary = meeting_data
	# Title mit Sekunden
	_meeting_title.text = "EMERGENCY MEETING — %ds" % remaining_seconds

	# Context block
	var lines: PackedStringArray = []
	var reporter: String = str(ctx.get("reporterName", ""))
	if reporter != "":
		lines.append("[color=#f5b042]Gemeldet von:[/color] %s" % reporter)
	var body: Variant = ctx.get("body", null)
	if typeof(body) == TYPE_DICTIONARY:
		var bd: Dictionary = body
		var victim: String = str(bd.get("victimName", "?"))
		var room: String = str(bd.get("room", "?")).replace("_", " ")
		lines.append("[color=#ef6464]Body:[/color] %s im [i]%s[/i]" % [victim, room])
	var recent: Array = ctx.get("recentEvents", [])
	if recent.size() > 0:
		lines.append("")
		lines.append("[color=#9ea4ad]Letzte Events:[/color]")
		var max_show: int = min(6, recent.size())
		for i in max_show:
			var e: Dictionary = recent[i]
			lines.append("• %s" % str(e.get("message", "")))
	_meeting_context_label.text = "\n".join(lines)

	# Voting buttons
	var alive: Array = ctx.get("alive", [])
	# Idempotent rebuild — nur wenn Liste sich geaendert hat.
	var existing_ids: Array = []
	for c in _meeting_vote_box.get_children():
		if c.has_meta("vote_id"):
			existing_ids.append(str(c.get_meta("vote_id")))
	var fresh_ids: Array = ["__skip__"]
	for a in alive:
		fresh_ids.append(str(a.get("id", "")))
	if existing_ids != fresh_ids or _voting_already_cast:
		for c in _meeting_vote_box.get_children():
			c.queue_free()
		var skip_btn := Button.new()
		skip_btn.text = "Skip"
		skip_btn.set_meta("vote_id", "__skip__")
		skip_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		skip_btn.disabled = _voting_already_cast
		skip_btn.pressed.connect(func(): _on_vote_pressed(""))
		_meeting_vote_box.add_child(skip_btn)
		for a in alive:
			var pid := str(a.get("id", ""))
			var pname := str(a.get("name", "?"))
			var btn := Button.new()
			btn.text = pname
			btn.set_meta("vote_id", pid)
			btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			btn.disabled = _voting_already_cast or pid == _player_id
			btn.pressed.connect(func(): _on_vote_pressed(pid))
			_meeting_vote_box.add_child(btn)


func _on_vote_pressed(target_id: String) -> void:
	if _voting_already_cast:
		return
	_voting_already_cast = true
	# Disable alle Buttons sofort.
	for c in _meeting_vote_box.get_children():
		if c is Button:
			c.disabled = true
	emit_signal("vote_pressed", target_id)


# Voting-Result-Toast — slide-in von oben, fade nach 5 s.

func _build_voting_toast() -> void:
	_voting_toast = PanelContainer.new()
	_voting_toast.anchor_left = 0.5
	_voting_toast.anchor_top = 0.0
	_voting_toast.anchor_right = 0.5
	_voting_toast.anchor_bottom = 0.0
	_voting_toast.offset_left = -260
	_voting_toast.offset_top = 100
	_voting_toast.offset_right = 260
	_voting_toast.offset_bottom = 200
	_voting_toast.visible = false

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_VOTING_TOAST_BG
	style.set_corner_radius_all(10)
	style.set_border_width_all(1)
	style.border_color = COLOR_ACCENT
	style.shadow_color = Color(0, 0, 0, 0.6)
	style.shadow_size = 20
	style.set_content_margin_all(16)
	_voting_toast.add_theme_stylebox_override("panel", style)
	add_child(_voting_toast)

	_voting_toast_label = RichTextLabel.new()
	_voting_toast_label.bbcode_enabled = true
	_voting_toast_label.fit_content = true
	_voting_toast_label.scroll_active = false
	_voting_toast_label.add_theme_color_override("default_color", COLOR_TEXT)
	_voting_toast_label.add_theme_font_size_override("normal_font_size", 13)
	_voting_toast.add_child(_voting_toast_label)

	_voting_toast_timer = Timer.new()
	_voting_toast_timer.one_shot = true
	_voting_toast_timer.timeout.connect(func(): _voting_toast.visible = false)
	add_child(_voting_toast_timer)


func show_voting_result(payload: Dictionary) -> void:
	if _voting_toast == null:
		return
	var lines: PackedStringArray = []
	var skipped: bool = bool(payload.get("skipped", false))
	var tie: bool = bool(payload.get("tie", false))
	var name: String = str(payload.get("removedPlayerName", ""))
	var was_chaos: bool = bool(payload.get("wasChaosAgent", false))
	var last_words: String = str(payload.get("lastWords", ""))
	if skipped:
		lines.append("[color=#9ea4ad]Skip-Vote — niemand wurde rausgevotet.[/color]")
	elif tie:
		lines.append("[color=#9ea4ad]Patt — niemand wurde rausgevotet.[/color]")
	elif name != "":
		var color: String = "ef6464" if was_chaos else "30c065"
		var team: String = "war Chaos-Agent" if was_chaos else "war Release-Team"
		lines.append("[color=#%s][b]%s wurde rausgevotet[/b][/color] (%s)." % [color, name, team])
	if last_words != "":
		lines.append("")
		lines.append("[i]\"%s\"[/i]" % last_words)
	_voting_toast_label.text = "\n".join(lines)
	_voting_toast.visible = true
	_voting_toast_timer.start(5.0)


# Endscreen (4.9) — Modal mit Win-Banner, Awards, Per-Player-Stats und
# AI-Postmortem-Block. Triggert beim phase=ended-Switch + finalSummary-Daten
# aus dem game_state. Reset-Button (host-only) sendet return_to_lobby.

const COLOR_WIN_RELEASE: Color = Color(0.30, 0.85, 0.45)
const COLOR_WIN_CHAOS: Color = Color(0.95, 0.40, 0.40)


func _build_endscreen_modal() -> void:
	if _endscreen_built:
		return
	_endscreen_built = true
	_endscreen_modal = PanelContainer.new()
	_endscreen_modal.anchor_left = 0.5
	_endscreen_modal.anchor_top = 0.5
	_endscreen_modal.anchor_right = 0.5
	_endscreen_modal.anchor_bottom = 0.5
	_endscreen_modal.offset_left = -340
	_endscreen_modal.offset_top = -260
	_endscreen_modal.offset_right = 340
	_endscreen_modal.offset_bottom = 260
	_endscreen_modal.visible = false

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.04, 0.06, 0.10, 0.97)
	style.set_corner_radius_all(14)
	style.set_border_width_all(2)
	style.border_color = COLOR_ACCENT
	style.shadow_color = Color(0, 0, 0, 0.7)
	style.shadow_size = 30
	style.set_content_margin_all(24)
	_endscreen_modal.add_theme_stylebox_override("panel", style)
	add_child(_endscreen_modal)


func show_endscreen(summary: Dictionary) -> void:
	_build_endscreen_modal()
	# Modal-Inhalt jedes Mal frisch rendern — finalSummary kommt nur einmal,
	# aber falls Reconnect spaeter dasselbe schickt, vermeiden wir
	# Stale-State.
	for child in _endscreen_modal.get_children():
		child.queue_free()

	var winner: String = str(summary.get("winner", ""))
	var reason: String = str(summary.get("reason", ""))
	var awards: Array = summary.get("awards", [])
	var per_player: Array = summary.get("perPlayer", [])
	var postmortem: String = str(summary.get("postmortem", ""))

	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_endscreen_modal.add_child(scroll)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 12)
	vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(vbox)

	# Banner
	var banner := Label.new()
	if winner == "release_team":
		banner.text = "RELEASE-TEAM GEWINNT"
		banner.add_theme_color_override("font_color", COLOR_WIN_RELEASE)
	elif winner == "chaos_agents":
		banner.text = "CHAOS-AGENTEN GEWINNEN"
		banner.add_theme_color_override("font_color", COLOR_WIN_CHAOS)
	else:
		banner.text = "RUNDE BEENDET"
		banner.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	banner.add_theme_font_size_override("font_size", 28)
	vbox.add_child(banner)

	if reason != "":
		var reason_label := Label.new()
		reason_label.text = reason
		reason_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
		reason_label.add_theme_font_size_override("font_size", 14)
		reason_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(reason_label)

	# Awards
	if awards.size() > 0:
		var awards_title := Label.new()
		awards_title.text = "AWARDS"
		awards_title.add_theme_color_override("font_color", COLOR_ACCENT)
		awards_title.add_theme_font_size_override("font_size", 14)
		vbox.add_child(awards_title)
		for a in awards:
			var aw_row := RichTextLabel.new()
			aw_row.bbcode_enabled = true
			aw_row.fit_content = true
			aw_row.scroll_active = false
			aw_row.add_theme_color_override("default_color", COLOR_TEXT)
			aw_row.add_theme_font_size_override("normal_font_size", 12)
			aw_row.text = "[b]%s[/b]: %s — %s" % [
				str(a.get("title", "?")),
				str(a.get("playerName", "?")),
				str(a.get("reason", "")),
			]
			vbox.add_child(aw_row)

	# Per-Player-Stats
	if per_player.size() > 0:
		var pp_title := Label.new()
		pp_title.text = "STATS"
		pp_title.add_theme_color_override("font_color", COLOR_ACCENT)
		pp_title.add_theme_font_size_override("font_size", 14)
		vbox.add_child(pp_title)
		for p in per_player:
			var row := RichTextLabel.new()
			row.bbcode_enabled = true
			row.fit_content = true
			row.scroll_active = false
			row.add_theme_color_override("default_color", COLOR_TEXT_DIM)
			row.add_theme_font_size_override("normal_font_size", 12)
			var team_color: String = "30c065" if str(p.get("team", "")) == "release_team" else "ef6464"
			var role_label: String = str(p.get("role", "")).replace("_", " ").capitalize()
			row.text = (
				"[color=#%s]%s[/color]  ·  %s  ·  Tasks: %d  ·  Sabotagen: %d  ·  Coffee: %s%s" % [
					team_color,
					str(p.get("name", "?")),
					role_label,
					int(p.get("tasksCompleted", 0)),
					int(p.get("sabotagesTriggered", 0)),
					str(p.get("coffeeFinal", 0.0)),
					"  ·  Ability used" if bool(p.get("abilityUsed", false)) else "",
				]
			)
			vbox.add_child(row)

	# AI-Postmortem
	if postmortem != "":
		var pm_title := Label.new()
		pm_title.text = "POSTMORTEM (AI)"
		pm_title.add_theme_color_override("font_color", COLOR_ACCENT)
		pm_title.add_theme_font_size_override("font_size", 14)
		vbox.add_child(pm_title)
		var pm := Label.new()
		pm.text = postmortem
		pm.add_theme_color_override("font_color", COLOR_TEXT)
		pm.add_theme_font_size_override("font_size", 12)
		pm.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		vbox.add_child(pm)

	# Reset-Button — sendet return_to_lobby (server entscheidet ob Host).
	var reset_btn := Button.new()
	reset_btn.text = "Zurueck zur Lobby"
	reset_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	reset_btn.pressed.connect(func(): emit_signal("return_to_lobby_pressed"))
	vbox.add_child(reset_btn)

	_endscreen_modal.visible = true


func hide_endscreen() -> void:
	if _endscreen_modal != null:
		_endscreen_modal.visible = false


# Proximity-Action-Buttons (4.10) — Take-Down + Report + Vent. world.gd
# berechnet pro Frame welche Targets in Reichweite sind und ruft
# set_proximity_actions(dict) — wir aktualisieren Buttons + visibility.

const COLOR_TAKEDOWN: Color = Color(0.95, 0.40, 0.40)
const COLOR_REPORT: Color = Color(0.95, 0.70, 0.30)
const COLOR_VENT: Color = Color(0.50, 0.30, 0.85)


func _build_action_buttons_panel() -> void:
	# Bottom-center, etwas hoeher als der Sabotage-Strip damit beide
	# nicht ueberlappen.
	_action_buttons_panel = PanelContainer.new()
	_action_buttons_panel.anchor_left = 0.5
	_action_buttons_panel.anchor_right = 0.5
	_action_buttons_panel.anchor_top = 1.0
	_action_buttons_panel.anchor_bottom = 1.0
	_action_buttons_panel.offset_left = -240
	_action_buttons_panel.offset_right = 240
	_action_buttons_panel.offset_top = -180
	_action_buttons_panel.offset_bottom = -110
	_action_buttons_panel.visible = false

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.05, 0.07, 0.10, 0.92)
	style.set_corner_radius_all(8)
	style.set_border_width_all(1)
	style.border_color = Color(1, 1, 1, 0.10)
	style.set_content_margin_all(8)
	_action_buttons_panel.add_theme_stylebox_override("panel", style)
	add_child(_action_buttons_panel)

	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 8)
	hbox.alignment = BoxContainer.ALIGNMENT_CENTER
	_action_buttons_panel.add_child(hbox)

	_takedown_btn = Button.new()
	_takedown_btn.text = "Force-Reboot"
	_takedown_btn.custom_minimum_size = Vector2(140, 40)
	_takedown_btn.add_theme_color_override("font_color", COLOR_TAKEDOWN)
	_takedown_btn.pressed.connect(func(): emit_signal("takedown_pressed", _last_takedown_target))
	_takedown_btn.visible = false
	hbox.add_child(_takedown_btn)

	_report_btn = Button.new()
	_report_btn.text = "Body melden"
	_report_btn.custom_minimum_size = Vector2(140, 40)
	_report_btn.add_theme_color_override("font_color", COLOR_REPORT)
	_report_btn.pressed.connect(func(): emit_signal("report_pressed", _last_report_body))
	_report_btn.visible = false
	hbox.add_child(_report_btn)

	_vent_btn = Button.new()
	_vent_btn.text = "Vent"
	_vent_btn.custom_minimum_size = Vector2(100, 40)
	_vent_btn.add_theme_color_override("font_color", COLOR_VENT)
	_vent_btn.pressed.connect(func(): emit_signal("vent_pressed", _last_vent_id))
	_vent_btn.visible = false
	hbox.add_child(_vent_btn)


func set_proximity_actions(actions: Dictionary) -> void:
	# actions = {takedownTargetId, takedownTargetName, reportBodyId, reportBodyName, ventId}
	if _action_buttons_panel == null:
		return
	_last_takedown_target = str(actions.get("takedownTargetId", ""))
	_last_report_body = str(actions.get("reportBodyId", ""))
	_last_vent_id = str(actions.get("ventId", ""))

	if _last_takedown_target != "":
		_takedown_btn.text = "Force-Reboot %s" % str(actions.get("takedownTargetName", "?"))
		_takedown_btn.visible = true
	else:
		_takedown_btn.visible = false

	if _last_report_body != "":
		_report_btn.text = "Body melden (%s)" % str(actions.get("reportBodyName", "?"))
		_report_btn.visible = true
	else:
		_report_btn.visible = false

	if _last_vent_id != "":
		_vent_btn.text = "Vent (%s)" % _last_vent_id
		_vent_btn.visible = true
	else:
		_vent_btn.visible = false

	# Panel ganz verstecken wenn nichts in Reichweite ist.
	_action_buttons_panel.visible = _takedown_btn.visible or _report_btn.visible or _vent_btn.visible


# Sabotage-VFX (4.10.y) — Lights-Out-Vignette + Comms-Down. Beide werden vom
# game_state.sabotages getrieben (active flag pro Sabotage-ID).

func _build_lights_overlay() -> void:
	# Vollflaechiger semi-transparenter dunkler Layer auf Layer-Top — wenn
	# active, blockiert er sicht aufs Spiel mit ~70 % Schwarz. Nicht-radial
	# (Godot-CanvasLayer ohne Shader = kein einfacher Radial-Cutout); JS-
	# Client hat einen Cutout-Vignette, hier reicht die flat-darken-Variante
	# fuer den ersten Wurf.
	_lights_overlay = ColorRect.new()
	_lights_overlay.color = Color(0, 0, 0, 0.72)
	_lights_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_lights_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_lights_overlay.visible = false
	add_child(_lights_overlay)


func _apply_sabotage_vfx(sabotages: Array) -> void:
	var lights_active: bool = false
	var comms_active: bool = false
	for s in sabotages:
		var sid := str(s.get("id", ""))
		var active: bool = bool(s.get("active", false))
		if sid == "lights_out":
			lights_active = active
		elif sid == "comms_outage":
			comms_active = active
	if _lights_overlay != null:
		_lights_overlay.visible = lights_active
	# Comms-Down state ist persistent waehrend Sabotage aktiv ist.
	if _comms_down != comms_active:
		_comms_down = comms_active
		# Re-render Tasks weil die Sicht sich gerade geaendert hat. (Wir
		# haben kein cached _last_tasks-Feld; die naechste game_state-Tick
		# wird sowieso neu rendern. Aber fuer den Wechsel-Moment ohne neuen
		# Tick: wir koennen das Personal-Task-Panel manuell leeren.)
		if _personal_task_list != null:
			for child in _personal_task_list.get_children():
				child.queue_free()


# Ghost-Banner (4.10.z) — visuelle Indikation wenn der lokale Spieler tot
# ist. Take-Down/Report/Sabotage-Buttons sind via die Alive-Gates schon
# aus, aber ohne Banner sehe ich als Geist nicht warum nichts mehr geht.

const COLOR_GHOST: Color = Color(0.65, 0.55, 0.85)


func _build_ghost_banner() -> void:
	_ghost_banner = Label.new()
	_ghost_banner.text = "★ Du bist coredumped — Spectator-Mode ★"
	_ghost_banner.anchor_left = 0.5
	_ghost_banner.anchor_right = 0.5
	_ghost_banner.anchor_top = 0.0
	_ghost_banner.anchor_bottom = 0.0
	_ghost_banner.offset_left = -200
	_ghost_banner.offset_right = 200
	_ghost_banner.offset_top = 92
	_ghost_banner.offset_bottom = 116
	_ghost_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_ghost_banner.add_theme_color_override("font_color", COLOR_GHOST)
	_ghost_banner.add_theme_font_size_override("font_size", 14)
	_ghost_banner.visible = false
	add_child(_ghost_banner)


func _apply_ghost_banner(players: Array) -> void:
	if _ghost_banner == null or _player_id == "":
		return
	var alive: bool = true
	for p in players:
		if str(p.get("id", "")) == _player_id:
			alive = bool(p.get("isAlive", true))
			break
	_is_ghost = not alive
	_ghost_banner.visible = _is_ghost


# Kill-Flash (4.10 Polish) — wenn ein Spieler stirbt, blitzt der Bildschirm
# kurz rot (alpha 0.45 -> 0 ueber 0.6 s). Wird von world.gd via
# trigger_kill_flash() aufgerufen.

func _build_kill_flash() -> void:
	_kill_flash = ColorRect.new()
	_kill_flash.color = Color(0.95, 0.1, 0.1, 0.0)
	_kill_flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	_kill_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_kill_flash)


func trigger_kill_flash() -> void:
	_play_full_screen_flash(Color(0.95, 0.10, 0.10), 0.45, 0.6)


func trigger_vent_flash() -> void:
	# Lila-Flash beim Vent-Use — visuelle Markierung "ich teleportiere".
	_play_full_screen_flash(Color(0.50, 0.30, 0.85), 0.55, 0.45)


func _play_full_screen_flash(color: Color, peak_alpha: float, fade_seconds: float) -> void:
	if _kill_flash == null:
		return
	if _kill_flash_tween != null and _kill_flash_tween.is_valid():
		_kill_flash_tween.kill()
	_kill_flash.color = Color(color.r, color.g, color.b, peak_alpha)
	_kill_flash_tween = create_tween()
	_kill_flash_tween.tween_property(_kill_flash, "color:a", 0.0, fade_seconds)


# Phase-Transition-Banner (4.11/Demo) — kurzer mid-screen Text bei jedem
# Phase-Wechsel. "RUNDE LAEUFT" / "MEETING TIME" / "RUNDE BEENDET".

func _build_phase_banner() -> void:
	_phase_banner_label = Label.new()
	_phase_banner_label.text = ""
	_phase_banner_label.anchor_left = 0.5
	_phase_banner_label.anchor_right = 0.5
	_phase_banner_label.anchor_top = 0.5
	_phase_banner_label.anchor_bottom = 0.5
	_phase_banner_label.offset_left = -300
	_phase_banner_label.offset_right = 300
	_phase_banner_label.offset_top = -50
	_phase_banner_label.offset_bottom = 50
	_phase_banner_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_phase_banner_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_phase_banner_label.add_theme_color_override("font_color", COLOR_ACCENT)
	_phase_banner_label.add_theme_font_size_override("font_size", 56)
	_phase_banner_label.add_theme_constant_override("outline_size", 8)
	_phase_banner_label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	_phase_banner_label.modulate.a = 0.0
	_phase_banner_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_phase_banner_label)


func _show_phase_banner_for(phase: String) -> void:
	if _phase_banner_label == null:
		return
	var text: String = ""
	var color: Color = COLOR_ACCENT
	match phase:
		"playing":
			text = "RUNDE LAEUFT"
			color = COLOR_ACCENT
		"meeting":
			text = "MEETING TIME"
			color = COLOR_WARN
		"ended":
			text = "RUNDE BEENDET"
			color = COLOR_TEXT_DIM
		_:
			return
	if _phase_banner_tween != null and _phase_banner_tween.is_valid():
		_phase_banner_tween.kill()
	_phase_banner_label.text = text
	_phase_banner_label.add_theme_color_override("font_color", color)
	_phase_banner_label.modulate.a = 0.0
	_phase_banner_tween = create_tween()
	_phase_banner_tween.tween_property(_phase_banner_label, "modulate:a", 1.0, 0.4)
	_phase_banner_tween.tween_interval(1.4)
	_phase_banner_tween.tween_property(_phase_banner_label, "modulate:a", 0.0, 0.6)


# Confetti (4.11/Demo) — beim Endscreen-Trigger. CPUParticles2D regnet
# bunte Punkte vom oberen Rand.

func _build_confetti() -> void:
	_confetti = CPUParticles2D.new()
	_confetti.amount = 80
	_confetti.lifetime = 4.0
	_confetti.preprocess = 0.0
	_confetti.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	_confetti.emission_rect_extents = Vector2(640, 4)
	_confetti.gravity = Vector2(0, 200)
	_confetti.initial_velocity_min = 50.0
	_confetti.initial_velocity_max = 120.0
	_confetti.angle_min = -180
	_confetti.angle_max = 180
	_confetti.angular_velocity_min = -180
	_confetti.angular_velocity_max = 180
	_confetti.scale_amount_min = 0.6
	_confetti.scale_amount_max = 1.4
	_confetti.color_ramp = _make_confetti_ramp()
	_confetti.position = Vector2(640, 0)  # mittig oben — wird via anchors gerueckt
	_confetti.set_anchors_preset(Control.PRESET_TOP_WIDE)
	_confetti.emitting = false
	add_child(_confetti)


func _make_confetti_ramp() -> Gradient:
	var g := Gradient.new()
	g.set_color(0, Color(0.95, 0.40, 0.40))
	g.add_point(0.25, Color(0.95, 0.85, 0.30))
	g.add_point(0.5, Color(0.30, 0.85, 0.45))
	g.add_point(0.75, Color(0.45, 0.65, 0.95))
	return g


func _set_confetti_active(on: bool) -> void:
	if _confetti == null:
		return
	_confetti.emitting = on
