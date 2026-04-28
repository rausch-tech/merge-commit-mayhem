extends Control

# Lobby + entry point. Builds the UI programmatically so the .tscn stays
# small and the entire connect flow lives in one readable script.
#
# Flow:
#   1. _ready() builds connect-form + lobby-card (lobby-card hidden initially).
#   2. on_connect_pressed → ws.connect_to_server → join_room.
#   3. room_joined  → cache map + player-id, swap UI to lobby-card.
#   4. lobby_state  → populate player list, expose Demo-Mode + Start-Button to host.
#   5. game_state phase=playing → load world.tscn, hand off ws + state.

const WORLD_SCENE: String = "res://scenes/world.tscn"

# UI click feedback — tiny, satisfying tap on each button press.
const UI_CLICK_STREAM: AudioStream = preload("res://assets/audio/ui/click.ogg")
const UI_CLICK_VOLUME_DB: float = -16.0

# Branding-Logo (Tier 4.x Lobby-Polish). Wird oben im Connect-/Lobby-Screen
# als TextureRect gezeigt; ersetzt das frueher fett-grosse Text-Title.
const LOGO_TEXTURE: Texture2D = preload("res://assets/branding/logo.png")

# UI colors (cyber/dev-themed, dark + green-cyan accent)
const COLOR_BG_TOP: Color = Color(0.05, 0.07, 0.12)
const COLOR_BG_BOTTOM: Color = Color(0.02, 0.03, 0.06)
const COLOR_PANEL_BG: Color = Color(0.10, 0.13, 0.18, 0.95)
const COLOR_ACCENT: Color = Color(0.27, 0.95, 0.55)            # bright green
const COLOR_ACCENT_DIM: Color = Color(0.27, 0.95, 0.55, 0.5)
const COLOR_TEXT: Color = Color(0.92, 0.96, 0.98)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_DANGER: Color = Color(0.95, 0.35, 0.35)
const COLOR_INPUT_BG: Color = Color(0.06, 0.08, 0.12)
const COLOR_INPUT_BORDER: Color = Color(0.20, 0.30, 0.40)

var _ws: WSClient
var _player_id: String = ""
var _room_code: String = ""
var _is_host: bool = false
var _map: Dictionary = {}
var _role_info: Dictionary = {}
# Guard so the 20 Hz game_state stream doesn't trigger world.tscn instantiation
# repeatedly between the first transition and Main's queue_free taking effect.
var _transitioning: bool = false

# UI Nodes (built in _ready)
var _connect_card: PanelContainer
var _url_field: LineEdit
var _room_field: LineEdit
var _name_field: LineEdit
var _connect_btn: Button
var _connect_status: Label

var _lobby_card: PanelContainer
var _lobby_room_label: Label
var _player_list: VBoxContainer
var _demo_check: CheckBox
var _start_btn: Button
var _leave_btn: Button
var _lobby_status: Label
var _map_select: OptionButton
var _role_select: OptionButton
var _add_bot_btn: Button
var _remove_bot_btn: Button
# Cache der availableMaps + bot-Liste, damit Re-Populate idempotent ist und
# wir bot_ids fuer remove_bot kennen.
var _available_maps: Array = []
var _selected_map_id: String = ""
var _bot_ids: Array = []
# Keine Signal-Loop wenn wir den Dropdown selber programmatisch setzen.
var _suppress_dropdown_signals: bool = false

# 5 Release-Rollen + "Egal" als Default. Order matched JS-Client-Lobby.
const ROLE_OPTIONS: Array = [
	{"id": "", "label": "Egal (zufaellig)"},
	{"id": "developer", "label": "Developer"},
	{"id": "devops_engineer", "label": "DevOps Engineer"},
	{"id": "qa_lead", "label": "QA Lead"},
	{"id": "scrum_master", "label": "Scrum Master"},
	{"id": "caffeine_collector", "label": "Caffeine Collector"},
]

var _log_area: TextEdit
var _click_player: AudioStreamPlayer

func _ready() -> void:
	_ws = WSClient.new()
	add_child(_ws)
	_ws.connected.connect(_on_connected)
	_ws.disconnected.connect(_on_disconnected)
	_ws.connection_error.connect(_on_error)
	_ws.message_received.connect(_on_message)

	_build_ui()
	_click_player = AudioStreamPlayer.new()
	_click_player.name = "ClickPlayer"
	_click_player.stream = UI_CLICK_STREAM
	_click_player.volume_db = UI_CLICK_VOLUME_DB
	add_child(_click_player)
	_show_connect_card()
	_append_log("[main] ready — connect to start")

