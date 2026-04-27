"""Single source of truth for valid MapObject kinds.

Reads ``maps/kinds.json`` once, exposes a fast membership check that the
``MapObject.kind`` Pydantic-validator wires up. Other consumers (the Godot
client's ``map_builder.gd``, the browser renderer ``static/render.js``,
the editor palette ``static/editor/editor-kinds.js``) read the same file
directly — Pydantic just guarantees that nothing slips onto the wire that
no consumer knows about.

**Failure mode: fail-loud.** A missing or malformed ``kinds.json`` raises
``RuntimeError`` on the first lookup. Production without a registry is a
deploy bug, mirroring how ``extra=forbid`` catches schema-drift on the
maps themselves (and how the legacy ``wallLines`` field silently nuked
``office_complex.json`` until the migrator caught it).

Cache: lazy-initialised on first ``get_kinds_registry()`` call. Tests can
swap ``_KINDS_PATH`` and call ``reload_kinds_registry()`` to point at a
tmp file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

# JSON layout: top-level keys are kind ids, plus a ``_meta`` block that
# documents the schema for human + machine consumers. Underscore-prefixed
# keys are treated as metadata, never as kinds.
_META_PREFIX: Final[str] = "_"

_KINDS_PATH: Final[Path] = Path(__file__).parent.parent.parent / "maps" / "kinds.json"

# Lazy-loaded cache. ``None`` means "not loaded yet" — the next lookup
# triggers a read. ``reload_kinds_registry()`` resets it to force a
# re-read at the next lookup (or when called explicitly during tests).
_KINDS_CACHE: dict[str, Any] | None = None


def discover_kinds(path: Path | None = None) -> dict[str, Any]:
    """Read ``kinds.json`` verbatim and return the parsed dict.

    Includes the ``_meta`` block — callers that need just the valid-kind
    set should iterate and filter underscore-prefixed keys (or use
    :func:`known_kinds`).

    ``path`` defaults to the module-level :data:`_KINDS_PATH` resolved at
    call time so monkey-patching in tests works without rebinding default
    args (same pattern as ``discover_maps``).

    Raises ``RuntimeError`` when the file is missing or unreadable —
    fail-loud so a broken deploy surfaces immediately instead of silently
    accepting unknown kinds.
    """
    if path is None:
        path = _KINDS_PATH
    if not path.exists():
        raise RuntimeError(
            f"Kinds registry not found at {path}. "
            "maps/kinds.json is the single source of truth for MapObject kinds; "
            "production deploys must include it."
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"Failed to load kinds registry from {path}: {exc}") from exc


def get_kinds_registry() -> dict[str, Any]:
    """Return the full registry dict (including ``_meta``). Cached."""
    global _KINDS_CACHE
    if _KINDS_CACHE is None:
        _KINDS_CACHE = discover_kinds()
    return _KINDS_CACHE


def reload_kinds_registry() -> dict[str, Any]:
    """Force a re-read of ``kinds.json`` and return the fresh registry.

    Used by tests when the path is swapped, and available to callers that
    want hot-reload semantics after editing ``kinds.json`` on the server.
    """
    global _KINDS_CACHE
    _KINDS_CACHE = discover_kinds()
    return _KINDS_CACHE


def is_known_kind(kind: str) -> bool:
    """O(1) check whether ``kind`` is a registered MapObject kind.

    Underscore-prefixed names (the ``_meta`` block) are explicitly NOT
    valid kinds — even if someone names their MapObject ``_meta`` it'd
    fail validation, which is intentional.
    """
    if not kind or kind.startswith(_META_PREFIX):
        return False
    return kind in get_kinds_registry()


def known_kinds() -> frozenset[str]:
    """Snapshot of the valid kind set (excluding ``_meta`` entries).

    Useful for error messages and Editor-side validation. Returns a
    frozenset so callers can't mutate it.
    """
    return frozenset(k for k in get_kinds_registry() if not k.startswith(_META_PREFIX))
