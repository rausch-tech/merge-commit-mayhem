# Vertical Slice: Lobby + Movement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Baue die client-agnostische Architektur-Pipeline für Merge Conflict Mayhem (Python-Backend autoritativ, Browser rendert nur) in einer Vertical Slice ohne Game-Loop-Mechanik — Ziel ist: drei Browser-Tabs joinen denselben Raumcode, Host startet, alle sehen sich auf der Map bewegen, Timer läuft runter, jeder Spieler kennt seine geheime Rolle.

**Architecture:** FastAPI mit einem globalen 20-Hz-Tick-Task in `lifespan`, einer `GameRegistry` (in-memory dict), einer `ConnectionManager`-Instanz und statischem Frontend-Serving direkt aus `/static`. Kein Build-Step, kein Docker. Alle Game-Entscheidungen (Position, Timer, Phase, Rollen) liegen serverseitig; der Client sendet Input-State und rendert empfangene Snapshots.

**Tech Stack:** Python 3.12, `uv`, FastAPI, Pydantic v2, Starlette WebSockets (via FastAPI), pytest, HTTPX (für TestClient), Vanilla JS + HTML + Canvas API.

**Reference Spec:** `docs/superpowers/specs/2026-04-24-vertical-slice-lobby-movement-design.md`

---

## Task 1: Projekt-Scaffold mit `uv`

**Files:**
- Create: `/home/sven-rausch/se/mcm/pyproject.toml`
- Create: `/home/sven-rausch/se/mcm/app/__init__.py`
- Create: `/home/sven-rausch/se/mcm/app/game/__init__.py`
- Create: `/home/sven-rausch/se/mcm/tests/__init__.py`
- Create: `/home/sven-rausch/se/mcm/tests/conftest.py`
- Create: `/home/sven-rausch/se/mcm/static/.gitkeep`

- [ ] **Step 1: Initialize uv project**

Run from `/home/sven-rausch/se/mcm`:

```bash
uv init --name merge-conflict-mayhem --python 3.12 --no-readme --no-workspace --bare
```

`--bare` erzeugt nur `pyproject.toml` ohne Demo-Code. Falls die Flag in deiner uv-Version fehlt, nutze `uv init` ohne Flags und entferne anschließend `hello.py` und den auto-erzeugten README.

Expected: `pyproject.toml` im Projektroot.

- [ ] **Step 2: Add runtime dependencies**

```bash
uv add fastapi 'uvicorn[standard]' pydantic
```

Expected: `pyproject.toml` hat `dependencies` mit den drei Paketen; `uv.lock` wird erzeugt.

- [ ] **Step 3: Add dev dependencies**

```bash
uv add --dev pytest httpx
```

`httpx` braucht FastAPIs `TestClient`. `pytest-asyncio` wird nicht benötigt, weil WebSocket-Tests über den synchronen Kontext-Manager von `TestClient` laufen.

- [ ] **Step 4: Create package directories**

```bash
mkdir -p app/game tests static
touch app/__init__.py app/game/__init__.py tests/__init__.py static/.gitkeep
```

- [ ] **Step 5: Configure pytest in `pyproject.toml`**

Füge am Ende von `pyproject.toml` ein:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-ra --strict-markers"
```

- [ ] **Step 6: Create `tests/conftest.py` with repo-root on path**

Inhalt:

```python
import sys
from pathlib import Path

# Ensure `app` is importable when pytest is invoked from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

- [ ] **Step 7: Verify pytest can run an empty collection**

```bash
uv run pytest
```

Expected: "no tests ran" (Exit 5 ist OK für pytest bei „keine Tests"); keine Import-Errors.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock app tests static
git commit -m "chore: scaffold uv project with fastapi and pytest"
```

---

## Task 2: Room-Code-Generator (TDD)

**Files:**
- Create: `/home/sven-rausch/se/mcm/app/game/room_code.py`
- Create: `/home/sven-rausch/se/mcm/tests/test_room_code.py`

- [ ] **Step 1: Write failing tests**

Inhalt `tests/test_room_code.py`:

```python
import pytest
from app.game.room_code import ALPHABET, generate, generate_unique


def test_alphabet_excludes_confusing_chars():
    assert "I" not in ALPHABET
    assert "O" not in ALPHABET
    assert "0" not in ALPHABET
    assert "1" not in ALPHABET
    assert len(ALPHABET) == 24


def test_generate_returns_four_chars_from_alphabet():
    for _ in range(50):
        code = generate()
        assert len(code) == 4
        assert all(ch in ALPHABET for ch in code)


def test_generate_unique_avoids_collisions():
    existing = {"ABCD", "EFGH"}
    code = generate_unique(existing)
    assert code not in existing
    assert len(code) == 4


def test_generate_unique_eventually_raises_when_saturated():
    # Saturate with all possible codes → generate_unique must give up.
    all_codes = {
        a + b + c + d
        for a in ALPHABET for b in ALPHABET for c in ALPHABET for d in ALPHABET
    }
    with pytest.raises(RuntimeError):
        generate_unique(all_codes)
```

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/test_room_code.py -v
```

Expected: Import-Error für `app.game.room_code` (Modul existiert nicht).

- [ ] **Step 3: Implement `room_code.py`**

Inhalt:

```python
import random
import string

# A–Z ohne I und O (Verwechslung mit 1/0).
ALPHABET = "".join(ch for ch in string.ascii_uppercase if ch not in {"I", "O"})

_MAX_ATTEMPTS = 32


def generate(rng: random.Random | None = None) -> str:
    """Return a 4-char code from the allowed alphabet."""
    r = rng or random
    return "".join(r.choices(ALPHABET, k=4))


def generate_unique(
    existing: set[str],
    rng: random.Random | None = None,
) -> str:
    """Return a code that is not in `existing`. Raises after 32 collisions."""
    for _ in range(_MAX_ATTEMPTS):
        code = generate(rng)
        if code not in existing:
            return code
    raise RuntimeError(
        f"Could not generate unique room code after {_MAX_ATTEMPTS} attempts."
    )
```

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/test_room_code.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/game/room_code.py tests/test_room_code.py
git commit -m "feat(game): add room code generator with collision avoidance"
```

---

## Task 3: Domain Models

**Files:**
- Create: `/home/sven-rausch/se/mcm/app/game/models.py`

Keine eigene Testdatei — die Modelle werden indirekt durch `test_game_room.py` und `test_ws_protocol.py` exerciert. Pydantic-Parsing selbst ist vom Framework getestet.

- [ ] **Step 1: Create `app/game/models.py`**

Inhalt:

```python
import time
from enum import Enum

from pydantic import BaseModel, Field


class Phase(str, Enum):
    LOBBY = "lobby"
    PLAYING = "playing"


class InputState(BaseModel):
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False


class Player(BaseModel):
    id: str
    name: str
    color: str
    is_host: bool = False
    role: str | None = None
    team: str | None = None
    x: float = 0.0
    y: float = 0.0
    input_state: InputState = Field(default_factory=InputState)
    joined_at: float = Field(default_factory=time.monotonic)

    model_config = {"arbitrary_types_allowed": False}
```

- [ ] **Step 2: Smoke-import**

```bash
uv run python -c "from app.game.models import Phase, Player, InputState; p = Player(id='x', name='y', color='red'); print(p.model_dump())"
```

Expected: druckt das serialisierte Player-Dict ohne Fehler.

- [ ] **Step 3: Commit**

```bash
git add app/game/models.py
git commit -m "feat(game): add Phase, InputState, Player domain models"
```

---

## Task 4: Room Layout Constant

**Files:**
- Create: `/home/sven-rausch/se/mcm/app/game/rooms.py`

- [ ] **Step 1: Create `app/game/rooms.py`**

Inhalt:

```python
"""
Raum-Layout für die Vertical Slice. Map: 900×400 px, zwei Reihen à drei Räumen
(300×200 px). Farben gemäß merge_conflict_mayhem_project/docs/07_visual_direction.md.

Wechsel auf rooms.json kommt in Sprint 4 (siehe Roadmap).
"""

from typing import Final, TypedDict


class RoomDef(TypedDict):
    id: str
    title: str
    x: int
    y: int
    width: int
    height: int
    color: str  # hex


ROOM_LAYOUT: Final[list[RoomDef]] = [
    {"id": "open_space", "title": "Open Space", "x": 0,   "y": 0,   "width": 300, "height": 200, "color": "#3a4560"},
    {"id": "meeting_room", "title": "Meeting Room", "x": 300, "y": 0,   "width": 300, "height": 200, "color": "#5a3a70"},
    {"id": "kitchen", "title": "Kitchen", "x": 600, "y": 0,   "width": 300, "height": 200, "color": "#7a5030"},
    {"id": "server_room", "title": "Server Room", "x": 0,   "y": 200, "width": 300, "height": 200, "color": "#2a4a70"},
    {"id": "war_room", "title": "War Room", "x": 300, "y": 200, "width": 300, "height": 200, "color": "#2a607a"},
    {"id": "legacy_basement", "title": "Legacy Basement", "x": 600, "y": 200, "width": 300, "height": 200, "color": "#3a6a3a"},
]

MAP_WIDTH: Final[int] = 900
MAP_HEIGHT: Final[int] = 400
```

- [ ] **Step 2: Verify layout invariants via a tiny smoke check**

```bash
uv run python -c "from app.game.rooms import ROOM_LAYOUT, MAP_WIDTH, MAP_HEIGHT; assert len(ROOM_LAYOUT) == 6; assert all(r['x'] + r['width'] <= MAP_WIDTH for r in ROOM_LAYOUT); assert all(r['y'] + r['height'] <= MAP_HEIGHT for r in ROOM_LAYOUT); print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add app/game/rooms.py
git commit -m "feat(game): add static six-room layout constant"
```

---

## Task 5: Rollen-Zuweisung (TDD)

**Files:**
- Create: `/home/sven-rausch/se/mcm/app/game/roles.py`
- Create: `/home/sven-rausch/se/mcm/tests/test_roles.py`

- [ ] **Step 1: Write failing tests**

Inhalt `tests/test_roles.py`:

```python
import random

import pytest

from app.game.roles import RoleInfo, assign


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6])
def test_assigns_exactly_one_chaos_agent(n: int):
    player_ids = [f"p{i}" for i in range(n)]
    result = assign(player_ids, rng=random.Random(42))
    chaos = [pid for pid, info in result.items() if info.role == "vibe_coder"]
    devs = [pid for pid, info in result.items() if info.role == "developer"]
    assert len(chaos) == 1
    assert len(devs) == n - 1