# -- UI construction ---------------------------------------------------------

func _build_ui() -> void:
	# Root mouse_filter: PASS so the root Control doesn't swallow events.
	mouse_filter = Control.MOUSE_FILTER_PASS

	# Background gradient — both layers are click-through (IGNORE) so they
	# never block the buttons sitting on top.
	var bg := ColorRect.new()
	bg.color = COLOR_BG_BOTTOM
	bg.anchor_right = 1.0
	bg.anchor_bottom = 1.0
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg)

	var bg_overlay := _make_gradient_panel()
	bg_overlay.anchor_right = 1.0
	bg_overlay.anchor_bottom = 1.0
	bg_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(bg_overlay)

	# Title block (top-center) — Logo-TextureRect, click-through.
	# Logo ist 1536x1024 (~3:2). Bei 240 px Hoehe wird's ~360 px breit;
	# expand_mode=KEEP_ASPECT_CENTERED haelt die Proportionen, expand=true
	# erlaubt das skalieren auf den Container-Rect.
	var logo := TextureRect.new()
	logo.texture = LOGO_TEXTURE
	logo.expand_mode = TextureRect.EXPAND_FIT_HEIGHT_PROPORTIONAL
	logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	logo.anchor_left = 0.5
	logo.anchor_right = 0.5
	logo.anchor_top = 0.0
	logo.anchor_bottom = 0.0
	logo.offset_left = -210
	logo.offset_right = 210
	logo.offset_top = 24
	logo.offset_bottom = 224
	logo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(logo)

	# Connect card (centered) — etwas filigraner als vorher; 22 px content_margin
	# vom Card-StyleBox liefert das Innenpadding zur Border.
	_connect_card = _make_card()
	_connect_card.anchor_left = 0.5
	_connect_card.anchor_top = 0.5
	_connect_card.anchor_right = 0.5
	_connect_card.anchor_bottom = 0.5
	_connect_card.offset_left = -240
	_connect_card.offset_top = -160
	_connect_card.offset_right = 240
	_connect_card.offset_bottom = 200
	add_child(_connect_card)

	var connect_vbox := VBoxContainer.new()
	connect_vbox.add_theme_constant_override("separation", 12)
	_connect_card.add_child(connect_vbox)

	connect_vbox.add_child(_make_section_label("CONNECT"))

	# URL-Feld nur im Native-Build (z.B. lokal aus dem Godot-Editor heraus).
	# Web-Build leitet die URL automatisch aus dem Page-Origin ab — dort
	# laeuft der Client immer gegen den Server, der ihn ausliefert
	# (prod-is-lava.dev/godot/ -> wss://prod-is-lava.dev/ws). Kein Feld =
	# kein „falsche URL eingetippt"-Footgun in Production.
	if not OS.has_feature("web"):
		_url_field = _make_line_edit("ws://127.0.0.1:8000/ws")
		connect_vbox.add_child(_make_field_row("Server", _url_field))

	_room_field = _make_line_edit("DEMO")
	_room_field.max_length = 8
	connect_vbox.add_child(_make_field_row("Raumcode", _room_field))

	_name_field = _make_line_edit("Player")
	_name_field.max_length = 16
	connect_vbox.add_child(_make_field_row("Spielername", _name_field))

	_connect_btn = _make_primary_button("VERBINDEN")
	_connect_btn.pressed.connect(_on_connect_pressed)
	_connect_btn.pressed.connect(_play_click)
	connect_vbox.add_child(_connect_btn)

	_connect_status = _make_status_label("")
	connect_vbox.add_child(_connect_status)

	# Lobby card (centered, slim — 500x460; 22 px content_margin im Card-Style
	# sorgt fuer Innenpadding, vorher klebten Buttons direkt an der Border weil
	# der alte _pad_container-Helper auf VBoxContainer keine Wirkung hatte.
	_lobby_card = _make_card()
	_lobby_card.anchor_left = 0.5
	_lobby_card.anchor_top = 0.5
	_lobby_card.anchor_right = 0.5
	_lobby_card.anchor_bottom = 0.5
	_lobby_card.offset_left = -250
	_lobby_card.offset_top = -220
	_lobby_card.offset_right = 250
	_lobby_card.offset_bottom = 240
	_lobby_card.visible = false
	add_child(_lobby_card)

	var lobby_vbox := VBoxContainer.new()
	lobby_vbox.add_theme_constant_override("separation", 10)
	_lobby_card.add_child(lobby_vbox)

	lobby_vbox.add_child(_make_section_label("LOBBY"))

	_lobby_room_label = Label.new()
	_lobby_room_label.text = "Raum: ?"
	_lobby_room_label.add_theme_color_override("font_color", COLOR_TEXT)
	_lobby_room_label.add_theme_font_size_override("font_size", 18)
	lobby_vbox.add_child(_lobby_room_label)

	# Map-Auswahl (Host-only, populiert sich aus lobby_state.availableMaps).
	_map_select = OptionButton.new()
	_map_select.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_map_select.item_selected.connect(_on_map_selected)
	lobby_vbox.add_child(_make_dropdown_row("Map", _map_select))

	# Rollen-Praeferenz (jeder Spieler kann seinen Wunsch setzen).
	_role_select = OptionButton.new()
	_role_select.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for opt in ROLE_OPTIONS:
		_role_select.add_item(opt["label"])
	_role_select.selected = 0
	_role_select.item_selected.connect(_on_role_selected)
	lobby_vbox.add_child(_make_dropdown_row("Rolle (Wunsch)", _role_select))

	var players_label := Label.new()
	players_label.text = "Spieler"
	players_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	players_label.add_theme_font_size_override("font_size", 14)
	lobby_vbox.add_child(players_label)

	var player_scroll := ScrollContainer.new()
	player_scroll.custom_minimum_size = Vector2(0, 100)
	player_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	lobby_vbox.add_child(player_scroll)

	_player_list = VBoxContainer.new()
	_player_list.add_theme_constant_override("separation", 6)
	_player_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	player_scroll.add_child(_player_list)

	# AI-Bot-Buttons (host-only). Add fuegt einen kuratierten Bot hinzu,
	# Remove kickt den letzten in der Liste — Server entscheidet welche Namen.
	var bot_row := HBoxContainer.new()
	bot_row.add_theme_constant_override("separation", 8)
	lobby_vbox.add_child(bot_row)

	_add_bot_btn = _make_secondary_button("+ Bot")
	_add_bot_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_add_bot_btn.pressed.connect(_on_add_bot_pressed)
	_add_bot_btn.pressed.connect(_play_click)
	_add_bot_btn.visible = false
	bot_row.add_child(_add_bot_btn)

	_remove_bot_btn = _make_secondary_button("- Bot")
	_remove_bot_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_remove_bot_btn.pressed.connect(_on_remove_bot_pressed)
	_remove_bot_btn.pressed.connect(_play_click)
	_remove_bot_btn.visible = false
	bot_row.add_child(_remove_bot_btn)

	_demo_check = CheckBox.new()
	_demo_check.text = "Demo-Mode (1 Spieler erlaubt, du bist Chaos)"
	_demo_check.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	_demo_check.button_pressed = true
	_demo_check.visible = false
	lobby_vbox.add_child(_demo_check)

	var btn_row := HBoxContainer.new()
	btn_row.add_theme_constant_override("separation", 10)
	lobby_vbox.add_child(btn_row)

	_leave_btn = _make_secondary_button("VERLASSEN")
	_leave_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_leave_btn.pressed.connect(_on_leave_pressed)
	_leave_btn.pressed.connect(_play_click)
	btn_row.add_child(_leave_btn)

	_start_btn = _make_primary_button("SPIEL STARTEN")
	_start_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_start_btn.pressed.connect(_on_start_pressed)
	_start_btn.pressed.connect(_play_click)
	_start_btn.visible = false
	btn_row.add_child(_start_btn)

	_lobby_status = _make_status_label("")
	lobby_vbox.add_child(_lobby_status)

	# Log area — schmale Statuszeile am unteren linken Rand. Vorher
	# blockierte das volle Log die Connect-Buttons (Mouse-Events fielen ins
	# TextEdit statt durchzudringen). Jetzt: schmal (60 px), nur ueber
	# linken Drittel, alle Mouse-Events pass-through bis zur Card hindurch.
	var log_panel := PanelContainer.new()
	log_panel.anchor_left = 0.0
	log_panel.anchor_right = 0.0
	log_panel.anchor_top = 1.0
	log_panel.anchor_bottom = 1.0
	log_panel.offset_left = 16
	log_panel.offset_right = 380
	log_panel.offset_top = -76
	log_panel.offset_bottom = -16
	log_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var log_style := StyleBoxFlat.new()
	log_style.bg_color = Color(0.04, 0.05, 0.08, 0.7)
	log_style.set_corner_radius_all(6)
	log_style.set_border_width_all(1)
	log_style.border_color = Color(0.20, 0.30, 0.40, 0.6)
	log_style.set_content_margin_all(6)
	log_panel.add_theme_stylebox_override("panel", log_style)
	add_child(log_panel)

	_log_area = TextEdit.new()
	_log_area.editable = false
	_log_area.scroll_smooth = true
	_log_area.add_theme_color_override("font_color", COLOR_ACCENT)
	_log_area.add_theme_color_override("background_color", Color(0, 0, 0, 0))
	_log_area.add_theme_font_size_override("font_size", 11)
	# Wichtig: IGNORE statt PASS — sonst frisst der TextEdit auch durch das
	# IGNORE-Panel hindurch Mouse-Events und blockiert die Connect-Card.
	_log_area.mouse_filter = Control.MOUSE_FILTER_IGNORE
	log_panel.add_child(_log_area)

