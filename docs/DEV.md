# Lokale Entwicklung

Alles was du brauchst, um lokal zu hacken, zu testen, und einen PR aufzumachen.

---

## 1. Voraussetzungen

| Tool            | Wie installieren                                                                      |
| --------------- | ------------------------------------------------------------------------------------- |
| **Python 3.12** | Wenn `uv` installiert ist, kümmert er sich darum: `uv python install 3.12`            |
| **uv**          | `curl -LsSf https://astral.sh/uv/install.sh \| sh` (siehe https://docs.astral.sh/uv/) |
| **Node.js 20+** | Optional (nur für Prettier). `nvm install 20` oder via Distro-Paket.                  |
| **Git**         | sollte da sein                                                                        |

---

## 2. Erst-Setup

```bash
# Repo clonen
git clone git@github.com:rausch-tech/merge-commit-mayhem.git
cd merge-commit-mayhem

# Python-Deps installieren (inkl. Dev-Tools)
uv sync

# Pre-commit-Hooks aktivieren (einmalig)
uv run pre-commit install
```

Nach `uv sync` hast du eine `.venv/` mit Python 3.12 + allen Deps. Du musst die nie selbst aktivieren — `uv run` macht das automatisch.

---

## 3. Server starten

```bash
uv run uvicorn app.main:app --reload
```

Browser: http://localhost:8000

`--reload` heißt Server startet bei jeder Code-Änderung neu. Static-Files im Browser brauchen einen normalen Refresh (cache busting nicht nötig wenn Reload aktiv).

### Mehrere Spieler simulieren

Drei Browser-Tabs mit selber URL, unterschiedliche Namen, gleicher Raumcode (`ABCD`). Erster Tab ist Host, sieht „Runde starten".

### Solo testen (Demo-Mode)

Im Lobby-Bildschirm „Demo-Mode" anhaken vor Start. Solo-Spieler bekommt automatisch die Chaos-Rolle, sieht Sabotage-Buttons, kann alle Mechaniken alleine testen.

---

## 4. Tests

```bash
# Alle Backend-Tests
uv run pytest

# Mit Output bei Fail (-q ist quiet, -v ist verbose)
uv run pytest -v

# Nur ein File
uv run pytest tests/test_game_room.py

# Nur ein Test
uv run pytest tests/test_voting.py::test_majority_vote_eliminates_target -v

# Test bricht ab beim ersten Fail (-x)
uv run pytest -x
```

Aktuell: 207 Backend-Tests. Frontend-Tests kommen mit Tier 0.3.

---

## 5. Lint + Format

```bash
# Python (Ruff)
uv run ruff check .              # Lint
uv run ruff check --fix .        # Lint + auto-fix
uv run ruff format .             # Format
uv run ruff format --check .     # Format-Check (CI-Style)

# JavaScript / Markdown (Prettier)
npx --yes prettier@3.3.3 --check 'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md' 'CONTRIBUTING.md' 'README.md'
npx --yes prettier@3.3.3 --write 'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md' 'CONTRIBUTING.md' 'README.md'

# Alles auf einmal (was CI auch macht):
uv run ruff check . && uv run ruff format --check . && uv run pytest -q && \
  npx --yes prettier@3.3.3 --check 'static/**/*.{js,css,html}' '*.md' 'docs/**/*.md' 'CONTRIBUTING.md' 'README.md'
```

Pre-commit-Hook (siehe Erst-Setup) macht das automatisch bei jedem `git commit`.

---

## 6. Branching + Worktrees

### Branch-Konvention

| Prefix              | Wofür                                                                           |
| ------------------- | ------------------------------------------------------------------------------- |
| `slice/<kurztitel>` | Sprint-Schnitte aus der Roadmap (z.B. `slice/voting`, `slice/scrolling-camera`) |
| `feat/<kurz>`       | Einzelnes Feature, kleiner als ein Tier-Item                                    |
| `fix/<kurz>`        | Bugfix                                                                          |
| `docs/<kurz>`       | Reine Doku-Änderung                                                             |
| `chore/<kurz>`      | Tooling, CI, deps                                                               |

### Worktree-Workflow (empfohlen für Slices)

Statt auf `main` zu wechseln: separate Working-Directory pro Branch. So bleibt der Server lokal weiterlaufen, während du an einer anderen Stelle baust.

```bash
# Neuen Slice anfangen
git worktree add .worktrees/<branch-basename> -b slice/<kurztitel>
cd .worktrees/<branch-basename>

# Hacken, testen, committen
uv sync
uv run pytest
git add ... && git commit -m "..."

# Wenn fertig: in Hauptpfad mergen + worktree weg
cd /home/sven-rausch/se/mcm
git merge --ff-only slice/<kurztitel>
git push origin main
git worktree remove .worktrees/<branch-basename>
git branch -d slice/<kurztitel>

# Optional: Tag
git tag -a slice/<kurztitel>-v1 -m "..."
git push origin slice/<kurztitel>-v1
```

`.worktrees/` ist per `.gitignore` ausgeschlossen.

---

## 7. Commit-Konventionen

[Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

Beispiele:

```text
feat(game): add MEETING phase, voting, and elimination
fix(routing): mount static files under /static to stop websocket crash
docs: add Pre-Godot cleanup checklist
chore: scaffold uv project with fastapi and pytest
test: add websocket integration tests covering join/start/disconnect
refactor: extract game map to data file
```

Common types: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`, `style`, `perf`, `build`, `ci`.

---

## 8. Pull-Request-Flow

1. Branch von `main`: `git checkout -b feat/dein-feature`
2. Hacken, testen, committen
3. Push: `git push -u origin feat/dein-feature`
4. PR aufmachen: `gh pr create --fill --base main`
5. CI muss grün sein (`gh pr checks <pr-number>` zum Verfolgen)
6. Review-Feedback einarbeiten (commits anhängen, kein force-push)
7. Merge erfolgt squash, damit `main`-History sauber bleibt

---

## 9. Häufige Aufgaben

### Neue Task implementieren

1. `app/game/tasks.py`: Definition zur `TASK_DEFINITIONS`-Liste hinzufügen
2. `maps/default.json`: Position in `taskAnchors` setzen (innerhalb des Raum-Rechtecks)
3. `static/sprites.js`: Sprite-Mapping in `SPRITES` ergänzen (Sheet `ui_icon_set.png`)
4. Test in `tests/test_tasks.py` (oder erweitern)

### Neue Sabotage implementieren

1. `app/game/sabotages.py`: `SabotageDefinition` zur Liste hinzufügen
2. `app/game/game_room.py:apply_sabotage`: Effekt-Branch
3. `static/sprites.js`: Icon-Mapping (Sheet `sabotage_icons.png`)
4. `static/sabotages.js:TITLE_LABELS`: Anzeige-Name
5. Test in `tests/test_sabotages.py`

### Neue Map

1. `maps/<name>.json` nach Schema in `docs/maps.md`
2. Validieren: `uv run python -c "from app.game.game_map import load_map; print(load_map('maps/<name>.json').name)"`
3. (Aktuell wird nur `maps/default.json` geladen — Multi-Map kommt mit Tier 1.8)

### Neuen Test schreiben

```bash
# Ein neues File anlegen, das mit test_ anfängt:
touch tests/test_my_feature.py

# Inhalt:
# def test_my_feature_does_x():
#     assert ...

uv run pytest tests/test_my_feature.py -v
```

Pytest-Konventionen:

- File-Name: `test_*.py`
- Funktions-Name: `test_*`
- Tests sind unabhängig — keine Reihenfolge-Annahmen
- Keine Mocks für `GameRoom` — nutze die echte Klasse, ist günstig genug

---

## 10. Häufige Probleme

### „Address already in use" beim `uv run uvicorn`

Anderer uvicorn läuft noch. Stoppe ihn:

```bash
pkill -f "uvicorn.*app.main"
```

### `uv sync` schlägt fehl mit Network-Error

`uv` braucht PyPI. Wenn du hinter einem Proxy bist: `uv sync --index-url https://your-proxy/...`. Sonst: VPN aus, Coffee, retry.

### Tests hängen unendlich

Wahrscheinlich ein WebSocket-Test ohne `with TestClient(app) as client:` — siehe Architektur-Doc Abschnitt 8. Lifespan läuft nicht, Tick-Loop fehlt, Tests warten auf Messages die nie kommen. Fix: Test mit `with`-Statement umbauen.

### CI rot, lokal grün

99 % der Fälle: pre-commit nicht installiert lokal. `uv run pre-commit install`, danach laufen die Hooks bei jedem Commit. Oder: `uv run pre-commit run --all-files` einmal manuell.

---

## 11. Wo ist was

Quick-Reference: siehe Code-Layout in [`ARCHITECTURE.md`](ARCHITECTURE.md) Abschnitte 5 + 6.

Wenn du etwas suchst:

- **WebSocket-Frame-Schema:** [`PROTOCOL.md`](PROTOCOL.md)
- **Map-JSON-Schema:** [`maps.md`](maps.md)
- **Deploy:** [`DEPLOY.md`](DEPLOY.md)
- **Roadmap:** [`ROADMAP.md`](ROADMAP.md)
- **Was beitragen:** [`../CONTRIBUTING.md`](../CONTRIBUTING.md)

---

## 12. Häufige `gh` (GitHub CLI) Befehle

```bash
# CI-Status nach einem Push
gh run list --limit 5
gh run watch                    # live-tailen während Run läuft
gh run view --log-failed        # nur Fehler-Logs

# PRs
gh pr list
gh pr create --fill
gh pr view <num>
gh pr checkout <num>            # PR-Branch lokal auschecken

# Secrets (für CI/Deploy)
gh secret list
gh secret set EC2_HOST --body "3.78.184.97"

# Repo im Browser
gh browse                       # aktueller Branch
gh browse docs/ROADMAP.md       # bestimmte Datei
```
