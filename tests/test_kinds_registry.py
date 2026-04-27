"""Tests for ``maps/kinds.json`` as the single source of truth for
MapObject kinds.

Three layers:

1. ``kinds_registry`` module: discover/get/reload + ``is_known_kind`` /
   ``known_kinds`` helpers, fail-loud when the file is missing/broken.
2. ``MapObject.kind`` Pydantic-validator: rejects unknown kinds with a
   message that names the offender + lists the registered set.
3. The ``GET /api/kinds`` endpoint: serves the full registry verbatim.

Plus a smoke that all maps in the production ``maps/`` directory still
load — a regression of the registered set would surface immediately.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.game import kinds_registry as kr
from app.game.game_map import MapObject, load_map
from app.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent
MAPS_DIR = REPO_ROOT / "maps"


@pytest.fixture
def tmp_kinds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the kinds registry to a tmp file + reset the cache.

    On teardown explicitly clears ``_KINDS_CACHE`` again so subsequent
    tests don't see this fixture's tmp registry — the production file
    is reloaded on the next lookup.
    """
    target = tmp_path / "kinds.json"
    monkeypatch.setattr(kr, "_KINDS_PATH", target)
    monkeypatch.setattr(kr, "_KINDS_CACHE", None)
    yield target
    kr._KINDS_CACHE = None


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _write_registry(path: Path, kinds: list[str], with_meta: bool = True) -> None:
    """Write a minimal kinds.json containing the requested kind names."""
    data: dict[str, Any] = {}
    if with_meta:
        data["_meta"] = {"version": 1, "description": "tmp registry for tests"}
    for k in kinds:
        data[k] = {
            "category": "Test",
            "label": k.title(),
            "default_size": [50, 50],
            "blocks_movement": True,
            "browser_2d": {"fill": "#888888", "label": k.upper()},
            "godot_asset": None,
        }
    path.write_text(json.dumps(data, indent=2))


# --- kinds_registry module --------------------------------------------------


def test_discover_kinds_strips_meta(tmp_kinds: Path) -> None:
    """``discover_kinds`` returns the raw dict; callers filter ``_meta``."""
    _write_registry(tmp_kinds, ["desk", "chair_desk"])
    raw = kr.discover_kinds()
    assert "_meta" in raw  # raw passthrough
    assert "desk" in raw
    assert raw["desk"]["category"] == "Test"


def test_known_kinds_excludes_meta(tmp_kinds: Path) -> None:
    """``known_kinds`` is the validation surface — ``_meta`` is not a kind."""
    _write_registry(tmp_kinds, ["desk", "monitor"])
    assert kr.known_kinds() == frozenset({"desk", "monitor"})


def test_is_known_kind_fast_lookup(tmp_kinds: Path) -> None:
    _write_registry(tmp_kinds, ["desk"])
    assert kr.is_known_kind("desk") is True
    assert kr.is_known_kind("never_seen") is False
    # Underscore-prefixed names are explicitly NOT valid kinds, even if
    # they happen to live as top-level dict keys (i.e. ``_meta``).
    assert kr.is_known_kind("_meta") is False
    assert kr.is_known_kind("") is False


def test_get_kinds_registry_caches(tmp_kinds: Path) -> None:
    """First lookup reads from disk; subsequent lookups hit the cache."""
    _write_registry(tmp_kinds, ["desk"])
    first = kr.get_kinds_registry()
    # Mutate the file behind the cache — should NOT be visible.
    _write_registry(tmp_kinds, ["desk", "monitor"])
    second = kr.get_kinds_registry()
    assert first is second
    assert "monitor" not in second
    # reload_kinds_registry forces a re-read.
    third = kr.reload_kinds_registry()
    assert "monitor" in third


def test_missing_kinds_json_fails_loudly(tmp_kinds: Path) -> None:
    """A deploy without kinds.json should not silently accept anything."""
    # tmp_kinds path was set but we never wrote to it.
    with pytest.raises(RuntimeError, match="not found"):
        kr.discover_kinds()


def test_malformed_kinds_json_fails_loudly(tmp_kinds: Path) -> None:
    tmp_kinds.write_text("{ not valid json")
    with pytest.raises(RuntimeError, match="Failed to load"):
        kr.discover_kinds()


# --- MapObject.kind validator -----------------------------------------------


def test_valid_kind_passes_validation(tmp_kinds: Path) -> None:
    _write_registry(tmp_kinds, ["desk", "chair_desk"])
    obj = MapObject(id="o1", x=100, y=100, width=50, height=50, kind="desk")
    assert obj.kind == "desk"


def test_unknown_kind_rejected_with_clear_message(tmp_kinds: Path) -> None:
    _write_registry(tmp_kinds, ["desk", "monitor"])
    with pytest.raises(ValidationError) as exc_info:
        MapObject(
            id="o1",
            x=100,
            y=100,
            width=50,
            height=50,
            kind="definitely_not_real",
        )
    msg = str(exc_info.value)
    assert "definitely_not_real" in msg
    assert "kinds.json" in msg
    # Known set should be enumerated so the dev knows what to use.
    assert "desk" in msg
    assert "monitor" in msg


def test_meta_key_is_not_a_valid_kind(tmp_kinds: Path) -> None:
    """Edge case: even if someone names a MapObject ``_meta`` (matching
    the registry's metadata block), validation should reject it."""
    _write_registry(tmp_kinds, ["desk"])
    with pytest.raises(ValidationError, match="_meta"):
        MapObject(id="o1", x=100, y=100, width=50, height=50, kind="_meta")


# --- Smoke: existing maps still parse --------------------------------------


def test_all_repo_maps_round_trip() -> None:
    """All on-disk ``maps/*.json`` (except kinds.json) load + validate.

    Regression guard: if anyone bumps the registry without keeping the
    maps in sync, this test surfaces the drift immediately.
    """
    # Force re-read against the production registry, undoing any prior
    # test that may have left a stale tmp cache around.
    kr.reload_kinds_registry()
    map_files = [p for p in MAPS_DIR.glob("*.json") if p.name != "kinds.json"]
    assert map_files, "no map files found under maps/ — refusing to falsely pass"
    for path in map_files:
        load_map(path)  # raises ValidationError on any unknown kind


# --- /api/kinds endpoint ---------------------------------------------------


def test_api_kinds_returns_full_registry(client: TestClient) -> None:
    """Endpoint serves the registry as-is, including ``_meta`` so
    consumers can read field documentation alongside the kinds."""
    kr.reload_kinds_registry()  # ensure we're serving the prod file
    r = client.get("/api/kinds")
    assert r.status_code == 200
    body = r.json()
    assert "_meta" in body
    # At least the canonical desk should be present (sanity check).
    assert "desk" in body
    assert body["desk"]["category"] == "Workstation"
