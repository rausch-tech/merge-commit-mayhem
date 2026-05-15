# HOWTO: Eine neue Rolle hinzufügen

Step-by-step für eine 9. Rolle (5 Release + 3 Chaos sind aktuell drin). Die [Roadmap](ROADMAP.md) nennt mehrere Kandidaten: Data Wizard, Incident Commander, Bug Squasher, Legacy Oracle.

> **Architektur-Erinnerung:** Rollen-Daten sind statisch (im Code), Rollen-Zuweisung ist server-authoritativ (`assign()` in `roles.py`), Rollen werden im `private_role`-Frame an genau einen Spieler gesendet. Ein Public-Broadcast einer Rolle ist ein Bug.

---

## 1. Definition in `app/game/roles.py`

Neue `RoleDefinition` ergänzen:

```python
DATA_WIZARD = RoleDefinition(
    id="data_wizard",
    title="Data Wizard",
    team="release_team",
    description=(
        "Du bist Data Wizard. Logs, Metriken, Dashboards — du weißt, was die "
        "Pipeline gerade tut, ohne sie zu fragen."
    ),
    short_blurb="Daten-Spezialist • Logs & Metriken",
    strength_categories=(TASK_CATEGORY_INFRA, TASK_CATEGORY_LEGACY),
    weak_categories=(TASK_CATEGORY_SCOPE,),
    coffee_decay_modifier=0.7,        # sip slowly; data takes patience
    coffee_full_speed_bonus=0.15,
    coffee_low_speed_penalty=0.10,
    ability_id="trace_query",          # neu, siehe Schritt 3
    ability_label="Trace Query",
    ability_hint="Markiert die letzten 5 Sabotage-relevanten Events sichtbar.",
    singleton=True,                    # max 1× pro Runde
)
```

Pflichtfelder: `id`, `title`, `team` (`release_team` oder `chaos_agents`), `description`, `short_blurb`. Alles andere hat Defaults — aber für eine spürbare Rolle willst du mindestens eine `strength_categories`-Liste setzen.

**Coffee-Profil:** `coffee_decay_modifier` 1.0 = neutral, 1.5 = drains fast (DevOps), 0.5 = sips slowly (Caffeine Collector). `max_coffee` darf > 100 sein.

**Ability:** Optional. Falls gesetzt, muss `ability_id` in `apply_use_ability` (in `app/game/game_room.py`) als `elif`-Zweig implementiert werden — siehe Schritt 3.

**Singleton:** True ⇒ Server gibt diese Rolle max. 1× pro Runde, auch wenn mehrere Spieler sie als Wunschrolle markieren.

## 2. Rolle in `assign()` einbauen

Untenstehende Liste in `roles.py` ergänzen:

```python
RELEASE_ROLES: tuple[RoleDefinition, ...] = (
    DEVELOPER, DEVOPS_ENGINEER, QA_LEAD, SCRUM_MASTER, CAFFEINE_COLLECTOR,
    DATA_WIZARD,  # neu
)
```

Bei Chaos-Rollen analog `CHAOS_ROLES = (...)` ergänzen — aber: **Chaos-Wunschrolle wird ignoriert**, das ist Geheimhaltungs-Design. Die Lobby-Wunschrolle wird nur für Release berücksichtigt.

`assign()` selbst musst du nicht ändern — der Algorithmus ist generisch, er pickt aus `RELEASE_ROLES` / `CHAOS_ROLES` mit Singleton-Cap und Wunsch-Best-Effort.

## 3. Ability-Logik (falls gesetzt)

In `app/game/game_room.py:apply_use_ability` einen neuen `elif`-Zweig:

```python
elif ability == "trace_query":
    # ability: Data Wizard markiert die letzten 5 Sabotage-Events
    # sichtbar im Eventfeed.
    self._emit_event(
        "info",
        f"{player.name} (Data Wizard) hat eine Trace-Query ausgeführt.",
    )
    result["traceMessage"] = "Letzte Sabotagen markiert."
```

