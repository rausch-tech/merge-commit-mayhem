extends CanvasLayer

# Generic Mini-Game-Modal-Host. Wird von world.gd auf TYPE_MINI_GAME_STARTED
# instanziiert, dispatcht auf eine Mini-Game-spezifische UI-Implementierung
# basierend auf miniGameId. UI-Implementierungen leben unter
# scripts/minigames/ und implementieren drei Methoden:
#
#   apply_view(view: Dictionary)  — initiale + Update-View
#   set_input_callback(cb)        — wird mit `func(action, params)` befuellt
#                                   und vom UI bei Input aufgerufen
#   (optional) on_complete(success, reason)
#
# Modal selbst ist nur Frame: Header (Titel + Close-Button), Content-Container
# in den die UI-Implementation reingeladen wird.

signal input_sent(action: String, params: Dictionary)
signal aborted

const COLOR_BACKDROP: Color = Color(0.0, 0.0, 0.0, 0.55)
const COLOR_PANEL_BG: Color = Color(0.10, 0.13, 0.18, 0.97)
const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_DANGER: Color = Color(0.95, 0.40, 0.40)

# Mapping miniGameId → Plugin-Script. Nicht-registrierte IDs zeigen Generic-
# Placeholder mit "UI folgt".
const MINI_GAME_SCRIPTS: Dictionary = {
	"sprint_trim": preload("res://scripts/minigames/sprint_trim.gd"),
	"log_filter": preload("res://scripts/minigames/log_filter.gd"),
	"diff_review": preload("res://scripts/minigames/diff_review.gd"),
	"test_suite_repair": preload("res://scripts/minigames/test_suite_repair.gd"),
	"release_notes": preload("res://scripts/minigames/release_notes.gd"),
	"coffee_pour": preload("res://scripts/minigames/coffee_pour.gd"),
}

var _task_id: String = ""
var _mini_game_id: String = ""
var _content_container: VBoxContainer
var _title_label: Label
var _ui_node: Control = null

func _ready() -> void:
	layer = 60  # ueber HUD (10) + Pause (50)
	var backdrop := ColorRect.new()
	backdrop.color = COLOR_BACKDROP
	backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	backdrop.mouse_filter = Control.MOUSE_FILTER_STOP  # blocks click-through
	add_child(backdrop)

	var panel := PanelContainer.new()
	panel.anchor_left = 0.5
	panel.anchor_right = 0.5
	panel.anchor_top = 0.5
	panel.anchor_bottom = 0.5
	panel.offset_left = -340
	panel.offset_right = 340
	panel.offset_top = -260
	panel.offset_bottom = 260
	add_child(panel)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_PANEL_BG
	style.set_corner_radius_all(12)
	style.set_border_width_all(1)
	style.border_color = Color(1, 1, 1, 0.10)
	style.set_content_margin_all(20)
	panel.add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 16)
	panel.add_child(vbox)

	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 12)
	vbox.add_child(header)

	_title_label = Label.new()
	_title_label.text = "Mini-Game"
	_title_label.add_theme_color_override("font_color", COLOR_ACCENT)
	_title_label.add_theme_font_size_override("font_size", 22)
	_title_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(_title_label)

	var abort_btn := Button.new()
	abort_btn.text = "Abbrechen (ESC)"
	abort_btn.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	abort_btn.add_theme_font_size_override("font_size", 13)
	abort_btn.pressed.connect(_on_abort)
	header.add_child(abort_btn)

	_content_container = VBoxContainer.new()
	_content_container.add_theme_constant_override("separation", 8)
	_content_container.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(_content_container)

func setup(task_id: String, mini_game_id: String, title: String, view: Dictionary) -> void:
	_task_id = task_id
	_mini_game_id = mini_game_id
	_title_label.text = title if title != "" else mini_game_id
	_load_ui(mini_game_id)
	if _ui_node and _ui_node.has_method("apply_view"):
		_ui_node.call("apply_view", view)

func apply_view(view: Dictionary) -> void:
	if _ui_node and _ui_node.has_method("apply_view"):
		_ui_node.call("apply_view", view)

func on_complete(success: bool, reason: String) -> void:
	if _ui_node and _ui_node.has_method("on_complete"):
		_ui_node.call("on_complete", success, reason)

func _load_ui(mini_game_id: String) -> void:
	for child in _content_container.get_children():
		child.queue_free()
	_ui_node = null
	if MINI_GAME_SCRIPTS.has(mini_game_id):
		var script: Script = MINI_GAME_SCRIPTS[mini_game_id]
		var ui := Control.new()
		ui.set_script(script)
		ui.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		ui.size_flags_vertical = Control.SIZE_EXPAND_FILL
		_content_container.add_child(ui)
		if ui.has_method("set_input_callback"):
			ui.call("set_input_callback", _on_input_from_ui)
		_ui_node = ui
	else:
		var placeholder := Label.new()
		placeholder.text = "Mini-Game '%s' — UI folgt in einem spaeteren Slice." % mini_game_id
		placeholder.add_theme_color_override("font_color", COLOR_TEXT_DIM)
		placeholder.add_theme_font_size_override("font_size", 14)
		placeholder.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_content_container.add_child(placeholder)

func _on_input_from_ui(action: String, params: Dictionary) -> void:
	input_sent.emit(action, params)

func _on_abort() -> void:
	aborted.emit()

func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if (event as InputEventKey).keycode == KEY_ESCAPE:
			_on_abort()
			get_viewport().set_input_as_handled()
