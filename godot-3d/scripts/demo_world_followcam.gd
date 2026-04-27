extends Node

# Same as demo_world.gd but uses the in-game perspective camera (follow-cam).
# Lets us screenshot the real Tier-4 view rather than the aerial overview.

const WORLD_SCENE: PackedScene = preload("res://scenes/world.tscn")

const MOCK_PLAYERS: Array = [
	{"id": "p1", "name": "Sven", "color": "#4ade80", "x": 800, "y": 800, "isHost": true, "isAlive": true},
	{"id": "p2", "name": "Ada", "color": "#60a5fa", "x": 1100, "y": 950, "isHost": false, "isAlive": true},
	{"id": "p3", "name": "Linus", "color": "#f59e0b", "x": 1400, "y": 1200, "isHost": false, "isAlive": true},
]

func _ready() -> void:
	var map := _load_map()
	var initial_state := {
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
	var role_info := {
		"role": "developer",
		"team": "release_team",
	}
	# Mock private_state — Personal-Coffee-Bar im HUD bei ~65% statt leer.
	var mock_private_state := {
		"coffeeEnergy": 65.0,
		"coffeeMax": 100.0,
		"abilityUsed": false,
		"takedownCooldownRemaining": 0.0,
	}

	var ws := WSClient.new()
	add_child(ws)

	var world := WORLD_SCENE.instantiate()
	world.set("ws_client", ws)
	world.set("player_id", "p1")
	world.set("is_host", true)
	world.set("map_data", map)
	world.set("role_info", role_info)
	world.set("initial_state", initial_state)
	world.set("private_state", mock_private_state)
	world.set("aerial_demo_camera", false)  # follow-cam mode
	get_tree().root.add_child.call_deferred(world)

func _load_map() -> Dictionary:
	var path := "res://maps/default.json"
	if not FileAccess.file_exists(path):
		return {"name": "fallback", "size": {"width": 4800, "height": 3200}, "rooms": [], "wallLines": [], "spawnPoints": [], "taskAnchors": []}
	var file := FileAccess.open(path, FileAccess.READ)
	var parsed = JSON.parse_string(file.get_as_text())
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}
