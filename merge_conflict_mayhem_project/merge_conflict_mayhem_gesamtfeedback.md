# Merge Conflict Mayhem — Gesamtfeedback & Entwicklungs-Briefing

**Stand:** 2026-04-26  
**Zielgruppe:** Claude Code / Entwicklerteam  
**Kontext:** Social-Deduction-Multiplayer-Spiel für Tech-Teams, aktuell Web-Prototyp vor Godot-Migration  

---

## 0. Executive Summary

Das Spiel hat bereits einen starken Kern: kurze Social-Deduction-Runden, Tech-/DevOps-Humor, Tasks, Sabotagen, Vents, Meetings, Voting, Ghosts und Map-Editor. Der nächste große Qualitätssprung entsteht nicht primär durch mehr Content, sondern durch **bessere soziale Lesbarkeit**:

- Spieler brauchen bessere Gründe, warum sie wo waren.
- Chaos-Agenten brauchen mehr Risiko beim Sabotieren.
- Release-Team-Spieler sollten unterschiedliche Rollen, Aufgaben und Stärken haben.
- Kaffee sollte von einem Witz zu einer echten Team-Ressource werden.
- Meetings brauchen mehr Gesprächsstoff, aber keine automatischen Beweise.
- Endscreen und Metriken sollten die Runde erzählbar und balancierbar machen.

Die wichtigste Designrichtung:

> Merge Conflict Mayhem sollte sich weniger wie „alle laufen herum und machen generische Tasks“ anfühlen und mehr wie „ein echtes Release-Team mit unterschiedlichen Spezialisten versucht, trotz Chaos-Agenten ein Release zu retten“.

---

## 1. Design-Prinzipien

### 1.1 Social Deduction zuerst

Das Spiel ist kein Tech-Skill-Spiel, sondern ein Social-Deduction-Spiel im Tech-Setting. Alle neuen Features sollten daher mindestens eines dieser Ziele erfüllen:

- bessere Alibis ermöglichen
- Verdacht erzeugen
- Diskussionen in Meetings verbessern
- Risiko für Chaos-Agenten erhöhen
- Teamkoordination fördern
- Situationen erzeugen, über die Spieler nach der Runde lachen

Nicht jedes Feature, das thematisch lustig ist, ist automatisch gutes Gameplay. Entscheidend ist: **Erzeugt es beobachtbares Verhalten?**

### 1.2 Server bleibt autoritativ

Alle neuen Systeme sollten der bestehenden Architektur folgen:

> Python entscheidet, der Client zeigt nur an.

Das gilt besonders für:

- Rollenverteilung
- Task-Zuweisung
- Task-Progress
- Sabotage-Trigger
- Distanzen zu Terminals / Objekten
- Kaffee-Effekte
- Cooldowns
- Meeting-Informationen
- Voting
- Ghost-Interaktionen

Der Client darf UI und Animationen anzeigen, aber keine Spiellogik entscheiden.

### 1.3 Keine harten Sackgassen

Spezialisierung ist gut. Harte Blockaden sind gefährlich.

Schlechte Variante:

> Nur DevOps kann CI/CD reparieren. DevOps stirbt. Release-Team kann nicht mehr gewinnen.

Bessere Variante:

> DevOps repariert CI/CD schnell. Andere können es auch, aber langsamer. Ghosts können eigene Tasks weiter erledigen. Optional können Tasks nach Tod neu verteilt werden.

### 1.4 Hinweise statt Beweise

Fähigkeiten und Meeting-Informationen sollten Verdacht erzeugen, aber nicht automatisch den Täter beweisen.

Gut:

> „In den letzten 20 Sekunden gab es eine verdächtige Aktion im Server Room.“

Schlecht:

> „Sven ist Chaos-Agent.“

---

## 2. Priorisierte Roadmap

### P0 — Kernloop reparieren und schärfen

1. Sabotagen an physische Sabotage-Objekte binden.
2. Remote-Sabotage von überall entfernen.
3. Sabotage-Trigger serverseitig mit Distanz, Rolle, Alive-State und Cooldown validieren.
4. Chaos-Agenten bekommen Fake-Tasks / Fake-Task-Liste.
5. Alle Hold-E-Tasks mittelfristig in Mini-Games umbauen.
6. Meeting-Screen mit besserem Kontext verbessern.

### P1 — Rollen, persönliche Tasks und Kaffee

1. Persönliche Task-Backlogs pro Release-Spieler.
2. Release-Rollen mit Stärken, Schwächen und aktiven Fähigkeiten.
3. Kaffee als persönlicher Wert `coffeeEnergy`.
4. Rollenabhängige Kaffee-Effekte.
5. Task-Speed-Modifikatoren je Rolle und Task-Kategorie.
6. Caffeine Collector als Support-Rolle.

### P2 — Runde erzählbarer machen

1. Endscreen mit Rundenstory und Fun-Stats.
2. Eventfeed-Texte ausbauen.
3. Ghost-Beitrag sichtbarer machen.
4. Playtest-Metriken exportieren.
5. Map-Heatmaps und Balance-Daten erfassen.

### P3 — Content und Godot-Polish

1. Neue Maps.
2. Erweiterte Rollen.
3. Sounds, Animationen, bessere Assets.
4. Godot-Client als polished Primary-Client.
5. KI-generierte Postmortems / Eventtexte optional später.

---

# Teil A — Chaos-Agenten, Sabotage und Angreifer-Design

---

## 3. Problem: Sabotagen von überall schwächen das Spiel

Aktueller beobachteter Fehler:

> Der Vibe Coder konnte überall stehen und seine Störattacken auslösen.

Das ist nicht nur ein technischer Bug, sondern ein grundlegendes Designproblem.

Wenn Chaos-Agenten aus beliebiger Position sabotieren können:

- gibt es zu wenig Risiko für Chaos
- Spieler können keine Orte absichern
- Beobachtungen werden wertlos
- Alibis werden zu leicht
- Meetings haben weniger Substanz
- Map-Design verliert Bedeutung

Social Deduction braucht sichtbares Verhalten:

```text
„Ich habe Sven am CI-Terminal gesehen.“
„Direkt danach wurde CI/CD rot.“
„Sven sagt, er hat Deployment repariert. Glauben wir ihm?“
```

Genau diese Art von Gespräch entsteht nur, wenn Sabotage physisch an Orte gebunden ist.

---

## 4. Ziel: Sabotage-Objekte statt globale Buttons

