# Merge Conflict Mayhem: Lunch Break Edition

## Master-Dokument für ein internes Multiplayer-Spiel

**Arbeitstitel:** Merge Conflict Mayhem  
**Untertitel:** Lunch Break Edition  
**Genre:** Social Deduction, Koop-Chaos, Dev-Humor  
**Zielgruppe:** internes Entwickler-, KI- und IT-Team  
**Rundenlänge:** 8–12 Minuten  
**Spielerzahl MVP:** 4–6 Spieler  
**Spielerzahl langfristig:** 4–12 Spieler  
**Technischer Leitgedanke:** Python entscheidet. Der Client zeigt nur an.  
**Langfristiges Ziel:** Godot-Client mit Python-Backend.

---

## Inhalt dieses ZIP-Pakets

Dieses Paket enthält alle zentralen Markdown-Dokumente, um das Projekt mit dem Team zu diskutieren und anschließend mit OpenCode zu starten.

```text
merge_conflict_mayhem_project/
  MASTER_Merge_Conflict_Mayhem.md
  docs/
    01_game_design.md
    02_technical_architecture.md
    03_websocket_protocol.md
    04_opencode_prompts.md
    05_asset_pack_master_prompt.md
    06_asset_checklist.md
    07_visual_direction.md
    08_roadmap_and_contribution.md
    09_first_sprint_plan.md
```

---

# 1. Hintergrund und Zielbild

**Merge Conflict Mayhem** ist ein internes Multiplayer-Spiel für Tech-Teams. Die Spieler befinden sich in einem Softwarebüro kurz vor einem wichtigen Release. Die meisten Spieler gehören zum Release-Team und müssen gemeinsam Aufgaben erledigen, um das Release erfolgreich abzuschließen.

Gleichzeitig befinden sich unter ihnen ein oder mehrere geheime Chaos-Agenten. Diese geben vor zu helfen, sabotieren aber heimlich das Release, erzeugen Production Incidents, machen die CI/CD-Pipeline kaputt, starten sinnlose Meetings oder legen die Kaffeemaschine lahm.

Der Kern des Spiels lautet:

> Das Team muss in 10 Minuten releasen, aber irgendjemand macht absichtlich alles kaputt.

Das Spiel soll:

- kurzweilig sein
- remote funktionieren
- in der Mittagspause spielbar sein
- mit Humor und Dev-Insidern funktionieren
- firmenintern offen weiterentwickelt werden
- zunächst im Browser spielbar sein
- später einen Godot-Client erhalten
- über ein Python-Backend gesteuert werden

---

# 2. Spielgefühl

Das gewünschte Spielgefühl ist eine Mischung aus:

- Among Us
- DevOps-Chaos
- Office-Humor
- Release-Stress
- isometrischem Mini-Game
- KI-Agenten-Wahnsinn
- internen Running Gags

Typische Spielsituationen:

- „Wer hat gerade auf main gepusht?“
- „Warum ist die Pipeline wieder rot?“
- „Wieso ist der Kunde plötzlich im Sprint?“
- „Der KI-Agent hat eigenständig optimiert.“
- „Das war nur ein kleiner Refactor.“
- „Die Tests sind flaky, aber nur manchmal.“
- „Funktioniert bei mir.“

Das Spiel soll absurd, aber klar spielbar sein.

---

# 3. Kernmechanik

Es gibt zwei Seiten:

## Release-Team

Die Mehrheit der Spieler gehört zum Release-Team. Ziel ist es, den Release erfolgreich abzuschließen.

Aufgaben:

- Tasks erledigen
- Sabotagen reparieren
- Incidents reduzieren
- Pipeline stabilisieren
- verdächtige Spieler beobachten
- Chaos-Agenten per Voting enttarnen

## Chaos-Agenten

Ein oder mehrere Spieler sind geheime Saboteure.

Aufgaben:

- unauffällig sabotieren
- Vertrauen gewinnen
- falsche Verdächtigungen streuen
- Tasks vortäuschen
- Meetings taktisch nutzen
- Pipeline und Teamkoordination stören

---

# 4. Rundenablauf

1. **Lobby:** Spieler treten per Link oder Raumcode bei.
2. **Rollenverteilung:** Der Server verteilt Rollen geheim.
3. **Spielphase:** Spieler erledigen Tasks oder sabotieren.
4. **Emergency Meeting:** Spieler können im War Room ein Meeting auslösen.
5. **Voting:** Spieler stimmen ab, wer entfernt wird.
6. **Endscreen:** Rollen werden aufgedeckt, Gewinnerteam und Awards erscheinen.

---

# 5. Win Conditions

## Release-Team gewinnt, wenn:

- `releaseProgress >= 100`
- oder alle Chaos-Agenten entfernt wurden

## Chaos-Agenten gewinnen, wenn:

- `pipelineStability <= 0`
- oder der Timer abläuft
- oder später: zu viele Incidents offen sind

Für den MVP reichen drei Bedingungen:

```text
Release Progress >= 100  -> Release-Team gewinnt
Pipeline Stability <= 0  -> Chaos-Agent gewinnt
Timer abgelaufen          -> Chaos-Agent gewinnt
```

