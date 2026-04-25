# Dokumentation

Hier liegen alle Projekt-Docs. Wenn du neu hier bist, fang mit der Roadmap an.

## Lebende Dokumente

| Doc | Was |
|---|---|
| [`ROADMAP.md`](ROADMAP.md) | **Der eine Plan.** Vision, Stand, sechs Tier mit konkreten Slices, „was ist nächstes?". Alle anderen Docs erklären Sub-Themen. |
| [`maps.md`](maps.md) | Map-JSON-Schema. Was darf in einer `maps/*.json` stehen, wie wird daraus das Spiel? |

## Kommt im Tier 0 dazu

Diese Docs werden im ersten Sauberkeits-Sprint geschrieben (siehe Roadmap Tier 0):

| Doc | Was |
|---|---|
| `PROTOCOL.md` | Vollständiger WebSocket-Vertrag — alle Messages mit Schema, Phase-Übergänge, Error-Codes |
| `ARCHITECTURE.md` | High-Level-Overview, Tick-Loop, Datenfluss |
| `DEPLOY.md` | Deploy-Workflow auf EC2 (Tarball, Caddy, Stop/Start) |
| `DEV.md` | Lokale Entwicklung, Branch-Konventionen, Testing |

## Im Repo, aber nicht hier

- [`../README.md`](../README.md) — Top-Level Repo-Intro + Quick-Start
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — wie du beitragen kannst (Erst-Anlauf für Mit-Entwickelnde)
- [`../CLAUDE.md`](../CLAUDE.md) — Leitfaden für AI-Assistant-Sessions (Claude Code)
- [`../merge_conflict_mayhem_project/`](../merge_conflict_mayhem_project/) — ursprüngliches Design-Paket. **Historisch.** Die Roadmap ist die aktuelle Wahrheit; das Master-Doc darin ist Inspiration und Quelle für Eventtexte/Rollen-Ideen.