Chaos-Agenten sollten Sabotagen nur an passenden Objekten auslösen können.

Nicht:

```text
Chaos klickt irgendwo auf „Slack Down“.
```

Sondern:

```text
Chaos steht am War-Room-Comms-Panel und löst dort „Slack Down“ aus.
```

## 4.1 Sabotage-Objekte

Beispiele:

| Objekt | Raum | Mögliche Sabotagen |
|---|---|---|
| CI-Konsole | Server Room | CI/CD Rot, Flaky Tests |
| Git-Terminal | Open Space / Dev Area | Merge Conflict Storm, Hotfix auf main |
| Kaffeemaschine | Kitchen | Kaffee leer |
| Kalender-Screen | Meeting Room | Mandatory Meeting, Legal Review |
| CRM-/Support-Terminal | War Room | Fake Customer Request |
| Monitoring-Konsole | Server Room | PagerDuty-Storm |
| Slack-/Comms-Panel | War Room | Slack-Down |
| Legacy-Konsole | Legacy Basement | Legacy Panic, Dependency Hell |

## 4.2 Servervalidierung

Bei jedem Sabotage-Trigger prüfen:

```text
- player is alive
- player is chaos team
- sabotage is available for player role
- sabotage cooldown is ready
- player is within interaction radius of a valid sabotage object
- sabotage object supports requested sabotage type
- current game phase allows sabotage
```

Pseudo-Struktur:

```json
{
  "sabotageObjectId": "ci_console_01",
  "position": { "x": 1220, "y": 840 },
  "radius": 50,
  "supportedSabotages": ["ci_red", "flaky_tests"],
  "visibleToAll": true
}
```

---

## 5. Sabotage muss wie Arbeit aussehen

Wichtig: Andere Spieler sollten von außen nicht direkt sehen, ob jemand sabotiert oder eine Task macht.

Gute UI nach außen:

```text
„Sven arbeitet am Terminal“
```

Schlechte UI:

```text
„Sven sabotiert gerade CI/CD“
```

Das erzeugt die richtige Spannung:

```text
„Ich war am CI-Terminal, weil ich Deployment repariert habe.“
„Komisch, direkt danach war CI rot.“
```

## 5.1 Interaktionsdauer

Sabotage sollte nicht immer instant sein.

Je stärker die Sabotage, desto riskanter der Trigger:

| Sabotage-Stärke | Beispiel | Trigger-Risiko |
|---|---|---|
| Klein | Flaky Tests | kurzer Hack, 0.5–1 s |
| Mittel | Merge Conflict Storm | 1–1.5 s Interaktion |
| Groß | PagerDuty-Storm / Slack-Down | 2 s Interaktion, auffälligere Animation/Sound |

---

## 6. Bewertung der aktuellen Sabotagen

### 6.1 CI/CD Rot

Aktuell:

```text
pipelineStability sofort -20
```

Bewertung:

- thematisch sehr passend
- aber als reiner Sofort-Abzug etwas stumpf
- sollte mehr Counterplay bekommen

Empfehlung:

```text
Trigger: CI-Konsole im Server Room
Effekt: Pipeline geht rot, Release-Progress pausiert oder Stability drainiert langsam
Repair: CI-Repair-Mini-Game im Server Room
```

Optional:

- Sofort kleiner Schaden, danach aktiver Zustand bis Repair
- klarer Alert für alle
- hoher Cooldown

### 6.2 Flaky Tests

Aktuell:

```text
pipelineStability -10
```

Problem:

- zu ähnlich zu CI/CD Rot

Bessere Mechanik:

```text
Effekt: Die nächsten 1–2 Tasks geben nur 50 % Progress
oder lösen ein kurzes Zusatz-Mini-Game aus.
```

Repair:

```text
QA-/Test-Terminal: fehlerhafte Tests identifizieren
```

Dadurch fühlt sich Flaky Tests anders an als CI/CD Rot.

### 6.3 Merge Conflict Storm

Bewertung:

- thematisch sehr stark
- sollte stärker mit PR Review / Git-Terminal verbunden werden

Vorschlag:

```text
Trigger: Git-Terminal
Effekt: Release-Progress drainiert langsam
Repair: Merge-Conflict-Mini-Game
```

Mini-Game-Idee:

- Konfliktblöcke vergleichen
- richtige Version wählen
- inkompatible Änderungen entfernen

### 6.4 Kaffee leer

Bewertung:

- sehr gut
- sollte nicht an ein Terminal gebunden sein, sondern an die Kaffeemaschine

Vorschlag:

```text
Trigger: Kaffeemaschine in Kitchen
Effekt: Team-Kaffee oder individuelle coffeeEnergy sinkt
Repair: Kaffee-Mini-Game
```

Mit neuem Kaffee-System wird diese Sabotage wichtiger.

### 6.5 Mandatory Meeting

Bewertung:

- sehr passend für Tech-/Office-Humor
- sollte eher Consultant-/Scrum-/Process-Sabotage sein

Vorschlag:

```text
Trigger: Meeting-Room-Beamer oder Kalender-Screen
Effekt: Spieler laufen kurz langsamer oder Task-Interaktionen dauern länger
```

Nicht zu stark machen. Es soll nerven, aber nicht komplett lähmen.

### 6.6 Fake Customer Request

Aktuell:

```text
Incidents +20
```

Problem:

- möglicherweise zu abstrakt
- unklar, was Incidents konkret bewirken

Bessere Version:

```text
Effekt: Ein zusätzlicher Urgent-Support-Task erscheint.
Wenn nicht gelöst, sinkt Stability nach 30 Sekunden.
```

Repair-Mini-Game:

```text
Triage: Bug / Feature Request / Bedienfehler / Cache-Problem
```

### 6.7 PagerDuty-Storm

Bewertung:

- sehr starke Sabotage
- Sichtreduktion ist gut für Spannung und Kills
- braucht hohen Cooldown

Vorschlag:

```text
Trigger: Monitoring-Konsole
Effekt: Sichtweite reduziert
Repair: Server-Room-Panel
```

Balance-Hinweis:

- nicht zu häufig erlauben
- kurze Audio-/UI-Warnung
- eventuell Take-Down für 2 Sekunden nach Trigger blockieren, damit es nicht komplett unfair wirkt

### 6.8 Slack-Down

Bewertung:

- ebenfalls sehr stark
- blockiert Tasks und andere Sabotagen
- sollte strategische High-Impact-Sabotage bleiben

Vorschlag:

