"""Tests fuer den Godot-Web-Export-Mount unter ``/godot/``.

Build-Output (`scripts/godot-web-export.sh`) landet unter
``godot-3d/exports/``. ``app/main.py`` mountet das Verzeichnis nur wenn
``index.html`` existiert. Wenn nicht: kein Mount, /godot gibt 404.

Wenn der Build vorliegt: der Mount muss
- index.html bei ``/godot/`` ausliefern,
- ``Cross-Origin-Opener-Policy`` und ``Cross-Origin-Embedder-Policy``
  setzen (sonst kann der Browser-Build kein SharedArrayBuffer nutzen),
- die anderen Pfade (``/``, ``/static/...``) NICHT mit den Headers
  belegen — die wuerden CDN-Resources im Editor blockieren.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

_REPO_ROOT = Path(__file__).resolve().parent.parent
_GODOT_INDEX = _REPO_ROOT / "godot-3d" / "exports" / "index.html"


def _has_build() -> bool:
    return _GODOT_INDEX.is_file()


def test_landing_does_not_carry_godot_isolation_headers() -> None:
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    # Negativ-Aussage: Apex / Landing soll OHNE die Cross-Origin-Headers
    # ausgeliefert werden, sonst zerschiesst es CDN-Loads im Editor.
    assert "cross-origin-opener-policy" not in {k.lower() for k in resp.headers}
    assert "cross-origin-embedder-policy" not in {k.lower() for k in resp.headers}


@pytest.mark.skipif(
    not _has_build(),
    reason="Godot-Web-Build nicht vorhanden — scripts/godot-web-export.sh ausfuehren",
)
def test_godot_index_served_with_isolation_headers() -> None:
    client = TestClient(app)
    resp = client.get("/godot/")
    assert resp.status_code == 200, resp.text[:200]
    assert resp.headers["cross-origin-opener-policy"] == "same-origin"
    assert resp.headers["cross-origin-embedder-policy"] == "require-corp"
    assert "<html" in resp.text.lower() or "<!doctype" in resp.text.lower()


@pytest.mark.skipif(not _has_build(), reason="Godot-Web-Build nicht vorhanden")
def test_godot_wasm_carries_isolation_headers() -> None:
    client = TestClient(app)
    resp = client.get("/godot/index.wasm")
    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/wasm"
    assert resp.headers["cross-origin-opener-policy"] == "same-origin"
    assert resp.headers["cross-origin-embedder-policy"] == "require-corp"
