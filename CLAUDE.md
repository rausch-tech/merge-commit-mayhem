# Merge Conflict Mayhem — Projekt-Leitfaden für Claude

## Was das ist

Internes Multiplayer-Spiel für Tech-Teams: Release-Team vs. geheime Chaos-Agenten
(Social Deduction mit DevOps-Humor, 8–12 Minuten pro Runde). Ziel: intern mit
5–12 Leuten in der Mittagspause spielbar; später Godot-Client mit Python-Backend.

## Architektur-Nordstern (nicht-verhandelbar)

> **Python entscheidet. Der Client zeigt nur an.**

- Backend (FastAPI, Pydantic v2, WebSockets) ist autoritativ für *allen* State.
- Clients senden Input, rendern empfangene Snapshots. Keine Spiellogik im Browser.
- WebSocket-Protokoll JSON, camelCase auf der Wire, Godot-kompatibel halten.
- Öffentlicher `game_state` enthält **nie** geheime Rollen.

Wenn eine Feature-Idee Spiellogik in den Client drücken würde → zurückschieben.

## Wichtige Orte

- **Design-Bibel** (Master-Paket, von Sven geliefert): `merge_conflict_mayhem_project/`
- **Aktive Specs**: `docs/superpowers/specs/`
- **Implementierungspläne**: `docs/superpowers/plans/`
- **Code**: `app/` (Backend), `static/` (Frontend), `tests/` (pytest)

Aktueller Sprint-Cut siehe:
`docs/superpowers/specs/2026-04-24-vertical-slice-lobby-movement-design.md`

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

Größere Features laufen so:
1. `superpowers:brainstorming` → Spec in `docs/superpowers/specs/`
2. `superpowers:writing-plans` → Plan in `docs/superpowers/plans/`
3. `superpowers:subagent-driven-development` → Ausführung im Worktree
4. `superpowers:finishing-a-development-branch` → Merge-Entscheidung

Kleinere Fixes dürfen direkt im aktuellen Branch passieren.

## Remote

- `origin` = `git@github.com:sven-rausch/merge-commit-mayhem.git`, branch `main` (primary, **push hier**).
- `gitlab` = `git@gitlab.com:rauschtechnology/mergeconflictmayhem.git` — historisches Mirror, nicht mehr aktiv. Push erforderte ggf. Force wegen Rebase-Divergenz; nicht ungefragt anfassen.

Repo wurde am 2026-04-25 von GitLab nach GitHub verschoben. Tags wurden re-tagged auf den GitHub-Commit-Graph (rebased onto GitHub's init commit).
