# Claude Code — Quick-Pointer

> Vollständige Agent-Onboarding-Doku: [`AGENTS.md`](AGENTS.md).
> Diese Datei hier ist nur ein Pointer für Claude-Code-Sessions.

## Was du als Erstes liest

1. **[`AGENTS.md`](AGENTS.md)** — Stack, Commands, CI-Gates, Conventions, Gotchas. Single Source of Truth für jeden AI-Agent.
2. **[`docs/ROADMAP.md`](docs/ROADMAP.md)** — was als Nächstes dran ist. Nichts eigenmächtig vorziehen.
3. **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** — Backend-Innenleben, wenn du Code anfasst.

## Claude-Code-spezifische Erinnerungen

- **Sprache:** Deutsch im Chat, knapp, Multiple-Choice wo's hilft. Code-Comments + Docstrings Englisch.
- **Niemals ungefragt pushen** — auch nicht nach klarer Zustimmung für andere Actions. Push = Live-Deploy auf prod-is-lava.dev.
- **Co-Author-Trailer** für AI-generierte Commits:
  `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`
- **Keine Emojis** in Code, Doku oder Commit-Messages.
- **Existing files editen** statt neue zu erstellen. Keine spontanen `NOTES.md`, `TODO.md` etc.

Bei Konflikten zwischen `CLAUDE.md` und `AGENTS.md` gewinnt `AGENTS.md`.