---

# 6. Globale Spielwerte

- **Release Progress:** Fortschritt Richtung Release, 0–100 %
- **Pipeline Stability:** Stabilität der Infrastruktur, 0–100 %
- **Incident Count:** offene Production Incidents
- **Coffee Level:** Humorwert, beeinflusst später Geschwindigkeit oder Taskdauer
- **Remaining Seconds:** Rundentimer, MVP: 600 Sekunden

---

# 7. MVP-Map

Für den ersten Prototypen genügt eine einfache Top-Down-/Isometrie-Map mit sechs Räumen.

```text
+------------------+------------------+------------------+
|   Open Space     |   Meetingraum    |      Küche       |
+------------------+------------------+------------------+
|   Serverraum     |     War Room     |  Legacy-Keller   |
+------------------+------------------+------------------+
```

## Räume

- **Open Space:** Unit Tests, Pull Requests, Merge Conflicts
- **Serverraum:** Deployments, Logs, Pipeline, Server
- **Meetingraum:** Scope Creep, Agenda, Kundenanforderungen
- **Küche:** Kaffee, Team-Moral, Utility-Buffs
- **Legacy-Keller:** alte Systeme, Cronjobs, grüne CRT-Terminals
- **War Room:** Status, Emergency Meetings, Dashboard

---

# 8. MVP-Rollen

## Release-Team

### Developer
Standardrolle. Erledigt normale Tasks und erhöht Release Progress.

### DevOps Engineer
Repariert Pipeline und Infrastruktur schneller.

### AI Engineer
Kann später Auto-Fix-Bots einsetzen. Im MVP zunächst normale Teamrolle.

## Chaos-Agent

### Vibe Coder
Schreibt sehr schnell Code, aber niemand weiß genau, was er tut. Kann Sabotagen auslösen.

---

# 9. MVP-Tasks

| Task | Raum | Typ | Effekt |
|---|---|---|---|
| Unit Tests fixen | Open Space | Hold Task | +10 % Release Progress |
| Pull Request reviewen | Open Space | Hold Task | +8 % Release Progress |
| Deployment reparieren | Serverraum | Hold Task | +15 % Pipeline Stability |
| Kaffee auffüllen | Küche | Hold Task | Coffee Level = 100 % |
| Legacy-Service beruhigen | Legacy-Keller | Hold Task | -1 Incident |
| Logs analysieren | Serverraum | Hold Task | -1 Incident oder +5 % Pipeline Stability |
| Scope reduzieren | Meetingraum | Hold Task | entfernt Fake Customer Request |
| Release Notes schreiben | War Room | Hold Task | +12 % Release Progress |

---

# 10. MVP-Sabotagen

## CI/CD Rot

Effekt:

- Pipeline Stability -20 %
- Release Progress wird kurz blockiert
- Eventfeed: „Die Pipeline ist rot. Niemand weiß warum.“

Cooldown: 60 Sekunden

## Kaffee leer

Effekt:

- Coffee Level auf 0 %
- Spieler bewegen sich langsamer
- Eventfeed: „Die Kaffeemaschine ist offline. Kritische Infrastruktur betroffen.“

Cooldown: 75 Sekunden

## Mandatory Meeting

Effekt:

- Spieler werden kurz verlangsamt
- Eventfeed: „Ein Meeting ohne Agenda wurde gestartet.“

Cooldown: 90 Sekunden

---

# 11. Technische Architektur

Die zentrale Architekturentscheidung lautet:

> Das Python-Backend ist autoritativ. Der Client rendert nur und sendet Inputs.

## Phase 1

```text
Python Backend <-> Browser/Phaser Client
```

## Phase 2

```text
Python Backend <-> Godot Client
```

## Zielarchitektur

```text
                 ┌────────────────────────────┐
                 │        Python Backend       │
                 │ FastAPI / WebSockets        │
                 │                            │
                 │ - Lobby                     │
                 │ - Rollenverteilung          │
                 │ - Game State                │
                 │ - Tasks                     │
                 │ - Sabotagen                 │
                 │ - Voting                    │
                 │ - Win/Lose                  │
                 └─────────────┬──────────────┘
                               │
                 WebSocket JSON Protocol
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                             │
┌───────▼────────┐                           ┌────────▼────────┐
│ Browser Client │                           │   Godot Client   │
│ JS / Phaser    │                           │ GDScript         │
│ MVP / Intranet │                           │ schöner Client   │
└────────────────┘                           └─────────────────┘
```

---

# 12. Empfohlener Stack

## Backend

- Python
- FastAPI
- WebSockets
- Pydantic
- Uvicorn
- pytest

## MVP-Frontend

- Vite
- Plain JavaScript
- Phaser oder Canvas
- HTML/CSS
- WebSocket-Client

## Späterer Hauptclient

- Godot
- GDScript
- WebSocket-Verbindung zum Python-Backend
- gleiches JSON-Protokoll

---

# 13. Repository-Struktur

