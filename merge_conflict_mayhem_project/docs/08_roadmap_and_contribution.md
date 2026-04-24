# 08 – Roadmap & Contribution Guide

## Ziel

Das Projekt soll intern offen entwickelt werden. Mitarbeitende sollen mit kleinen Pull Requests neue Inhalte beitragen können.

---

# 1. Roadmap

## Sprint 1 – Spielbarer technischer Prototyp

Ziel:

> Eine Runde kann technisch gespielt werden.

Features:

- Projektstruktur
- FastAPI-Backend
- WebSocket-Verbindung
- Lobby
- einfache Map
- Spielerbewegung
- GameState-Broadcast
- Timer
- einfache Tasks
- einfache Sabotage
- Win/Lose Screen

---

## Sprint 2 – Social Deduction Loop

Ziel:

> Verdächtigungen und Diskussionen entstehen.

Features:

- Emergency Meetings
- Voting
- Spieler entfernen
- Rollen am Ende aufdecken
- Eventfeed
- Sabotage-Cooldowns

---

## Sprint 3 – Humor und Firmenidentität

Ziel:

> Das Spiel fühlt sich intern und einzigartig an.

Features:

- mehr Eventtexte
- Endscreen-Awards
- Insider-Gags
- eigene Avatare
- lustige Tasknamen
- Firmen-/Office-Map

---

## Sprint 4 – Modding und Contributions

Ziel:

> Mitarbeitende können einfach neue Inhalte beitragen.

Features:

- Tasks aus JSON
- Sabotagen aus JSON
- Rollen aus JSON
- Contribution Guide
- Beispiel-Issues
- Balancing-Dateien

---

## Sprint 5 – Godot-Client

Ziel:

> Ein schönerer Client ersetzt oder ergänzt den Browser-Prototyp.

Features:

- Godot-Projekt
- WebSocket-Anbindung
- gleiche Protokollstruktur
- isometrische Map
- Animationen
- Sound
- bessere UI

---

# 2. Contribution-Prinzip

Jeder Pull Request darf etwas Kleines beitragen:

- neue Task
- neue Sabotage
- neuer Eventtext
- neuer Endscreen-Award
- neue Rolle
- neuer Raum
- neuer Skin
- neues Meme
- Balancing-Anpassung

Wichtig:

> Kleine PRs sind besser als riesige Umbauten.

---

# 3. Beispiel-Issue: Neue Sabotage

```text
Feature: Neue Sabotage "Flaky Tests"

Beschreibung:
Der Chaos-Agent kann "Flaky Tests" auslösen. Für 30 Sekunden haben abgeschlossene Tasks eine 25%-Chance, wieder geöffnet zu werden.

Akzeptanzkriterien:
- Sabotage ist nur für Chaos-Agenten sichtbar
- Cooldown: 90 Sekunden
- Eventfeed zeigt: "Die Tests sind flaky. Natürlich nur manchmal."
- Effekt endet automatisch nach 30 Sekunden
```

---

# 4. Beispiel-Issue: Neuer Award

```text
Feature: Endscreen-Award "Most Suspicious Innocent"

Beschreibung:
Am Ende der Runde soll ein unschuldiger Spieler ausgezeichnet werden, der besonders oft verdächtigt wurde.

Akzeptanzkriterien:
- Votes gegen unschuldige Spieler werden gezählt
- Spieler mit den meisten falschen Verdächtigungen erhält den Award
- Award wird im Endscreen angezeigt
```

---

# 5. Beispiel-Issue: Neue Task

```text
Feature: Neue Task "Find Missing Semicolon"

Beschreibung:
Im Open Space soll eine neue Hold-Task erscheinen: "Find Missing Semicolon".

Akzeptanzkriterien:
- Task liegt im Raum Open Space
- Taskdauer: 4 Sekunden
- Reward: +6 % Release Progress
- Eventfeed nach Abschluss: "Ein Semikolon wurde gefunden. Niemand weiß, wie lange es gefehlt hat."
- Task ist in tasks.json konfigurierbar
```

---

# 6. Beispiel-Issue: Neuer Eventtext

```text
Feature: Neue Eventtexte für Pipeline-Fehler

Beschreibung:
Ergänze 10 neue Eventtexte für BUILD FAILED Events.

Beispiele:
- "Die Pipeline hat emotionalen Schaden genommen."
- "Unit Tests sind nur eine Meinung."
- "Build failed. Aber wenigstens konsistent."

Akzeptanzkriterien:
- Texte liegen in event_texts.json
- Keine doppelten Texte
- Texte sind kurz genug für den Eventfeed
```

---

# 7. Contribution Guidelines

## Neue Tasks

Tasks sollten:

- einen klaren Raum haben
- eine kurze Dauer haben
- einen einfachen Effekt haben
- humorvoll, aber verständlich sein
- im MVP primär Hold Tasks sein

## Neue Sabotagen

Sabotagen sollten:

- sichtbar sein
- reparierbar sein
- nicht sofort das Spiel entscheiden
- einen Cooldown haben
- lustige Eventtexte erzeugen

## Neue Rollen

Rollen sollten:

- klar verständlich sein
- eine einfache Fähigkeit haben
- nicht zu stark sein
- zum Dev-/Office-Humor passen

## Neue Assets

Assets sollten:

- transparenten Hintergrund haben
- konsistent benannt sein
- zur Farbpalette passen
- in die bestehende Ordnerstruktur einsortiert werden

---

# 8. Code Review-Kriterien

Ein PR sollte beantwortbar machen:

- Macht es das Spiel lustiger?
- Bleibt die Runde kurz?
- Ist es verständlich?
- Ist es serverseitig validiert?
- Ist es config-getrieben, wo sinnvoll?
- Bricht es den Godot-Zukunftspfad nicht?