```text
Trigger: Slack-/Comms-Panel im War Room
Repair: War Room
Cooldown: lang
```

Optional:

- pro Chaos-Agent nur 1x pro Runde
- oder sehr langer Cooldown

---

## 7. Rollen-spezifische Chaos-Agenten

Nicht jeder Chaos-Agent sollte alle Sabotagen gleich gut können.

Ziel:

- Vibe Coder = Code-/CI-/Git-Chaos
- Rogue Consultant = Meetings, Scope, Fake Customer Requests
- Shadow Admin = Slack, PagerDuty, Zugriffs-/Infra-Sabotage

## 7.1 Vibe Coder

Passende Sabotagen:

```text
- Merge Conflict Storm
- Flaky Tests
- CI/CD Rot
- Dependency Hell
- Hotfix direkt auf main
- AI-generated Spaghetti Code
```

Weniger passend:

```text
- Kaffee leer
- Mandatory Meeting
- Slack-Down
- PagerDuty-Storm
```

Vibe Coder sollte am Git-/CI-/Dev-Terminal verdächtig sein.

## 7.2 Rogue Consultant

Passende Sabotagen:

```text
- Mandatory Meeting
- Fake Customer Request
- Legal Review
- Scope Creep
- PowerPoint Panic
```

Spielgefühl:

- sozial manipulativ
- stört Teamkoordination
- erzeugt Zusatzarbeit

## 7.3 Shadow Admin

Passende Sabotagen:

```text
- Slack-Down
- PagerDuty-Storm
- Access Revoked
- Firewall Surprise
- Monitoring Blindness
```

Spielgefühl:

- Infrastruktur-/System-Sabotage
- nutzt War Room / Server Room / Admin-Panels

---

## 8. Neue Sabotage-Ideen

### 8.1 Dependency Hell

```text
Trigger: Package-/Dev-Terminal
Effekt: technische Tasks dauern 30 % länger
Repair: kompatible Versionen auswählen
```

### 8.2 Hotfix direkt auf main

```text
Trigger: Git-Terminal
Effekt: kleiner Progress-Verlust + PR-Review kurz blockiert
Repair: Rollback-Mini-Game
```

### 8.3 AI-Spaghetti-Code

```text
Trigger: Vibe-Coding-Terminal
Effekt: ein Task bekommt zusätzliche verwirrende Anforderungen
Repair: schlechten AI-Code identifizieren
```

### 8.4 Broken Env Variables

```text
Trigger: Server-/Deploy-Konsole
Effekt: Deployment-Task blockiert
Repair: ENV-Keys korrekt zuordnen
```

### 8.5 Legal Review

```text
Trigger: Meeting-Room / Compliance-Terminal
Effekt: Tasks dauern temporär doppelt so lang oder Release-Progress pausiert kurz
Repair: Freigabeformular sortieren
```

### 8.6 Zoom-Anrufer

```text
Trigger: Meeting-Room
Effekt: zufälliger Spieler wird 8–10 Sekunden verlangsamt oder kann keine Tasks starten
```

Vorsicht: Nicht zu frustrierend machen.

---

# Teil B — Tasks und Mini-Games

---

## 9. Tasks als größter Spannungstreiber

Tasks sollten nicht nur Progress erzeugen. Sie sollten:

- Spieler verwundbar machen
- Positionen erklären
- Fake-Tasking ermöglichen
- Rollenidentität stärken
- kurze thematische Witze liefern

Aktuell gibt es bereits gute Mini-Game-Patterns:

```text
- Sequencing
- Pairing
- Timing
- Filter-by-Criterion
- Subset-by-Constraint
```

Die drei Hold-E-Tasks sollten als Nächstes umgebaut werden:

```text
- review_pr
- calm_legacy_service
- write_release_notes
```

---

## 10. Neue Mini-Games für bestehende Hold-E-Tasks

### 10.1 Pull Request reviewen

Mechanik:

```text
Diff Review / Fehler markieren
```

Spieler sieht 5–8 Code-Zeilen und muss 2 problematische Stellen markieren.

Beispiele:

```text
- Hardcoded API Key
- TODO: fix in production
- catch(Exception) {}
- SELECT * without LIMIT
- console.log("debug")
- works on my machine
```

Warum gut:

- thematisch perfekt
- schnell verständlich
- guter Developer-Task
- sehr gut für Fake-Task-Alibis

### 10.2 Legacy Service beruhigen

Mechanik:

```text
Stabilitäts-Balancing
```

Drei Werte müssen in den grünen Bereich:

```text
- CPU
- Memory
- Queue
```

Aber: Wenn man einen Wert verbessert, verschlechtert sich ein anderer leicht.

Warum gut:

- passt ins Legacy Basement
- erzeugt Stress
- guter Task für Legacy Oracle / DevOps

### 10.3 Release Notes schreiben

Mechanik:

```text
Drag & Drop / Kategorisieren
```

Commits müssen sortiert werden:

```text
- Feature
- Bugfix
- Breaking Change
- Known Issue
- Should not be mentioned publicly
```

Warum gut:

- lustig
- Meeting-/Scrum-/Developer-nah
- weniger techniklastig

---

## 11. Weitere Task-Ideen

### 11.1 Jira-Ticket finden

Mechanik:

```text
Suche aus einer Liste das einzige Ticket mit sinnvollem Titel.
```

Beispiele:

```text
- Fix bug
- Important thing
- Customer says it is broken
- Login fails when token expired
```

### 11.2 Monitoring Alert ernst nehmen

Mechanik:

```text
Filtere echte Alerts von Noise.
```

### 11.3 Docker Compose starten

Mechanik:

```text
Services in richtiger Reihenfolge starten.
```

### 11.4 Excel aus der Hölle importieren

Mechanik:

```text
Falsche Spalten erkennen / Mapping setzen.
```

### 11.5 Kundenbug reproduzieren

Mechanik:

```text
Schritte in richtiger Reihenfolge anklicken.
```

### 11.6 API-Key rotieren

Mechanik:

```text
Alten Key deaktivieren, neuen erzeugen, Service neu starten.
```

---

## 12. Neue Mini-Game-Patterns

Neben bestehenden Patterns könnten diese ergänzt werden:

### 12.1 Memory Replay

```text
Kurze Sequenz merken und wiederholen.
```

Passt für:

- Deployment Steps
- Incident Timeline
- Reproduction Steps

### 12.2 Drag-Reorder

```text
Elemente in richtige Reihenfolge bringen.
```

Passt für:

