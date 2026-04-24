# KI-Ideen für Merge Conflict Mayhem

## Grundprinzip

KI sollte das Spiel **lustiger, persönlicher und variantenreicher** machen, aber nicht den fairen Multiplayer-Core gefährden.

**Leitregel:**

> KI macht Stimmung, Humor und Content — aber sie entscheidet nicht direkt über Sieg oder Niederlage.

Der eigentliche Game-Core bleibt deterministisch:

- Rollen
- Tasks
- Sabotagen
- Timer
- Voting
- Win Conditions
- Balancing

KI ergänzt das Spiel durch:

- Kommentare
- Eventtexte
- Awards
- Flavor-Texte
- Fake Logs
- Rollenbeschreibungen
- Postmortems
- Daily Challenges
- optionale Chaos-Mechaniken

---

# 1. KI-Rundenkommentator

## Idee

Nach jeder Runde erstellt die KI einen lustigen Bericht über den Spielverlauf.

Das Spiel übergibt strukturierte Matchdaten an das LLM:

```json
{
  "winner": "chaos_agents",
  "players": [
    {
      "name": "Sven",
      "role": "DevOps Engineer",
      "tasksCompleted": 4,
      "votesReceived": 3
    },
    {
      "name": "Max",
      "role": "Vibe Coder",
      "sabotagesTriggered": 5
    }
  ],
  "events": [
    "CI/CD Rot triggered",
    "Coffee Outage triggered",
    "Sven called emergency meeting",
    "Max was not voted out"
  ]
}
```

## Beispielausgabe

```markdown
## Postmortem: Kaffee war nicht das einzige Problem

Das Release-Team hatte gute Absichten, aber schlechte Beobachtungsgabe. Während HotfixHero tapfer die Pipeline stabilisierte, stand SneakySyntax auffällig oft neben Dingen, die kurz darauf kaputt waren.

**Root Cause:** Zu viel Vertrauen in Menschen mit Hoodie.

**Action Item:** Adminrechte erst nach dem zweiten Kaffee vergeben.
```

## Warum gut?

- sehr hoher Funfaktor
- keine Auswirkung auf Balancing
- perfekt für interne Running Gags
- leicht umzusetzen
- ideal für Endscreen

## Priorität

**P0 – sehr empfehlenswert für frühe Version**

---

# 2. KI-generierte Endscreen-Awards

## Idee

Am Ende jeder Runde vergibt die KI jedem Spieler einen lustigen Award.

Beispiele:

- „Pipeline-Flüsterer“
- „Most Suspicious Innocent“
- „Held der Kaffeemaschine“
- „Certified Meeting Victim“
- „Lord of Legacy“
- „Hat viel gerannt, aber wenig erreicht“
- „Bug Summoner“
- „Main-Branch-Monster“

## Beispielinput

```json
{
  "players": [
    {
      "name": "Sven",
      "role": "DevOps Engineer",
      "tasksCompleted": 7,
      "sabotagesTriggered": 0,
      "votesAgainstInnocents": 2,
      "timeNearCoffeeMachine": 180
    }
  ]
}
```

## Beispielausgabe

```json
[
  {
    "playerName": "Sven",
    "awardTitle": "Pipeline-Flüsterer",
    "awardDescription": "Hat mehr Deployments gerettet als sein Blutdruck erlaubt."
  }
]
```

## Warum gut?

- motiviert zu weiteren Runden
- erzeugt Memes
- macht jede Runde individueller
- keine Gameplay-Risiken

## Priorität

**P0**

---

# 3. KI-generierte Eventfeed-Texte

## Idee

Der Eventfeed bekommt mehr Variation und Humor.

Statt immer:

```text
CI/CD Rot ausgelöst.
```

generiert die KI mehrere Varianten:

```text
Die Pipeline ist rot. Sie wirkt enttäuscht.
Build failed. Niemand übernimmt Verantwortung.
CI/CD hat das Vertrauen in die Menschheit verloren.
Ein Test schlägt fehl, der gestern noch grün war. Klassisch.
```

