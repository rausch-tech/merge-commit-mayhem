extends Control

# Mini-Game „cable_pairing" UI (repair_deployment task). Mirror von
# static/minigames/cable_pairing.js — Tap-Pair: Spieler tippt einen
# farbigen Source-Stecker links, dann eine Destination rechts.
# Server validiert ueber Farbgleichheit, Mismatch resettet die Connection.
#
# View-Schema (server public_view):
#   { sources: [{id, color}], destinations: [{id, color}],
#     connections: {sourceId: destinationId}, totalPairs }
#
# Input zurueck:
#   action="connect", params={sourceId, destinationId}

const COLOR_TEXT: Color = Color(0.95, 0.97, 0.99)
const COLOR_TEXT_DIM: Color = Color(0.62, 0.70, 0.78)
const COLOR_ACCENT: Color = Color(0.30, 0.95, 0.55)
const COLOR_NODE_BG: Color = Color(0.10, 0.13, 0.18)

var _input_callback: Callable = Callable()
var _progress_label: Label
var _sources_col: VBoxContainer
var _dests_col: VBoxContainer
var _selected_source_id: String = ""
var _last_view: Dictionary = {}


func _ready() -> void:
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	vbox.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(vbox)

	var hint := Label.new()
	hint.text = "Verbinde jeden Stecker mit der gleichfarbigen Buchse. Linke Spalte zuerst."
	hint.add_theme_color_override("font_color", COLOR_TEXT_DIM)
	hint.add_theme_font_size_override("font_size", 12)
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(hint)

	_progress_label = Label.new()
	_progress_label.text = "—"
	_progress_label.add_theme_color_override("font_color", COLOR_ACCENT)
	_progress_label.add_theme_font_size_override("font_size", 14)
	vbox.add_child(_progress_label)

	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 32)
	hbox.alignment = BoxContainer.ALIGNMENT_CENTER
	hbox.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(hbox)

	_sources_col = VBoxContainer.new()
	_sources_col.add_theme_constant_override("separation", 10)
	_sources_col.alignment = BoxContainer.ALIGNMENT_CENTER
	hbox.add_child(_sources_col)

	_dests_col = VBoxContainer.new()
	_dests_col.add_theme_constant_override("separation", 10)
	_dests_col.alignment = BoxContainer.ALIGNMENT_CENTER
	hbox.add_child(_dests_col)


func set_input_callback(cb: Callable) -> void:
	_input_callback = cb


func apply_view(view: Dictionary) -> void:
	if _progress_label == null:
		return
	_last_view = view
	var conns: Dictionary = view.get("connections", {})
	var total: int = int(view.get("totalPairs", 0))
	_progress_label.text = "Verbunden: %d / %d" % [conns.size(), total]

	# Wenn unsere Selection inzwischen connected ist, droppen — der Server
	# hat das Pair akzeptiert.
	if _selected_source_id != "" and conns.has(_selected_source_id):
		_selected_source_id = ""

	var connected_sources: Dictionary = {}  # set
	var connected_dests: Dictionary = {}
	for k in conns.keys():
		connected_sources[str(k)] = true
		connected_dests[str(conns[k])] = true

	for child in _sources_col.get_children():
		child.queue_free()
	for child in _dests_col.get_children():
		child.queue_free()
	for n in view.get("sources", []):
		_sources_col.add_child(_build_node(n, "src", connected_sources))
	for n in view.get("destinations", []):
		_dests_col.add_child(_build_node(n, "dst", connected_dests))


func _build_node(node: Dictionary, side: String, connected: Dictionary) -> Button:
	var btn := Button.new()
	var node_id: String = str(node.get("id", ""))
	var color_hex: String = str(node.get("color", "#888888"))
	btn.text = ""
	btn.custom_minimum_size = Vector2(80, 40)

	var style := StyleBoxFlat.new()
	style.bg_color = Color(color_hex) if color_hex.begins_with("#") else COLOR_NODE_BG
	style.set_corner_radius_all(6)
	style.set_content_margin_all(4)
	style.set_border_width_all(2)
	if connected.has(node_id):
		style.border_color = COLOR_ACCENT
	elif side == "src" and node_id == _selected_source_id:
		style.border_color = COLOR_TEXT
	else:
		style.border_color = Color(1, 1, 1, 0.20)
	btn.add_theme_stylebox_override("normal", style)
	btn.add_theme_stylebox_override("hover", style)
	btn.add_theme_stylebox_override("pressed", style)

	btn.disabled = connected.has(node_id)
	btn.pressed.connect(func(): _handle_tap(node_id, side, color_hex))
	return btn


func _handle_tap(node_id: String, side: String, _color_hex: String) -> void:
	if _last_view.is_empty():
		return
	var conns: Dictionary = _last_view.get("connections", {})
	if side == "src":
		if conns.has(node_id):
			return
		_selected_source_id = node_id
		# Re-render: damit der "selected"-Border sofort sichtbar ist.
		apply_view(_last_view)
	else:
		if _selected_source_id == "":
			return
		# Dest darf noch nicht verwendet sein.
		var dest_taken: bool = false
		for v in conns.values():
			if str(v) == node_id:
				dest_taken = true
				break
		if dest_taken:
			return
		var src_id := _selected_source_id
		_selected_source_id = ""
		if _input_callback.is_valid():
			_input_callback.call("connect", {"sourceId": src_id, "destinationId": node_id})


func on_complete(_success: bool, _reason: String) -> void:
	pass
