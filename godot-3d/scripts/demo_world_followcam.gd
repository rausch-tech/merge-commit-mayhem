extends Node

# Same as demo_world.gd but uses the in-game perspective camera (follow-cam).
# Lets us screenshot the real Tier-4 view rather than the aerial overview.

const WORLD_SCENE: PackedScene = preload("res://scenes/world.tscn")

const MOCK_PLAYERS: Array = [
	{"id": "p1", "name": "Sven", "color": "#4ade80", "x": 800, "y": 800, "isHost": true, "isAlive": true},
	{"id": "p2", "name": "Ada", "color": "#60a5fa", "x": 1100, "y": 950, "isHost": false, "isAlive": true},
	{"id": "p3", "name": "Linus", "color": "#f59e0b", "x": 1400, "y": 1200, "isHost": false, "isAlive": true},
]

# Eine Mock-Task direkt neben Spieler p1 (800,800) damit der Hold-Prompt im
# HUD sichtbar ist (TASK_INTERACTION_RADIUS = 40 server-px).
const MOCK_TASKS: Array = [
	{
		"id": "task-uuid-1",
		"taskId": "fix_unit_tests",
		"playerId": "p1",
		"x": 820,
		"y": 800,
		"progress": 0.4,
		"objectType": "qa_terminal",
	},
]

# Mock-Mini-Game-View, gesetzt nach 1.2s Delay damit ein Headless-Render auch
# das Modal + Sprint-Trim-UI capturen kann. Ohne Server-Backend simulieren wir
# einen mini_game_started-Push direkt ueber den ws.message_received-Signal.
const MOCK_SPRINT_TRIM_VIEW: Dictionary = {
	"tickets": [
		{"id": "t0", "title": "Refactor billing service", "points": 8, "priority": false, "removed": false},
		{"id": "t1", "title": "Migrate auth to OIDC", "points": 13, "priority": false, "removed": false},
		{"id": "t2", "title": "Add dark mode", "points": 3, "priority": true, "removed": false},
		{"id": "t3", "title": "Fix flaky test_login_locks", "points": 2, "priority": false, "removed": false},
		{"id": "t4", "title": "Implement audit log export", "points": 5, "priority": true, "removed": false},
		{"id": "t5", "title": "Upgrade Postgres 14 -> 16", "points": 8, "priority": false, "removed": false},
	],
	"budget": 18,
	"remainingPoints": 39,
}

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
		"tasks": MOCK_TASKS,
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

	# Mock-Mini-Game-Trigger nach kurzem Delay, damit Headless-Render ein
	# Frame mit offenem Modal capturen kann. _trigger_mock_minigame fired
	# einen mini_game_started in den ws-Signal-Stream — der WSClient leitet
	# nichts (ist nicht verbunden), aber world.gd haengt am Signal.
	var timer := Timer.new()
	timer.wait_time = 1.2
	timer.one_shot = true
	timer.timeout.connect(func(): _trigger_mock_minigame(ws))
	add_child(timer)
	timer.start()

func _trigger_mock_minigame(ws: WSClient) -> void:
	ws.message_received.emit("mini_game_started", {
		"taskId": "fix_unit_tests",
		"miniGameId": "sprint_trim",
		"title": "Scope reduzieren",
		"view": MOCK_SPRINT_TRIM_VIEW,
	})

func _load_map() -> Dictionary:
	var path := "res://maps/default.json"
	if not FileAccess.file_exists(path):
		return {"name": "fallback", "size": {"width": 4800, "height": 3200}, "rooms": [], "wallLines": [], "spawnPoints": [], "taskAnchors": []}
	var file := FileAccess.open(path, FileAccess.READ)
	var parsed = JSON.parse_string(file.get_as_text())
	return parsed if typeof(parsed) == TYPE_DICTIONARY else {}