## Umsetzung

Die KI generiert vorab Textvarianten für feste Eventtypen:

- CI/CD Red
- Coffee Outage
- Mandatory Meeting
- Legacy Awakening
- Merge Conflict Storm
- Fake Customer Request
- Flaky Tests
- Scope Creep

## Wichtig

Die KI sollte diese Texte **vor der Runde** oder beim Serverstart generieren, nicht mitten in kritischen Spielsituationen.

## Warum gut?

- macht das Spiel sofort lebendiger
- geringe technische Komplexität
- keine Auswirkungen auf Fairness
- sehr gut cachebar

## Priorität

**P0**

---

# 4. KI-generierte Task-Flavor-Texte

## Idee

Die Spielmechanik bleibt gleich, aber die Aufgaben bekommen dynamische lustige Namen und Beschreibungen.

Mechanik bleibt z. B.:

```json
{
  "taskTemplate": "fix_unit_tests",
  "type": "hold",
  "requiredSeconds": 5,
  "releaseProgressReward": 10
}
```

KI erzeugt nur den Flavor:

```json
{
  "generatedTitle": "Fix flaky tests caused by emotional YAML",
  "generatedDescription": "The test suite has developed trust issues."
}
```

## Beispieltexte

- „Fixe Tests, die nur montags fehlschlagen.“
- „Beruhige die YAML-Datei.“
- „Entferne einen TODO-Kommentar aus 2009.“
- „Erkläre dem Kunden, dass Echtzeit nicht ‘sofort gestern’ bedeutet.“
- „Mache das Dashboard schneller, ohne Code zu ändern.“

## Warum gut?

- mehr Abwechslung
- sehr einfach umzusetzen
- keine Balance-Probleme
- perfekter Dev-Humor

## Priorität

**P0 / P1**

---

# 5. KI-generierte Meeting-Titel

## Idee

Emergency Meetings erhalten dynamische Titel basierend auf dem Spielverlauf.

## Beispiele

- „Wer hat auf main gepusht?“
- „Warum riecht der Serverraum nach Kaffee?“
- „Wieso ist SneakySyntax seit 4 Minuten im Keller?“
- „Wer hat dem KI-Agenten Schreibrechte gegeben?“
- „Warum blinkt die Pipeline in einer Farbe, die wir nicht definiert haben?“
- „Wer hat schon wieder ‘quick fix’ gesagt?“

## Umsetzung

Input an KI:

```json
{
  "lastEvents": [
    "coffee_outage",
    "ci_cd_red",
    "player_seen_in_server_room"
  ],
  "room": "war_room",
  "remainingSeconds": 312
}
```

Output:

```json
{
  "meetingTitle": "Warum riecht der Serverraum nach Kaffee?"
}
```

## Warum gut?

- hohe Sichtbarkeit
- lustiger Meeting-Moment
- geringe technische Komplexität

## Priorität

**P0 / P1**

---

# 6. KI-generierte Rollenbeschreibungen

## Idee

Die festen Rollen bleiben gleich, aber jede Runde bekommt jeder Spieler eine lustige Beschreibung.

## Beispiel: DevOps Engineer

```text
Du bist DevOps Engineer. Du kannst Deployments reparieren, Server beruhigen und so tun, als sei YAML eine gute Idee.
```

## Beispiel: Vibe Coder

```text
Du bist Vibe Coder. Dein Code kompiliert nicht, aber deine Zuversicht ist beeindruckend. Sabotiere das Release, ohne dass das Team merkt, dass du eigentlich gar keinen Plan hast.
```

## Beispiel: AI Engineer

```text
Du bist AI Engineer. Du kannst einen AutoFixBot starten. Er hilft meistens. Betonung auf meistens.
```

## Warum gut?

- einfache Personalisierung
- sehr lustig beim Rollen-Reveal
- keine Auswirkungen auf Balancing

## Priorität

**P1**

---

# 7. KI-generierte Fake Logs

## Idee

