"""Tests for the standalone map-editor page (Tier 1.7).

The editor is a pure client-side tool. The server's only contribution is a
single ``GET /editor`` route that serves the static HTML, plus the existing
``/static`` mount which already exposes the JS/CSS modules. These tests
guard:

  * the route exists, returns 200 + HTML,
  * the static module is reachable through the existing mount,
  * a JSON shaped like what ``editor-state.js::blankMap()`` produces (with a
    single room/spawn/war-room added) loads cleanly through ``load_map()``.

JS-side behaviour is out of scope — no JS test runner in this project.
"""

import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.game.game_map import load_map
from app.main import app

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EDITOR_HTML = _REPO_ROOT / "static" / "editor" / "editor.html"
_EDITOR_JS = _REPO_ROOT / "static" / "editor" / "editor.js"


def test_editor_route_returns_200_and_html() -> None:
    client = TestClient(app)
    resp = client.get("/editor")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_editor_route_serves_editor_html_contents() -> None:
    client = TestClient(app)
    resp = client.get("/editor")
    assert resp.status_code == 200
    expected = _EDITOR_HTML.read_text(encoding="utf-8")
    assert resp.text == expected


def test_editor_js_is_reachable_via_static_mount() -> None:
    client = TestClient(app)
    resp = client.get("/static/editor/editor.js")
    assert resp.status_code == 200
    # Sanity check: the served file matches the on-disk module.
    assert resp.text == _EDITOR_JS.read_text(encoding="utf-8")


def _blank_map_payload() -> dict:
    """Mirror ``editor-state.js::blankMap()`` for round-trip testing."""
    return {
        "name": "untitled",
        "size": {"width": 4800, "height": 3200},
        "rooms": [],
        "doors": [],
        "spawnPoints": [],
        "taskAnchors": [],
        "warRoomId": "",
    }


def test_exported_minimal_map_round_trips_through_load_map() -> None:
    """A blank map plus one room + one spawn + a war-room must validate."""
    payload = _blank_map_payload()
    payload["name"] = "round_trip_test"
    payload["rooms"].append(
        {
            "id": "r1",
            "title": "Room 1",
            "x": 0,
            "y": 0,
            "width": 1600,
            "height": 1600,
            "color": "#3a4560",
        }
    )
    payload["spawnPoints"].append({"x": 400, "y": 400})
    payload["warRoomId"] = "r1"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        tmp_path = Path(f.name)

    game_map = load_map(tmp_path)
    assert game_map.name == "round_trip_test"
    assert len(game_map.rooms) == 1
    assert game_map.rooms[0].id == "r1"
    assert game_map.war_room_id == "r1"
    assert len(game_map.spawn_points) == 1
    assert game_map.spawn_points[0].x == 400