def test_roles_have_correct_teams():
    player_ids = ["a", "b", "c"]
    result = assign(player_ids, rng=random.Random(7))
    for info in result.values():
        if info.role == "vibe_coder":
            assert info.team == "chaos_agents"
        elif info.role == "developer":
            assert info.team == "release_team"
        else:
            pytest.fail(f"Unexpected role {info.role!r}")


def test_all_input_ids_present_in_output():
    player_ids = ["alpha", "beta", "gamma", "delta"]
    result = assign(player_ids, rng=random.Random(0))
    assert set(result.keys()) == set(player_ids)


def test_deterministic_with_seeded_rng():
    ids = ["a", "b", "c", "d"]
    first = assign(ids, rng=random.Random(123))
    second = assign(ids, rng=random.Random(123))
    assert {k: v.role for k, v in first.items()} == {k: v.role for k, v in second.items()}


def test_raises_for_too_few_players():
    with pytest.raises(ValueError):
        assign(["only_one"], rng=random.Random(0))


def test_raises_for_too_many_players():
    with pytest.raises(ValueError):
        assign([f"p{i}" for i in range(7)], rng=random.Random(0))


def test_role_info_exposes_description():
    result = assign(["a", "b"], rng=random.Random(0))
    for info in result.values():
        assert isinstance(info.description, str)
        assert info.description  # non-empty
```

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/test_roles.py -v
```

Expected: Import-Error für `app.game.roles`.

- [ ] **Step 3: Implement `roles.py`**

Inhalt:

```python
import random
from dataclasses import dataclass

_MIN_PLAYERS = 2
_MAX_PLAYERS = 6

_DESCRIPTIONS = {
    "developer": "Du bist ein Developer. Bring das Release über die Linie.",
    "vibe_coder": (
        "Du bist der Vibe Coder. Sabotiere das Release, ohne entdeckt zu werden."
    ),
}
_TEAMS = {
    "developer": "release_team",
    "vibe_coder": "chaos_agents",
}


@dataclass(frozen=True)
class RoleInfo:
    role: str
    team: str
    description: str


def assign(
    player_ids: list[str],
    rng: random.Random | None = None,
) -> dict[str, RoleInfo]:
    """Weist Rollen zufällig zu: genau 1 Vibe Coder, Rest Developer.

    Gilt für 2..6 Spieler.
    rng injizierbar für deterministische Tests.
    """
    n = len(player_ids)
    if n < _MIN_PLAYERS or n > _MAX_PLAYERS:
        raise ValueError(
            f"assign() erwartet {_MIN_PLAYERS}..{_MAX_PLAYERS} Spieler, bekam {n}."
        )

    r = rng or random.SystemRandom()
    shuffled = list(player_ids)
    r.shuffle(shuffled)

    chaos_id, *dev_ids = shuffled
    out: dict[str, RoleInfo] = {
        chaos_id: RoleInfo(
            role="vibe_coder",
            team=_TEAMS["vibe_coder"],
            description=_DESCRIPTIONS["vibe_coder"],
        ),
    }
    for dev_id in dev_ids:
        out[dev_id] = RoleInfo(
            role="developer",
            team=_TEAMS["developer"],
            description=_DESCRIPTIONS["developer"],
        )
    return out
```

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/test_roles.py -v
```

Expected: 11 passed (5 parametrized + 6 single).

- [ ] **Step 5: Commit**

```bash
git add app/game/roles.py tests/test_roles.py
git commit -m "feat(game): add role assignment with deterministic rng support"
```

---

## Task 6a: `GameRoom` — Player-Management (TDD)

**Files:**
- Create: `/home/sven-rausch/se/mcm/app/game/game_room.py`
- Create: `/home/sven-rausch/se/mcm/tests/test_game_room.py`

Wir teilen `GameRoom` in zwei Tasks: 6a Player-Management + Lifecycle, 6b Tick/Movement/Phase. So bleiben die Schritte beißbar.

- [ ] **Step 1: Write failing tests for add/remove/host-transfer**

Inhalt `tests/test_game_room.py`:

```python
import random

import pytest

from app.game.game_room import GameRoom, GameRoomError, MAX_PLAYERS
from app.game.models import Phase


def test_first_player_becomes_host():
    room = GameRoom(code="ABCD")
    player = room.add_player("Sven")
    assert player.is_host is True
    assert player.name == "Sven"
    assert len(room.players) == 1
    assert room.phase is Phase.LOBBY


def test_second_player_is_not_host():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    second = room.add_player("Max")
    assert second.is_host is False


def test_add_player_rejects_duplicate_name():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.add_player("Sven")
    assert exc.value.code == "NAME_TAKEN"


def test_add_player_rejects_when_full():
    room = GameRoom(code="ABCD")
    for i in range(MAX_PLAYERS):
        room.add_player(f"player_{i}")
    with pytest.raises(GameRoomError) as exc:
        room.add_player("overflow")
    assert exc.value.code == "ROOM_FULL"


def test_remove_host_promotes_oldest_remaining():
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    second = room.add_player("Max")
    third = room.add_player("Lea")

    room.remove_player(host.id)
    assert host.id not in room.players
    # Max joined second → should become host.
    assert room.players[second.id].is_host is True
    assert room.players[third.id].is_host is False


def test_remove_last_player_marks_empty():
    room = GameRoom(code="ABCD")
    player = room.add_player("Sven")
    room.remove_player(player.id)
    assert room.is_empty() is True


def test_unique_colors_assigned():
    room = GameRoom(code="ABCD")
    colors = set()
    for i in range(MAX_PLAYERS):
        p = room.add_player(f"player_{i}")
        colors.add(p.color)
    assert len(colors) == MAX_PLAYERS
```

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/test_game_room.py -v
```

Expected: Import-Error.

- [ ] **Step 3: Implement minimal `game_room.py` (Player-Management)**

Inhalt (wird in Task 6b erweitert):