Für Tasks wie „Logs analysieren“ generiert die KI kurze, absurde, aber plausible Logzeilen.

## Beispiel

```text
[WARN] CoffeeMachineService latency above threshold
[ERROR] BuildPipeline failed at emotional dependency resolution
[INFO] User SneakySyntax accessed deploy panel
[DEBUG] LegacyService whispered: still here
```

Der Spieler muss anschließend eine Ursache auswählen:

```text
Was ist die wahrscheinlichste Ursache?

A) Coffee Outage
B) CI/CD Red
C) Legacy Awakening
D) Mandatory Meeting
```

## Wichtig

Die korrekte Antwort wird nicht von der KI entschieden, sondern vom Server.

Die KI generiert nur die Logtexte.

## Warum gut?

- sehr passend zum Tech-Team
- kleine Minigame-Komponente
- ideal für Serverraum-Tasks
- humorvoll und nützlich

## Priorität

**P1**

---

# 8. KI-Assistent im War Room

## Idee

Im War Room gibt es einen KI-Assistenten, der gelegentlich Hinweise gibt.

Er darf aber nicht zu stark sein.

## Beispielhinweise

```text
Auffällig: Kurz vor dem Coffee Outage befanden sich drei Spieler in der Küche.
```

```text
Zwischen 06:31 und 06:18 wurde im Serverraum etwas Dummes getan.
```

```text
Meine Analyse ist mit 73 % Konfidenz nutzlos.
```

## Mögliche Mechanik

- pro Runde maximal 2–3 KI-Hinweise
- Hinweise sind ungenau
- Hinweise kosten Zeit oder müssen als Task freigeschaltet werden
- KI darf den Saboteur nie direkt verraten

## Warum gut?

- bringt KI sichtbar ins Spiel
- unterstützt Diskussionen
- kann absichtlich leicht halluzinieren

## Priorität

**P1**

---

# 9. AutoFixBot als riskanter KI-Helfer

## Idee

Der AI Engineer kann einen KI-Agenten starten, der automatisch einen Task erledigt.

Aber der Bot ist nicht immer zuverlässig.

## Beispielmechanik

```text
70 %: AutoFixBot erledigt den Task langsam
20 %: AutoFixBot macht nichts
10 %: AutoFixBot erzeugt einen Mini-Incident
```

## Eventfeed-Beispiele

```text
AutoFixBot hat den Task gelöst. Niemand weiß wie.
```

```text
AutoFixBot hat 300 Zeilen Code entfernt. Das Problem ist weg. Die App auch.
```

```text
Der KI-Agent hat Kubernetes installiert. Warum auch immer.
```

## Warum gut?

- KI wird zur echten Spielmechanik
- Nutzen/Risiko-Entscheidung
- perfekt für AI Engineer
- sehr hoher Funfaktor

## Priorität

**P1 / P2**

---

# 10. KI-generierte Daily Challenges

## Idee

Jeden Tag oder jede Woche gibt es einen KI-generierten Sondermodus.

## Beispiele

### Friday Deploy

```text
Niemand weiß, warum ihr freitags deployed. Aber jetzt ist es zu spät.
```

### No Coffee Mode

```text
Die Kaffeemaschine ist dauerhaft offline. Viel Glück.
```

### Everyone is DevOps

```text
Alle dürfen deployen. Was soll schon schiefgehen?
```

### Legacy Basement Only

```text
Alle kritischen Tasks spawnen im Keller. Das System freut sich.
```

### Consultant Invasion

```text
Meetings dauern doppelt so lang, klingen aber wichtiger.
```

## Warum gut?

- sorgt für Abwechslung
- gut für Mittagspausen-Routine
- leicht intern teilbar

## Priorität

**P1 / P2**

---

# 11. KI-generierte Postmortems

## Idee

Nach der Runde wird ein formeller, aber absurder Incident-Report erzeugt.

## Struktur

```markdown
# Incident Postmortem

## Summary

## Timeline

## Root Cause

## Contributing Factors

## What Went Well

## What Went Wrong

## Action Items
```

