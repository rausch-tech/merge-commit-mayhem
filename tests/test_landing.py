"""Tests für die Landing-Page-Routen.

Routing-Layout (siehe ``app/main.py``):

* ``GET /``       -> ``static/landing.html`` (Marketing-Landing)
* ``GET /play``   -> ``static/index.html``   (das Spiel selbst)
* ``GET /editor`` -> ``static/editor/editor.html`` (Map-Editor, separater Test)

Die Landing ist ein statisches Dokument ohne Server-State. Die Tests stellen
sicher, dass die Routes existieren, das richtige File ausliefern und der
Static-Mount Landing-Assets erreichbar macht.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

_REPO_ROOT = Path(__file__).resolve().parent.parent
_LANDING_HTML = _REPO_ROOT / "static" / "landing.html"
_INDEX_HTML = _REPO_ROOT / "static" / "index.html"
_LANDING_CSS = _REPO_ROOT / "static" / "landing.css"
_LANDING_JS = _REPO_ROOT / "static" / "landing.js"


def test_root_serves_landing_html() -> None:
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert resp.text == _LANDING_HTML.read_text(encoding="utf-8")


def test_play_route_serves_game_index_html() -> None:
    client = TestClient(app)
    resp = client.get("/play")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert resp.text == _INDEX_HTML.read_text(encoding="utf-8")


def test_landing_links_to_play_route() -> None:
    """Smoke check: die Landing muss eine Spielen-CTA auf /play haben."""
    html = _LANDING_HTML.read_text(encoding="utf-8")
    assert 'href="/play"' in html


def test_landing_css_is_reachable_via_static_mount() -> None:
    client = TestClient(app)
    resp = client.get("/static/landing.css")
    assert resp.status_code == 200
    assert resp.text == _LANDING_CSS.read_text(encoding="utf-8")


def test_landing_js_is_reachable_via_static_mount() -> None:
    client = TestClient(app)
    resp = client.get("/static/landing.js")
    assert resp.status_code == 200
    assert resp.text == _LANDING_JS.read_text(encoding="utf-8")
