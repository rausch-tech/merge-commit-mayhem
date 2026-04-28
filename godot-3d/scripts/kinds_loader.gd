class_name KindsLoader
extends Node

# Async fetcher fuer maps/kinds.json + maps/<id>.json gegen den Backend-Server,
# mit Fallback auf res://maps/. Gehoert zu Tier 3.9 / Option C — Backend ist
# Single Source of Truth fuer Kinds-Registry, Godot-Client haelt nur eine
# Demo-Kopie als Offline-Fallback.
#
# Usage:
#   var loader := KindsLoader.new()
#   add_child(loader)
#   var ok: bool = await loader.fetch_kinds(http_base)   # populates MapBuilder cache
#   var map: Dictionary = await loader.fetch_map(http_base, "office_complex")
#
# Beide Calls fallen auf res://maps/ zurueck wenn der Server nicht erreichbar
# ist oder die Antwort kaputt ist. fetch_map gibt {} zurueck wenn auch der
# Fallback nicht klappt.

const _HTTP_TIMEOUT_SEC: float = 3.0
const _RES_KINDS_PATH: String = "res://maps/kinds.json"
const _RES_MAP_PATH_TEMPLATE: String = "res://maps/%s.json"

# True wenn die Kinds-Registry erfolgreich geladen wurde (HTTP oder Fallback).
# Idempotent — weitere fetch_kinds-Calls geben sofort True zurueck.
static var _kinds_loaded_signal: bool = false

# -- public API --------------------------------------------------------------

func fetch_kinds(http_base: String) -> bool:
	# Schon geladen? Dann waren wir Optio A (sync res://) oder ein frueheres
	# fetch_kinds erfolgreich. MapBuilder cached selbst, also sind wir hier safe.
	if MapBuilder.is_kinds_loaded():
		return true
	if http_base != "":
		var data: Variant = await _http_get_json(http_base + "/api/kinds")
		if typeof(data) == TYPE_DICTIONARY:
			MapBuilder.set_kinds_from_dict(data)
			return true
		push_warning("KindsLoader: HTTP fetch /api/kinds failed — falling back to res://maps/kinds.json")
	# Fallback: res://maps/kinds.json. Reaktiviert das alte Verhalten — der
	# Editor hat eine Demo-Kopie unter godot-3d/maps/, die im Fall „Server
	# offline" einspringt. Drift-toleranz: alt > nichts.
	if FileAccess.file_exists(_RES_KINDS_PATH):
		var file := FileAccess.open(_RES_KINDS_PATH, FileAccess.READ)
		var parsed = JSON.parse_string(file.get_as_text())
		if typeof(parsed) == TYPE_DICTIONARY:
			MapBuilder.set_kinds_from_dict(parsed)
			return true
	push_warning("KindsLoader: kein Fallback gefunden — alle Kinds rendern als graue Box.")
	return false

func fetch_map(http_base: String, map_id: String) -> Dictionary:
	if http_base != "":
		var data: Variant = await _http_get_json("%s/api/maps/%s" % [http_base, map_id])
		if typeof(data) == TYPE_DICTIONARY and not data.is_empty():
			return data
		push_warning("KindsLoader: HTTP fetch /api/maps/%s failed — falling back to res://" % map_id)
	var path := _RES_MAP_PATH_TEMPLATE % map_id
	if FileAccess.file_exists(path):
		var file := FileAccess.open(path, FileAccess.READ)
		var parsed = JSON.parse_string(file.get_as_text())
		if typeof(parsed) == TYPE_DICTIONARY:
			return parsed
	return {}

# -- HTTP helper -------------------------------------------------------------

# Issue a GET against `url`, await the completion signal, return parsed JSON
# (Dictionary) or null on any failure. Uses a child HTTPRequest node so we
# don't leak between calls. Timeout enforced server-side via timeout_sec.
func _http_get_json(url: String) -> Variant:
	var req := HTTPRequest.new()
	req.timeout = _HTTP_TIMEOUT_SEC
	add_child(req)
	var err := req.request(url)
	if err != OK:
		req.queue_free()
		return null
	var result: Array = await req.request_completed
	req.queue_free()
	# request_completed signature: (result_code, response_code, headers, body).
	var result_code: int = int(result[0]) if result.size() > 0 else -1
	var response_code: int = int(result[1]) if result.size() > 1 else 0
	var body: PackedByteArray = result[3] if result.size() > 3 else PackedByteArray()
	if result_code != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		return null
	var text := body.get_string_from_utf8()
	var parsed = JSON.parse_string(text)
	return parsed