- Release Notes
- Deployment Pipeline
- Customer Bug Reproduction

### 12.3 Classification

```text
Einträge in Kategorien sortieren.
```

Passt für:

- Logs
- Tickets
- Release Notes
- Incidents

### 12.4 Balance / Stabilize

```text
Regler in grünem Bereich halten.
```

Passt für:

- Legacy Service
- Load Balancer
- Coffee Machine Pressure

### 12.5 Spot-the-Bug

```text
Ein fehlerhaftes Element aus mehreren auswählen.
```

Passt für:

- PR Review
- Config Review
- Test Failure

---

# Teil C — Rollen, persönliche Aufgaben und Stärken

---

## 13. Grundidee: persönlicher Backlog statt globale Aufgaben

Jeder Release-Team-Spieler sollte nur eine begrenzte Anzahl an persönlichen Aufgaben haben.

Nicht:

```text
Alle Release-Team-Spieler können alle Tasks machen.
```

Sondern:

```text
Jeder Spieler hat 3–4 persönliche Tasks.
```

Beispiel:

```text
Developer:
- Pull Request reviewen
- Merge Conflict lösen
- Release Notes ergänzen

DevOps Engineer:
- CI/CD reparieren
- Deployment freigeben
- Server-Rack verkabeln

QA Lead:
- Test-Suite reparieren
- Logs analysieren
- Bug reproduzieren
```

## 13.1 Warum das gut ist

Persönliche Aufgaben erzeugen automatisch:

- bessere Alibis
- stärkere Verdächtigungen
- mehr Teamkoordination
- glaubwürdigeres Rollenspiel
- bessere Meetings

Beispiel:

```text
„Warum warst du im Server Room?“
„Ich musste Deployment fixen.“
„Du bist aber Scrum Master. Warum machst du DevOps-Aufgaben?“
```

---

## 14. Task-Klassen

| Task-Typ | Beschreibung | Beispiel |
|---|---|---|
| Personal Task | gehört einem bestimmten Spieler | „Review deinen PR“ |
| Role Task | passt besonders gut zu einer Rolle | „CI/CD reparieren“ für DevOps |
| General Task | kann von vielen erledigt werden | Kaffee auffüllen |
| Emergency Task | globale Störungs-Reparatur | PagerDuty reparieren |
| Ghost Task | kleine Aufgaben für Eliminierte | Logs sortieren |

## 14.1 Keine harten Blockaden

Empfehlung:

```text
Spezialisten sind schneller.
Andere können viele Tasks auch erledigen, aber langsamer.
Geister können eigene Tasks weiter erledigen.
```

---

## 15. Rollenmodell

Jede Rolle besteht aus vier Bausteinen:

```text
- Spezialisierung
- Schwäche
- aktive Fähigkeit
- Kaffee-Verhalten
```

Beispiel-Datenstruktur:

```json
{
  "id": "devops_engineer",
  "displayName": "DevOps Engineer",
  "team": "release",
  "strengthCategories": ["ci_cd", "deployment", "server_repair"],
  "weakCategories": ["release_notes", "scope"],
  "ability": "rollback",
  "coffeeProfile": "high_dependency"
}
```

---

## 16. MVP-Rollen für das Release-Team

Für die erste Version reichen 5 Release-Rollen:

```text
- Developer
- DevOps Engineer
- QA Lead
- Scrum Master
- Caffeine Collector
```

Später ergänzbar:

```text
- Bug Squasher
- Data Wizard
- Legacy Oracle
- Incident Commander
```

---

## 17. Rolle: Developer

### Fantasy

Der klassische Entwickler. Stark bei Code, Pull Requests und Merge-Problemen.

### Stärken

```text
- Pull Request reviewen
- Merge Conflicts lösen
- Release Notes schreiben
- kleine Code-Fixes
```

### Schwächen

```text
- Infrastruktur-Aufgaben langsamer
- Incident-Triage nur durchschnittlich
```

### Fähigkeit: Deep Work

```text
Ein passender Code-Task wird 30 % schneller erledigt.
Währenddessen ist der Spieler verwundbarer, z. B. kann er sich nicht bewegen.
```

### Kaffee

Normaler Kaffeeverbrauch.

---

## 18. Rolle: DevOps Engineer

### Fantasy

Der wichtigste Infrastruktur-Spieler.

### Stärken

```text
- CI/CD
- Deployment
- Server-Racks
- PagerDuty
- Monitoring
```

### Schwächen

```text
- Release Notes
- Meeting-/Scope-Aufgaben
```

### Fähigkeit: Rollback

```text
Einmal pro Runde +10 bis +15 Pipeline-Stability.
```

Soll keinen Sieg garantieren, aber kritische Momente entschärfen.

### Kaffee

Starke Kaffeeabhängigkeit.

```text
Hoher Kaffee = sehr effizient
Niedriger Kaffee = deutlich langsamer
```

---

## 19. Rolle: QA Lead

### Fantasy

Findet Fehler, validiert Tasks und erkennt komische Dinge.

### Stärken

```text
- Tests reparieren
- Logs analysieren
- Fake Requests erkennen
- Bug reproduzieren
```

### Schwächen

```text
- große Infrastruktur-Aufgaben
- Deployment
```

### Fähigkeit: Reproduce Bug

```text
Prüft eine kürzlich abgeschlossene Task oder Interaktion.
Ergebnis: plausibel / verdächtig / unklar.
```

Wichtig: Nicht beweisend.

### Kaffee

Relativ stabil, weniger abhängig.

---

## 20. Rolle: Scrum Master

### Fantasy

Koordiniert das Team, reduziert Scope und löst Meetings aus.

### Stärken

```text
- Scope reduzieren
- Sprint Board sortieren
- Meeting Notes
- Teamkoordination
```

### Schwächen

```text
- technische Tasks deutlich langsamer
```

### Fähigkeit: Standup

Empfohlene MVP-Variante:

```text
Kann einmal pro Runde ein zusätzliches Emergency Meeting auslösen,
auch außerhalb des War Rooms,
aber nur, wenn keine aktive Sabotage läuft.
```

Alternative:

```text
Zeigt für wenige Sekunden grobe Raumpositionen aller Spieler.
```

### Kaffee

Kaffee gibt eher Movement-Speed als Task-Speed.

---

## 21. Rolle: Caffeine Collector

### Fantasy

Support-Rolle. Hält das Team arbeitsfähig.

### Stärken

```text
- Kaffee auffüllen
- Kaffee verteilen
- Team-Speed buffen
- Kitchen-Aufgaben
```

