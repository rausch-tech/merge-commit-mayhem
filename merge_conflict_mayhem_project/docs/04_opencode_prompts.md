# 04 – OpenCode Prompts

Dieses Dokument enthält copy-paste-fähige Prompts für den Start mit OpenCode.

---

# Prompt 1 – Projektgrundgerüst

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

Bitte erstelle ein Monorepo mit folgender Struktur:

merge-conflict-mayhem/
  README.md
  docker-compose.yml
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
  docs/
    protocol.md
    game-design.md
    contribution-guide.md

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

Wichtig:
- Implementiere zuerst einen einfachen, aber lauffähigen Prototyp.
- Keine perfekte Grafik.
- Keine Authentifizierung.
- Kein Persistenzlayer.
- Fokus auf Spielbarkeit.
- README mit Startanleitung für lokale Entwicklung.
```

---

# Prompt 2 – Erster vollständiger Game Loop

```text
Erweitere Merge Conflict Mayhem um den ersten vollständigen Game Loop.

Implementiere:

1. Lobby-Phase:
   - Spieler joinen
   - Spieler sehen alle Teilnehmer
   - Host startet das Spiel

2. Rollenverteilung:
   - Bei 4-6 Spielern genau ein Chaos-Agent
   - Rolle bleibt für andere Spieler geheim
   - Spieler sieht eigene Rolle auf dem Screen

3. Playing-Phase:
   - Timer startet bei 10 Minuten
   - Tasks erscheinen in bestimmten Räumen
   - Spieler können Tasks ausführen, wenn sie in der Nähe sind
   - Hold-Task mit Fortschrittsbalken

4. Sabotage:
   - Nur Chaos-Agent sieht Sabotage-Buttons
   - CI/CD Rot reduziert pipelineStability
   - Kaffee leer setzt coffeeLevel auf 0 und reduziert Movement Speed
   - Mandatory Meeting verlangsamt alle Spieler kurzzeitig

5. Win/Lose:
   - Release-Team gewinnt bei releaseProgress >= 100
   - Chaos-Agent gewinnt bei pipelineStability <= 0 oder Timer-Ende

6. Eventfeed:
   - Zeige lustige Events an, z. B.
     "Die Pipeline ist rot. Niemand weiß warum."
     "Die Kaffeemaschine ist offline."
     "Ein KI-Agent hat eigenständig refactored."

7. Endscreen:
   - Gewinnerteam anzeigen
   - Rollen aufdecken
   - kleine Statistik anzeigen:
     - erledigte Tasks
     - ausgelöste Sabotagen
     - entfernte Spieler
```

---

# Prompt 3 – Emergency Meetings und Voting

```text
Implementiere Emergency Meetings und Voting für Merge Conflict Mayhem.

Anforderungen:

1. Jeder Spieler hat ein Emergency Meeting pro Runde.
2. Ein Meeting kann nur im War Room ausgelöst werden.
3. Während eines Meetings pausiert das normale Spiel.
4. Alle Spieler sehen eine Meeting-Ansicht mit:
   - Liste aller Spieler
   - Button zum Abstimmen
   - Button "Skip"
5. Nach 60 Sekunden endet das Voting automatisch.
6. Spieler mit den meisten Stimmen wird aus dem Spiel entfernt.
7. Bei Gleichstand wird niemand entfernt.
8. Entfernte Spieler können nicht mehr Tasks erledigen und nicht sabotieren.
9. Wenn alle Chaos-Agenten entfernt sind, gewinnt das Release-Team.
10. Ergänze lustige Meeting-Titel:
   - "Wer hat auf main gepusht?"
   - "Warum sind die Tests rot?"
   - "Wieso ist der Kunde im Sprint?"
   - "Wer hat den KI-Agenten unbeaufsichtigt gelassen?"
```

---

# Prompt 4 – Godot-ready Client-Agnostic Refactor

```text
Bitte überprüfe die aktuelle Architektur von Merge Conflict Mayhem darauf, dass später ein Godot-Client angebunden werden kann.

Ziele:
- Alle Spiellogik muss im Python-Backend liegen.
- Der Browser-Client darf nur rendern und Inputs senden.
- Das WebSocket-Protokoll muss vollständig in docs/protocol.md dokumentiert sein.
- Der Server soll keine browser-spezifischen Annahmen machen.
- Alle Server-Events müssen JSON-kompatibel und einfach in Godot/GDScript parsebar sein.

Bitte liefere:
1. Eine kurze Analyse der aktuellen Architektur.
2. Konkrete Refactorings, falls Logik noch im Frontend liegt.
3. Eine aktualisierte protocol.md.
4. Ein Beispiel, wie ein Godot-Client die wichtigsten Events implementieren würde.
```

---

# Prompt 5 – MVP UI mit Platzhaltern

```text
Baue für Merge Conflict Mayhem ein funktionales MVP-UI im Browser-Client.

Das UI soll zunächst mit Platzhalter-Assets funktionieren und später leicht durch echte Assets ersetzt werden können.

UI-Elemente:
1. Top HUD:
   - Release Progress
   - Pipeline Stability
   - Incidents
   - Coffee
   - Timer
2. Linke Taskliste:
   - Task-Icon
   - Task-Titel
   - Raum
   - Checkmark bei abgeschlossenem Task
3. Rechte Eventfeed-Spalte:
   - Zeit
   - Event-Titel
   - kurzer Text
   - Severity-Farbe
4. Untere Actionbar:
   - Interact
   - Report
   - Emergency Meeting
   - Vote / Skip im Meeting
5. Meeting Overlay:
   - Meeting-Titel
   - Spieler-Liste
   - Vote-Buttons
   - Skip-Button
   - Countdown
6. Endscreen:
   - Gewinnerteam
   - Rollenaufdeckung
   - Statistik pro Spieler

Wichtig:
- Daten sollen aus dem GameState kommen.
- UI soll responsive genug für 16:9 sein.
- Noch keine finalen Grafiken notwendig.
- Nutze klare CSS-Klassen und eine zentrale Farbpalette.
```

---

# Prompt 6 – JSON Config Loader

```text
Erweitere das Backend so, dass zentrale Spielinhalte aus JSON-Konfigurationsdateien geladen werden.

Dateien:
- backend/app/config/rooms.json
- backend/app/config/tasks.json
- backend/app/config/roles.json
- backend/app/config/sabotages.json
- backend/app/config/event_texts.json

Anforderungen:
1. Lade die Konfiguration beim Serverstart.
2. Validiere die Daten mit Pydantic-Modellen.
3. Gib klare Fehlermeldungen aus, wenn eine Config ungültig ist.
4. GameRoom soll Tasks, Rollen und Sabotagen aus den Config-Dateien initialisieren.
5. Ergänze Tests für valide und invalide Configs.
6. Dokumentiere in docs/contribution-guide.md, wie Mitarbeitende neue Tasks oder Sabotagen hinzufügen können.
```