> **Convention:** Eine Ability mutiert Room-State (Pipeline, Coffee, Phase, ...) oder emittet ein Event — niemals beides gleichzeitig zu viel auf einmal. Wenn du ein neues Phase-Verhalten willst (wie Standup), ruf `self._meeting_ctl.begin_meeting(...)` auf statt copy/paste.

## 4. Frontend-Anbindung

**Role-Card-Modal** (`static/role_intro.js`): rendert automatisch alles aus `private_role.payload` — Title, Description, Strengths, Ability. Keine Änderung nötig.

**HUD-Pille** (`static/hud.js`): zeigt den `role.title` aus `private_role`. Keine Änderung nötig.

**Ability-Button** (`static/main.js`): rendert wenn `private_role.ability_id` gesetzt ist. Falls die Ability ein neues Trigger-UI braucht (z.B. "klicke einen Spieler"), muss das hier ergänzt werden — sonst nichts.

## 5. Tests

`tests/test_roles.py` ergänzen:

```python
def test_data_wizard_has_strength_in_infra_and_legacy():
    rd = role_by_id("data_wizard")
    assert "infra" in rd.strength_categories
    assert "legacy" in rd.strength_categories
    assert rd.team == "release_team"


def test_data_wizard_singleton_at_most_one_per_round():
    # 12 players, all want data_wizard
    # Server muss genau 1 Data Wizard, andere Release-Rollen verteilen.
    ...


def test_trace_query_ability_emits_event():
    room = _make_started_room(player_count=4)
    wizard_id = next(p.id for p in room.players.values() if p.role == "data_wizard")
    if wizard_id is None:
        pytest.skip("rng didn't pick data_wizard this seed")
    before_events = len(room.events)
    room.apply_use_ability(wizard_id)
    assert len(room.events) > before_events
```

**Common gotcha:** Wenn die Rolle in der Test-Suite nicht auftaucht, hast du wahrscheinlich `RELEASE_ROLES` nicht ergänzt — `assign()` zieht nur aus dieser Liste.

## 6. Map-Compatibility

Eine neue Rolle braucht **keine Map-Änderungen**. Spawn-Points sind generisch, `task_speed_multiplier` greift kategoriebasiert auf alle existierenden Tasks zu.

Falls du eine **neue Task-Kategorie** für die Rolle einführen willst (z.B. `data` für Data Wizard), gehört das in eine eigene Slice — Task-Definitionen müssten dann auch `category="data"` eintragen, sonst hat die Rolle nichts woran sie spürbar wird.

---

## Beispiel-Diff

- `app/game/roles.py`: +30 LoC (RoleDefinition + RELEASE_ROLES-Eintrag)
- `app/game/game_room.py:apply_use_ability`: +6 LoC (falls Ability)
- `tests/test_roles.py`: +40 LoC (3–5 Tests)

Total ~80 LoC. Frontend braucht typischerweise null Änderung — die Rolle taucht im Role-Intro-Modal automatisch auf.

---

## Anti-Patterns (don't)

- **Rolle ohne `category` in einer der bestehenden Tasks.** Dann hat sie keine spürbaren Stärken. Mindestens eine bestehende Kategorie matchen.
- **Public-broadcast der Rolle.** `RoleInfo` darf NUR via `manager.send_to_player(room, pid, ...)` an den Owner. Jeder `manager.broadcast(...)`-Pfad mit Rolle ist ein Leak.
- **Chaos-Variante mit anderer Mechanik.** Chaos-Rollen unterscheiden sich nur in `available_sabotages`. Wenn du chaos-spezifische Mechaniken willst → eigene Slice, weil Movement/Take-Down etc. global sind.
- **Ability-Cooldown pro Tick zählen.** Abilities sind 1×/Runde. `player.ability_used` wird gesetzt und auf `reset_for_new_round` zurückgesetzt — nichts dazu erfinden.