func _make_card() -> PanelContainer:
	var card := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_PANEL_BG
	style.set_corner_radius_all(10)
	style.set_border_width_all(1)
	style.border_color = COLOR_ACCENT_DIM
	style.shadow_size = 18
	style.shadow_color = Color(0, 0, 0, 0.45)
	# Content-Margin sorgt fuer Innenabstand zur Border. PanelContainer ehrt
	# StyleBox-content_margin, anders als VBoxContainer das `margin_*`
	# theme-constants ignoriert (siehe alter `_pad_container`-Helper, der
	# faktisch ein No-Op war auf VBoxContainer).
	style.set_content_margin_all(22)
	card.add_theme_stylebox_override("panel", style)
	return card

func _make_gradient_panel() -> Control:
	var rect := ColorRect.new()
	rect.color = COLOR_BG_TOP
	rect.modulate.a = 0.6
	return rect

func _make_section_label(text: String) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_color_override("font_color", COLOR_ACCENT)
	label.add_theme_font_size_override("font_size", 13)
	return label

func _make_field_row(label_text: String, edit: LineEdit) -> VBoxContainer:
	var row := VBoxContainer.new()
	row.add_theme_constant_override("separation", 4)
	var lbl := Label.new()
	lbl.text = label_text
	lbl.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	lbl.add_theme_font_size_override("font_size", 12)
	row.add_child(lbl)
	row.add_child(edit)
	return row


