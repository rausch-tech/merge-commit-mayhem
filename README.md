# Merge Conflict Mayhem

[![CI](https://github.com/rausch-tech/merge-commit-mayhem/actions/workflows/ci.yml/badge.svg)](https://github.com/rausch-tech/merge-commit-mayhem/actions/workflows/ci.yml)

Ein Among-Us-artiges Social-Deduction-Game für Tech-Teams. Statt Raumstation: ein Software-Büro mitten im Release. Statt Crewmates und Imposter: Release-Team und Chaos-Agenten. Mit der Mechanik-Klarheit von Among Us und der Insider-Komik eines Engineering-Teams in der Krise.

**Status:** Spielbar als Browser-Client (live, auto-deployed) und als Godot-3D-Client (parallel in Tier 4). Beide gegen denselben FastAPI-Server. Siehe [`docs/ROADMAP.md`](docs/ROADMAP.md) für Stand und nächste Schritte.

**Live (Test-Server):** https://prod-is-lava.dev

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

In der Lobby gibt's eine Checkbox „Demo-Mode". Damit kannst du allein eine Runde starten — du wirst automatisch zum Chaos-Agent und siehst die Sabotage-UI. Alternativ kannst du als Host KI-Bots in die Lobby einladen ("+ Bot hinzufügen"), die heuristisch oder LLM-getrieben mitspielen.

### Mit anderen testen

Drei Browser-Tabs (oder echte Geräte im selben Netz) öffnen, je einen Namen + denselben Raumcode eingeben (z. B. `ABCD`), joinen. Der erste Spieler ist Host, sieht „Runde starten". Nach Start bewegen alle sich mit WASD oder Pfeiltasten.

## Tests

```bash
uv run pytest          # ~714 Backend-Tests
npx vitest run         # ~109 Frontend-Tests
```

## Architektur (kurz)

- **Backend autoritativ:** Python + FastAPI + WebSockets. Server hält allen Spielzustand, rechnet Positionen, verteilt Rollen, prüft Win-Conditions.
- **Browser-Client:** Vanilla JS + Canvas. Sendet Input-State, rendert empfangene Snapshots. Keine Spiellogik im Browser.
- **Godot-3D-Client (`godot-3d/`):** Godot 4.6, gleicher WebSocket-Vertrag wie der Browser-Client. 3D-Render mit echten KayKit-Assets, holt Map + Kinds-Registry zur Laufzeit vom Backend.
- **Map als Daten:** `maps/*.json` ist Single Source of Truth für Räume, Türen, Spawns, Task-Anker, Möbel. Vom Server validiert + an Client geschickt. `maps/kinds.json` ist die zentrale Registry für MapObject-Typen (Desk, Server-Rack, …) inklusive Asset-Pfade pro Client.
- **Wire-Format:** JSON über WebSocket, camelCase, client-agnostisch. Browser- und Godot-Client teilen sich denselben Server.

## Mehr Doku

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — der vollständige Plan: Vision, Stand, Tier 0–7
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Backend-Innenleben, Tick-Loop, Controller-Layout
- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — vollständiger WebSocket-Vertrag
- [`docs/maps.md`](docs/maps.md) — Map-JSON-Schema + MapObject-Kinds
- [`docs/GODOT_HANDOFF.md`](docs/GODOT_HANDOFF.md) — Onboarding für Godot-Entwickler:innen
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — wie du beitragen kannst

## Lizenz

The source code of this project is licensed under the MIT License — see
[`LICENSE`](LICENSE).

Game assets, including logos, artwork, sprites, audio, and branding materials,
are licensed separately. See [`ASSET_LICENSE.md`](ASSET_LICENSE.md) for the
asset terms and `sounds/CREDITS.md` / `images/README.md` for third-party
attributions.
