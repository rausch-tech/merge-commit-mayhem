# Dokumentation

Hier liegen alle Projekt-Docs. Wenn du neu hier bist, fang mit der Roadmap an.

## Lebende Dokumente

| Doc                                                    | Was                                                                                                                                      |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| [`ROADMAP.md`](ROADMAP.md)                             | **Der eine Plan.** Vision, Stand, sieben Tier mit konkreten Slices, „was ist nächstes?". Alle anderen Docs erklären Sub-Themen.          |
| [`ARCHITECTURE.md`](ARCHITECTURE.md)                   | High-Level-Overview, Tick-Loop, Backend-Layout (Controller + BotManager), Frontend-Layout, Performance-Baseline.                         |
| [`PROTOCOL.md`](PROTOCOL.md)                           | Vollständiger WebSocket-Vertrag — alle Messages mit Schema, Phase-Übergänge, Error-Codes.                                                |
| [`DEV.md`](DEV.md)                                     | Lokale Entwicklung, Worktree-Workflow, gh-CLI-Befehle.                                                                                   |
| [`DEPLOY.md`](DEPLOY.md)                               | Deploy-Workflow: Auto-Deploy via GitHub Actions, manueller Deploy, Server-Innenleben, Caddy, LLM-Secrets, Rollback.                      |
| [`maps.md`](maps.md)                                   | Map-JSON-Schema + MapObject-Kinds-Katalog. Was darf in einer `maps/*.json` stehen, wie wird daraus das Spiel?                            |
| [`GAME_OVERVIEW.md`](GAME_OVERVIEW.md)                 | Shareable Markdown-Tour des Spiels für externe Brainstorm-Runden.                                                                        |
| [`GODOT_HANDOFF.md`](GODOT_HANDOFF.md)                 | Onboarding für Godot-Entwickler:innen am Tier-4-Client (Stack, Architektur, Asset-Pipeline, Slice-Plan).                                 |
| [`GODOT-DEV-WITH-CLAUDE.md`](GODOT-DEV-WITH-CLAUDE.md) | Workflow-Quick-Ref für KI-Agenten am Godot-Client: Headless-Render, GDScript-Parse-Check, Demo-Szenen, Asset-Pipeline, Permission-Setup. |
| [`ASSET_SPEC.md`](ASSET_SPEC.md)                       | Asset-Pipeline-Konvention (Pivot, Polycount-Budget, kinds.json-Erweiterungs-Workflow) für die Godot-Devs.                                |

## Erweiterungs-HOWTOs

Step-by-step für die häufigsten Erweiterungen, geschrieben für neue Team-Mitglieder:

| Doc                                      | Was                                                                                                           |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| [`HOWTO-SABOTAGE.md`](HOWTO-SABOTAGE.md) | Neue Sabotage hinzufügen — Definition, Effekt-Switch, Object-Binding, Tests.                                  |
| [`HOWTO-MINIGAME.md`](HOWTO-MINIGAME.md) | Neues Mini-Game-Plugin — `init_state` / `handle_input` / `is_complete` / `public_view`. Frontend-Plugin dazu. |
| [`HOWTO-ROLE.md`](HOWTO-ROLE.md)         | Neue Rolle definieren — `RoleDefinition`, Coffee-Profil, optional Ability + Singleton-Cap.                    |

## Im Repo, aber nicht hier

- [`../README.md`](../README.md) — Top-Level Repo-Intro + Quick-Start
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — wie du beitragen kannst (Erst-Anlauf für Mit-Entwickelnde)
- [`../AGENTS.md`](../AGENTS.md) — Single Source of Truth für AI-Agenten (Stack, Commands, CI-Gates, Conventions, Gotchas)
- [`../CLAUDE.md`](../CLAUDE.md) — Pointer für Claude-Code-Sessions auf AGENTS
- [`../merge_conflict_mayhem_project/`](../merge_conflict_mayhem_project/) — ursprüngliches Design-Paket. **Historisch.** Die Roadmap ist die aktuelle Wahrheit; das Master-Doc darin ist Inspiration und Quelle für Eventtexte/Rollen-Ideen.