func _make_dropdown_row(label_text: String, dropdown: OptionButton) -> VBoxContainer:
	var row := VBoxContainer.new()
	row.add_theme_constant_override("separation", 4)
	var lbl := Label.new()
	lbl.text = label_text
	lbl.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	lbl.add_theme_font_size_override("font_size", 12)
	row.add_child(lbl)
	row.add_child(dropdown)
	return row

func _make_line_edit(default_text: String) -> LineEdit:
	var edit := LineEdit.new()
	edit.text = default_text
	edit.placeholder_text = default_text
	edit.add_theme_color_override("font_color", COLOR_TEXT)
	edit.add_theme_font_size_override("font_size", 13)
	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_INPUT_BG
	style.set_corner_radius_all(6)
	style.set_border_width_all(1)
	style.border_color = COLOR_INPUT_BORDER
	style.set_content_margin_all(8)
	edit.add_theme_stylebox_override("normal", style)
	var focus_style := style.duplicate() as StyleBoxFlat
	focus_style.border_color = COLOR_ACCENT
	edit.add_theme_stylebox_override("focus", focus_style)
	return edit

func _make_primary_button(text: String) -> Button:
	var btn := Button.new()
	btn.text = text
	btn.add_theme_color_override("font_color", Color(0.04, 0.06, 0.10))
	btn.add_theme_color_override("font_hover_color", Color(0.04, 0.06, 0.10))
	btn.add_theme_font_size_override("font_size", 15)
	btn.custom_minimum_size = Vector2(0, 38)
	for state in ["normal", "hover", "pressed"]:
		var style := StyleBoxFlat.new()
		style.bg_color = COLOR_ACCENT if state == "normal" else COLOR_ACCENT.lightened(0.1)
		if state == "pressed":
			style.bg_color = COLOR_ACCENT.darkened(0.15)
		style.set_corner_radius_all(8)
		style.set_content_margin_all(10)
		btn.add_theme_stylebox_override(state, style)
	return btn

