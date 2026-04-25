# Merge Conflict Mayhem

[![CI](https://github.com/rausch-tech/merge-commit-mayhem/actions/workflows/ci.yml/badge.svg)](https://github.com/rausch-tech/merge-commit-mayhem/actions/workflows/ci.yml)

Ein Among-Us-artiges Social-Deduction-Game für Tech-Teams. Statt Raumstation: ein Software-Büro mitten im Release. Statt Crewmates und Imposter: Release-Team und Chaos-Agenten. Mit der Mechanik-Klarheit von Among Us und der Insider-Komik eines Engineering-Teams in der Krise.

**Status:** Spielbar als Browser-Prototyp, in aktiver Entwicklung. Godot-Client folgt nach der Foundation-Cleanup-Phase. Siehe [`docs/ROADMAP.md`](docs/ROADMAP.md) für den vollständigen Plan.

**Live (Test-Server):** https://mcm.3-78-184-97.sslip.io

## Schnellstart

Voraussetzungen: Python 3.12 und [`uv`](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:rausch-tech/merge-commit-mayhem.git
cd merge-commit-mayhem
uv sync
uv run uvicorn app.main:app --reload
```

Danach http://localhost:8000 im Browser öffnen.

### Alleine testen (Demo-Mode)

In der Lobby gibt's eine Checkbox „Demo-Mode". Damit kannst du allein eine Runde starten — du wirst automatisch zum Chaos-Agent und siehst die Sabotage-UI.

### Mit anderen testen

Drei Browser-Tabs (oder echte Geräte im selben Netz) öffnen, je einen Namen + denselben Raumcode eingeben (z. B. `ABCD`), joinen. Der erste Spieler ist Host, sieht „Runde starten". Nach Start bewegen alle sich mit WASD oder Pfeiltasten.

## Tests

```bash
uv run pytest
```

Aktuell: 207 Tests grün.

## Architektur (kurz)

- **Backend autoritativ:** Python + FastAPI + WebSockets. Server hält allen Spielzustand, rechnet Positionen, verteilt Rollen, prüft Win-Conditions.
- **Client minimal:** Vanilla JS + Canvas. Sendet Input-State, rendert empfangene Snapshots. Keine Spiellogik im Browser.
- **Map als Daten:** `maps/default.json` ist Single Source of Truth für Räume, Wände, Türen, Spawns, Task-Anker. Vom Server validiert + an Client geschickt.
- **Protokoll Godot-kompatibel:** JSON über WebSocket, camelCase auf der Wire. Browser-Client + späterer Godot-Client teilen sich denselben Server.

## Mehr Doku

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — der vollständige Plan: Vision, Stand, sechs Tier
- [`docs/maps.md`](docs/maps.md) — Map-JSON-Schema
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — wie du beitragen kannst

## Lizenz

Aktuell privates Repo, keine Lizenz definiert. Entscheidung pending.