### Schwächen

```text
- technische Tasks weniger effizient
```

### Fähigkeit: Coffee Run

```text
Gibt nahen Spielern temporären Buff.
Beispiel: +20 % Movement-Speed oder Task-Speed für 8–10 Sekunden.
```

### Kaffee

Kann Kaffee über Maximum speichern.

```text
Normal: maxCoffee = 100
Caffeine Collector: maxCoffee = 130
```

---

## 22. Weitere Rollen für später

### Bug Squasher

```text
Stark bei kleinen Bugfixes, Tests und Fehlermeldungen.
Fähigkeit: Quick Fix — kleines Mini-Game überspringen oder stark beschleunigen.
Kaffee: sehr starker Bonus bei hohem Kaffee, starker Malus bei niedrigem Kaffee.
```

### Data Wizard

```text
Stark bei Logs, Monitoring, Metriken und Anomalien.
Fähigkeit: Trace Query — zeigt Raum einer kritischen Aktion, aber nicht den Spieler.
Kaffee: Analyse-Tasks werden stark beschleunigt.
```

### Legacy Oracle

```text
Stark im Legacy Basement und bei alten Services.
Fähigkeit: Ancient Knowledge — Legacy-Task teilweise sofort reparieren.
Kaffee: fast immun gegen Kaffee-Mangel.
Flavor: läuft seit Jahren auf Restenergie und Zynismus.
```

### Incident Commander

```text
Stark bei Notfällen und Koordination.
Fähigkeit: zeigt aktive Störungen oder priorisiert Emergency Tasks.
```

---

## 23. Task-Speed-Modifikatoren

Nicht passende Tasks sollten nicht verboten, sondern langsamer sein.

Vorschlag:

```text
Passende Rolle: Taskdauer × 0.75
Normale Rolle: Taskdauer × 1.0
Unpassende Rolle: Taskdauer × 1.35
```

Beispiel CI/CD:

```text
DevOps Engineer: 6 Sekunden
Developer: 8 Sekunden
Scrum Master: 11 Sekunden
```

---

## 24. Progress-Gewichtung

Nicht jede Aufgabe sollte gleich viel Release-Progress geben.

| Task-Art | Progress |
|---|---:|
| Kleine persönliche Task | +4 % |
| Normale Rollen-Task | +7 % |
| Schwierige Spezialisten-Task | +10 % |
| Ghost Task | +2–3 % |
| Emergency Repair | kein Progress, verhindert Schaden |

Emergency Repairs sollten eher Schaden verhindern als direkten Release-Progress geben.

---

# Teil D — Kaffee-System

---

## 25. Kaffee als echte Team-Ressource

Kaffee sollte nicht nur ein Gag sein, sondern strategisch wichtig werden.

Ziel:

- Kaffee beeinflusst Task-Speed
- Kaffee beeinflusst Movement-Speed leicht
- Rollen reagieren unterschiedlich auf Kaffee
- Kaffee erzeugt Alibis und Verdacht
- Caffeine Collector wird als Rolle wertvoll

---

## 26. Persönlicher Kaffee-Wert

Jeder Spieler bekommt:

```text
coffeeEnergy: 0–100
```

Dieser Wert sinkt:

```text
- langsam über Zeit
- stärker bei Tasks
- rollenabhängig unterschiedlich schnell
```

### Beispiel-Level

| Kaffeelevel | Effekt |
|---|---|
| 80–100 | +10 % Task-Speed |
| 40–79 | normal |
| 15–39 | -10 % Task-Speed, -5 % Movement |
| 0–14 | -20 % Task-Speed, -10 % Movement |

---

## 27. Rollenabhängiger Kaffee

| Rolle | Kaffee-Effekt |
|---|---|
| Developer | normal |
| DevOps Engineer | stark abhängig |
| QA Lead | stabil, weniger abhängig |
| Scrum Master | Kaffee gibt eher Movement-Speed |
| Caffeine Collector | kann Kaffee speichern/verteilen |
| Bug Squasher | sehr starker Bonus bei hohem Kaffee |
| Data Wizard | Analyse-Tasks stark kaffeeverstärkt |
| Legacy Oracle | fast immun gegen Kaffee-Mangel |

---

## 28. Warum Kaffee Social Deduction verbessert

Kaffee erzeugt Diskussionen:

```text
„Warum hast du Kaffee genommen, obwohl DevOps leer war?“
„Warum warst du so lange in der Küche?“
„Ich musste Kaffee holen, weil Bug Squasher sonst die Tests nicht schafft.“
„Komisch, direkt danach lag dort ein Body.“
```

Kaffee ist damit:

```text
- Ressource
- Alibi
- Verdachtsmoment
- Support-Mechanik
- Teamstrategie
```

---

# Teil E — Fake-Tasks und Alibi-Spiel

---

## 29. Chaos braucht Fake-Tasks

Wenn Release-Spieler persönliche Tasks bekommen, brauchen Chaos-Agenten plausible Fake-Tasks.

Sonst fliegen sie zu leicht auf.

## 29.1 Fake-Task-Liste

Chaos-Agenten bekommen zu Rundenbeginn eine Fake-Task-Liste passend zur Tarnrolle.

Beispiel Vibe Coder:

```text
Fake Tasks:
- PR reviewen im Open Space
- Flaky Test untersuchen im Server Room
- Release Notes checken im Meeting Room
```

## 29.2 Fake-Task-Interaktion

Chaos sollte an echten Task-Orten „arbeiten“ können, ohne Progress zu erzeugen.

Andere sehen:

```text
„Sven arbeitet am Terminal“
```

Nicht:

```text
„Sven macht Fake-Task“
```

## 29.3 Fake-Task-Dauer

Fake-Tasks sollten glaubwürdige Dauer haben.

Optional:

- Chaos kann Fake-Task abbrechen
- Fake-Task zeigt nach außen Busy-State
- Fake-Task hat keine Release-Wirkung
- QA Lead kann später vielleicht „plausibel/verdächtig“ prüfen

---

# Teil F — Meetings und Voting

---

## 30. Meetings sind der wichtigste Moment

Meetings sind der Kern von Social Deduction. Hier entscheidet sich, ob das Spiel nach einer Runde lustig war.

Ziel:

- mehr Kontext
- bessere Gesprächsimpulse
- keine automatischen Täterbeweise
- klarere Voting-UI
- stärkere Story

---

## 31. Meeting-Screen: Kontext anzeigen