func _make_secondary_button(text: String) -> Button:
	var btn := Button.new()
	btn.text = text
	btn.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	btn.add_theme_font_size_override("font_size", 13)
	btn.custom_minimum_size = Vector2(0, 32)
	for state in ["normal", "hover", "pressed"]:
		var style := StyleBoxFlat.new()
		style.bg_color = COLOR_INPUT_BG if state == "normal" else COLOR_INPUT_BG.lightened(0.05)
		style.set_corner_radius_all(8)
		style.set_border_width_all(1)
		style.border_color = COLOR_INPUT_BORDER
		style.set_content_margin_all(10)
		btn.add_theme_stylebox_override(state, style)
	return btn

func _make_status_label(text: String) -> Label:
	var lbl := Label.new()
	lbl.text = text
	lbl.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	lbl.add_theme_font_size_override("font_size", 13)
	lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return lbl

func _show_connect_card() -> void:
	_connect_card.visible = true
	_lobby_card.visible = false

func _show_lobby_card() -> void:
	_connect_card.visible = false
	_lobby_card.visible = true

# -- Connect flow ------------------------------------------------------------

func _resolve_server_url() -> String:
	# Native: aus dem URL-Feld lesen (Sven editiert lokal auf seinem Dev-
	# Setup). Web-Build: Page-Origin in WebSocket-Origin uebersetzen — die
	# Web-App weiss, von wo sie geladen wurde, also auch wo der Server steht.
	if _url_field != null:
		return _url_field.text.strip_edges()
	if not OS.has_feature("web"):
		# Defensive — sollte nie passieren (Field nur auf Web weggelassen).
		return "ws://127.0.0.1:8000/ws"
	var origin_raw: Variant = JavaScriptBridge.eval("window.location.origin", true)
	var origin := str(origin_raw)
	if origin.begins_with("https://"):
		return "wss://" + origin.substr(8) + "/ws"
	if origin.begins_with("http://"):
		return "ws://" + origin.substr(7) + "/ws"
	# Unerwartetes Schema (file:// in Editor-Preview etc.) — Fallback auf
	# explizite Apex-Domain damit zumindest die Production-URL versucht wird.
	return "wss://prod-is-lava.dev/ws"


func _on_connect_pressed() -> void:
	var url := _resolve_server_url()
	var room := _room_field.text.strip_edges().to_upper()
	var name_ := _name_field.text.strip_edges()
	if url == "" or room == "" or name_ == "":
		_set_connect_status("Bitte alle Felder ausfüllen.", true)
		return
	_set_connect_status("Verbinde mit %s …" % url, false)
	_append_log("[ws] connecting to %s" % url)
	set_meta("pending_room", room)
	set_meta("pending_name", name_)
	_connect_btn.disabled = true
	_ws.connect_to_server(url)

func _on_connected() -> void:
	_append_log("[ws] connected")
	_set_connect_status("Verbunden — sende join_room …", false)
	var room := str(get_meta("pending_room"))
	var name_ := str(get_meta("pending_name"))
	_ws.send(Protocol.TYPE_JOIN_ROOM, {"roomCode": room, "playerName": name_})
	_append_log("[ws] sent join_room room=%s name=%s" % [room, name_])

func _on_disconnected() -> void:
	_append_log("[ws] disconnected")
	_connect_btn.disabled = false
	_set_connect_status("Verbindung verloren.", true)
	_show_connect_card()

func _on_error(reason: String) -> void:
	_append_log("[ws] error: %s" % reason)
	_connect_btn.disabled = false
	_set_connect_status("Fehler: %s" % reason, true)

