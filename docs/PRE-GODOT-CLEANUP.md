# Pre-Godot-Cleanup

**Ziel:** Bevor wir Godot anfangen, soll die Basis sauber stehen. Das umfasst mehr als nur „Features fertig" — auch Code-Hygiene, Tests, Doku, Tooling, operative Robustheit.

Dieses Dokument ist die Checkliste. Reihenfolge ist Vorschlag, nicht Pflicht. Pro Punkt: Aufwand-Schätzung + Begründung.

---

## A. Mit echten Spielern getestet

Bevor wir abstrakte Sauberkeit machen, sollten wir das Spiel **mit deinem Team mindestens 3–5 Runden** gespielt haben. Live-Tests bringen Bugs und UX-Probleme an die Oberfläche, die in synthetischen Tests nicht passieren:

- Latenz von verschiedenen Geräten / Netzen
- Multi-Tab vs. Multi-Maschine (Synchronität, Cookies)
- Was passiert wenn jemand mitten im Meeting reload macht
- Sind die 4 Tasks und 3 Sabotagen genug für 10–12 Min?
- Verstehen Spieler die UI ohne Erklärung?
- Crashes / Memory-Leaks bei längerer Session

**Status:** Server läuft auf https://mcm.3-78-184-97.sslip.io, kann jederzeit getestet werden.
**Aufwand:** 1 Termin mit 4–6 Leuten, ~1h. Bug-Tracking in Issues.
**Priorität:** SOFORT — bestimmt was als nächstes wichtig wird.

---

## B. Code-Hygiene

### B1. Lint + Format

Aktuell: kein ruff, kein prettier, kein pre-commit. Code-Stil ist konsistent weil ich aufpasse, aber automatisch ist es nicht.

- **Python:** `ruff` — formatter (ersetzt black) + linter (ersetzt flake8). Konfig in `pyproject.toml`.
- **JavaScript:** `prettier` (Format) + optional `eslint` (Lint). Konfig in `.prettierrc.json` + `package.json`.
- **Pre-commit-Hook:** `pre-commit` Framework, läuft beide bei jedem Commit.

**Aufwand:** 0.5 Tag.
**Priorität:** Hoch — verhindert Stil-Drift während wir uns um Inhalt kümmern.

### B2. CI auf GitHub Actions

- `.github/workflows/ci.yml`: bei jedem Push/PR `uv run pytest` + Ruff + Prettier
- Status-Badge im README
- (später) Auto-Deploy auf EC2 bei Push auf `main` — eigener Mini-Sprint, nicht jetzt

**Aufwand:** 0.5 Tag.
**Priorität:** Hoch — verhindert Test-Drift.

### B3. Frontend-Tests

Aktuell: 207 Backend-Tests, 0 Frontend-Tests. Frontend-Code ist nicht mehr trivial (meetings.js, sabotages.js, render.js).

