# Merge Conflict Mayhem — Game Overview

Eine kompakte, vollstaendige Beschreibung des Spiels, mit der jemand der noch nie eine Runde gesehen hat sofort versteht worum es geht — und wo sinnvoll Ideen einbringen kann. Stand: 2026-04-26, Tier 0–3 komplett, vor Godot-Migration.

**Live-Server:** https://game.prod-is-lava.dev
**Repo:** https://github.com/rausch-tech/merge-commit-mayhem

---

## Was ist das eigentlich?

Ein **Social-Deduction-Multiplayer-Spiel fuer Tech-Teams**, gedacht fuer 8–12 Leute in einer 8–15-Minuten-Runde (perfekte Mittagspausen-Laenge). Mechanisch ein Among-Us-Klon — aber statt Raumstation ein **Software-Buero mitten in einem Release**, statt Crewmates und Imposter ein **Release-Team und Chaos-Agenten**, statt „elektrische Schalter reparieren" Tasks wie **„Pull Request reviewen"** und **„CI/CD reparieren"**, statt Sabotagen wie „Lichter aus" Sabotagen wie **„PagerDuty-Storm"** und **„Slack-Down"**.

Die Spannungsquelle ist die selbe wie bei Among Us: **du weisst nicht, wer auf deiner Seite ist**. Das Release-Team will die Pipeline gruen halten und das Release rausschiessen. Die Chaos-Agenten arbeiten heimlich dagegen — sie koennen Sabotagen triggern, Mitspieler still „takedownen" (Among-Us-Kill, hier euphemistisch „Force-Reboot") und durch Server-Tunnel ventilieren.

Spielziel ist **nicht** primaer Tech-Kompetenz beim Brettspielen, sondern **soziales Lesen der anderen** — wer war wo, wer behauptet was, wer hat eine plausible Story. Die DevOps-Thematik liefert nur die Witze und die diegetische Begruendung dafuer dass jemand „mal eben in den Server-Raum musste".

---

## Wie laeuft eine Runde ab?

1. **Lobby**: Alle joinen mit einem 4-stelligen Raumcode, Host startet die Runde. Server verteilt geheim Rollen — die Mehrheit ist Release-Team, 1 Chaos-Agent bei <7 Spielern, 2 Chaos-Agenten ab 7 Spielern.
2. **Spiel laeuft** (15 Minuten Default): Jeder bewegt sich frei durch die 4800×3200-Map, sieht alle anderen Spieler in Echtzeit, aber **nicht** ihre Rolle.
3. **Release-Team** erledigt Tasks (Pull Requests reviewen, Tests fixen, Logs analysieren, Kaffee auffuellen, ...) — jede erfuellte Task pusht den **Release-Progress-Balken** Richtung 100%.
4. **Chaos-Agenten** triggern Sabotagen die den Release-Progress runterziehen oder das Spiel storen, ventilieren durch heimliche Tunnel zwischen Raeumen, und koennen einzelne Mitspieler im Proximity-Radius eliminieren.
5. **Wenn ein toter Spieler entdeckt wird** (Body-Discovery), kann jeder Lebende den Body reporten → das triggert ein **Emergency Meeting**: alle stoppen, ueber die Verdaechtigen wird abgestimmt, einer wird (oder keiner) entfernt. Jeder Spieler hat **ein** Emergency-Meeting pro Runde, das er selbst aus dem War-Room heraus auslosen kann (auch ohne Body).
6. **Win-Conditions** (in Reihenfolge first-to-fire):
   - Pipeline kollabiert (`pipelineStability <= 0`) → **Chaos gewinnt**
   - Alle Chaos-Agenten ausgevoted → **Release-Team gewinnt**
   - Release-Progress erreicht 100% → **Release-Team gewinnt**
   - 15 Minuten abgelaufen → **Chaos gewinnt**

---

## Rollen + Teams