```python
import itertools
import uuid
from dataclasses import dataclass

from app.game.models import InputState, Phase, Player

MAX_PLAYERS = 6

# Feste 6er-Palette (Doc 07 Farbsystem).
_COLOR_PALETTE = [
    "#4ade80",  # green
    "#60a5fa",  # blue
    "#fb923c",  # orange
    "#c084fc",  # purple
    "#facc15",  # yellow
    "#f87171",  # red
]


@dataclass
class GameRoomError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class GameRoom:
    def __init__(self, code: str) -> None:
        self.code = code
        self.phase: Phase = Phase.LOBBY
        self.players: dict[str, Player] = {}
        self.remaining_seconds: float = 600.0

    # --- player management -------------------------------------------------

    def add_player(self, name: str) -> Player:
        if len(self.players) >= MAX_PLAYERS:
            raise GameRoomError(code="ROOM_FULL", message="Room is full.")
        if any(p.name == name for p in self.players.values()):
            raise GameRoomError(
                code="NAME_TAKEN",
                message=f"Name {name!r} already taken in this room.",
            )
        player = Player(
            id=uuid.uuid4().hex,
            name=name,
            color=self._next_color(),
            is_host=len(self.players) == 0,
        )
        self.players[player.id] = player
        return player

    def remove_player(self, player_id: str) -> None:
        removed = self.players.pop(player_id, None)
        if removed is None:
            return
        if removed.is_host and self.players:
            # Promote oldest by joined_at.
            oldest = min(self.players.values(), key=lambda p: p.joined_at)
            oldest.is_host = True

    def is_empty(self) -> bool:
        return not self.players

    def _next_color(self) -> str:
        used = {p.color for p in self.players.values()}
        for color in _COLOR_PALETTE:
            if color not in used:
                return color
        # Fallback — kann nur passieren, wenn MAX_PLAYERS > Palette.
        raise GameRoomError(code="NO_COLORS", message="Color palette exhausted.")
```

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/test_game_room.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add app/game/game_room.py tests/test_game_room.py
git commit -m "feat(game): add GameRoom player management with host transfer"
```

---

## Task 6b: `GameRoom` — Start, Input, Tick (TDD)

**Files:**
- Modify: `/home/sven-rausch/se/mcm/app/game/game_room.py`
- Modify: `/home/sven-rausch/se/mcm/tests/test_game_room.py`

- [ ] **Step 1: Append failing tests for start/input/tick**

Am Ende von `tests/test_game_room.py` anhängen:

```python
# --- start() ---------------------------------------------------------------


def _make_started_room(player_count: int = 3) -> GameRoom:
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    for i in range(player_count - 1):
        room.add_player(f"p{i}")
    room.start(requesting_player_id=host.id, rng=random.Random(0))
    return room


def test_start_requires_host():
    room = GameRoom(code="ABCD")
    room.add_player("Sven")
    second = room.add_player("Max")
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=second.id, rng=random.Random(0))
    assert exc.value.code == "NOT_HOST"


def test_start_requires_min_two_players():
    room = GameRoom(code="ABCD")
    host = room.add_player("Sven")
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=host.id, rng=random.Random(0))
    assert exc.value.code == "NOT_ENOUGH_PLAYERS"


def test_start_requires_lobby_phase():
    room = _make_started_room(player_count=2)
    host_id = next(p.id for p in room.players.values() if p.is_host)
    with pytest.raises(GameRoomError) as exc:
        room.start(requesting_player_id=host_id, rng=random.Random(0))
    assert exc.value.code == "WRONG_PHASE"


def test_start_transitions_to_playing_and_assigns_roles():
    room = _make_started_room(player_count=3)
    assert room.phase is Phase.PLAYING
    roles = [p.role for p in room.players.values()]
    assert roles.count("vibe_coder") == 1
    assert roles.count("developer") == 2
    assert all(p.team in {"release_team", "chaos_agents"} for p in room.players.values())


def test_start_sets_timer_to_600():
    room = _make_started_room(player_count=2)
    assert room.remaining_seconds == 600.0


def test_start_places_players_on_map():
    room = _make_started_room(player_count=4)
    for p in room.players.values():
        assert 0 <= p.x <= 900
        assert 0 <= p.y <= 400


# --- apply_input + tick ----------------------------------------------------


def test_apply_input_updates_state():
    room = _make_started_room(player_count=2)
    any_player = next(iter(room.players.values()))
    room.apply_input(any_player.id, InputState(right=True))
    assert room.players[any_player.id].input_state.right is True


def test_tick_moves_player_right():
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x = 100.0
    room.apply_input(p.id, InputState(right=True))
    room.tick(0.1)  # 12 px bei 120 px/s
    assert p.x == pytest.approx(112.0)


def test_tick_clamps_at_map_borders():
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x = 895.0
    room.apply_input(p.id, InputState(right=True))
    room.tick(1.0)  # Versucht 120 px rechts → wird auf 900 geclampt.
    assert p.x == 900.0

    p.y = 5.0
    room.apply_input(p.id, InputState(right=False, up=True))
    room.tick(1.0)
    assert p.y == 0.0


def test_tick_diagonal_is_not_faster_than_axis():
    # Normalisierte Bewegung: Diagonal ≈ gleiche Geschwindigkeit wie axial.
    room = _make_started_room(player_count=2)
    p = next(iter(room.players.values()))
    p.x, p.y = 400.0, 100.0
    room.apply_input(p.id, InputState(right=True, down=True))
    room.tick(0.1)
    dx, dy = p.x - 400.0, p.y - 100.0
    speed = (dx**2 + dy**2) ** 0.5
    assert speed == pytest.approx(12.0, abs=0.01)


def test_tick_decrements_timer():
    room = _make_started_room(player_count=2)
    room.tick(0.5)
    assert room.remaining_seconds == pytest.approx(599.5)


def test_tick_is_noop_in_lobby():
    room = GameRoom(code="ABCD")
    p1 = room.add_player("Sven")
    room.add_player("Max")
    room.apply_input(p1.id, InputState(right=True))
    start_x = p1.x
    room.tick(0.1)
    assert p1.x == start_x


# --- serialization accessors ----------------------------------------------


def test_public_state_excludes_secrets():
    room = _make_started_room(player_count=3)
    state = room.public_state()
    for player in state["players"]:
        assert "role" not in player
        assert "team" not in player
        assert "inputState" not in player
        assert "input_state" not in player


def test_private_role_returns_tuple():
    room = _make_started_room(player_count=2)
    any_id = next(iter(room.players))
    info = room.private_role_for(any_id)
    assert info.role in {"vibe_coder", "developer"}
    assert info.team in {"release_team", "chaos_agents"}
    assert info.description
```

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/test_game_room.py -v
```

Expected: new tests fail with `AttributeError` (methods nicht definiert).

- [ ] **Step 3: Extend `game_room.py`**

Füge oben den Import hinzu:

```python
import random

from app.game.roles import RoleInfo, assign as assign_roles
from app.game.rooms import MAP_HEIGHT, MAP_WIDTH
```

Konstanten direkt unter `MAX_PLAYERS`:

```python
MIN_PLAYERS_TO_START = 2
PLAYER_SPEED = 120.0  # px/s
PLAYER_RADIUS = 12
ROUND_SECONDS = 600.0

_START_POSITIONS = [
    (150.0, 100.0),  # open_space center
    (180.0, 120.0),
    (120.0, 80.0),
    (200.0, 100.0),
    (100.0, 120.0),
    (170.0, 70.0),
]
```

Dann am Ende der `GameRoom`-Klasse ergänzen:

```python
    # --- lifecycle ---------------------------------------------------------

    def start(
        self,
        requesting_player_id: str,
        rng: random.Random | None = None,
    ) -> None:
        player = self.players.get(requesting_player_id)
        if player is None or not player.is_host:
            raise GameRoomError(
                code="NOT_HOST",
                message="Only the host can start the game.",
            )
        if self.phase is not Phase.LOBBY:
            raise GameRoomError(
                code="WRONG_PHASE",
                message=f"Cannot start in phase {self.phase.value}.",
            )
        if len(self.players) < MIN_PLAYERS_TO_START:
            raise GameRoomError(
                code="NOT_ENOUGH_PLAYERS",
                message=f"Need at least {MIN_PLAYERS_TO_START} players to start.",
            )

        role_map = assign_roles(list(self.players.keys()), rng=rng)
        for pid, info in role_map.items():
            self.players[pid].role = info.role
            self.players[pid].team = info.team

        for (pos_x, pos_y), player in zip(_START_POSITIONS, self.players.values()):
            player.x = pos_x
            player.y = pos_y

        self.remaining_seconds = ROUND_SECONDS
        self.phase = Phase.PLAYING

    # --- input + tick ------------------------------------------------------

    def apply_input(self, player_id: str, input_state: InputState) -> None:
        player = self.players.get(player_id)
        if player is None:
            return
        player.input_state = input_state

    def tick(self, dt: float) -> None:
        if self.phase is not Phase.PLAYING:
            return
        for player in self.players.values():
            dx = (int(player.input_state.right) - int(player.input_state.left))
            dy = (int(player.input_state.down) - int(player.input_state.up))
            if dx or dy:
                length = (dx * dx + dy * dy) ** 0.5
                player.x += (dx / length) * PLAYER_SPEED * dt
                player.y += (dy / length) * PLAYER_SPEED * dt
                # Clamp in map bounds.
                if player.x < 0:
                    player.x = 0.0
                elif player.x > MAP_WIDTH:
                    player.x = float(MAP_WIDTH)
                if player.y < 0:
                    player.y = 0.0
                elif player.y > MAP_HEIGHT:
                    player.y = float(MAP_HEIGHT)
        self.remaining_seconds = max(0.0, self.remaining_seconds - dt)

    # --- serialization accessors ------------------------------------------

    def public_state(self) -> dict:
        """Öffentlicher GameState — enthält keine Rolle/Team/Input."""
        return {
            "phase": self.phase.value,
            "remainingSeconds": int(self.remaining_seconds),
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "x": round(p.x, 2),
                    "y": round(p.y, 2),
                    "color": p.color,
                    "isHost": p.is_host,
                }
                for p in self.players.values()
            ],
        }

    def lobby_snapshot(self) -> dict:
        return {
            "roomCode": self.code,
            "players": [
                {"id": p.id, "name": p.name, "color": p.color, "isHost": p.is_host}
                for p in self.players.values()
            ],
        }

    def private_role_for(self, player_id: str) -> RoleInfo:
        p = self.players[player_id]
        if p.role is None or p.team is None:
            raise GameRoomError(
                code="NO_ROLE",
                message="Player has no role assigned yet.",
            )
        return RoleInfo(
            role=p.role,
            team=p.team,
            description=description_for(p.role),
        )
```

Ergänze außerdem oben im selben File den Import:

```python
from app.game.roles import RoleInfo, assign as assign_roles, description_for
```

(Der `description_for`-Helper wird im folgenden Step-Teil in `roles.py` ergänzt; Task 5 lieferte nur `assign` und `RoleInfo`.)

- [ ] **Step 3b: Extend `app/game/roles.py` with public description helper**

Am Ende von `app/game/roles.py` anfügen:

```python
def description_for(role: str) -> str:
    """Public helper so game_room doesn't reach into a private dict."""
    return _DESCRIPTIONS.get(role, "")
```

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/test_game_room.py -v
```

Expected: alle Tests passen (7 aus 6a + 14 aus 6b = 21).

- [ ] **Step 5: Commit**

```bash
git add app/game/game_room.py tests/test_game_room.py
git commit -m "feat(game): add start, apply_input, tick, and state accessors to GameRoom"
```

---

## Task 7: Protokoll-Modelle (TDD)

**Files:**
- Create: `/home/sven-rausch/se/mcm/app/protocol.py`
- Create: `/home/sven-rausch/se/mcm/tests/test_protocol.py`

- [ ] **Step 1: Write failing tests**

Inhalt `tests/test_protocol.py`:

```python
import pytest
from pydantic import ValidationError

from app.protocol import (
    ErrorMsg,
    GameStateMsg,
    IncomingMessage,
    JoinRoom,
    LobbyStateMsg,
    PlayerInput,
    PrivateRoleMsg,
    RoomJoinedMsg,
    StartGame,
    parse_incoming,
)


# --- incoming parsing -------------------------------------------------------


def test_parse_join_room():
    raw = {"type": "join_room", "payload": {"roomCode": "ABCD", "playerName": "Sven"}}
    msg = parse_incoming(raw)
    assert isinstance(msg, JoinRoom)
    assert msg.payload.room_code == "ABCD"
    assert msg.payload.player_name == "Sven"


def test_parse_start_game():
    raw = {"type": "start_game", "payload": {}}
    msg = parse_incoming(raw)
    assert isinstance(msg, StartGame)


def test_parse_player_input():
    raw = {
        "type": "player_input",
        "payload": {"up": True, "down": False, "left": False, "right": True},
    }
    msg = parse_incoming(raw)
    assert isinstance(msg, PlayerInput)
    assert msg.payload.up is True
    assert msg.payload.right is True


def test_parse_rejects_unknown_type():
    with pytest.raises(ValidationError):
        parse_incoming({"type": "unknown_event", "payload": {}})


def test_parse_rejects_missing_type():
    with pytest.raises(ValidationError):
        parse_incoming({"payload": {}})


# --- outgoing serialization ------------------------------------------------


def test_room_joined_serializes_to_camel_case():
    msg = RoomJoinedMsg(room_code="ABCD", player_id="abc123", is_host=True)
    dumped = msg.model_dump(by_alias=True)
    assert dumped == {"roomCode": "ABCD", "playerId": "abc123", "isHost": True}