Der Meeting-Screen sollte grobe Informationen liefern.

Mögliche Elemente:

```text
- Wer hat den Body reported?
- Wo wurde der Body gefunden?
- Wie lange ist der Tod ungefähr her?
- Welche Sabotage war zuletzt aktiv?
- Welche großen Events passierten kurz vorher?
- Wer ist alive / dead / ghost?
```

Beispiel:

```text
Body Reported
Found by: Anna
Location: Server Room
Estimated death window: 20–40 seconds ago
Recent events:
- Coffee Empty
- CI/CD Red
- Body Report
```

Wichtig:

```text
Keine exakte Täterliste.
Keine exakten Bewegungslogs.
Keine sicheren Beweise.
```

---

## 32. Accusation-Pings / Meeting-Tags

Da kein Free-Form-Chat im Spiel geplant ist, könnten einfache Meeting-Tags helfen.

Spieler können andere markieren als:

```text
- sus
- war mit mir
- hat Task gemacht
- hat Body reported
- war still
- war nahe Body
```

Diese Tags sollten nur im Meeting sichtbar sein und keine mechanische Beweiskraft haben.

Vorteil:

- funktioniert auch ohne Textchat
- unterstützt Voice-Diskussion
- hilft Mobile-Spielern

---

## 33. Voting verbessern

Aktuelles Voting ist funktional. Verbesserungen:

```text
- klarer Timer
- sichtbar, wer schon abgestimmt hat, aber nicht zwingend für wen
- Skip gut sichtbar
- Tie/Skip-Regel klar erklären
- nach Vote Ergebnis dramatisch anzeigen
```

Optional:

```text
- kurze „last words“-Zeile als Flavor
- Ergebnistext je nach Rolle erst im Endscreen revealen, nicht sofort
```

---

## 34. Meeting-Balance

Achtung: Zu viele Meetings machen Runden zäh.

Empfehlungen:

```text
- Body Reports bleiben immer möglich
- Emergency Meeting bleibt begrenzt
- Scrum Master kann optional zusätzliches Meeting triggern
- Meeting nicht während kritischer Sabotage, außer Design gewollt
```

---

# Teil G — Ghosts, Endscreen und Rundenstory

---

## 35. Ghosts weiter wertvoll machen

Bestehender Spectator-Mode ist gut: Eliminierte Spieler können weiter Tasks erledigen, sehen andere Geister, aber nicht voten/reporten.

Mit persönlichem Task-System:

```text
- Geister behalten ihre persönlichen Tasks
- Ghost-Tasks geben eventuell weniger Progress
- Geister können nicht reporten, nicht voten, keine Meetings auslösen
```

Optional später:

```text
- Ghost-only Mini-Tasks
- Ghost-Emotes nur unter Geistern
- Endscreen zeigt Ghost-Beitrag
```

---

## 36. Endscreen stärker machen

Der Endscreen sollte nicht nur Rollen zeigen, sondern die Runde erzählen.

Beispiele:

```text
- Chaos-Agenten waren: Sven, Lisa
- Erster Force-Reboot: 03:12 in Kitchen
- Meiste Tasks: Anna
- Meiste Repairs: Max
- Meiste Zeit ohne Kaffee: Tom
- Schnellster Repair: Lisa
- Final Release Progress: 87 %
- Final Pipeline Stability: 14 %
```

Warum wichtig:

```text
Der Endscreen ist der Moment, in dem Leute lachen, diskutieren und „noch eine Runde“ wollen.
```

---

## 37. Postmortem-Flavor

Optional später mit oder ohne KI:

```text
Incident Report:
Release 42 ist gescheitert, weil das Team gleichzeitig Kaffee holen,
Slack reparieren und Sven aus dem Meeting werfen wollte.
```

Oder:

```text
Root Cause:
Vibe Coding direkt auf main.
```

---

# Teil H — Eventfeed, Humor und Game Feel

---

## 38. Eventfeed ausbauen

Der Eventfeed sollte Atmosphäre erzeugen, aber nicht zu viel verraten.

Schlecht:

```text
Sven sabotiert CI/CD.
```

Gut:

```text
CI/CD ist rot. Niemand weiß warum. Alle wissen warum.
```

Beispiele:

```text
- Ein Kunde hat „nur eine kleine Änderung“ gemeldet.
- Legacy-Service macht Legacy-Service-Dinge.
- Kaffeemaschine meldet 418: I’m a teapot.
- Jemand hat direkt auf main gepusht. Natürlich.
- Slack ist down. Produktivität steigt kurz an.
- PagerDuty möchte einfach nur reden.
```

---

## 39. Game-Feel-Polish

Später, aber wichtig:

```text
- kurze Terminal-Animation bei Task/Sabotage
- Sound für Body Report
- Sound für Sabotage-Start
- dezente Rolle-Intro-Animation
- klare Repair-Hints
- besseres Busy-Feedback
- Mini-Game-Erfolg/Fehlschlag Feedback
```

---

# Teil I — Map, Räume und Lesbarkeit

---

## 40. Default-Map zuerst perfektionieren

Vor neuen Maps sollte die Default-Map gut funktionieren.

Fragen für Playtests:

```text
- Gibt es Räume, die nie genutzt werden?
- Gibt es zu viele tote Ecken?
- Werden Bodies zu schnell oder zu spät gefunden?
- Gibt es genug Engstellen?
- Sind wichtige Räume gut verteilt?
- Gibt es gute Alibi-Routen?
- Sind Vents zu stark oder zu schwach?
```

---

## 41. Räume mit klarer Funktion

Jeder Raum sollte spielerisch eine Identität haben.

| Raum | Funktion |
|---|---|
| Open Space | Hub, Developer Tasks, Git-Terminal |
| Server Room | DevOps, CI/CD, Monitoring, PagerDuty |
| Kitchen | Kaffee, Support, Social Trap |
| Meeting Room | Scrum, Scope, Mandatory Meeting |
| Legacy Basement | Legacy Tasks, riskanter isolierter Raum |
| War Room | Slack, Emergency Meeting, Incident Triage |

---

# Teil J — Mobile und Onboarding

---

## 42. Role Intro Screen

Zu Rundenbeginn sollte jeder Spieler eine klare Rollenkarte bekommen.

Beispiel:

```text
Du bist: DevOps Engineer
Team: Release-Team

Stärken:
- CI/CD
- Deployment
- Server-Reparaturen

Schwäche:
- Release Notes dauern länger

Fähigkeit:
Rollback — Stelle einmal pro Runde Pipeline-Stability wieder her.

Kaffee:
Du arbeitest mit Kaffee deutlich schneller.
```

