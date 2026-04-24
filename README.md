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
