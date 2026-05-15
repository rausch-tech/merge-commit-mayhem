# HOWTO: Ein neues Mini-Game hinzufügen

Step-by-step für ein neues Mini-Game. Das Spiel hat aktuell 8 Mechanik-Patterns (Sequencing, Pairing, Timing, Filter, Subset, Stop-Timing, Rotating-Correction, Click-to-Cycle-Sort), jede der 8 Standard-Tasks ist mit einem Mini-Game verknüpft. Eine neue Task-Kategorie oder ein zusätzliches Pattern braucht das gleiche Six-Step-Setup unten.

> **Architektur-Erinnerung:** Server hält den State, Plugin definiert die Regeln. Client zeigt nur was `public_view(state)` zurückgibt. Cheat-Resistance kommt daher, dass der Client den `state` nicht sieht.

---

## 1. Plugin-Klasse in `app/game/minigames/`

Neue Datei `<task_id>_<mechanik>.py`, z.B. `app/game/minigames/diff_review.py` (für `review_pr`):

```python
"""Mini-Game für review_pr — Spot-the-Bug.

Mechanik: 5–8 Code-Zeilen, 2 problematische sind dabei. Spieler muss
beide markieren, danach 'submit'. Falsche Markierung = Soft-Reset.
"""

import random
from app.game.minigames.base import MiniGamePlugin, MiniGamePluginError

NUM_LINES = 6
NUM_BUGS = 2

_LINE_TEMPLATES = [
    {"text": "API_KEY = 'sk-prod-1234'", "is_bug": True},
    {"text": "logger.info(f'user {user.email} logged in')", "is_bug": False},
    {"text": "except Exception: pass", "is_bug": True},
    # ...
]


class DiffReview(MiniGamePlugin):
    id = "diff_review"
    title = "PR-Review"

    def init_state(self, seed: int) -> dict:
        rng = random.Random(seed)
        chosen = rng.sample(_LINE_TEMPLATES, NUM_LINES)
        rng.shuffle(chosen)
        return {
            "lines": [{"id": f"l{i}", **line, "marked": False} for i, line in enumerate(chosen)],
            "submitted": False,
        }

    def handle_input(self, state: dict, action: str, params: dict) -> dict:
        if action == "toggle":
            line_id = params.get("lineId")
            if not isinstance(line_id, str):
                raise MiniGamePluginError(code="INVALID_PARAMS", message="Missing lineId.")
            for line in state["lines"]:
                if line["id"] == line_id:
                    line["marked"] = not line["marked"]
                    return state
            raise MiniGamePluginError(code="UNKNOWN_LINE", message=f"Unknown lineId {line_id!r}.")
        if action == "submit":
            marked = {line["id"] for line in state["lines"] if line["marked"]}
            actual_bugs = {line["id"] for line in state["lines"] if line["is_bug"]}
            if marked == actual_bugs:
                state["submitted"] = True
            else:
                # Soft-reset: alle Markierungen droppen.
                for line in state["lines"]:
                    line["marked"] = False
            return state
        raise MiniGamePluginError(code="UNKNOWN_ACTION", message=f"Unknown action {action!r}.")

    def is_complete(self, state: dict) -> bool:
        return state["submitted"]

    def public_view(self, state: dict) -> dict:
        return {
            # Wichtig: ``is_bug`` NICHT raussenden — sonst sieht der Client
            # die Lösung und kann automatisch "submit"-en.
            "lines": [
                {"id": line["id"], "text": line["text"], "marked": line["marked"]}
                for line in state["lines"]
            ],
            "totalLines": NUM_LINES,
        }
```

Pflicht-Methoden (Plugin-Interface, siehe `app/game/minigames/base.py`):

| Methode                               | Zweck                                                                                          |
| ------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `init_state(seed)`                    | Initial-State, deterministisch via seed (Server liefert random seed pro Session)               |
| `handle_input(state, action, params)` | Mutiert state. Wirft `MiniGamePluginError` bei kaputten Inputs.                                |
| `is_complete(state)`                  | True ⇒ Server beendet die Session und vergibt Reward.                                          |
| `public_view(state)`                  | Was der Client zu sehen kriegt. **NIEMALS** Lösungs-Felder (`is_bug`, `correct_order`) leaken. |

## 2. Plugin registrieren

`app/game/minigames/registry.py`:

```python
from app.game.minigames.diff_review import DiffReview

MINI_GAME_PLUGINS: dict[str, MiniGamePlugin] = {
    # ... bestehende ...
    "diff_review": DiffReview(),
}
```

