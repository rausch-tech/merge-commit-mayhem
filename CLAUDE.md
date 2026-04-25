# Merge Conflict Mayhem — Projekt-Leitfaden für Claude

## Was das ist

Internes Multiplayer-Spiel für Tech-Teams: Release-Team vs. geheime Chaos-Agenten
(Social Deduction mit DevOps-Humor, 8–12 Minuten pro Runde). Ziel: intern mit
5–12 Leuten in der Mittagspause spielbar; später Godot-Client mit Python-Backend.

## Architektur-Nordstern (nicht-verhandelbar)

> **Python entscheidet. Der Client zeigt nur an.**

- Backend (FastAPI, Pydantic v2, WebSockets) ist autoritativ für _allen_ State.
- Clients senden Input, rendern empfangene Snapshots. Keine Spiellogik im Browser.
- WebSocket-Protokoll JSON, camelCase auf der Wire, Godot-kompatibel halten.
- Öffentlicher `game_state` enthält **nie** geheime Rollen.

Wenn eine Feature-Idee Spiellogik in den Client drücken würde → zurückschieben.

## Wichtige Orte

- **Roadmap (eine Wahrheit)**: `docs/ROADMAP.md` — Vision + sechs Tier mit konkreten Slices
- **Map-Schema**: `docs/maps.md`
- **Doku-Index**: `docs/README.md`
- **Contributor-Onboarding**: `CONTRIBUTING.md` (top-level)
- **Repo-Quick-Start**: `README.md` (top-level)
- **Code**: `app/` (Backend), `static/` (Frontend), `tests/` (pytest), `maps/` (Map-JSONs)
- **Historisches Design-Paket** (Inspiration, nicht aktuell): `merge_conflict_mayhem_project/`

Specs/Plans pro Slice sind nicht mehr persistiert — die Roadmap ist die Wahrheit, Slice-Details fließen direkt in Implementer-Prompts. Alte Spec-/Plan-Files wurden 2026-04-25 entfernt.

## Tooling

- Python 3.12 + `uv` (kein `pip`, kein `poetry`, kein Venv-Dance)
- Run: `uv run uvicorn app.main:app --reload` → `http://localhost:8000`
- Tests: `uv run pytest`
- Frontend ist plain HTML/CSS/JS + Canvas, serviert von FastAPI (kein Vite/npm in der Slice)

## Konventionen

- **Kommunikation**: Deutsch, knapp, Multiple-Choice-Fragen wenn sinnvoll.
- **Branches**: `slice/<kurztitel>` für Sprint-Teilschnitte, `feat/<kurz>` für Features.
- **Worktrees**: unter `.worktrees/<branch-basename>/` — ist per `.gitignore` ausgeschlossen.
- **Commits**: konventionelle Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:` …).
- **Niemals ungefragt pushen** — auch nicht nach vermeintlich klarer Zustimmung für andere Actions.
- **Keine Emojis** in Code oder Docs, außer explizit angefragt.

## Workflow-Erwartungen

- **Slices** sind die Arbeitseinheit. Pro Slice: eigener Branch (`slice/<kurztitel>` oder `feat/<kurz>`), eigener Worktree unter `.worktrees/`, Tests müssen grün bleiben.
- **Roadmap** (`docs/ROADMAP.md`) bestimmt Reihenfolge. Nicht eigenmächtig springen.
- **Specs/Plans** schreiben wir nur für nicht-triviale Slices (>1 Tag). Kleinere Slices werden direkt via Implementer-Prompt umgesetzt.
- **Live-Tests** validieren Tier-Übergänge — Tier ist erst „done" wenn mit echten Spielern getestet.
- **Live-Server** läuft auf https://game.prod-is-lava.dev (AWS EC2, eu-central-1). Deploy via Tarball + scp.

Kleinere Fixes dürfen direkt im aktuellen Branch passieren.

## Remote

`origin` = `git@github.com:rausch-tech/merge-commit-mayhem.git`, branch `main`.

Repo-History: 2026-04-25 von GitLab (`rauschtechnology/mergeconflictmayhem`) → GitHub (`sven-rausch/merge-commit-mayhem`) → GitHub-Org (`rausch-tech/merge-commit-mayhem`). Tags wurden beim ersten GitHub-Move neu gesetzt (rebase auf GitHub-Init); der spätere Org-Move hat alles 1:1 mitgenommen. Alte Remote-URLs sind nicht mehr eingebunden.