## Beispiel

```markdown
# Incident Postmortem: Main Branch Emotional Damage

## Summary
Das Release scheiterte nach einer Kette von Entscheidungen, die einzeln fragwürdig und gemeinsam katastrophal waren.

## Root Cause
Ein Vibe Coder mit Adminrechten.

## Contributing Factors
- Kaffeepegel unter 40 %
- Meeting ohne Agenda
- Legacy-System wurde direkt angeschaut

## Action Items
- Kein Deployment ohne Kaffee
- Keine Adminrechte für Menschen mit „quick fix“-Energie
```

## Warum gut?

- extrem passend für Dev-/Ops-Kultur
- hoher Meme-Faktor
- gut zum Teilen im Teamchat

## Priorität

**P1**

---

# 12. KI-generierte Content-Vorschläge für Pull Requests

## Idee

Mitarbeitende können im Admin-Bereich Ideen eintragen, und die KI schlägt daraus strukturierte JSON-Konfigurationen vor.

## Beispielinput

```text
Mach eine Sabotage aus unserem letzten echten Deployment-Problem mit kaputten Dependencies.
```

## KI-Ausgabe

```json
{
  "id": "dependency_hell",
  "title": "Dependency Hell",
  "effect": "spawn_extra_tasks",
  "cooldownSeconds": 90,
  "eventText": "Ein Dependency Update hat Gefühle entwickelt."
}
```

## Wichtig

Der KI-Vorschlag wird nicht automatisch ins Spiel übernommen.

Ablauf:

1. Mitarbeitender gibt Idee ein
2. KI erzeugt Vorschlag
3. Mensch reviewed
4. Pull Request wird erstellt
5. Merge nach Review

## Warum gut?

- passt perfekt zum internen Open-Source-Gedanken
- senkt Einstiegshürde für Beiträge
- macht Content-Erstellung einfacher

## Priorität

**P2**

---

# 13. KI-Bot-Spieler

## Idee

Wenn zu wenige Spieler da sind, kann ein KI-Bot mitspielen.

## Einfache Variante

Der Bot ist kein echter intelligenter Spieler, sondern ein chaotischer NPC:

- läuft zufällig herum
- erledigt gelegentlich Tasks
- steht manchmal im Weg
- triggert lustige Events
- kann nicht gewinnen
- erzeugt Chaos

## Beispiel

```text
InternBot3000 hat versucht zu helfen. Das war ein Fehler.
```

## Komplexe Variante

Ein echter Bot-Spieler, der:

- Tasks priorisiert
- Spieler beobachtet
- Meetings bewertet
- als Saboteur agieren kann

## Einschätzung

Echte Bot-Spieler sind deutlich komplexer und sollten nicht früh gebaut werden.

## Priorität

**P2**

---

# 14. AI Director

## Idee

Ein KI-System beobachtet die Runde und macht Vorschläge für dramatische Ereignisse.

## Erlaubt

- Flavor-Events erzeugen
- lustige Texte einstreuen
- kleine optionale Mini-Incidents vorschlagen
- Daily Challenges auswählen
- Endscreen dramaturgisch kommentieren

## Nicht erlaubt

- Saboteur verraten
- Win Condition ändern
- harte Spielmechanik unfair manipulieren
- plötzlich Spieler bestrafen
- zufällig Sieg/Niederlage beeinflussen

## Leitregel

> Der AI Director darf Stimmung machen, aber keine unfairen Entscheidungen treffen.

## Priorität

**P2**

---

# 15. Prompt-Battle-Minispiel

## Idee

Im Meetingraum gibt es einen Task, bei dem Spieler Prompts beurteilen oder schreiben müssen.

## Beispieltask

```text
Formuliere einen Prompt, damit der KI-Agent den Legacy-Service beruhigt, ohne die Datenbank zu löschen.
```

## Variante A: Multiple Choice

Spieler wählen aus drei Prompts:

```text
A) Bitte repariere den Legacy-Service vorsichtig und ändere keine produktiven Daten.
B) Optimiere alles maximal. Keine Rückfragen.
C) Lösche alles, was alt aussieht.
```

## Variante B: Freitext

Spieler schreiben einen Prompt. Die KI bewertet humorvoll:

```text
Dieser Prompt ist formal korrekt, aber emotional gefährlich.
```

## Warum gut?

- sehr passend zum Team
- verbindet Spielmechanik und KI-Kultur
- ideal als Meetingraum-Task

## Priorität

**P2**

---

# 16. KI-generierte Ingame-News

## Idee

In der Lobby oder im War Room gibt es eine kleine „Company News“-Anzeige, die KI-generierte Fake-News aus dem Spieluniversum zeigt.

## Beispiele

```text
Breaking: Kaffeemaschine erhält Status als kritische Infrastruktur.
```

```text
Studie zeigt: 87 % aller Bugs entstehen kurz nach „nur ein kleiner Fix“.
```

```text
Legacy-System fordert mehr Respekt und weniger Neustarts.
```

## Warum gut?

- Atmosphäre
- Humor
- keine Gameplay-Risiken
- gut für Lobby-Screen

## Priorität

**P2**

---

# 17. Empfohlene KI-Roadmap

## P0: Erste KI-Features

Diese Features sind leicht umzusetzen und bringen sofort Spaß:

1. KI-Rundenkommentator
2. KI-Endscreen-Awards
3. KI-generierte Eventfeed-Texte
4. KI-generierte Task-Flavor-Texte
5. KI-generierte Meeting-Titel

## P1: Erweiterte KI-Features

6. KI-generierte Fake Logs
7. KI-Assistent im War Room
8. AutoFixBot
9. Rollenbeschreibungen pro Runde
10. KI-generierte Postmortems
11. Daily Challenges

## P2: Spätere Experimente

12. KI-Bot-Spieler
13. AI Director
14. KI-generierte Content-PRs
15. Prompt-Battle-Minispiele
16. Ingame-News

---

# 18. Technische Architektur für KI

## Vorschlag

Im Python-Backend gibt es ein eigenes KI-Modul:

```text
backend/
  app/
    ai/
      ai_client.py
      prompts.py
      schemas.py
      generators.py
      safety.py
      cache.py
```

## Aufgaben der Module

### ai_client.py

- Schnittstelle zum lokalen oder externen LLM
- Request/Response-Handling
- Timeout-Handling
- Fehlerbehandlung

### prompts.py

- Prompt-Templates
- Systemprompts
- Stilvorgaben
- Beispiele

### schemas.py

- Pydantic-Modelle für KI-Ausgaben
- Validierung von JSON-Strukturen

### generators.py

- Funktionen wie:
  - generate_round_summary()
  - generate_awards()
  - generate_event_texts()
  - generate_task_flavor()
  - generate_meeting_title()

### safety.py

- Filter für beleidigende Inhalte
- Begrenzung auf freundlichen Humor
- keine echten Personen angreifen
- keine sensiblen Daten verwenden

### cache.py

- Zwischenspeichern generierter Texte
- Vermeidung unnötiger LLM-Aufrufe
- Pre-Generation vor Rundenstart

---

# 19. Wann KI aufrufen?

## Vor der Runde

Gut für:

- Eventfeed-Textvarianten
- Task-Flavor
- Rollenbeschreibungen
- Meeting-Titel-Pool
- Daily Challenge

## Während der Runde

Nur vorsichtig nutzen.

Besser:

- gecachte Texte anzeigen
- keine blockierenden LLM-Aufrufe
- keine KI in kritischer Game-Loop

## Nach der Runde

Ideal für:

- Rundenbericht
- Awards
- Postmortem
- Statistiken kommentieren

---

# 20. Beispielprompt: Rundenbericht