**Release-Team** (Mehrheit, „Crewmates" in Among-Us-Sprech):

- Macht Tasks, repariert Sabotagen
- Versucht Chaos-Agenten zu identifizieren und auszuvoten
- Beispielrollen: `developer`, `qa_lead`, `scrum_master`

**Chaos-Agenten** (1–2 je nach Spielerzahl, „Imposter"):

- Triggert Sabotagen aus einer rollen-spezifischen Auswahl
- Kann Take-Down (eliminieren) im 40-px-Proximity-Radius mit 25-s-Cooldown
- Kann Vents nutzen (Teleport-Tunnel zwischen Raeumen, fuer alle anderen unsichtbar)
- Kann selbst voten (typischer Move: deflect blame)
- Beispielrollen: `vibe_coder`, `rogue_consultant`

Jeder Spieler erfaehrt seine Rolle privat ueber den `private_role`-Frame — niemand sonst sieht sie bis zum Endscreen.

**Spectator-Mode** (Tier 2.6): Eliminierte Spieler werden zu Geistern. Sie koennen weiterhin Tasks erledigen und damit dem Release-Team helfen (auch nach Tod — wichtig fuer das Zielgefuehl), sehen andere Geister, koennen sich frei bewegen — aber nicht mehr abstimmen oder reporten. Lebende sehen sie nicht.

---

## Mechaniken im Detail

### Tasks (Release-Team)

Acht Tasks verteilt auf der Map. Spieler laeuft hin, drueckt **E** in 40-px-Naehe. Drei Wege wie eine Task abgewickelt wird:

- **Hold-E** (klassisch): N Sekunden gedrueckt halten, fertig. Einfach, wenig Spannung.
- **Mini-Game** (Tier 3): Ein Modal oeffnet sich, der Spieler muss eine kleine Server-validierte Aufgabe loesen, dann ist sie fertig. Sichtbar fuer andere als „Sven ist gerade beschaeftigt".

Aktuell gibt es fuenf verschiedene Mini-Game-**Mechanik-Patterns**:
| Pattern | Beispiel | Aktion |
|---|---|---|
| Sequencing | Test-Suite reparieren | Klick die fehlerhaften Tests in numerischer Reihenfolge |
| Pairing | Server-Racks verkabeln | Tap Source links, Tap Destination rechts mit gleicher Farbe |
| Timing | Kaffee einschenken | Tasse fuellt sich zyklisch — STOP im Sweet-Spot 70-100 % |
| Filter-by-Criterion | Logs analysieren | Klick alle ERROR-Zeilen, lass WARN/INFO in Ruhe |
| Subset-by-Constraint | Scope reduzieren | Tickets aus Sprint nehmen bis Story-Points unter Budget — Priority-Tickets nicht anfassen |

Drei Tasks (`review_pr`, `calm_legacy_service`, `write_release_notes`) laufen aktuell noch ueber Hold-E.

### Sabotagen (Chaos)

Acht Sabotagen, jeweils mit eigenem Cooldown:

- **CI/CD Rot** — pipelineStability sofort -20
- **Kaffee leer** — coffeeLevel auf 0, Spieler werden langsam bis Coffee-Task erledigt
- **Mandatory Meeting** — alle laufen 5 s halbe Geschwindigkeit (Diegese: alle muessen ins Daily)
- **Merge Conflict Storm** — pipelineStability langsamer Drain
- **Fake Customer Request** — Incidents +20
- **Flaky Tests** — pipelineStability -10
- **PagerDuty-Storm** (Tier 2.4) — Vignette: Spieler sehen nur ~150 px Radius um sich; Repair-Panel im Server-Room
- **Slack-Down** (Tier 2.5) — Tasks + andere Sabotagen werden blockiert; Repair-Panel im War-Room

Reparatur-Sabotagen (PagerDuty-Storm, Slack-Down) haben einen **physischen Reparatur-Punkt** auf der Map. Jeder lebende Spieler in 50-px-Naehe kann sie reparieren.

### Vents (Chaos)

Vorab definierte Tunnel-Punkte auf der Map. Chaos-Agent steht in 50-px-Naehe → druckt **V** → cycelt durch die verbundenen Ziel-Vents → wird sofort dorthin teleportiert. Andere Spieler sehen die Vents zwar (sie sind Map-Architektur), koennen sie aber nicht nutzen.

Aktuell 3 Vents auf der Default-Map, vernetzt zwischen Kitchen, Office und Legacy-Basement. Strategischer Wert: schnell von einer Sabotage-Trigger zum Tatort, oder weg vom Body, oder hinter eine plausible Alibi-Position.

### Take-Down (Chaos)

Chaos in 40-px-Naehe eines lebenden Mitspielers → Button „Force-Reboot" → Target wird `isAlive=false`, ein Body bleibt liegen, Cooldown 25 s. Server validiert alles authoritativ.

### Body-Discovery + Report

Sobald ein Body von einem **lebenden** Spieler entdeckt wird (in Reichweite), kann er ihn reporten → Meeting wird ausgeloest, alle Bodies werden gerade weggeraeumt. Wenn niemand reportet, bleibt der Body liegen — taktisch interessant fuer Chaos.

### Voting

Im Meeting (60 s) sehen alle die lebenden Spieler. Jeder lebende kann **EIN** Stimme abgeben (entweder fuer einen Spieler oder Skip). Re-Vote ueberschreibt. Nach 60 s oder wenn alle voted haben → Resolve: hoechste Stimmen-Anzahl wird eliminiert (Skip oder Tie → niemand). Geister duerfen nicht voten.

---

## Map

**Default-Map**: 4800×3200 px, sechs benannte Raeume:

- Open Space (zentraler Hub)
- Server Room (Tasks: deployment, logs; Repair-Panel: PagerDuty-Storm)
- Kitchen (Task: Kaffee)
- Meeting Room (Tasks: scope, release notes)
- Legacy Basement (Task: Legacy-Service)
- War Room (einziger Ort von dem aus Emergency-Meeting ausgeloest werden kann; Repair-Panel: Slack-Down)

Alles als **JSON** in `maps/default.json` — Raum-Geometrien, Wand-Linien, Tueren, Spawn-Punkte, Task-Anker, Sabotage-Panels, Vent-Konnektoren. Ein Map-Editor unter `/editor` erlaubt nicht-coderischen Map-Bau — Tier 1.7. Multi-Map-Support: Host waehlt aus dem Lobby-Dropdown welche Map gespielt wird.

---

## Tech-Stack

- **Backend**: Python 3.12 + FastAPI + Pydantic v2 + asyncio. 20-Hz-Tick-Loop. WebSocket-Endpoint `/ws`. Authoritativ fuer **allen** State.
- **Frontend** (aktueller Web-Client): Vanilla HTML/CSS/JS + `<canvas>`-Renderer. Keine Build-Pipeline, keine Frameworks.
- **Naechste Stufe**: Godot 4 als polished Primary-Client (Tier 4) — Browser-Client bleibt als Web-Fallback und Reference-Implementation. Asset-Pack-Entscheidung dafuer laeuft gerade beim Team.
- **Hosting**: AWS EC2 t4g.nano in eu-central-1, Caddy als HTTPS-Reverse-Proxy, GitHub-Actions-Auto-Deploy auf jedem `main`-Push.
- **Tests**: 466 Backend-Tests (pytest), 37 Frontend-Tests (vitest).
- **Performance**: Tick-Compute p99 = 0.6 ms bei 12 Spielern (~84× Headroom auf das 50-ms-Tick-Budget). 1 MB/s Server-Egress fuer eine volle Lobby. Server-CPU ist nicht der Bottleneck.

Architektur-Nordstern: **Python entscheidet, der Client zeigt nur an.** Nichts an Spiellogik im Frontend. Wenn eine Idee Spiellogik in den Client drueckt, geht sie zurueck.

---

## Aktueller Stand (2026-04-26)

**Was funktioniert auf Live:**

- 4–12 Spieler joinen, Lobby mit Map-Auswahl, Multi-Chaos ab 7 Spielern
- Komplettes Among-Us-Feature-Set: Movement, Tasks, Sabotagen, Vents, Take-Down, Body-Discovery, Report, Voting, Endscreen mit Rollen-Reveal, Spectator-Mode
- 5 von 8 Tasks haben Mini-Games (siehe Pattern-Tabelle oben)
- Mobile-Touch-Controls (Quick-Hack, spielbar aber nicht polished)
- Reconnect (30 s Grace nach Disconnect)
- Map-Editor unter `/editor`

**Was offen ist:**

- 3 Tasks ohne Mini-Game (review_pr, calm_legacy_service, write_release_notes) — bleiben Hold-E
- **Sabotage-Console-Mechanik** — aktuell kann Chaos Sabotagen von ueberall triggern; sollte wie Among Us an spezifische Sabotage-Console-Punkte gebunden werden
- **Asset-Pack-Entscheidung** fuer den Godot-Sprint (laeuft beim Team)
- **Godot-Migration** als naechster grosser Brocken (5–7 Wochen)
- Spaeter: BGM, Account-System, Skins, Custom-Lobby-Links, erweitertes Rollen-Set

---

## Wo Brainstorming-Input besonders hilft

Wenn ihr die Runde durchgespielt habt oder die Doku gelesen, sind das die offenen Achsen mit dem groessten Hebel — bringt Ideen mit:

1. **Neue Tasks und Mini-Games** (groesster Spannungstreiber)

   - Welche „Pull Request reviewen", „Logs analysieren", „Sprint-Trim"-Aequivalente fehlen noch im DevOps-Alltag?
   - Mechanik-Patterns: Sequencing, Pairing, Timing, Filter, Subset — gibt es eine sechste Klasse die wir noch nicht haben? (z. B. Memory-Replay, Drag-Reorder, Math-Puzzle?)

2. **Neue Sabotagen** (Chaos-Hebel)

   - Welche DevOps-Schmerzen gibt es noch die als 8-Sekunden-Sabotage funktionieren?
   - Ideen: „Production-Hotfix" (alle muessen sofort in Server-Room), „Zoom-Anrufer" (ein zufaelliger Spieler kann 10 s nicht laufen), „Legal-Review" (Tasks brauchen 2x so lang)
   - Welche brauchen Repair-Panel und welche laufen einfach durch?

3. **Erweiterte Rollen** (Asymmetrie statt Standard-Crewmate/Imposter)

   - Aus der Roadmap-Liste: Data Wizard, Shadow Admin, Incident Commander, Caffeine Collector, Bug Squasher, Legacy Oracle, Scrum Master mit Spezial-Faehigkeiten
   - Spezial-Aktionen: Auto-Fix-Bot (Release-Team-Helper), Distract (Chaos-Helper), Speed Boost, Coffee Run, Scan Logs, Rollback, etc.
   - Welche Rolle laesst eine ganze Spielsession anders aussehen?

4. **Map-Themen** (neue Maps fuer Variety)

   - Default ist generisches Office. Was sollten weitere Maps sein? Konferenz? Hackathon-Garage? Daten-Center? Open-Plan vs. Cubicles?
   - Map-Editor existiert — Beitrag muss kein Code sein

5. **Insider-Gags und Eventtexte**

   - Eventfeed-Strings sind kuratierbar — Pool ohne Code-Touch erweiterbar
   - Welche Tech-Memes, welche Branchenwitze, welche „das ist mir mal echt passiert"-Storys?

6. **Mobile-/Cross-Device-Spielflow**

   - Aktuell Quick-Hack auf Touch — gibt es Use-Cases fuer Tablet vs. Desktop in der gleichen Lobby?
   - Lobby-Link-Sharing: was wuerde das schnellste Setup ermoeglichen (QR an die Wand, Slack-Bot, etc.)?

7. **Game-Feel-Polish**
   - Was im Live-Test ist „technisch ok aber fuehlt sich nicht gut an"?
   - Animations-Wuensche, Sound-Wuensche, Hint-Wuensche

---

## Wie ihr selbst spielen koennt

1. https://game.prod-is-lava.dev oeffnen (geht auf Phone, Tablet, Desktop)
2. Raumcode ausdenken (4 Buchstaben), Namen eintragen, „Join"
3. Andere joinen mit gleichem Code
4. Host (= erster im Raum) startet die Runde, optional vorher Map waehlen
5. WASD/Arrows zum Bewegen, **E** fuer Tasks, **F** fuer Sabotage-Repair, **V** fuer Vent (nur Chaos), Klick auf Sabotage-Buttons (nur Chaos)
6. Bei Body-Fund: Report-Button. Bei Verdacht ohne Body: ins War-Room laufen und Emergency-Meeting

Mindestens 4 Spieler fuer eine sinnvolle Runde, Sweet-Spot 6–10.

---

## Was wir NICHT vorhaben (bewusste Scope-Limits)

- Keine Persistenz von Spielern (kein Login, kein Profil — bewusst minimal fuer interne Mittagspausen)
- Kein Free-Form-Chat (Voice-Chat passiert auf Slack/Discord nebenher; im Spiel nur Eventfeed + Voting)
- Keine Microtransactions, keine Werbung, kein Open-Public-Release vor Tier 7

Brainstorming sollte sich an dem Setup orientieren — Vorschlaege die das brechen sind nicht falsch, aber waeren ein Pivot.

---

## Quellen / Weiterlesen

- `docs/ROADMAP.md` — sechs Tier in Reihenfolge, was done und was offen
- `docs/PROTOCOL.md` — vollstaendiger WebSocket-Vertrag (fuer alle die einen alternativen Client basteln wollen)
- `docs/ARCHITECTURE.md` — wie das Backend organisiert ist + Performance-Numbers
- `docs/maps.md` — Map-JSON-Schema (fuer Map-Bauer)
- `merge_conflict_mayhem_project/docs/` — historisches Design-Paket, Inspiration aber nicht aktuell