func _on_message(type_: String, payload: Dictionary) -> void:
	match type_:
		Protocol.TYPE_ROOM_JOINED:
			_player_id = str(payload.get("playerId", ""))
			_is_host = bool(payload.get("isHost", false))
			_map = payload.get("map", {})
			_room_code = str(payload.get("roomCode", ""))
			_append_log("[room_joined] playerId=%s isHost=%s mapName=%s" % [
				_player_id, _is_host, _map.get("name", "?")
			])
			_lobby_room_label.text = "Raum: %s" % _room_code
			_set_lobby_status("In der Lobby — warte auf Spielstart.", false)
			_demo_check.visible = _is_host
			_start_btn.visible = _is_host
			# Map-Auswahl + Bot-Buttons sind Host-only — Client-Spieler sehen sie nicht.
			_map_select.disabled = not _is_host
			_add_bot_btn.visible = _is_host
			_remove_bot_btn.visible = _is_host
			_show_lobby_card()
		Protocol.TYPE_LOBBY_STATE:
			_update_player_list(payload.get("players", []))
			_update_map_select(
				payload.get("availableMaps", []),
				str(payload.get("selectedMapId", "")),
			)
		Protocol.TYPE_PRIVATE_ROLE:
			_role_info = payload.duplicate()
			_append_log("[private_role] role=%s team=%s" % [
				payload.get("role", "?"), payload.get("team", "?")
			])
		Protocol.TYPE_GAME_STATE:
			if _transitioning:
				return  # already on the way to world.tscn; ignore further ticks
			var phase := str(payload.get("phase", ""))
			if phase == Protocol.PHASE_PLAYING or phase == Protocol.PHASE_MEETING:
				_transitioning = true
				_transition_to_world(payload)
		Protocol.TYPE_ERROR:
			var code := str(payload.get("code", "?"))
			var message := str(payload.get("message", ""))
			_append_log("[server_error] %s: %s" % [code, message])
			_set_lobby_status("%s: %s" % [code, message], true)
		_:
			# Ignore other messages in lobby (they belong to the world scene).
			pass

func _update_player_list(players: Array) -> void:
	for child in _player_list.get_children():
		child.queue_free()
	_bot_ids.clear()
	for p in players:
		var entry := _make_player_row(p)
		_player_list.add_child(entry)
		if bool(p.get("isBot", false)):
			_bot_ids.append(str(p.get("id", "")))
	# Remove-Bot nur sinnvoll wenn ueberhaupt Bots da sind.
	if _is_host:
		_remove_bot_btn.disabled = _bot_ids.is_empty()


func _update_map_select(available: Array, selected_id: String) -> void:
	# Vergleichshash: wenn die Map-Liste unveraendert ist, lassen wir den
	# Dropdown in Ruhe — sonst "klingelt" jeder 1 Hz LobbyState das Selection.
	var sig := []
	for m in available:
		sig.append({"id": str(m.get("id", "")), "name": str(m.get("name", ""))})
	if sig == _available_maps and selected_id == _selected_map_id:
		return
	_available_maps = sig
	_selected_map_id = selected_id
	_suppress_dropdown_signals = true
	_map_select.clear()
	var sel_idx := 0
	for i in available.size():
		var m: Dictionary = available[i]
		_map_select.add_item(str(m.get("name", "?")))
		_map_select.set_item_metadata(i, str(m.get("id", "")))
		if str(m.get("id", "")) == selected_id:
			sel_idx = i
	if available.size() > 0:
		_map_select.selected = sel_idx
	_suppress_dropdown_signals = false


func _on_map_selected(idx: int) -> void:
	if _suppress_dropdown_signals or not _is_host:
		return
	if idx < 0 or idx >= _map_select.item_count:
		return
	var map_id := str(_map_select.get_item_metadata(idx))
	if map_id == "":
		return
	_ws.send(Protocol.TYPE_SELECT_MAP, {"mapId": map_id})
	_append_log("[ws] sent select_map mapId=%s" % map_id)


func _on_role_selected(idx: int) -> void:
	if _suppress_dropdown_signals:
		return
	if idx < 0 or idx >= ROLE_OPTIONS.size():
		return
	var role_id: String = ROLE_OPTIONS[idx]["id"]
	# Empty string -> null im JSON-Payload (Server akzeptiert beides).
	var payload := {"role": role_id if role_id != "" else null}
	_ws.send(Protocol.TYPE_SET_PREFERRED_ROLE, payload)
	_append_log("[ws] sent set_preferred_role role=%s" % role_id)


