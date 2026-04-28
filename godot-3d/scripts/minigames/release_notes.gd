extends Control

# Mini-Game „release_notes" UI (write_release_notes task). Mirror von
# static/minigames/release_notes.js — click-to-cycle: jeder Klick auf einen
# Commit cycelt seine Kategorie durch. Submit erst aktiv wenn alle commits
# zugewiesen sind. Server-Validation beim Submit; bei Fehler droppt er
# alles (Soft-Reset).
#
# View-Schema (server public_view):
#   { commits: [{id, message, assigned}], categories, totalCommits, assignedCount }
#
# Input zurueck:
#   action="cycle", params={commitId}
#   action="submit", params={}

const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_LINE_BG: Color = Color(0.10, 0.12, 0.16, 1.0)
const COLOR_CAT_FEATURE: Color = Color(0.30, 0.85, 0.45)
const COLOR_CAT_BUGFIX: Color = Color(0.45, 0.65, 0.95)
const COLOR_CAT_BREAKING: Color = Color(0.95, 0.40, 0.40)
const COLOR_CAT_NOPROD: Color = Color(0.95, 0.70, 0.30)
const COLOR_CAT_UNASSIGNED: Color = Color(0.40, 0.40, 0.45)

const CATEGORY_LABEL: Dictionary = {
	"feature": "Feature",
	"bugfix": "Bugfix",
	"breaking": "Breaking",
	"noprod": "Don't mention",
}

var _input_callback: Callable = Callable()
var _desc_label: Label
var _list_container: VBoxContainer
var _submit_btn: Button


func _ready() -> void:
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	vbox.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(vbox)

	_desc_label = Label.new()
	_desc_label.text = "Sortiere jeden Commit. Klick wechselt durch Feature → Bugfix → Breaking → Don't mention."
	_desc_label.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	_desc_label.add_theme_font_size_override("font_size", 12)
	_desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(_desc_label)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	vbox.add_child(scroll)

	_list_container = VBoxContainer.new()
	_list_container.add_theme_constant_override("separation", 4)
	_list_container.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(_list_container)

	_submit_btn = Button.new()
	_submit_btn.text = "Release Notes einreichen"
	_submit_btn.disabled = true
	_submit_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_submit_btn.pressed.connect(_on_submit_pressed)
	vbox.add_child(_submit_btn)


func set_input_callback(cb: Callable) -> void:
	_input_callback = cb


func apply_view(view: Dictionary) -> void:
	if _desc_label == null:
		return
	var assigned: int = int(view.get("assignedCount", 0))
	var total: int = int(view.get("totalCommits", 0))
	_desc_label.text = "Sortiere jeden Commit (%d / %d zugewiesen). Klick wechselt durch Feature → Bugfix → Breaking → Don't mention." % [assigned, total]

	for child in _list_container.get_children():
		child.queue_free()
	for c in view.get("commits", []):
		_list_container.add_child(_build_commit_row(c))

	var all_assigned: bool = assigned >= total and total > 0
	_submit_btn.disabled = not all_assigned


func _build_commit_row(commit: Dictionary) -> Button:
	var btn := Button.new()
	var message: String = str(commit.get("message", ""))
	var assigned_cat: String = str(commit.get("assigned", ""))
	var label: String = CATEGORY_LABEL.get(assigned_cat, "(klick mich)") if assigned_cat != "" else "(klick mich)"
	btn.text = "%s   [%s]" % [message, label]
	btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	btn.add_theme_font_size_override("font_size", 12)
	btn.add_theme_color_override("font_color", COLOR_TEXT)

	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_LINE_BG
	style.set_corner_radius_all(3)
	style.set_content_margin_all(6)
	style.set_border_width_all(1)
	match assigned_cat:
		"feature":
			style.border_color = COLOR_CAT_FEATURE
		"bugfix":
			style.border_color = COLOR_CAT_BUGFIX
		"breaking":
			style.border_color = COLOR_CAT_BREAKING
		"noprod":
			style.border_color = COLOR_CAT_NOPROD
		_:
			style.border_color = COLOR_CAT_UNASSIGNED
	btn.add_theme_stylebox_override("normal", style)
	btn.add_theme_stylebox_override("hover", style)
	btn.add_theme_stylebox_override("pressed", style)

	var commit_id: String = str(commit.get("id", ""))
	btn.pressed.connect(func(): _on_commit_pressed(commit_id))
	return btn


func _on_commit_pressed(commit_id: String) -> void:
	if _input_callback.is_valid():
		_input_callback.call("cycle", {"commitId": commit_id})


func _on_submit_pressed() -> void:
	if _input_callback.is_valid():
		_input_callback.call("submit", {})


func on_complete(_success: bool, _reason: String) -> void:
	pass