```text
merge-conflict-mayhem/
  README.md
  docker-compose.yml
  .gitignore

  docs/
    game-design.md
    protocol.md
    roadmap.md
    contribution-guide.md

  backend/
    pyproject.toml
    app/
      main.py
      websocket.py
      game/
        models.py
        game_room.py
        game_state.py
        roles.py
        tasks.py
        sabotages.py
        voting.py
        tick_loop.py
      config/
        rooms.json
        tasks.json
        roles.json
        sabotages.json
        event_texts.json
      tests/

  frontend/
    package.json
    index.html
    src/
      main.js
      websocket.js
      game/
        scene.js
        renderer.js
        input.js
        ui.js
      styles.css
```

---

# 14. OpenCode-Startprompt

```text
Wir entwickeln ein internes Multiplayer-Spiel namens "Merge Conflict Mayhem: Lunch Break Edition".

Wichtige Architekturentscheidung:
Das Python-Backend ist die autoritative Quelle für die gesamte Spiellogik. Der erste Client ist ein einfacher Browser-Client, aber später soll ein Godot-Client denselben Server nutzen können.

Bitte baue deshalb das System client-agnostisch:
- Keine Spiellogik ausschließlich im Frontend.
- Alle Regeln liegen im Backend.
- Kommunikation ausschließlich über ein dokumentiertes JSON-WebSocket-Protokoll.
- Der Browser-Client ist nur eine einfache Referenzimplementierung.
- Das Protokoll soll später von einem Godot/GDScript-Client einfach implementierbar sein.

Technologie:
- Backend: Python, FastAPI, WebSockets, Pydantic
- Frontend MVP: Vite + Plain JavaScript oder Phaser
- Späterer Zielclient: Godot mit GDScript
- Deployment: Docker Compose

Bitte erstelle:
1. Ein Python-Backend mit Game Rooms, Lobby, Rollenverteilung, Tasks, Sabotagen, Timer und Win/Lose-Logik.
2. Ein klar dokumentiertes WebSocket-Protokoll in docs/protocol.md.
3. Einen einfachen Browser-Client als Referenzclient.
4. Eine saubere Trennung zwischen Backend-Game-Logik und Client-Rendering.
5. JSON-Konfigurationsdateien für Räume, Tasks, Rollen, Sabotagen und Eventtexte.
6. README mit Startanleitung.

MVP:
- Lobby per Raumcode
- Spielername
- Host startet Spiel
- Rollen: developer, devops, ai_engineer, vibe_coder als Chaos-Agent
- Map mit sechs Räumen: Open Space, Serverraum, Meetingraum, Küche, Legacy-Keller, War Room
- Bewegung per WASD
- Hold-Tasks
- Sabotagen: CI/CD Rot, Kaffee leer, Mandatory Meeting
- globale Werte: releaseProgress, pipelineStability, incidentCount, coffeeLevel, remainingSeconds
- Endbedingungen:
  - releaseProgress >= 100: Release-Team gewinnt
  - pipelineStability <= 0: Chaos-Agent gewinnt
  - Timer abgelaufen: Chaos-Agent gewinnt
```

---

# 15. Asset-Pack-Kurzfassung

Für den ersten MVP braucht ihr nicht 200 Assets. Ziel: maximal 40–60 Assets.

## P0 Assets

### Branding

- Hauptlogo
- kleines HUD-Logo

### UI

- Top HUD Panel
- Task Sidebar
- Eventfeed Sidebar
- Popup Panel
- Stat Cards
- Buttons

### Icons

- Release Progress
- Pipeline Stability
- Incidents
- Coffee
- Timer
- Fix Unit Tests
- Review Pull Request
- Refill Coffee
- Calm Legacy System
- CI/CD Red
- Coffee Outage
- Mandatory Meeting
- Emergency Meeting
- Vote
- Skip Vote

### World

- Boden-Tiles
- Wände
- Türen
- Schreibtisch
- Monitor
- Server Rack
- Kaffeemaschine
- Meeting Table
- Retro Terminal
- Dashboard Screen
- einfache Charakterfigur
- Nametag
- Task Marker
- Sabotage Marker

---

# 16. Visual Direction

## Marketing-Cover

- hochpoliert
- chaotisch
- comicartig
- viele Details
- geeignet zum Team-Pitch

## Realistischer MVP-Look

- simple isometrische Tilemap
- sechs klare Räume
- wenige Props
- wiederverwendbare Assets
- kleine Figuren
- UI mit klaren Panels
- Task- und Sabotage-Icons

Das Cover ist der Nordstern. Der MVP-Look ist die realistische erste Umsetzung.

---

# 17. Erste Erfolgskriterien

Das Projekt ist erfolgreich, wenn nach dem ersten internen Test folgende Aussagen stimmen:

- Eine Runde kann ohne Erklärung schnell gestartet werden.
- Die Spieler verstehen innerhalb von 1–2 Minuten, was sie tun müssen.
- Es entstehen Verdächtigungen.
- Die Sabotagen sind sichtbar und lustig.
- Die Runde dauert nicht zu lange.
- Die Spieler lachen.
- Jemand sagt: „Noch eine Runde.“

Das wichtigste Erfolgskriterium ist nicht perfekte Grafik, sondern:

> Macht das Spiel in Runde 1 schon Spaß?