func _on_add_bot_pressed() -> void:
	if not _is_host:
		return
	_ws.send(Protocol.TYPE_ADD_BOT, {})


func _on_remove_bot_pressed() -> void:
	if not _is_host or _bot_ids.is_empty():
		return
	# Letzten Bot kicken — JS-Client macht es genauso.
	var bot_id: String = _bot_ids[-1]
	_ws.send(Protocol.TYPE_REMOVE_BOT, {"botId": bot_id})

func _make_player_row(player: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var dot := ColorRect.new()
	var color_hex := str(player.get("color", "#888888"))
	dot.color = Color(color_hex) if color_hex.begins_with("#") else Color(0.5, 0.5, 0.5)
	dot.custom_minimum_size = Vector2(16, 16)
	row.add_child(dot)
	var name_label := Label.new()
	name_label.text = str(player.get("name", "?"))
	name_label.add_theme_color_override("font_color", COLOR_TEXT)
	name_label.add_theme_font_size_override("font_size", 16)
	row.add_child(name_label)
	if bool(player.get("isHost", false)):
		var host_tag := Label.new()
		host_tag.text = "HOST"
		host_tag.add_theme_color_override("font_color", COLOR_ACCENT)
		host_tag.add_theme_font_size_override("font_size", 11)
		row.add_child(host_tag)
	if bool(player.get("isBot", false)):
		var bot_tag := Label.new()
		bot_tag.text = "BOT"
		bot_tag.add_theme_color_override("font_color", COLOR_TEXT_DIM)
		bot_tag.add_theme_font_size_override("font_size", 11)
		row.add_child(bot_tag)
	return row

func _on_start_pressed() -> void:
	if not _is_host:
		return
	var demo := _demo_check.button_pressed
	_ws.send(Protocol.TYPE_START_GAME, {"demo": demo})
	_set_lobby_status("Spielstart angefragt …", false)
	_append_log("[ws] sent start_game demo=%s" % demo)

func _on_leave_pressed() -> void:
	_ws.close()
	_show_connect_card()
	_connect_btn.disabled = false
	_set_connect_status("Verbindung getrennt.", false)

func _set_connect_status(text: String, is_error: bool) -> void:
	_connect_status.text = text
	_connect_status.add_theme_color_override(
		"font_color", COLOR_DANGER if is_error else COLOR_TEXT_DIM
	)

func _set_lobby_status(text: String, is_error: bool) -> void:
	_lobby_status.text = text
	_lobby_status.add_theme_color_override(
		"font_color", COLOR_DANGER if is_error else COLOR_TEXT_DIM
	)

func _transition_to_world(initial_state: Dictionary) -> void:
	_append_log("[main] phase=playing — switching to 3D world")
	# Disconnect the message stream so further ticks queueing during the
	# call_deferred-then-await window don't reach _on_message again.
	if _ws != null and _ws.message_received.is_connected(_on_message):
		_ws.message_received.disconnect(_on_message)
	var world_packed := load(WORLD_SCENE) as PackedScene
	if world_packed == null:
		_set_lobby_status("world.tscn nicht gefunden", true)
		_transitioning = false
		return
	var world := world_packed.instantiate()
	world.set("ws_client", _ws)
	world.set("player_id", _player_id)
	world.set("room_code", _room_code)
	world.set("is_host", _is_host)
	world.set("map_data", _map)
	world.set("role_info", _role_info)
	world.set("initial_state", initial_state)
	get_tree().root.add_child.call_deferred(world)
	# Hand over WSClient ownership: detach from Main, reparent to world.
	# Reparent on next frame so Main still receives any in-flight signals safely.
	await get_tree().process_frame
	if _ws.get_parent() == self:
		remove_child(_ws)
		world.add_child(_ws)
	# Hide ourselves but keep in tree so signals still flow if anything dangling.
	visible = false
	queue_free()

func _append_log(line: String) -> void:
	print(line)
	if _log_area == null:
		return
	_log_area.text += line + "\n"
	_log_area.scroll_vertical = _log_area.get_line_count()

func _play_click() -> void:
	if _click_player != null:
		_click_player.play()