def test_lobby_state_serializes_to_camel_case():
    msg = LobbyStateMsg(
        room_code="ABCD",
        players=[
            {"id": "p1", "name": "Sven", "color": "#4ade80", "isHost": True},
        ],
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["roomCode"] == "ABCD"
    assert dumped["players"][0]["isHost"] is True


def test_game_state_serializes_to_camel_case():
    msg = GameStateMsg(
        phase="playing",
        remaining_seconds=598,
        players=[
            {"id": "p1", "name": "Sven", "x": 120.5, "y": 99.0, "color": "#4ade80", "isHost": True},
        ],
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped["remainingSeconds"] == 598
    assert "phase" in dumped


def test_private_role_serializes_as_expected():
    msg = PrivateRoleMsg(
        role="vibe_coder",
        team="chaos_agents",
        description="Sabotier das Release.",
    )
    dumped = msg.model_dump(by_alias=True)
    assert dumped == {
        "role": "vibe_coder",
        "team": "chaos_agents",
        "description": "Sabotier das Release.",
    }


def test_error_msg_serializes_correctly():
    msg = ErrorMsg(code="NOT_HOST", message="Only host can start.")
    dumped = msg.model_dump(by_alias=True)
    assert dumped == {"code": "NOT_HOST", "message": "Only host can start."}
```

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/test_protocol.py -v
```

Expected: Import-Error für `app.protocol`.

- [ ] **Step 3: Implement `app/protocol.py`**

Inhalt:

```python
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Field
from pydantic.alias_generators import to_camel


def _camel_config() -> ConfigDict:
    return ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


# --- incoming payloads ------------------------------------------------------


class JoinRoomPayload(BaseModel):
    model_config = _camel_config()
    room_code: str
    player_name: str


class StartGamePayload(BaseModel):
    model_config = _camel_config()


class PlayerInputPayload(BaseModel):
    model_config = _camel_config()
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False


class JoinRoom(BaseModel):
    model_config = _camel_config()
    type: Literal["join_room"]
    payload: JoinRoomPayload


class StartGame(BaseModel):
    model_config = _camel_config()
    type: Literal["start_game"]
    payload: StartGamePayload = Field(default_factory=StartGamePayload)


class PlayerInput(BaseModel):
    model_config = _camel_config()
    type: Literal["player_input"]
    payload: PlayerInputPayload


IncomingMessage = Annotated[
    Union[JoinRoom, StartGame, PlayerInput],
    Discriminator("type"),
]


class _IncomingEnvelope(BaseModel):
    """Wrapper to trigger Pydantic's discriminated-union validation."""
    model_config = _camel_config()
    root: IncomingMessage


def parse_incoming(raw: dict[str, Any]) -> IncomingMessage:
    return _IncomingEnvelope(root=raw).root


# --- outgoing messages ------------------------------------------------------


class RoomJoinedMsg(BaseModel):
    model_config = _camel_config()
    room_code: str
    player_id: str
    is_host: bool


class LobbyStateMsg(BaseModel):
    model_config = _camel_config()
    room_code: str
    players: list[dict[str, Any]]


class GameStateMsg(BaseModel):
    model_config = _camel_config()
    phase: str
    remaining_seconds: int
    players: list[dict[str, Any]]


class PrivateRoleMsg(BaseModel):
    model_config = _camel_config()
    role: str
    team: str
    description: str


class ErrorMsg(BaseModel):
    model_config = _camel_config()
    code: str
    message: str


def envelope(type_: str, payload: BaseModel) -> dict[str, Any]:
    """Wrap a payload model into the {type, payload} wire format."""
    return {"type": type_, "payload": payload.model_dump(by_alias=True)}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/test_protocol.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add app/protocol.py tests/test_protocol.py
git commit -m "feat(protocol): add pydantic message models with camelCase aliases"
```

---

## Task 8: `ConnectionManager`

**Files:**
- Create: `/home/sven-rausch/se/mcm/app/ws.py`

`ws.py` wird direkt beim Integrations-Test in Task 10 exerciert. Kein eigener Unit-Test — die Methoden sind trivial state-tracking und durch den End-to-End-Test abgedeckt.

- [ ] **Step 1: Create `app/ws.py`**

Inhalt:

```python
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class _Session:
    ws: WebSocket
    player_id: str
    room_code: str


@dataclass
class ConnectionManager:
    _by_ws: dict[int, _Session] = field(default_factory=dict)

    async def accept(self, ws: WebSocket) -> None:
        await ws.accept()

    def register(self, ws: WebSocket, player_id: str, room_code: str) -> None:
        self._by_ws[id(ws)] = _Session(ws=ws, player_id=player_id, room_code=room_code)

    def forget(self, ws: WebSocket) -> _Session | None:
        return self._by_ws.pop(id(ws), None)

    def session_for(self, ws: WebSocket) -> _Session | None:
        return self._by_ws.get(id(ws))

    def sessions_in_room(self, room_code: str) -> list[_Session]:
        return [s for s in self._by_ws.values() if s.room_code == room_code]

    async def send_to(self, ws: WebSocket, message: dict) -> None:
        await ws.send_json(message)

    async def send_to_player(self, room_code: str, player_id: str, message: dict) -> None:
        for session in self.sessions_in_room(room_code):
            if session.player_id == player_id:
                await session.ws.send_json(message)
                return

    async def broadcast(self, room_code: str, message: dict) -> None:
        for session in self.sessions_in_room(room_code):
            await session.ws.send_json(message)
```

- [ ] **Step 2: Smoke-import**

```bash
uv run python -c "from app.ws import ConnectionManager; print(ConnectionManager())"
```

Expected: druckt die leere Instanz ohne Import-Fehler.

- [ ] **Step 3: Commit**

```bash
git add app/ws.py
git commit -m "feat(ws): add ConnectionManager for per-room websocket sessions"
```

---

## Task 9: FastAPI-App, WS-Route, Tick-Loop

**Files:**
- Create: `/home/sven-rausch/se/mcm/app/main.py`

- [ ] **Step 1: Create `app/main.py`**

Inhalt:

```python
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.game.game_room import GameRoom, GameRoomError
from app.game.models import InputState, Phase
from app.game.room_code import generate_unique
from app.protocol import (
    ErrorMsg,
    GameStateMsg,
    JoinRoom,
    LobbyStateMsg,
    PlayerInput,
    PrivateRoleMsg,
    RoomJoinedMsg,
    StartGame,
    envelope,
    parse_incoming,
)
from app.ws import ConnectionManager

TICK_HZ = 20
TICK_DT = 1.0 / TICK_HZ

log = logging.getLogger("mcm")


class GameRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, GameRoom] = {}

    def get_or_create(self, room_code: str) -> GameRoom:
        code = room_code.upper()
        room = self._rooms.get(code)
        if room is None:
            room = GameRoom(code=code)
            self._rooms[code] = room
        return room

    def get(self, room_code: str) -> GameRoom | None:
        return self._rooms.get(room_code.upper())

    def drop_if_empty(self, room_code: str) -> None:
        room = self._rooms.get(room_code.upper())
        if room is not None and room.is_empty():
            del self._rooms[room_code.upper()]

    def active_rooms(self) -> list[GameRoom]:
        return list(self._rooms.values())

    def known_codes(self) -> set[str]:
        return set(self._rooms.keys())


registry = GameRegistry()
manager = ConnectionManager()


async def _tick_loop() -> None:
    try:
        while True:
            await asyncio.sleep(TICK_DT)
            for room in list(registry.active_rooms()):
                if room.phase is not Phase.PLAYING:
                    continue
                room.tick(TICK_DT)
                msg = envelope(
                    "game_state",
                    GameStateMsg(
                        phase=room.phase.value,
                        remaining_seconds=int(room.remaining_seconds),
                        players=room.public_state()["players"],
                    ),
                )
                await manager.broadcast(room.code, msg)
    except asyncio.CancelledError:
        log.info("tick loop cancelled")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_tick_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await manager.accept(ws)
    try:
        while True:
            raw = await ws.receive_json()
            try:
                msg = parse_incoming(raw)
            except ValidationError as e:
                await ws.send_json(
                    envelope("error", ErrorMsg(code="BAD_MESSAGE", message=str(e)))
                )
                continue

            if isinstance(msg, JoinRoom):
                await _handle_join(ws, msg)
            elif isinstance(msg, StartGame):
                await _handle_start(ws)
            elif isinstance(msg, PlayerInput):
                await _handle_input(ws, msg)
    except WebSocketDisconnect:
        pass
    finally:
        await _handle_disconnect(ws)


async def _handle_join(ws: WebSocket, msg: JoinRoom) -> None:
    code = msg.payload.room_code.upper()
    room = registry.get_or_create(code)
    try:
        player = room.add_player(msg.payload.player_name)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
        # If the room was created empty for this join, clean it up.
        registry.drop_if_empty(code)
        return

    manager.register(ws, player.id, code)
    await ws.send_json(
        envelope(
            "room_joined",
            RoomJoinedMsg(room_code=code, player_id=player.id, is_host=player.is_host),
        )
    )
    await manager.broadcast(code, envelope("lobby_state", LobbyStateMsg(**room.lobby_snapshot())))


async def _handle_start(ws: WebSocket) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    try:
        room.start(requesting_player_id=session.player_id)
    except GameRoomError as exc:
        await ws.send_json(envelope("error", ErrorMsg(code=exc.code, message=exc.message)))
        return
    # Send private role to each player.
    for player_id in list(room.players.keys()):
        info = room.private_role_for(player_id)
        await manager.send_to_player(
            room.code,
            player_id,
            envelope(
                "private_role",
                PrivateRoleMsg(role=info.role, team=info.team, description=info.description),
            ),
        )
    # Immediate public state so clients switch to the game view.
    await manager.broadcast(
        room.code,
        envelope(
            "game_state",
            GameStateMsg(
                phase=room.phase.value,
                remaining_seconds=int(room.remaining_seconds),
                players=room.public_state()["players"],
            ),
        ),
    )


async def _handle_input(ws: WebSocket, msg: PlayerInput) -> None:
    session = manager.session_for(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    room.apply_input(
        session.player_id,
        InputState(
            up=msg.payload.up,
            down=msg.payload.down,
            left=msg.payload.left,
            right=msg.payload.right,
        ),
    )


async def _handle_disconnect(ws: WebSocket) -> None:
    session = manager.forget(ws)
    if session is None:
        return
    room = registry.get(session.room_code)
    if room is None:
        return
    room.remove_player(session.player_id)
    if room.is_empty():
        registry.drop_if_empty(session.room_code)
        return
    # Rebroadcast lobby or game state so remaining clients see the departure.
    if room.phase is Phase.LOBBY:
        await manager.broadcast(
            room.code, envelope("lobby_state", LobbyStateMsg(**room.lobby_snapshot()))
        )
    else:
        await manager.broadcast(
            room.code,
            envelope(
                "game_state",
                GameStateMsg(
                    phase=room.phase.value,
                    remaining_seconds=int(room.remaining_seconds),
                    players=room.public_state()["players"],
                ),
            ),
        )


# Static frontend — MOUNT MUST BE LAST so /ws route wins.
_static_dir = Path(__file__).parent.parent / "static"
app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
```

**Critical:** `app.mount("/", ...)` muss **nach** `@app.websocket("/ws")` stehen, sonst swallowt StaticFiles die Route.

- [ ] **Step 2: Smoke-start the server**

```bash
uv run uvicorn app.main:app --port 8765 &
SERVER_PID=$!
sleep 2
curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8765/
kill $SERVER_PID
wait 2>/dev/null
```

Expected: `404` (noch keine `index.html` in `static/`) — aber **kein** Crash.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: wire FastAPI app with websocket route and 20Hz tick loop"
```

---

## Task 10: Integrations-Test via `TestClient`

**Files:**
- Create: `/home/sven-rausch/se/mcm/tests/test_ws_protocol.py`

- [ ] **Step 1: Write failing integration tests**

Inhalt:

```python
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app, registry


@pytest.fixture(autouse=True)
def _reset_registry():
    yield
    registry._rooms.clear()


def _join(client_ws, room_code: str, name: str) -> dict:
    client_ws.send_json(
        {"type": "join_room", "payload": {"roomCode": room_code, "playerName": name}}
    )
    return client_ws.receive_json()  # room_joined


def _drain_until(ws, type_: str, max_msgs: int = 10) -> dict:
    """Receive messages until one with `type` arrives, or fail."""
    for _ in range(max_msgs):
        msg = ws.receive_json()
        if msg["type"] == type_:
            return msg
    raise AssertionError(f"Did not receive {type_!r} within {max_msgs} messages.")


def test_two_clients_can_join_same_room():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        joined_a = _join(ws_a, "ABCD", "Alice")
        assert joined_a["type"] == "room_joined"
        assert joined_a["payload"]["isHost"] is True

        # Alice receives lobby_state after joining.
        lobby_a1 = ws_a.receive_json()
        assert lobby_a1["type"] == "lobby_state"
        assert len(lobby_a1["payload"]["players"]) == 1

        joined_b = _join(ws_b, "ABCD", "Bob")
        assert joined_b["type"] == "room_joined"
        assert joined_b["payload"]["isHost"] is False

        # Both receive an updated lobby_state.
        lobby_a2 = ws_a.receive_json()
        lobby_b1 = ws_b.receive_json()
        assert lobby_a2["type"] == "lobby_state"
        assert lobby_b1["type"] == "lobby_state"
        assert len(lobby_a2["payload"]["players"]) == 2


def test_non_host_cannot_start_game():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "EFGH", "Alice")
        ws_a.receive_json()  # lobby
        _join(ws_b, "EFGH", "Bob")
        ws_a.receive_json()  # lobby update (2 players)
        ws_b.receive_json()  # lobby update

        ws_b.send_json({"type": "start_game", "payload": {}})
        err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_HOST"


def test_host_start_gives_private_role_and_game_state():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "JKLM", "Alice")
        ws_a.receive_json()
        _join(ws_b, "JKLM", "Bob")
        ws_a.receive_json()
        ws_b.receive_json()

        ws_a.send_json({"type": "start_game", "payload": {}})

        # Each client should receive a private_role and then a game_state.
        role_a = _drain_until(ws_a, "private_role")
        state_a = _drain_until(ws_a, "game_state")
        role_b = _drain_until(ws_b, "private_role")
        state_b = _drain_until(ws_b, "game_state")

        assert role_a["payload"]["role"] in {"vibe_coder", "developer"}
        assert role_b["payload"]["role"] in {"vibe_coder", "developer"}
        # Exactly one is chaos, one is dev.
        roles = {role_a["payload"]["role"], role_b["payload"]["role"]}
        assert roles == {"vibe_coder", "developer"}

        assert state_a["payload"]["phase"] == "playing"
        # Public state must not leak roles.
        for p in state_a["payload"]["players"]:
            assert "role" not in p
            assert "team" not in p