## 3. Task-Verknüpfung

`app/game/tasks.py`: dem entsprechenden `TaskDefinition` das Feld `mini_game="diff_review"` geben:

```python
TaskDefinition(
    id="review_pr",
    # ...
    mini_game="diff_review",   # hier
    category="code",
),
```

Sobald das Feld gesetzt ist, springt `apply_task_hold_start` automatisch in den Mini-Game-Pfad statt Hold-E zu starten.

## 4. Frontend-Plugin

`static/minigames/<plugin_id>.js` mit gleichem `id`-String. Client-side Plugin-Interface:

```js
export const DiffReviewPlugin = {
  id: "diff_review",
  title: "PR-Review",

  // view ist das, was Server's public_view() zurückgibt
  render(view, sendInput) {
    // DOM bauen, mit sendInput("toggle", { lineId: ... }) Inputs senden
  },
};
```

In `static/minigames/registry.js` registrieren — die Modal-UI lädt automatisch das passende Plugin anhand der `mini_game_id` im `mini_game_started`-Frame.

> **Frontend ≠ Source of Truth.** Es darf optimistisch rendern, aber bei `mini_game_state` (Server-Echo) muss es den Server-View nehmen, nicht den eigenen lokalen.

## 5. Tests

`tests/test_minigame_<plugin_id>.py`:

```python
def test_diff_review_completes_when_correct_bugs_submitted():
    plugin = DiffReview()
    state = plugin.init_state(seed=0)
    bug_ids = [line["id"] for line in state["lines"] if line["is_bug"]]
    for bid in bug_ids:
        state = plugin.handle_input(state, "toggle", {"lineId": bid})
    state = plugin.handle_input(state, "submit", {})
    assert plugin.is_complete(state) is True


def test_diff_review_soft_resets_on_wrong_submit():
    plugin = DiffReview()
    state = plugin.init_state(seed=0)
    non_bug = next(line["id"] for line in state["lines"] if not line["is_bug"])
    state = plugin.handle_input(state, "toggle", {"lineId": non_bug})
    state = plugin.handle_input(state, "submit", {})
    assert plugin.is_complete(state) is False
    assert all(not line["marked"] for line in state["lines"])
```

Bonus: `tests/test_minigame_concurrency.py` testet das Lifecycle-Framework (start, input, complete, cancel) und ist bereits generisch — du musst dort nichts ergänzen.

## 6. Spec-Validation

**Reward**: Mini-Game-Completion löst `room._tasks_ctl.apply_reward(definition, completed_by=player_id)` aus. Reward-Werte stehen in der `TaskDefinition` (z.B. `release_progress_reward=8`). Du musst keinen Reward-Code im Plugin schreiben.

**Cooldown**: Auch das ist generisch — `TASK_RESPAWN_COOLDOWN` (8s) gilt nach jeder Completion.

**Cancel-Verhalten**: Mini-Games werden gecancelt bei Disconnect, Take-Down, Meeting-Start, Round-End. Du musst nichts dafür tun, das Framework ruft `cancel_all`/`cancel` an den richtigen Punkten.

---

## Beispiel-Diff (typisch ~250 LoC für ein Mini-Game)

- `app/game/minigames/<plugin>.py`: ~80 LoC (Plugin-Klasse + Templates)
- `app/game/minigames/registry.py`: +2 LoC (Import + dict-Eintrag)
- `app/game/tasks.py`: +1 LoC (`mini_game="<id>"`)
- `static/minigames/<plugin>.js`: ~60 LoC (UI)
- `static/minigames/registry.js`: +2 LoC
- `tests/test_minigame_<plugin>.py`: ~80 LoC (5–10 Tests)
- `tests-frontend/minigame-<plugin>.test.js`: ~30 LoC (Smoke)

---

## Anti-Patterns (don't)

- **`public_view` mit Lösung.** Wenn Client die richtige Antwort sehen kann, ist das Mini-Game wertlos. Server-State darf reicher sein als `public_view`.
- **Plugin liest/schreibt `room.<feld>`.** Plugins sind pure — sie kennen keinen `GameRoom`. Reward + Cooldown laufen über das Framework.
- **Aktion-Input ungeprüft.** `handle_input` muss jeden falschen `action`-String und jeden malformed `params` mit `MiniGamePluginError` ablehnen, sonst kann der Client das Plugin abschießen.
- **Animationen in `init_state`.** State muss JSON-serialisierbar bleiben — keine Funktionen, keine Objekt-Referenzen, nur Dicts/Lists/Skalare.
