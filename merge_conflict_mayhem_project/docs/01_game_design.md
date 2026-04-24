# 01 – Game Design

## Merge Conflict Mayhem: Lunch Break Edition

**Genre:** Social Deduction, Koop-Chaos, Dev-Humor  
**Rundenlänge:** 8–12 Minuten  
**Spielerzahl MVP:** 4–6  
**Spielerzahl langfristig:** 4–12

---

# 1. High Concept

Ein Entwicklerteam steht kurz vor dem Release. Die meisten Spieler versuchen, Tasks zu erledigen und die Pipeline stabil zu halten. Ein geheimer Chaos-Agent sabotiert das Release, löst Incidents aus und versucht, unentdeckt zu bleiben.

Das Spiel lebt von kurzer Rundenlänge, remote-fähigem Multiplayer und humorvollen Dev-/KI-/Office-Gags.

---

# 2. Zielgruppe

- Entwickler
- KI-Teams
- Data Scientists
- DevOps Engineers
- DnD-Spieler
- Among-Us-Fans
- Remote-Teams
- Teams mit trockenem Tech-Humor

Nicht-Gamer sollen mitspielen können. Deshalb:

- einfache Steuerung
- klare Aufgaben
- wenig Regeln
- kurze Runden
- hohe Lesbarkeit

---

# 3. Spielgefühl

Das Spiel soll sich anfühlen wie:

> Wir müssen in 10 Minuten releasen, aber irgendjemand macht absichtlich alles kaputt.

Typische Momente:

- „Wer hat auf main gepusht?“
- „Warum sind die Tests rot?“
- „Wieso ist die Kaffeemaschine offline?“
- „Wer war gerade allein im Serverraum?“
- „Der KI-Agent hat eigenständig refactored.“

---

# 4. Teams

## Release-Team

Ziel: Release erfolgreich abschließen.

Möglichkeiten:

- Tasks erledigen
- Sabotagen reparieren
- Incidents reduzieren
- Pipeline stabilisieren
- Chaos-Agenten identifizieren

## Chaos-Agenten

Ziel: Release verhindern.

Möglichkeiten:

- Pipeline sabotieren
- Kaffeeversorgung lahmlegen
- Meetings auslösen
- Misstrauen säen
- als normaler Spieler tarnen

---

# 5. Game Loop

1. Lobby
2. Rollenverteilung
3. Spielphase
4. Sabotagen und Tasks
5. Emergency Meeting
6. Voting
7. Endscreen

---

# 6. Globale Werte

| Wert | Bedeutung |
|---|---|
| Release Progress | Fortschritt Richtung Release |
| Pipeline Stability | Zustand der Infrastruktur |
| Incident Count | Anzahl offener Incidents |
| Coffee Level | Kaffeeversorgung / Humor-Utility |
| Remaining Seconds | Rundentimer |

---

# 7. Win Conditions

## Release-Team gewinnt

- Release Progress erreicht 100 %
- oder alle Chaos-Agenten wurden entfernt

## Chaos-Agenten gewinnen

- Pipeline Stability fällt auf 0 %
- oder der Timer läuft ab
- später optional: zu viele Incidents offen

---

# 8. MVP-Map

```text
+------------------+------------------+------------------+
|   Open Space     |   Meetingraum    |      Küche       |
+------------------+------------------+------------------+
|   Serverraum     |     War Room     |  Legacy-Keller   |
+------------------+------------------+------------------+
```

## Open Space

Tasks:

- Unit Tests fixen
- Pull Request reviewen
- Merge Conflict lösen

## Serverraum

Tasks:

- Deployment reparieren
- Logs analysieren
- Server neustarten

Sabotagen:

- CI/CD Rot
- Netzwerk-Lag

## Meetingraum

Tasks:

- Scope reduzieren
- Kundenanforderung entschlüsseln
- Agenda finden

Sabotagen:

- Mandatory Meeting
- Scope Creep

## Küche

Tasks:

- Kaffee auffüllen
- Snack Supply sichern

Sabotagen:

- Kaffee leer

## Legacy-Keller

Tasks:

- Legacy-Service beruhigen
- alten Cronjob stoppen

Sabotagen:

- Legacy Awakening

## War Room

Funktionen:

- Emergency Meeting starten
- Status anzeigen
- später: Dashboard / globale Aktionen

---

# 9. Rollen

## MVP-Rollen

### Developer

- normale Tasks
- Release Progress

### DevOps Engineer

- Pipeline reparieren
- Infrastruktur stabilisieren

### AI Engineer

- später: Auto-Fix Bot
- MVP: normale Teamrolle mit Flavor

### Vibe Coder

- Chaos-Agent
- sabotiert heimlich

---

# 10. Erweiterbare Rollen

- Data Wizard
- Consultant
- Shadow Admin
- Incident Commander
- Caffeine Collector
- Bug Squasher
- Legacy Oracle
- Scrum Master

---

# 11. MVP-Tasks

| Task | Raum | Dauer | Effekt |
|---|---|---:|---|
| Unit Tests fixen | Open Space | 5 s | +10 % Release Progress |
| Pull Request reviewen | Open Space | 5 s | +8 % Release Progress |
| Deployment reparieren | Serverraum | 6 s | +15 % Pipeline Stability |
| Kaffee auffüllen | Küche | 4 s | Coffee Level = 100 % |
| Legacy-Service beruhigen | Legacy-Keller | 7 s | -1 Incident |
| Logs analysieren | Serverraum | 5 s | -1 Incident |
| Scope reduzieren | Meetingraum | 5 s | entfernt Fake Request |
| Release Notes schreiben | War Room | 6 s | +12 % Release Progress |

---

# 12. MVP-Sabotagen

## CI/CD Rot

- Pipeline Stability -20 %
- Release Progress kurz blockiert
- Cooldown: 60 s

## Kaffee leer

- Coffee Level = 0 %
- Spieler langsamer
- Cooldown: 75 s

## Mandatory Meeting

- Spieler kurz verlangsamt
- Meetingraum hervorgehoben
- Cooldown: 90 s

---

# 13. Meetings und Voting

- Jeder Spieler hat ein Emergency Meeting pro Runde.
- Meeting kann im MVP nur im War Room gestartet werden.
- Während des Meetings pausiert das Spiel.
- Spieler stimmen für eine Person oder Skip.
- Bei Gleichstand wird niemand entfernt.
- Entfernte Spieler können keine Tasks und Sabotagen mehr ausführen.

Meeting-Titel:

- Wer hat auf main gepusht?
- Warum sind die Tests rot?
- Wieso ist der Kunde im Sprint?
- Wer hat den KI-Agenten unbeaufsichtigt gelassen?

---

# 14. Eventfeed

Beispiele:

- Die Pipeline ist rot. Niemand weiß warum.
- Ein KI-Agent hat eigenständig refactored.
- Der Kunde hat nur eine kleine Änderung geschickt.
- Main wurde direkt gepusht. Mutig.
- Die Kaffeemaschine ist offline.
- Legacy-Service hat Geräusche gemacht.
- Ein Meeting ohne Agenda wurde gestartet.
- Die Tests schlagen fehl, aber nur manchmal.

---

# 15. Endscreen-Awards

- Held der Kaffeemaschine
- Most Suspicious Innocent
- Chief Merge Destroyer
- Pipeline Whisperer
- Lord of Legacy
- Meeting-Minister
- Bug Summoner
- Stacktrace-Schamane
- Main-Branch-Monster