- **Stack:** Vitest + happy-dom (oder JSDOM)
- **Coverage-Ziel:** wenigstens Smoke-Tests pro JS-Modul (`Hud`, `MeetingOverlay`, `SabotagePanel`, `EndscreenOverlay`, `TaskList`, `Renderer.computeWallsClient`)
- **Was nicht getestet werden muss:** Browser-WebSocket (Backend deckt's), Canvas-Drawing (visuell)

**Aufwand:** 1 Tag.
**Priorität:** Mittel — gibt uns Sicherheit beim Refactoring.

### B4. Type-Hints im Frontend-JS

Aktuell: kein TypeScript, kein JSDoc. Bei Refactor müssen wir alle Aufrufer manuell finden.

- **Option A:** `// @ts-check` Header + JSDoc-Types pro Modul. Minimaler Aufwand, kein Build.
- **Option B:** Migration zu TypeScript. Saubererer Path, +Build-Step.

**Empfehlung:** A für jetzt; B könnte mit Godot-Sprint zusammen, wenn wir eh eine Pipeline bauen.

**Aufwand:** A = 0.5 Tag, B = 2–3 Tage.
**Priorität:** Mittel.

### B5. Dead Code raus

- `incidentCount`-Feld im Protokoll, immer 0, kein Mechanik-Hook → entweder Tier-1-Incidents bauen ODER Feld entfernen
- Composite-Spritesheets ungenutzt: `buttons.png`, `pansels_ui_frames.png`, `room_labels.png`, `action_ability_icons.png`, `cover.png`, `ingame.png`. Behalten als Asset-Quelle, aber dokumentieren in `assets/CREDITS.md` warum sie da liegen.
- BGM-Tracks (`Cyberpunk Moonlight Sonata.mp3`, `MyVeryOwnDeadShip.ogg`) werden nicht abgespielt → Mute-Toggle bauen ODER entfernen.

**Aufwand:** 0.5 Tag.
**Priorität:** Niedrig, aber leicht.

---

## C. Dokumentation

### C1. `docs/protocol.md` — vollständiger WS-Vertrag

Aktuell: jede Slice hat einzelne Specs, keine konsolidierte Protokoll-Doku. Godot-Implementierer braucht das als Single Source of Truth.

Inhalt:
- Verbindungs-Lifecycle (connect → join → ...)
- Alle Incoming-Messages mit Schema
- Alle Outgoing-Messages mit Schema
- Phase-Übergänge (LOBBY → PLAYING → MEETING → ENDED → LOBBY)
- Error-Codes komplett gelistet
- Beispiel-Sequenzen (Lobby-Flow, Game-Loop, Voting-Flow)

**Aufwand:** 0.5 Tag.
**Priorität:** Hoch (Voraussetzung für Godot).

### C2. `docs/architecture.md`

High-Level-Overview für neue Devs / Godot-Port:
- Warum „Backend autoritativ"
- Tick-Loop-Topologie (20 Hz)
- WebSocket vs. REST
- Map-Daten-Flow (JSON → Server → Client)
- Test-Strategie

**Aufwand:** 0.5 Tag.
**Priorität:** Mittel.

### C3. `docs/contribution-guide.md`

Wie Mitarbeitende beitragen:
- Neue Task hinzufügen (Code + Map-JSON)
- Neue Sabotage hinzufügen (Code + Effekt)
- Neue Map (JSON-Beispiel + Validierung)
- Neuer Eventtext (Sprint-3-Vorbereitung)
- Beispiel-Issues

**Aufwand:** 0.5 Tag.
**Priorität:** Mittel — ermöglicht Team-Beiträge.

### C4. `docs/deploy.md`

Wie deployt man:
- Initial-Setup auf EC2 (Schritte aus dem AWS-Spaß-Sprint dokumentieren)
- Update-Deployment (Tarball-Workflow)
- Server stoppen / starten (Kosten sparen wenn nicht im Test)
- Log-Zugriff (`journalctl -u mcm-server.service`)
- Caddy-Konfig anpassen
- Notfall: Rollback auf vorherigen Tag

**Aufwand:** 0.5 Tag.
**Priorität:** Hoch — sonst weiß künftig keiner wie's geht.

### C5. `docs/dev.md`

Lokale Entwicklung:
- `uv sync` + `uv run uvicorn`
- Tests ausführen
- Branch-Konventionen (`slice/*`, `feat/*`)
- Commit-Konventionen (Conventional Commits)
- Worktree-Workflow (existiert in CLAUDE.md, aber nicht in normalen Docs)

**Aufwand:** 0.25 Tag.
**Priorität:** Mittel.

---

## D. Operationelles

### D1. Deploy-Script

Aktuell deployen wir per ad-hoc Tarball + scp + ssh. Soll automatisiert werden:

- `scripts/deploy.sh` macht Tarball, scp, ssh-restart in einem Befehl
- Kein git-clone auf der EC2 (Deploy-Token vermeiden)
- Optional: Confirm-Prompt vor Deploy (verhindert Versehen)
- Optional: deploy.sh tagged automatisch mit `deploy/<timestamp>`

**Aufwand:** 0.5 Tag.
**Priorität:** Hoch — sonst Code-Updates teuer.

### D2. EC2-Stop-/Start-Scripts

t4g.nano kostet ~$3/Mo bei 24/7. Public-IP ~$3.60/Mo (gilt nur wenn Instance läuft). Wenn wir nicht aktiv testen, EC2 stoppen → keine Compute-Kosten:

- `scripts/server-start.sh` startet die Instance + zeigt IP + restartet die Apps
- `scripts/server-stop.sh` stoppt die Instance
- DNS-Trick: sslip.io-URL muss neu gesetzt werden wenn IP wechselt → entweder Elastic IP (+$3.60/Mo) oder DNS bei jedem Start neu

**Empfehlung:** Elastic IP nehmen, dann ist die URL stabil. Kostet immer $3.60/Mo (auch beim Stoppen).

**Aufwand:** 0.5 Tag.
**Priorität:** Niedrig — nice-to-have.

### D3. Health-Check + Monitoring

- `/healthz`-Endpoint (returns 200 + Server-Stats)
- Caddy oder UptimeRobot pingt regelmäßig
- Optional: Sentry / Loki für Error-Logs

**Aufwand:** 0.5 Tag (basic), 1 Tag (mit Sentry).
**Priorität:** Niedrig — derzeit irrelevant, nur internes Tool.

### D4. Backup-Strategie

EBS-Volume sollte regelmäßig snapshotten. Aktuell: nichts.

- AWS DLM (Data Lifecycle Manager) für tägliche Snapshots
- Aufbewahrung: 7 Tage

**Aufwand:** 0.25 Tag.
**Priorität:** Niedrig (kein Persistent-State auf EC2; alles wichtig im Repo).

---

## E. Stabilität + Edge-Cases

### E1. Reconnect-State-Restore

Aktuell: WebSocket-Close = Spieler raus aus dem Raum, kommt nicht in dieselbe Runde zurück. Bei Flaky-Wifi nervt das.

**Lösung:** Server bewahrt Spieler-Identität (id+name+role+team) für 30 s nach Disconnect; Client kann mit selber Identität rejoin.

**Aufwand:** 1 Tag (Backend + Frontend).
**Priorität:** Mittel — verhindert Frust bei Live-Tests.

### E2. Edge-Cases

- Host disconnected während MEETING-Phase → wer leitet Voting? (aktuell läuft Timer einfach durch, niemand entfernt — okay, aber UI sollte das anzeigen)
- Letzter Spieler verlässt während ENDED-Phase → Raum wird gedroppt, was passiert wenn jemand zurückkommt? (rejoin → neue Lobby)
- 6 Spieler joinen gleichzeitig → Race auf Farb-Palette? (sollte serialisiert sein durch async)
- Spieler in Demo-Mode + zweiter joint → was passiert?

Diese durchgehen, Code-Walkthrough oder Test-Sessions.

**Aufwand:** 0.5–1 Tag.
**Priorität:** Hoch (vor Live-Test mit Team).

### E3. Memory-Leaks / Lifetime

- Werden GameRooms gelöscht wenn alle Spieler weg sind? **Ja** (`drop_if_empty`)
- Werden disconnete WebSockets aus dem ConnectionManager rausgesucht? **Ja** (in `_handle_disconnect`)
- Werden `last_voting_result` / `has_broadcast_end` korrekt resettet? **Ja**

Vermutlich solide, aber: ein Smoke-Test mit 100 Rounds nacheinander wäre Bestätigung.

**Aufwand:** 0.5 Tag (lange Test-Session beobachten).
**Priorität:** Mittel.

---

## F. Mechanik-Vervollständigung (Tier 1)

Bevor wir Godot bauen, soll der Browser-Client feature-stable sein. Sonst doppelte Arbeit beim Porten.

| Slice | Was | Aufwand |
|---|---|---|
| **Eventfeed** | Live-Feed rechts neben dem Canvas | 1 Tag |
| **Incidents-Mechanik** | Drittes Stat + 2 Tasks die's reduzieren + 1 Sabotage die's erzeugt | 1 Tag |
| **Take-Down-Mechanik** | Chaos kann Spieler im Proximity-Radius außer Gefecht setzen | 1 Tag |

Alternative für Incidents: rauswerfen statt einbauen. Wenn unklar ob wir's wollen, lieber raus als halbgar drin.

**Priorität Eventfeed:** Hoch — macht Voting-Phasen verständlich.
**Priorität Take-Down:** Mittel — bringt Eskalations-Spannung.
**Priorität Incidents:** Mittel — macht den 3. Stat sinnvoll, sonst raus damit.

---

## G. Spielerzahl + Multi-Chaos

Master-Doc-Ziel: 4–12 Spieler statt aktuell 2–6. Bei großen Lobbys typischerweise 2 Chaos-Agenten.

| Schritt | Aufwand |
|---|---|
| MAX_PLAYERS auf 12 hochziehen, Color-Palette erweitern (12 Farben + 6 Char-Sprites mehrfach belegen) | 0.5 Tag |
| Rollen-Verteilung skaliert: 2–4 Chaos-Threshold | 0.5 Tag |
| Lobby-UI für 12 Slots optimieren | 0.5 Tag |

**Priorität:** Hoch falls dein Team > 6 ist; sonst Mittel.

---

## H. Map-Editor (Phase 1)

Damit wir mehrere Maps bauen können, ohne JSON-Hand-zu-zeichnen.

- Eigene Seite `/editor`
- Canvas-Tool: Räume rechtecken, Wände + Türen platzieren, Task-Anker droppen, Spawns droppen
- Export als JSON-Download
- Load existierende JSON
- Validierung visualisieren

**Aufwand:** 2–3 Tage.
**Priorität:** Mittel — ohne Editor designen wir Maps trotzdem hand-JSON, aber langsam.

---

## I. Decisions die Godot blocken

Aus `docs/GODOT-TRANSITION.md` Abschnitt 3 und 8:

| # | Frage | Empfehlung (zur Diskussion) |
|---|---|---|
| 1 | Among-Us-Features (Vents, Body+Report, Kill-Anim)? | NEIN für Beta — eigene DevOps-Mechanik reicht |
| 2 | Mobile-Target? | Nein erstmal — Desktop/Web reicht |
| 3 | Art-Stil? | Pixel Art — meistes Asset-Material verfügbar |
| 4 | Art-Quelle? | Asset-Pack + AI-Hybrid — du hast schon AI-PNGs in `images/`, ergänzen mit Pack |
| 5 | Account-System? | Nein — Name + Raumcode wie aktuell |
| 6 | Multi-Map-Support? | Ja — kommt mit dem Editor |

Sven entscheidet. Empfehlungen sind nur das.

---

## Empfohlene Reihenfolge (Total ~2–3 Wochen)

```text
Woche 1: Code-Hygiene + Doku-Block
  Mo-Di:  B1 (Lint) + B2 (CI) + B3 (Frontend-Tests)
  Mi:     B5 (Dead code) + D1 (Deploy-Script)
  Do-Fr:  C1 (protocol.md) + C2 (architecture.md) + C4 (deploy.md) + C3 + C5

Woche 2: Mechanik-Vervollständigung + Stabilität
  Mo:     E2 (Edge-Cases) + E3 (Memory-Smoke)
  Di:     F-Eventfeed
  Mi:     F-Incidents (oder rauswerfen)
  Do:     F-Take-Down
  Fr:     E1 (Reconnect)

Woche 3: Map-Editor + Decisions
  Mo-Di:  G (Spielerzahl 4–12)
  Mi-Fr:  H (Map-Editor Phase 1)
  Fr-Sa:  I (Godot-Decisions mit Sven)
```

Optional Woche 0: A (Test mit echten Spielern), bringt eventuelle Quick-Fixes für Woche 1.

---

## Definition of „sauber"

Wenn wir Godot starten, sollte gelten:

- ☐ Alle Tests grün, lokal und CI
- ☐ Lint/Format clean (kein Drift)
- ☐ `docs/protocol.md` ist die Wahrheit über das WS-Protokoll
- ☐ `docs/contribution-guide.md` reicht aus, dass jemand neue Tasks/Sabotagen/Maps beitragen kann ohne Hilfe
- ☐ Deploy-Script funktioniert, dokumentiert
- ☐ Eventfeed + Take-Down sind drin (oder bewusst weggelassen)
- ☐ Reconnect funktioniert
- ☐ Spielerzahl matcht Master-Doc-Ziel (4–12)
- ☐ Map-Editor existiert mindestens als Phase 1
- ☐ Mit echten Leuten getestet, größere Bugs gefixt
- ☐ Godot-Decisions aus I gefällt, in `docs/GODOT-TRANSITION.md` festgehalten

Erst dann ist „die Basis ist sauber" wahr.