```text
Du bist der sarkastische, aber freundliche Kommentator eines internen Multiplayer-Spiels namens "Merge Conflict Mayhem".

Das Spiel parodiert Softwareentwicklung, DevOps, KI-Agenten, Meetings, Legacy-Systeme und Release-Chaos.

Erstelle eine kurze, lustige Zusammenfassung der Runde auf Deutsch.

Ton:
- humorvoll
- nerdig
- nicht beleidigend
- keine echten Personen angreifen
- maximal 120 Wörter
- gerne im Stil eines technischen Postmortems

Matchdaten:
{match_json}

Gib zurück:
1. Eine Überschrift
2. Eine kurze Zusammenfassung
3. Eine Root Cause
4. Ein absurdes Action Item
```

---

# 21. Beispielprompt: Eventfeed-Texte

```text
Erzeuge 10 kurze Eventfeed-Texte für ein humorvolles Software-Release-Sabotage-Spiel.

Event-Typ: Coffee Outage

Regeln:
- Deutsch
- maximal 80 Zeichen pro Text
- lustig, aber kurz
- keine Beleidigungen
- kein Fließtext
- jeder Text eine einzelne Zeile
- Tech-/Office-Humor

Beispiele für Stil:
- "Die Kaffeemaschine ist offline. Kritische Infrastruktur betroffen."
- "CoffeeService returned 503."
```

---

# 22. Beispielprompt: Awards

```text
Du vergibst am Ende einer Runde "Merge Conflict Mayhem" lustige Awards.

Nutze diese Matchdaten:
{match_json}

Erzeuge für jeden Spieler genau einen Award.

Regeln:
- Award-Titel maximal 5 Wörter
- Beschreibung maximal 1 Satz
- humorvoll, freundlich, nerdig
- niemanden hart beleidigen
- Deutsch

Gib JSON zurück:
[
  {
    "playerId": "...",
    "awardTitle": "...",
    "awardDescription": "..."
  }
]
```

---

# 23. Beispielprompt: Fake Logs

```text
Erzeuge kurze Fake-Logzeilen für ein Minigame in "Merge Conflict Mayhem".

Kontext:
Ein Spieler analysiert Logs im Serverraum.
Die tatsächliche Ursache ist: {root_cause}

Regeln:
- 6 bis 10 Logzeilen
- Stil: Software-/DevOps-Logs
- humorvoll, aber plausibel
- Deutsch oder englische Log-Syntax gemischt
- keine echten Namen
- keine echten Systeme
- die Ursache soll erkennbar, aber nicht zu offensichtlich sein

Gib nur die Logzeilen zurück.
```

---

# 24. Beispielprompt: Meeting-Titel

```text
Erzeuge einen lustigen Titel für ein Emergency Meeting in "Merge Conflict Mayhem".

Spielkontext:
{recent_events_json}

Regeln:
- Deutsch
- maximal 12 Wörter
- humorvoll
- verdächtigend
- Software-/Office-/DevOps-Bezug
- keine direkten Beleidigungen
- kein Spoiler, wer der Saboteur ist

Gib nur den Meeting-Titel zurück.
```

---

# 25. Wichtigste Regeln für KI im Spiel

1. **KI nicht in den kritischen Game-Loop packen**
2. **KI-Ausgaben validieren**
3. **KI-Texte cachen**
4. **Mechanik bleibt deterministisch**
5. **KI darf keine Spieler unfair verraten**
6. **KI darf keine echten Personen beleidigen**
7. **KI soll freundlich, nerdig und absurd sein**
8. **LLM-Fehler dürfen das Spiel nicht blockieren**
9. **Fallback-Texte bereithalten**
10. **Humor ja, Frust nein**

---

# 26. Beste erste Umsetzung

Für die erste Version würde ich genau diese drei KI-Features bauen:

## 1. KI-Rundenbericht

Nach dem Spiel.

## 2. KI-Awards

Für jeden Spieler ein lustiger Titel.

## 3. KI-Eventfeed-Texte

Vor der Runde generierte Varianten für bekannte Events.

Damit habt ihr KI sichtbar im Spiel, ohne dass Gameplay, Performance oder Fairness leiden.
