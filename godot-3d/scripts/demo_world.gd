extends Node

# Headless demo entry — loads the World scene directly with mocked data so we
# can validate the 3D render without running the FastAPI backend or doing the
# manual Godot lobby flow. Shipped for demo screenshots and quick visual
# regression checks. Not part of the real game flow — main.tscn is the entry.
#
# Usage:
#   godot --path godot-3d --rendering-driver opengl3 \
#       --main-scene res://scenes/demo_world.tscn --quit-after 200

const WORLD_SCENE: PackedScene = preload("res://scenes/world.tscn")

const MOCK_PLAYERS: Array = [
	{"id": "p1", "name": "Sven", "color": "#4ade80", "x": 800, "y": 800, "isHost": true, "isAlive": true},
	{"id": "p2", "name": "Ada", "color": "#60a5fa", "x": 1100, "y": 950, "isHost": false, "isAlive": true},
	{"id": "p3", "name": "Linus", "color": "#f59e0b", "x": 2400, "y": 800, "isHost": false, "isAlive": true},
	{"id": "p4", "name": "Grace", "color": "#ec4899", "x": 4000, "y": 1200, "isHost": false, "isAlive": true},
	{"id": "p5", "name": "Carol", "color": "#a855f7", "x": 1100, "y": 2400, "isHost": false, "isAlive": true},
]

func _ready() -> void:
	var map := _load_map()
	var initial_state := _mock_state(map)
	var role_info := {
		"role": "developer",
		"team": "release_team",
		"description": "Du bist Developer. Beende Tasks und finde die Chaos-Agenten.",
	}

	var ws := WSClient.new()
	# We don't actually connect — the WSClient just sits there silently.
	add_child(ws)

	var world := WORLD_SCENE.instantiate()
	world.set("ws_client", ws)
	world.set("player_id", "p1")
	world.set("is_host", true)
	world.set("map_data", map)
	world.set("role_info", role_info)
	world.set("initial_state", initial_state)
	# Aerial mode is the default for screenshots; flip to false to test the
	# real game-mode follow-camera locally via:
	#   godot --path godot-3d --scene res://scenes/demo_world.tscn
	# combined with editing this line.
	world.set("aerial_demo_camera", true)
	get_tree().root.add_child.call_deferred(world)

func _load_map() -> Dictionary:
	# Hardcoded to office_complex for the bigger 9-room map with central corridor.
	# Switch back to "default" via the path constant if the small map is needed.
	var path := "res://maps/office_complex.json"
	print("[demo] map exists: ", FileAccess.file_exists(path))
	if not FileAccess.file_exists(path):
		print("[demo] map fallback: minimal map")
		return {
			"name": "fallback",
			"size": {"width": 4800, "height": 3200},
			"rooms": [],
			"wallLines": [],
			"spawnPoints": [],
			"taskAnchors": [],
		}
	var file := FileAccess.open(path, FileAccess.READ)
	var text := file.get_as_text()
	var parsed = JSON.parse_string(text)
	if typeof(parsed) == TYPE_DICTIONARY:
		print("[demo] map loaded: ", parsed.get("name", "?"), " rooms=", parsed.get("rooms", []).size())
		return parsed
	print("[demo] map parse failed")
	return {}

func _mock_state(_map: Dictionary) -> Dictionary:
	return {
		"phase": "playing",
		"remainingSeconds": 542,
		"releaseProgress": 35,
		"pipelineStability": 78,
		"coffeeLevel": 90,
		"incidents": 12,
		"players": MOCK_PLAYERS,
		"tasks": [],
		"sabotages": [],
		"events": [],
		"bodies": [],
		"meeting": null,
	}