---

## 43. Persönliche Task-Liste im UI

Beispiel:

```text
Deine Aufgaben:
[ ] CI/CD reparieren — Server Room
[ ] Deployment freigeben — Server Room
[ ] Kaffee holen — Kitchen
```

Optional:

```text
- Rollenicon
- Raumhinweis
- passender Task visuell markiert
- Hinweis, wenn man bei einer Task langsam/schnell ist
```

---

## 44. Context Action Button für Mobile

Auf Mobile sollte es möglichst wenige Buttons geben.

Ein Kontextbutton kann je nach Nähe wechseln:

```text
- Task
- Repair
- Report
- Vent
- Emergency
- Fake Task
```

---

## 45. QR-Lobby

Für Mittagspausen-Spielrunden extrem wertvoll:

```text
Host öffnet Lobby → großer QR-Code → alle joinen schnell.
```

---

# Teil K — Playtest-Metriken und Balancing

---

## 46. Metriken erfassen

Ab jetzt sollte jede Runde Metriken sammeln.

Wichtige Werte:

```text
- Rundendauer
- Winrate Release-Team vs. Chaos
- Anzahl Meetings
- Anzahl Body Reports
- Anzahl Emergency Meetings
- Anzahl Force-Reboots
- Tasks completed pro Spieler
- Tasks completed pro Rolle
- Sabotagen ausgelöst
- Sabotagen repariert
- Kills pro Raum
- häufigste Todesorte
- häufigste Vote-Targets
- Skip-Rate
- Kaffeeverbrauch pro Rolle
- durchschnittliche coffeeEnergy
- Ghost-Tasks completed
```

---

## 47. Zielwerte für Balance

Grobe Zielwerte:

```text
Release-Team Winrate: 45–55 %
Rundendauer: meistens 8–13 Minuten
Meetings pro Runde: 2–4
Chaos-Kills pro Runde: 1–4 je nach Spielerzahl
Keine Rolle sollte deutlich nutzlos sein
Kein Raum sollte irrelevant sein
```

---

## 48. Heatmaps

Sehr hilfreich für Map-Balancing:

```text
- Movement Heatmap
- Kill Heatmap
- Body Discovery Heatmap
- Task Completion Heatmap
- Sabotage Trigger Heatmap
```

Damit sieht man schnell:

```text
- welche Räume zu leer sind
- wo Chaos zu stark ist
- wo Bodies nie gefunden werden
- welche Tasks ignoriert werden
```

---

# Teil L — Technische Umsetzungsideen

---

## 49. Neue Datenmodelle

### 49.1 RoleDefinition

```json
{
  "id": "devops_engineer",
  "displayName": "DevOps Engineer",
  "team": "release",
  "strengthCategories": ["ci_cd", "deployment", "server_repair"],
  "weakCategories": ["release_notes", "scope"],
  "ability": "rollback",
  "coffeeProfile": "high_dependency"
}
```

### 49.2 TaskDefinition

```json
{
  "id": "fix_ci",
  "displayName": "CI/CD reparieren",
  "category": "ci_cd",
  "room": "server_room",
  "baseDuration": 8,
  "baseProgress": 7,
  "preferredRoles": ["devops_engineer"],
  "fallbackAllowed": true,
  "miniGameType": "sequencing"
}
```

### 49.3 AssignedTask

```json
{
  "taskId": "fix_ci",
  "assignedTo": "player_123",
  "status": "open",
  "progress": 0,
  "isGhostCompletable": true
}
```

### 49.4 PlayerState-Erweiterung

```json
{
  "playerId": "player_123",
  "role": "devops_engineer",
  "assignedTasks": ["fix_ci", "approve_deployment", "coffee_run"],
  "fakeTasks": [],
  "coffeeEnergy": 72,
  "abilityCooldown": 0,
  "abilityUsed": false
}
```

### 49.5 SabotageObject

```json
{
  "id": "ci_console_01",
  "room": "server_room",
  "position": { "x": 1250, "y": 880 },
  "radius": 50,
  "supportedSabotages": ["ci_red", "flaky_tests"],
  "visibleToAll": true
}
```

---

## 50. Task-Zuweisung bei Rundenstart

MVP-Regel:

```text
Jeder Release-Spieler bekommt 3 persönliche Tasks.
Davon:
- 2 rollenpassende Tasks
- 1 allgemeine Task
```

Chaos-Agenten bekommen:

```text
- 3 Fake-Tasks
- passend zur Tarnrolle
- passend zu echten Map-Orten
```

---

## 51. Task-Speed-Berechnung

Pseudo-Logik:

```python
multiplier = 1.0

if task.category in role.strengthCategories:
    multiplier *= 0.75

if task.category in role.weakCategories:
    multiplier *= 1.35

multiplier *= coffee_speed_modifier(player.coffeeEnergy, role.coffeeProfile)

effective_duration = task.baseDuration * multiplier
```

---

## 52. Kaffee-Tick

Pseudo-Logik:

```python
for player in alive_players:
    player.coffeeEnergy -= base_decay_per_second * dt

    if player.isDoingTask:
        player.coffeeEnergy -= task_decay_modifier * dt

    player.coffeeEnergy = clamp(player.coffeeEnergy, 0, player.maxCoffee)
```

---

## 53. Sabotage-Trigger-Validierung

Pseudo-Logik:

```python
def can_trigger_sabotage(player, sabotage_id, object_id):
    if not player.is_alive:
        return False
    if player.team != "chaos":
        return False
    if sabotage_id not in player.available_sabotages:
        return False
    if not cooldown_ready(player, sabotage_id):
        return False

    obj = sabotage_objects[object_id]
    if sabotage_id not in obj.supportedSabotages:
        return False
    if distance(player.position, obj.position) > obj.radius:
        return False

    return True
```

---

# Teil M — Acceptance Criteria

---

## 54. Sabotage / Chaos

```text
- Chaos kann Sabotagen nicht mehr von überall triggern.
- Jede Sabotage hat erlaubte Sabotage-Objekte.
- Server validiert Distanz und Objekt.
- Starke Sabotagen haben höheres Risiko oder längeren Cooldown.
- Sabotage-Interaktion sieht nach außen wie normale Terminalarbeit aus.
- Vibe Coder ist stärker auf Code-/CI-/Git-Chaos fokussiert.
```