def test_start_fails_with_only_one_player():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a:
        _join(ws_a, "NOPQ", "Alice")
        ws_a.receive_json()  # lobby

        ws_a.send_json({"type": "start_game", "payload": {}})
        err = ws_a.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NOT_ENOUGH_PLAYERS"


def test_duplicate_name_rejected():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a, client.websocket_connect("/ws") as ws_b:
        _join(ws_a, "RSTU", "Sven")
        ws_a.receive_json()

        ws_b.send_json(
            {"type": "join_room", "payload": {"roomCode": "RSTU", "playerName": "Sven"}}
        )
        err = ws_b.receive_json()
        assert err["type"] == "error"
        assert err["payload"]["code"] == "NAME_TAKEN"


def test_disconnect_removes_player_and_promotes_host():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws_a:
        _join(ws_a, "VWXY", "Alice")
        ws_a.receive_json()

        # Second client joins inside nested with, then leaves.
        with client.websocket_connect("/ws") as ws_b:
            _join(ws_b, "VWXY", "Bob")
            ws_a.receive_json()  # lobby update after Bob joined
            ws_b.receive_json()
        # After ws_b closes, Alice should see a lobby update without Bob.
        lobby = ws_a.receive_json()
        assert lobby["type"] == "lobby_state"
        names = [p["name"] for p in lobby["payload"]["players"]]
        assert names == ["Alice"]
```

- [ ] **Step 2: Run integration tests — expect pass**

```bash
uv run pytest tests/test_ws_protocol.py -v
```

Expected: 6 passed.

**If any test hangs**: wahrscheinlich fehlendes `lobby_state`-Broadcast oder StaticFiles swallowt `/ws`. Prüfe `app/main.py`: `app.mount("/", ...)` muss nach `@app.websocket("/ws")` stehen.

- [ ] **Step 3: Run full suite**

```bash
uv run pytest -v
```

Expected: alle Tests passen (Room-Code + Roles + GameRoom + Protocol + Integration).

- [ ] **Step 4: Commit**

```bash
git add tests/test_ws_protocol.py
git commit -m "test: add websocket integration tests covering join/start/disconnect"
```

---

## Task 11: Static HTML + Styles

**Files:**
- Create: `/home/sven-rausch/se/mcm/static/index.html`
- Create: `/home/sven-rausch/se/mcm/static/styles.css`

- [ ] **Step 1: Create `static/index.html`**

Inhalt:

```html
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8" />
  <title>Merge Conflict Mayhem</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="stylesheet" href="/styles.css" />
</head>
<body>
  <main id="app">
    <section id="lobby-screen">
      <h1>Merge Conflict Mayhem</h1>
      <p class="subtitle">Lunch Break Edition</p>

      <div id="join-form">
        <label>
          Name
          <input id="input-name" type="text" maxlength="16" autocomplete="off" />
        </label>
        <label>
          Raumcode
          <input id="input-room-code" type="text" maxlength="4" autocomplete="off" />
        </label>
        <button id="btn-join" type="button">Join</button>
      </div>

      <div id="lobby-waiting" class="hidden">
        <h2>Raum <span id="lobby-room-code"></span></h2>
        <ul id="lobby-player-list"></ul>
        <button id="btn-start" type="button" class="hidden">Runde starten</button>
        <p id="lobby-hint">Warte auf den Host…</p>
      </div>

      <p id="error-banner" class="hidden"></p>
    </section>

    <section id="game-screen" class="hidden">
      <div id="hud">
        <div id="hud-timer" class="hud-pill">--:--</div>
        <div id="hud-role" class="hud-pill">Rolle: —</div>
        <div id="hud-players" class="hud-pill"></div>
      </div>
      <canvas id="game-canvas" width="900" height="400"></canvas>
    </section>
  </main>

  <script type="module" src="/main.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `static/styles.css`**

Inhalt:

```css
:root {
  --bg: #14182a;
  --panel: #1f253d;
  --text: #e6ecff;
  --muted: #8892b0;
  --accent: #4ade80;
  --danger: #f87171;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, sans-serif;
  min-height: 100vh;
}

#app {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px;
}

.hidden { display: none !important; }

h1 {
  margin: 0;
  font-size: 2rem;
  letter-spacing: 0.02em;
}

.subtitle {
  color: var(--muted);
  margin: 4px 0 24px;
}

#lobby-screen {
  background: var(--panel);
  padding: 24px;
  border-radius: 12px;
}

#join-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 320px;
}

#join-form label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.9rem;
}

#join-form input {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #2e3656;
  background: #10152a;
  color: var(--text);
  font-size: 1rem;
}

button {
  padding: 10px 16px;
  border-radius: 6px;
  border: none;
  background: var(--accent);
  color: #0f172a;
  font-weight: 600;
  cursor: pointer;
}

button:hover { filter: brightness(1.1); }

#lobby-waiting ul {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

#lobby-waiting li {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

#error-banner {
  margin-top: 16px;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--danger);
  color: #1a0505;
}

#game-screen {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

#hud {
  display: flex;
  gap: 12px;
  padding: 8px 12px;
  background: var(--panel);
  border-radius: 10px;
}

.hud-pill {
  padding: 6px 10px;
  background: #10152a;
  border-radius: 6px;
  font-variant-numeric: tabular-nums;
}

#game-canvas {
  background: #0b0f1f;
  border-radius: 10px;
  width: 100%;
  height: auto;
  max-width: 900px;
  image-rendering: pixelated;
}
```

- [ ] **Step 3: Commit**

```bash
git add static/index.html static/styles.css
git commit -m "feat(frontend): add lobby/game HTML skeleton with dark theme"
```

---

## Task 12: WebSocket-Client

**Files:**
- Create: `/home/sven-rausch/se/mcm/static/ws.js`

- [ ] **Step 1: Create `static/ws.js`**

Inhalt:

```javascript
// Minimal WebSocket wrapper. No reconnection state restore — a closed socket
// requires re-joining from the lobby. The server is the source of truth.

const RECONNECT_DELAY_MS = 3000;

export class WsClient {
  constructor(url) {
    this.url = url;
    this.handlers = new Map(); // type -> fn(payload)
    this.socket = null;
    this.shouldReconnect = true;
    this._onOpen = null;
  }

  on(type, fn) {
    this.handlers.set(type, fn);
  }

  onOpen(fn) {
    this._onOpen = fn;
  }

  connect() {
    this.socket = new WebSocket(this.url);
    this.socket.addEventListener("open", () => {
      if (this._onOpen) this._onOpen();
    });
    this.socket.addEventListener("message", (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      const handler = this.handlers.get(msg.type);
      if (handler) handler(msg.payload);
    });
    this.socket.addEventListener("close", () => {
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
      }
    });
  }

  send(type, payload) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.socket.send(JSON.stringify({ type, payload: payload ?? {} }));
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/ws.js
git commit -m "feat(frontend): add websocket client wrapper"
```

---

## Task 13: Input-Handling

**Files:**
- Create: `/home/sven-rausch/se/mcm/static/input.js`

- [ ] **Step 1: Create `static/input.js`**

Inhalt:

```javascript
// WASD + Arrow Keys → {up,down,left,right}. Edge-triggered: only send when
// the state actually changes. Reset on window blur to avoid stuck keys.

const KEY_MAP = {
  KeyW: "up", ArrowUp: "up",
  KeyS: "down", ArrowDown: "down",
  KeyA: "left", ArrowLeft: "left",
  KeyD: "right", ArrowRight: "right",
};

export function attachInput(wsClient) {
  const state = { up: false, down: false, left: false, right: false };

  const send = () => wsClient.send("player_input", { ...state });

  const setAxis = (axis, value) => {
    if (state[axis] === value) return false;
    state[axis] = value;
    return true;
  };

  window.addEventListener("keydown", (e) => {
    const axis = KEY_MAP[e.code];
    if (!axis) return;
    if (e.repeat) return;
    if (setAxis(axis, true)) send();
  });

  window.addEventListener("keyup", (e) => {
    const axis = KEY_MAP[e.code];
    if (!axis) return;
    if (setAxis(axis, false)) send();
  });

  window.addEventListener("blur", () => {
    let changed = false;
    for (const axis of ["up", "down", "left", "right"]) {
      if (state[axis]) {
        state[axis] = false;
        changed = true;
      }
    }
    if (changed) send();
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add static/input.js
git commit -m "feat(frontend): add edge-triggered WASD input handler"
```

---

## Task 14: Canvas-Renderer

**Files:**
- Create: `/home/sven-rausch/se/mcm/static/render.js`

- [ ] **Step 1: Create `static/render.js`**

Inhalt:

```javascript
// Pure rendering. Holds no game state — just takes snapshots.
// ROOM_LAYOUT mirrors app/game/rooms.py (must match until moved to config).

const ROOM_LAYOUT = [
  { id: "open_space", title: "Open Space", x: 0, y: 0, width: 300, height: 200, color: "#3a4560" },
  { id: "meeting_room", title: "Meeting Room", x: 300, y: 0, width: 300, height: 200, color: "#5a3a70" },
  { id: "kitchen", title: "Kitchen", x: 600, y: 0, width: 300, height: 200, color: "#7a5030" },
  { id: "server_room", title: "Server Room", x: 0, y: 200, width: 300, height: 200, color: "#2a4a70" },
  { id: "war_room", title: "War Room", x: 300, y: 200, width: 300, height: 200, color: "#2a607a" },
  { id: "legacy_basement", title: "Legacy Basement", x: 600, y: 200, width: 300, height: 200, color: "#3a6a3a" },
];

const PLAYER_RADIUS = 12;

export class Renderer {
  constructor(canvas) {
    this.ctx = canvas.getContext("2d");
    this.canvas = canvas;
    this.players = [];
    this.ownPlayerId = null;
    this._running = false;
  }

  setOwnPlayerId(id) { this.ownPlayerId = id; }
  setPlayers(players) { this.players = players; }

  start() {
    this._running = true;
    const loop = () => {
      if (!this._running) return;
      this._draw();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  stop() { this._running = false; }

  _draw() {
    const { ctx, canvas } = this;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Rooms.
    for (const room of ROOM_LAYOUT) {
      ctx.fillStyle = room.color;
      ctx.fillRect(room.x, room.y, room.width, room.height);
      ctx.strokeStyle = "#0b0f1f";
      ctx.lineWidth = 2;
      ctx.strokeRect(room.x, room.y, room.width, room.height);

      ctx.fillStyle = "rgba(230,236,255,0.85)";
      ctx.font = "12px system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText(room.title.toUpperCase(), room.x + 8, room.y + 8);
    }

    // Players.
    for (const player of this.players) {
      ctx.beginPath();
      ctx.arc(player.x, player.y, PLAYER_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = player.color;
      ctx.fill();

      if (player.id === this.ownPlayerId) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 3;
        ctx.stroke();
      } else {
        ctx.strokeStyle = "rgba(0,0,0,0.4)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      ctx.fillStyle = "#e6ecff";
      ctx.font = "12px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillText(player.name, player.x, player.y - PLAYER_RADIUS - 4);
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/render.js
git commit -m "feat(frontend): add canvas renderer for rooms and players"
```

---

## Task 15: HUD-Logik

**Files:**
- Create: `/home/sven-rausch/se/mcm/static/hud.js`

- [ ] **Step 1: Create `static/hud.js`**

Inhalt:

```javascript
export class Hud {
  constructor() {
    this.timerEl = document.getElementById("hud-timer");
    this.roleEl = document.getElementById("hud-role");
    this.playersEl = document.getElementById("hud-players");
  }

  setTimer(seconds) {
    const m = Math.max(0, Math.floor(seconds / 60));
    const s = Math.max(0, Math.floor(seconds % 60));
    this.timerEl.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  setRole(role, team) {
    const label = role === "vibe_coder" ? "Vibe Coder (Chaos)" : role;
    this.roleEl.textContent = `Rolle: ${label}`;
    if (team === "chaos_agents") {
      this.roleEl.style.background = "#4a1e1e";
    }
  }

  setPlayers(players) {
    this.playersEl.textContent = `Spieler: ${players.length}`;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/hud.js
git commit -m "feat(frontend): add HUD bindings for timer, role, player count"
```

---

## Task 16: Frontend-Entry `main.js`

**Files:**
- Create: `/home/sven-rausch/se/mcm/static/main.js`

- [ ] **Step 1: Create `static/main.js`**

Inhalt:

```javascript
import { WsClient } from "./ws.js";
import { attachInput } from "./input.js";
import { Renderer } from "./render.js";
import { Hud } from "./hud.js";

const state = {
  playerId: null,
  isHost: false,
  roomCode: null,
  phase: "lobby",
  players: [],
  ownRole: null,
};

const els = {
  joinForm: document.getElementById("join-form"),
  lobbyWaiting: document.getElementById("lobby-waiting"),
  lobbyRoomCode: document.getElementById("lobby-room-code"),
  lobbyPlayerList: document.getElementById("lobby-player-list"),
  btnJoin: document.getElementById("btn-join"),
  btnStart: document.getElementById("btn-start"),
  inputName: document.getElementById("input-name"),
  inputRoomCode: document.getElementById("input-room-code"),
  lobbyScreen: document.getElementById("lobby-screen"),
  gameScreen: document.getElementById("game-screen"),
  errorBanner: document.getElementById("error-banner"),
  canvas: document.getElementById("game-canvas"),
};

const wsUrl = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
const ws = new WsClient(wsUrl);
const hud = new Hud();
const renderer = new Renderer(els.canvas);
renderer.start();

function showError(msg) {
  els.errorBanner.textContent = msg;
  els.errorBanner.classList.remove("hidden");
  setTimeout(() => els.errorBanner.classList.add("hidden"), 4000);
}

function renderLobby() {
  els.lobbyPlayerList.innerHTML = "";
  for (const p of state.players) {
    const li = document.createElement("li");
    const dot = document.createElement("span");
    dot.className = "color-dot";
    dot.style.background = p.color;
    li.appendChild(dot);
    const text = document.createElement("span");
    text.textContent = p.name + (p.isHost ? "  (Host)" : "");
    li.appendChild(text);
    els.lobbyPlayerList.appendChild(li);
  }
  els.btnStart.classList.toggle("hidden", !state.isHost);
}

ws.on("room_joined", (payload) => {
  state.playerId = payload.playerId;
  state.isHost = payload.isHost;
  state.roomCode = payload.roomCode;
  renderer.setOwnPlayerId(payload.playerId);
  els.joinForm.classList.add("hidden");
  els.lobbyWaiting.classList.remove("hidden");
  els.lobbyRoomCode.textContent = payload.roomCode;
});

ws.on("lobby_state", (payload) => {
  state.players = payload.players;
  renderLobby();
});

ws.on("private_role", (payload) => {
  state.ownRole = payload;
  hud.setRole(payload.role, payload.team);
});

ws.on("game_state", (payload) => {
  if (state.phase !== "playing" && payload.phase === "playing") {
    els.lobbyScreen.classList.add("hidden");
    els.gameScreen.classList.remove("hidden");
  }
  state.phase = payload.phase;
  state.players = payload.players;
  renderer.setPlayers(payload.players);
  hud.setTimer(payload.remainingSeconds);
  hud.setPlayers(payload.players);
});

ws.on("error", (payload) => {
  showError(`${payload.code}: ${payload.message}`);
});

els.btnJoin.addEventListener("click", () => {
  const name = els.inputName.value.trim();
  const roomCode = els.inputRoomCode.value.trim().toUpperCase();
  if (!name || !roomCode) {
    showError("Name und Raumcode sind Pflicht.");
    return;
  }
  ws.send("join_room", { roomCode, playerName: name });
});

els.btnStart.addEventListener("click", () => {
  ws.send("start_game", {});
});

attachInput(ws);
ws.connect();
```

- [ ] **Step 2: Commit**

```bash
git add static/main.js
git commit -m "feat(frontend): wire lobby/game router with ws, renderer, hud"
```

---

## Task 17: README

**Files:**
- Modify: `/home/sven-rausch/se/mcm/README.md` (ersetzt GitLab-Default-README)

- [ ] **Step 1: Replace `README.md`**

Inhalt:

```markdown
# Merge Conflict Mayhem — Lunch Break Edition

Internes Multiplayer-Spiel: Release-Team vs. geheime Chaos-Agenten. Social Deduction
mit DevOps-Humor; 8–12 Minuten pro Runde.

## Status

Vertical Slice `Lobby + Movement`. Kein Task-/Sabotage-Gameplay. Siehe
[`docs/superpowers/specs/2026-04-24-vertical-slice-lobby-movement-design.md`](docs/superpowers/specs/2026-04-24-vertical-slice-lobby-movement-design.md).

Design-Bibel: [`merge_conflict_mayhem_project/`](merge_conflict_mayhem_project/).

## Lokale Entwicklung

Voraussetzungen: Python 3.12 und [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Danach http://localhost:8000 im Browser öffnen.

### Mehrere Spieler simulieren

Drei Browser-Tabs öffnen, je einen Namen + denselben Raumcode eingeben
(z. B. `ABCD`), joinen. Der erste Spieler ist automatisch Host und sieht
einen „Runde starten"-Button. Nach Start bewegen sich alle mit WASD
oder Pfeiltasten.

## Tests

```bash
uv run pytest
```

## Architektur

- **Backend autoritativ**: Python + FastAPI + WebSockets. Der Server hält den
  Spielzustand, rechnet Positionen, verteilt Rollen, zählt den Timer.
- **Client ist dumm**: Vanilla JS + Canvas. Sendet Input-State, rendert
  empfangene Snapshots. Keine Spiellogik im Browser.
- **Protokoll**: JSON über `/ws`, camelCase auf der Wire. Vollständig
  implementierbar auch von einem Godot-Client (Sprint 5).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, tests, and architecture summary"
```

---

## Task 18: End-to-End-Verifikation + Slice-Abschluss

**Files:** (keine Änderungen, nur Smoke-Tests)

- [ ] **Step 1: Run the full test suite one more time**

```bash
uv run pytest -v
```

Expected: alle Tests passen, zero warnings über `DeprecationWarning` hinaus.

- [ ] **Step 2: Start the server**

```bash
uv run uvicorn app.main:app --reload
```

In separatem Terminal/Browser-Tab:

- [ ] **Step 3: Manual DoD verification**

Drei Chrome/Firefox-Tabs öffnen (jeweils auf `http://localhost:8000`). In jedem Tab:

1. Name eingeben (drei verschiedene).
2. Raumcode `ABCD` eingeben (derselbe in allen Tabs).
3. Join klicken.

**Verify:**

- [ ] In allen drei Tabs erscheint die Spielerliste mit allen drei Namen.
- [ ] Nur Tab 1 sieht „Runde starten"-Button.
- [ ] Nach Klick auf Start: alle drei Tabs wechseln auf Canvas-View.
- [ ] Timer läuft in allen Tabs synchron runter (Unterschied < 1 s).
- [ ] WASD in Tab 1 bewegt die Figur; Tabs 2 und 3 sehen diese Bewegung live.
- [ ] Jeder Tab zeigt oben seine Rolle (zwei sehen „developer", einer „Vibe Coder (Chaos)").
- [ ] Wenn ein Tab geschlossen wird: verbleibende Tabs sehen den Spieler verschwinden.

- [ ] **Step 4: Tag the slice completion**

```bash
git tag -a slice/lobby-movement-v1 -m "Vertical slice: lobby + movement pipeline complete"
```

- [ ] **Step 5: Push branch and tag to origin (ask user first)**

⚠️ Nicht automatisch pushen — Sven explizit fragen, ob der Slice-Abschluss auf GitLab gepusht werden soll.

Wenn Sven zustimmt:

```bash
git push origin main
git push origin slice/lobby-movement-v1
```

---

## Fertigstellungs-Kriterien für diese Slice

Slice ist done, wenn alle Tasks 1–18 abgeschlossen sind **und**:

- `uv run pytest` zeigt alle Tests grün.
- Drei Browser-Tabs können die DoD-Schritte in Task 18 ohne Fehler durchlaufen.
- Der WebSocket-Traffic entspricht dem Protokoll aus Abschnitt 7 der Spec (camelCase, keine Rollen im öffentlichen `game_state`).
- Kein Code-Pfad hat einen Test-Marker `xfail` oder einen ungefixten `TODO`.

Alles, was darüber hinausgeht (Tasks, Sabotagen, Win/Lose, Voting, …) ist **nicht** Teil dieses Plans und wird in separaten Specs/Plänen behandelt.
