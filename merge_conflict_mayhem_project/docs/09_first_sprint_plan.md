# 09 – First Sprint Plan

## Ziel des ersten Sprints

Eine erste spielbare Version, die intern getestet werden kann.

Nicht das Ziel:

- perfekte Grafik
- fertiger Godot-Client
- ausgefeiltes Balancing
- schöne Animationen

Hauptfrage:

> Lachen die Leute in der ersten Runde und wollen direkt nochmal spielen?

---

# 1. Sprint-Ziel

Am Ende des ersten Sprints soll möglich sein:

1. Server starten
2. Browser öffnen
3. Raum erstellen
4. Spieler joinen
5. Host startet Runde
6. Rollen werden verteilt
7. Spieler bewegen sich
8. Tasks können abgeschlossen werden
9. Saboteur kann Sabotagen auslösen
10. Spiel endet mit Gewinnerteam

---

# 2. Sprint-Scope

## Muss

- Monorepo
- Docker Compose
- Python FastAPI Backend
- WebSocket-Verbindungen
- Lobby
- GameRoom
- GameState
- Spielertabelle
- Rollenverteilung
- einfache Map
- WASD-Input
- Spielerpositionen
- GameState-Broadcast
- Hold Tasks
- 3 Sabotagen
- Timer
- Win/Lose-Logik
- Endscreen

## Sollte

- Eventfeed
- Taskliste
- globale Werte im UI
- einfache Nametags
- private Rollenanzeige

## Kann

- erste Placeholder-Icons
- einfache Sounds
- einfache Map-Labels

## Nicht im Sprint

- Godot
- Accounts
- Persistenz
- Voicechat
- Matchmaking
- KI-generierte Inhalte
- finale Assets
- komplexe Minispiele

---

# 3. Tasks Backend

## Backend Setup

- FastAPI App
- WebSocket Endpoint
- Uvicorn Start
- Dockerfile / Docker Compose

## GameRoom

- Raumcode erzeugen
- Spieler joinen
- Host bestimmen
- Spieler verlassen

## Rollenverteilung

- 4–6 Spieler: 1 Vibe Coder
- Rest: Developer / DevOps / AI Engineer
- private Role Message

## GameState

- phase
- players
- tasks
- releaseProgress
- pipelineStability
- incidentCount
- coffeeLevel
- remainingSeconds
- winner
- events

## Tick Loop

- Timer reduzieren
- Movement anwenden
- Task-Fortschritt berechnen
- Sabotage-Cooldowns berechnen
- Win Conditions prüfen
- GameState broadcasten

## Tasks

- Unit Tests fixen
- Pull Request reviewen
- Deployment reparieren
- Kaffee auffüllen
- Legacy-Service beruhigen

## Sabotagen

- CI/CD Rot
- Kaffee leer
- Mandatory Meeting

---

# 4. Tasks Frontend

## Lobby

- Raumcode eingeben
- Name eingeben
- Join Button
- Spielerliste anzeigen
- Start Button für Host

## Spielansicht

- Map anzeigen
- Spieler anzeigen
- eigene Figur steuern
- andere Spieler anzeigen
- Nametags anzeigen

## HUD

- Top Bar mit globalen Werten
- Taskliste links
- Eventfeed rechts
- eigene Rolle anzeigen
- Sabotagebuttons nur für Chaos-Agenten

## Interaktion

- Task starten
- Task halten
- Task-Fortschritt anzeigen
- Sabotage auslösen

## Endscreen

- Gewinnerteam anzeigen
- Rollen aufdecken
- einfache Statistik

---

# 5. Testplan

## Technische Tests

- Kann ein Raum erstellt werden?
- Können mehrere Spieler joinen?
- Werden Rollen korrekt verteilt?
- Bleibt die Rolle geheim?
- Wird GameState synchronisiert?
- Funktionieren Tasks?
- Funktionieren Sabotagen?
- Endet das Spiel korrekt?

## Spieltests

- Versteht man das Ziel?
- Sind die Räume erkennbar?
- Ist die Bewegung schnell genug?
- Sind Tasks zu lang oder zu kurz?
- Sind Sabotagen sichtbar?
- Ist der Saboteur zu stark oder zu schwach?
- Dauert die Runde maximal 10 Minuten?
- Entstehen Verdächtigungen?

---

# 6. Erste Balancing-Werte

| Wert | Startwert |
|---|---:|
| Rundendauer | 600 s |
| Release Progress Start | 0 % |
| Pipeline Stability Start | 100 % |
| Coffee Level Start | 100 % |
| Incident Count Start | 0 |
| CI/CD Rot Damage | -20 Pipeline |
| Kaffee leer Effekt | Coffee = 0 |
| Mandatory Meeting Slow | 5 s |
| Taskdauer | 4–7 s |
| Release Reward pro Task | 8–12 % |

---

# 7. Erste interne Demo

Ablauf:

1. 5–6 Leute einladen
2. kurze Erklärung: „Release-Team vs. geheimer Saboteur“
3. Runde starten
4. möglichst wenig erklären
5. beobachten, wo Spieler hängen bleiben
6. nach Runde fragen:
   - Was war lustig?
   - Was war unklar?
   - War die Runde zu lang?
   - War Sabotage sichtbar genug?
   - Wollt ihr nochmal spielen?

---

# 8. Definition of Done für Sprint 1

Sprint 1 ist fertig, wenn:

- mindestens 4 Spieler eine Runde spielen können
- Spielzustand synchron bleibt
- Release-Team gewinnen kann
- Chaos-Agent gewinnen kann
- Tasks und Sabotagen funktionieren
- Endscreen erscheint
- README erklärt, wie man lokal startet