## 55. Tasks

```text
- Alle Release-Spieler haben persönliche Tasks.
- Nicht jeder Spieler hat identische Aufgaben.
- Drei alte Hold-E-Tasks werden als Mini-Games konzipiert.
- Task-Kategorien existieren serverseitig.
- Task-Speed hängt von Rolle und Kaffee ab.
```

## 56. Rollen

```text
- Release-Team-Rollen haben Stärken, Schwächen und Fähigkeit.
- Keine Rolle ist allein spielentscheidend.
- Keine Aufgabe wird durch Tod/Disconnect komplett unmöglich.
- Rollen erzeugen bessere Alibis und Verdacht.
```

## 57. Kaffee

```text
- Spieler haben coffeeEnergy.
- Kaffee beeinflusst Task-Speed und optional Movement-Speed.
- Rollen reagieren unterschiedlich auf Kaffee.
- Caffeine Collector kann Kaffee strategisch nutzen.
```

## 58. Meetings

```text
- Meeting-Screen zeigt Body-Ort, Reporter und grobe Event-Historie.
- Informationen erzeugen Gesprächsstoff, aber keine Beweise.
- Voting-Status ist klarer.
- Skip/Tie-Regeln sind verständlich.
```

## 59. Ghosts

```text
- Geister können persönliche Tasks weiter erledigen.
- Geister können nicht voten/reporten.
- Ghost-Beitrag wird im Endscreen sichtbar.
```

## 60. Metriken

```text
- Jede Runde exportiert Basis-Metriken.
- Winrate, Rundendauer, Meetings, Kills, Tasks und Sabotagen werden erfasst.
- Daten helfen beim Balancing.
```

---

# Teil N — Nicht für MVP

Diese Dinge vorerst nicht priorisieren:

```text
- Skilltrees
- dauerhafte Account-Progression
- Items/Inventar
- zu viele Rollen auf einmal
- perfekte KI-Features
- harte Task-Exklusivität ohne Fallback
- komplexe Wirtschaftssysteme
- große neue Maps vor Default-Map-Balancing
```

---

# Teil O — Empfohlene Implementierungsreihenfolge

## Step 1 — Sabotage-Orte

```text
- SabotageObject in Map-JSON einführen
- Sabotage-Trigger nur in Radius erlauben
- Remote-Sabotage-Buttons deaktivieren, wenn kein passendes Objekt in Nähe ist
```

## Step 2 — Fake-Tasks

```text
- Chaos-Agenten bekommen Fake-Task-Liste
- Fake-Task-Interaktion an Task-Orten erlauben
- Busy-State nach außen anzeigen
```

## Step 3 — persönliche Tasks

```text
- AssignedTasks pro Spieler bei Rundenstart
- UI zeigt persönliche Task-Liste
- Progress nur für zugewiesene / erlaubte Tasks
```

## Step 4 — Rollenmodifikatoren

```text
- RoleDefinition serverseitig
- Task-Kategorien
- Task-Speed-Multiplikatoren
```

## Step 5 — Kaffee-System

```text
- coffeeEnergy pro Spieler
- Kaffee-Decays
- Kaffee-Buffs/Mali
- Caffeine Collector MVP
```

## Step 6 — Meetings

```text
- Meeting-Screen mit Kontext
- Body-Ort, Reporter, Event-Historie
- Voting-UI verbessern
```

## Step 7 — Hold-E-Tasks umbauen

```text
- PR Review Mini-Game
- Legacy Service Mini-Game
- Release Notes Mini-Game
```

## Step 8 — Endscreen & Metriken

```text
- Fun-Stats
- Rundenstory
- Playtest-Metriken exportieren
```

---

# Teil P — Claude-Code-Auftrag als kompakter Prompt

```text
Arbeite das bestehende Merge Conflict Mayhem Spiel so weiter, dass Social Deduction stärker wird.

Priorität 1:
- Sabotagen dürfen nicht mehr global von überall ausgelöst werden.
- Führe SabotageObject-Definitionen in der Map ein.
- Jede Sabotage hat erlaubte Trigger-Objekte.
- Server validiert Distanz, Rolle, Cooldown und Alive-State.
- Die UI zeigt Sabotage-Actions nur, wenn ein passendes Objekt in der Nähe ist.
- Nach außen soll Sabotage wie normale Terminalarbeit aussehen.

Priorität 2:
- Führe persönliche Tasks pro Release-Spieler ein.
- Jeder Spieler bekommt zu Rundenbeginn 3 Tasks.
- Release-Rollen haben Stärken und Schwächen je Task-Kategorie.
- Nicht passende Tasks sind nicht verboten, sondern langsamer.
- Chaos-Agenten bekommen Fake-Tasks passend zur Tarnrolle.

Priorität 3:
- Führe ein einfaches coffeeEnergy-System ein.
- Kaffee beeinflusst Task-Speed und optional Movement-Speed.
- Rollen reagieren unterschiedlich auf Kaffee.
- Caffeine Collector kann Kaffee als Support-Rolle nutzen.

Priorität 4:
- Verbessere Meetings.
- Zeige Reporter, Body-Ort, grobes Todesfenster und letzte globale Events.
- Keine exakten Täterbeweise anzeigen.

Priorität 5:
- Baue die drei Hold-E-Tasks review_pr, calm_legacy_service und write_release_notes als Mini-Games um.
- Nutze PR-Diff-Review, Legacy-Stabilitäts-Balancing und Release-Notes-Kategorisierung.

Bei allem gilt:
- Server bleibt autoritativ.
- Keine harten Sackgassen durch tote Rollen.
- Hinweise statt Beweise.
- Features sollen Alibis, Verdacht und Teamkoordination erzeugen.
```

---

# Schlussfazit

Die stärkste Richtung für Merge Conflict Mayhem ist:

```text
Ein echtes Release-Team mit unterschiedlichen Spezialisten, persönlichen Aufgaben,
Kaffee als Team-Ressource und Chaos-Agenten, die für Sabotage wirklich Orte aufsuchen müssen.
```

Dadurch entstehen automatisch bessere Runden:

```text
- Warum warst du im Server Room?
- Warum hat der Scrum Master CI/CD gemacht?
- Warum war der Caffeine Collector so lange in der Kitchen?
- Wer hat am Git-Terminal gearbeitet, bevor Merge Conflict Storm losging?
- Warum hatte DevOps keinen Kaffee mehr?
```

Das sind die Gespräche, die das Spiel tragen.

