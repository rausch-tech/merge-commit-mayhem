"""Tests for the map registry: discover_maps, lazy cache, and bad-file skip."""

import json
from pathlib import Path

from app.game.game_map import (
    DEFAULT_MAP_ID,
    GameMap,
    discover_maps,
    get_map_registry,
    load_map,
    reload_map_registry,
    resolve_default_map_id,
)


def test_discover_maps_returns_default_and_small():
    registry = discover_maps()
    assert "default" in registry
    assert "small" in registry
    assert isinstance(registry["default"], GameMap)
    assert isinstance(registry["small"], GameMap)


def test_default_and_small_load_via_load_map():
    maps_dir = Path(__file__).parent.parent / "maps"
    default_map = load_map(maps_dir / "default.json")
    small_map = load_map(maps_dir / "small.json")
    assert default_map.name == "default-office"
    assert small_map.name == "small-arena"
    assert small_map.size.width == 2400
    assert small_map.size.height == 1600


def test_corrupt_json_in_maps_dir_does_not_break_discovery(tmp_path):
    # A good map clone + a corrupt file should still yield the good one.
    maps_dir = Path(__file__).parent.parent / "maps"
    good_payload = json.loads((maps_dir / "default.json").read_text(encoding="utf-8"))
    (tmp_path / "good.json").write_text(json.dumps(good_payload), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")
    # And a structurally invalid one (missing war_room_id) — Pydantic should reject.
    bad_struct = {"name": "x", "size": {"width": 1, "height": 1}, "rooms": []}
    (tmp_path / "structbad.json").write_text(json.dumps(bad_struct), encoding="utf-8")

    registry = discover_maps(tmp_path)
    assert "good" in registry
    assert "broken" not in registry
    assert "structbad" not in registry


def test_get_map_registry_is_cached():
    a = get_map_registry()
    b = get_map_registry()
    assert a is b


def test_reload_map_registry_replaces_cache():
    a = get_map_registry()
    b = reload_map_registry()
    assert b is not a
    # The newly-cached one is also returned by subsequent get_map_registry calls.
    assert get_map_registry() is b


def test_resolve_default_map_id_prefers_default_constant():
    assert resolve_default_map_id({"default": object(), "small": object()}) == DEFAULT_MAP_ID


def test_resolve_default_map_id_falls_back_to_first_sorted():
    assert resolve_default_map_id({"foo": object(), "bar": object()}) == "bar"


def test_resolve_default_map_id_handles_empty_registry():
    # Falls back to the constant so wire never has empty selectedMapId.
    assert resolve_default_map_id({}) == DEFAULT_MAP_ID
