# Security Policy

## Supported Versions

Merge Conflict Mayhem ist ein aktiv entwickelter Showcase. Es gibt bisher kein
formales Release-Schema; Sicherheits-Fixes laufen direkt auf `main` und werden
von dort automatisch auf die Test-Server-Instanz deployed.

## Reporting a Vulnerability

**Bitte keine Sicherheitsprobleme als öffentliches GitHub-Issue melden.**

Nutze stattdessen GitHubs eingebautes **Private Vulnerability Reporting**:

1. Auf der Repo-Seite: **Security** → **Report a vulnerability**
2. Beschreibung mit Reproduktionsschritten, betroffenem Code-Pfad, geschätztem
   Impact

Wir bestätigen den Eingang innerhalb von 72 Stunden, melden uns mit einem ersten
Status binnen einer Woche, und koordinieren Fix + Disclosure-Zeitpunkt mit dem
Reporter.

## Scope

In Scope:

- Authentifizierung / Autorisierung (Room-Codes, Host-Privileges,
  Rollen-Privacy)
- Server-State-Manipulation via WebSocket-Nachrichten (z. B. Position-Forging,
  Vote-Manipulation, Mini-Game-Cheat)
- Information-Disclosure (Rollen anderer Spieler, Privatdaten anderer
  Sessions)
- Resource-Exhaustion am Backend (Memory, CPU, Connection-Pool)
- Cross-Site-Scripting im Browser-Client oder Map-Editor

Out of Scope:

- Selbst-DoS (z. B. eigenen Browser-Tab überlasten)
- Social-Engineering ohne technischen Vektor
- Schwachstellen in Third-Party-Assets (KayKit, Soundpacks) — bitte direkt
  beim Asset-Autor melden

## Hall of Fame

Wenn du möchtest, listen wir dich nach Behebung in den Release-Notes oder
im Repo-README.
