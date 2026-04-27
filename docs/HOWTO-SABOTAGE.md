# HOWTO: Eine neue Sabotage hinzufügen

Step-by-step für den Fall, dass du eine 9. Sabotage ergänzen willst (nach den 8 aus Tier 2.5/2.7). Der Server-Code, der Map-Editor und der Browser-Client müssen alle mitziehen.

> **Architektur-Erinnerung:** Backend ist autoritativ. Wenn du eine neue Sabotage baust, schreibt sich der Effekt in `SabotagesController.trigger`, nicht im Frontend. Das Frontend zeigt nur den Button + Cooldown.

---

## 1. Definition in `app/game/sabotages.py`

Add a `SabotageDefinition` to `SABOTAGE_DEFINITIONS`:

```python
SabotageDefinition(
    id="rubber_duck_panic",         # Wire-Identifier, snake_case
    title="Rubber-Duck-Panic",      # Anzeigename im HUD
    cooldown_seconds=80.0,
    incidents_increase=15,           # optional, +n Incidents on trigger
    trigger_object_types=("dev_chair",),  # Tier 2.7 object-binding
    object_hint="Schreibtisch im Open Space",
)
```

Pflichtfelder: `id`, `title`, `cooldown_seconds`. Alles andere hat Defaults.

**Convention:** Tier 2.7 verlangt `trigger_object_types`, sonst ist die Sabotage nur auf Maps ohne typed-anchors (legacy-Pfad) triggerbar. Heißt praktisch: **immer setzen**, sonst kommt sie auf der `default.json` nicht zur Geltung.

## 2. Effekt in `app/game/controllers/sabotages.py`

In `SabotagesController.trigger()`:

- füge einen `elif sabotage_id == "rubber_duck_panic":` Block in den **Effekt-Switch** ein. Lies/schreibe Room-State über `room.<feldname>` (z.B. `room.pipeline_stability`, `room.coffee_level`, `room.lights_off`).
- füge einen `elif`-Block in den **Event-Switch** ein, der die Eventfeed-Zeile emittiert: `room._emit_event("warn", "Dev starrt eine Quietsche-Ente an. Niemand denkt mehr.")`.

Wenn die Sabotage einen **Repair-Pfad** braucht (wie `lights_out` und `comms_outage`), ergänze:

- den `elif` in `SabotagesController.repair()`,
- ein `SabotagePanel` in `maps/default.json` (siehe `docs/maps.md`),
- den active-Flag-Block in `SabotagesController.tick()`.

Wenn die Sabotage nur einmalig wirkt (wie `merge_conflict_storm`), ist nichts davon nötig.

## 3. Map-Anchor

Falls du einen neuen `object_type` einführst (z.B. `dev_chair`), trage in `maps/default.json` mindestens einen `taskAnchor` mit dieser `objectType`-Annotation ein. Wenn du einen bestehenden type nutzt (z.B. `git_terminal`), reicht das.

`docs/maps.md` listet alle aktuell genutzten `objectType`-Werte.

## 4. Frontend-Button

`static/sabotages.js` rendert die Buttons aus dem Server-state (`game_state.sabotages[]`). **Keine Änderung nötig** — wenn der Server eine neue ID liefert, wird sie automatisch gerendert. Falls du einen passenden Icon-Text willst, ergänze einen Mapping-Entry in der gleichen Datei.

## 5. Tests

Pflicht: Ein neuer Test in `tests/test_sabotages.py`, der:

1. Den Chaos-Spieler an den richtigen Anchor snappt: `snap_to_object_for_sabotage(room, chaos_id, "rubber_duck_panic")`.
2. `room.apply_sabotage(chaos_id, "rubber_duck_panic")` aufruft.
3. Den erwarteten Effekt prüft (z.B. `room.incidents == 15`).

**Common gotcha:** Ohne `snap_to_object_for_sabotage` kommt `NOT_NEAR_OBJECT` — Tier 2.7 Object-Binding gilt für alle typed-anchor-Maps.

## 6. CI-Gate-Run

```bash
uv run pytest -k sabotage              # neuer Test grün?
uv run ruff check . && uv run ruff format --check .
```

Wenn das durchläuft, ist die Sabotage live nach Merge auf `main`.

---

## Wo nichts geändert werden muss

- `app/protocol.py` — Sabotagen sind generisch (id + cooldown + active-Flag). Keine neuen Pydantic-Models nötig.
- `app/game/game_room.py` — der Cleanup-Slice hat alle Sabotage-Logik in den Controller verschoben. Falls du was in `game_room.py` editieren willst, nochmal überlegen ob es nicht in `controllers/sabotages.py` gehört.
- `static/render.js` — Sabotage-Render-Layer (Lights-Out-Vignette, Slack-Down-Banner) ist bereits implementiert für die etablierten Effekte. Eine neue Sabotage ohne neuen Render-Effekt braucht nichts.

---

## Beispiel-Diff (8.5 LoC im Schnitt)

Ein typischer "neue-Sabotage"-PR berührt:

- `app/game/sabotages.py`: +9 LoC (eine `SabotageDefinition`)
- `app/game/controllers/sabotages.py`: +4 LoC (Effekt + Event-emit)
- `maps/default.json`: +1 LoC (oder 0 wenn bestehender object_type)
- `tests/test_sabotages.py`: +15 LoC (ein Test)

Total ~30 Zeilen. Wenn dein Diff größer ist, hast du wahrscheinlich Spiellogik in den Client gedrückt — zurück zum Backend.
