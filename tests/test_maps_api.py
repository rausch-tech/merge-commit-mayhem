"""Tests for the /api/maps endpoints used by the editor's Save-to-Server flow.

These endpoints write into the live ``maps/`` directory. The fixtures here
redirect ``_MAPS_DIR`` into a tmp dir so the real maps don't get clobbered
by test runs.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.game import game_map as gm
from app.main import app


@pytest.fixture
def tmp_maps_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the registry at an empty tmp dir + invalidate the cache so each
    test gets a fresh maps storage."""
    target = tmp_path / "maps"
    target.mkdir()
    monkeypatch.setattr(gm, "_MAPS_DIR", target)
    monkeypatch.setattr(gm, "_MAP_REGISTRY_CACHE", None)
    yield target


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _minimal_map() -> dict[str, object]:
    return {
        "name": "test-arena",
        "size": {"width": 1600, "height": 1200},
        "rooms": [
            {
                "id": "room_a",
                "title": "A",
                "x": 0,
                "y": 0,
                "width": 800,
                "height": 1200,
                "color": "#3a4560",
            },
            {
                "id": "room_b",
                "title": "B",
                "x": 800,
                "y": 0,
                "width": 800,
                "height": 1200,
                "color": "#5a3a70",
            },
        ],
        "doors": [],
        "spawnPoints": [{"x": 100, "y": 100}],
        "taskAnchors": [],
        "sabotagePanels": [],
        "vents": [],
        "mapObjects": [],
        "warRoomId": "room_a",
    }


def test_list_maps_returns_sorted_id_name_pairs(tmp_maps_dir: Path, client: TestClient) -> None:
    """GET /api/maps lists every *.json under maps/ as ``{id, name}``."""
    (tmp_maps_dir / "alpha.json").write_text(json.dumps({**_minimal_map(), "name": "Alpha-Map"}))
    (tmp_maps_dir / "beta.json").write_text(json.dumps({**_minimal_map(), "name": "Beta-Map"}))
    r = client.get("/api/maps")
    assert r.status_code == 200
    data = r.json()
    assert data == {
        "maps": [
            {"id": "alpha", "name": "Alpha-Map"},
            {"id": "beta", "name": "Beta-Map"},
        ]
    }


def test_get_map_returns_full_json(tmp_maps_dir: Path, client: TestClient) -> None:
    """GET /api/maps/{id} returns the full JSON for the editor to load."""
    payload = _minimal_map()
    (tmp_maps_dir / "alpha.json").write_text(json.dumps(payload))
    r = client.get("/api/maps/alpha")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "test-arena"
    assert body["warRoomId"] == "room_a"
    assert len(body["rooms"]) == 2


def test_get_map_unknown_id_404(tmp_maps_dir: Path, client: TestClient) -> None:
    r = client.get("/api/maps/never_existed")
    assert r.status_code == 404
    assert r.json()["detail"] == "map not found"


def test_get_map_invalid_id_400(tmp_maps_dir: Path, client: TestClient) -> None:
    """Slug must be ``[a-z0-9][a-z0-9_-]{0,39}``."""
    r = client.get("/api/maps/UPPERCASE")
    assert r.status_code == 400


def test_put_map_creates_file_and_updates_registry(tmp_maps_dir: Path, client: TestClient) -> None:
    """PUT /api/maps/{id} writes the JSON and reloads the registry."""
    payload = _minimal_map()
    r = client.put("/api/maps/freshly_made", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "id": "freshly_made",
        "name": "test-arena",
        "rooms": 2,
        "doors": 0,
        "mapObjects": 0,
    }
    target = tmp_maps_dir / "freshly_made.json"
    assert target.exists()
    on_disk = json.loads(target.read_text())
    assert on_disk["name"] == "test-arena"
    # Registry picked up the new map without restart.
    assert "freshly_made" in gm.get_map_registry()


def test_put_map_overwrites_existing(tmp_maps_dir: Path, client: TestClient) -> None:
    """PUT is idempotent: posting the same id twice overwrites the file."""
    payload = _minimal_map()
    client.put("/api/maps/edited", json=payload)
    payload2 = {**payload, "name": "renamed-arena"}
    r = client.put("/api/maps/edited", json=payload2)
    assert r.status_code == 200
    target = tmp_maps_dir / "edited.json"
    on_disk = json.loads(target.read_text())
    assert on_disk["name"] == "renamed-arena"


def test_put_map_invalid_id_rejected(tmp_maps_dir: Path, client: TestClient) -> None:
    """Path-traversal-ish ids fail with 400 — the disk never sees them."""
    r = client.put("/api/maps/../etc_passwd", json=_minimal_map())
    # Either FastAPI normalizes the URL to nothing matching (404) or our
    # validator catches it (400). Both block the write — we just need to
    # confirm nothing was written.
    assert r.status_code in (400, 404)
    assert not list(tmp_maps_dir.glob("*.json"))


def test_put_map_validation_error_returns_422(tmp_maps_dir: Path, client: TestClient) -> None:
    """A schema-violating body comes back with 422 + Pydantic error details."""
    bad = _minimal_map()
    del bad["warRoomId"]  # required field
    r = client.put("/api/maps/broken", json=bad)
    assert r.status_code == 422
    assert "detail" in r.json()
    assert not (tmp_maps_dir / "broken.json").exists()


def test_put_map_extra_fields_rejected(tmp_maps_dir: Path, client: TestClient) -> None:
    """Pydantic ``extra=forbid`` rejects unknown top-level keys (e.g. the
    pre-Slice-3 ``wallLines`` schema)."""
    legacy = _minimal_map()
    legacy["wallLines"] = []
    r = client.put("/api/maps/legacy", json=legacy)
    assert r.status_code == 422


def test_save_map_atomic_rename(tmp_maps_dir: Path) -> None:
    """``save_map`` uses tmp + rename so a partial write never leaves a
    corrupt JSON behind."""
    gm.save_map("atomic_test", _minimal_map(), maps_dir=tmp_maps_dir)
    files = sorted(p.name for p in tmp_maps_dir.iterdir())
    assert files == ["atomic_test.json"]


def test_is_valid_map_id() -> None:
    assert gm.is_valid_map_id("foo")
    assert gm.is_valid_map_id("foo_bar")
    assert gm.is_valid_map_id("foo-bar-1")
    assert gm.is_valid_map_id("a" * 40)
    assert not gm.is_valid_map_id("")
    assert not gm.is_valid_map_id("Foo")  # uppercase
    assert not gm.is_valid_map_id("_leading")  # starts with separator
    assert not gm.is_valid_map_id("-leading")
    assert not gm.is_valid_map_id("a" * 41)  # too long
    assert not gm.is_valid_map_id("a/b")  # slash
    assert not gm.is_valid_map_id("..")
