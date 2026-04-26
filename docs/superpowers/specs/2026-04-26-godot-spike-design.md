# Godot-Client Bootstrapping-Spike — Design

**Status:** Spec für Implementierung bereit
**Datum:** 2026-04-26
**Roadmap-Verortung:** Vorbereitung für Tier 3, läuft parallel zu Tier 1.9 / Tier 2 ohne deren Reihenfolge zu ändern.

---

## 1. Ziel

Einen schmalen Godot-4-Client gegen den existierenden FastAPI-Backend bauen, der:

1. die im `docs/PROTOCOL.md` dokumentierten Annahmen real validiert,
2. Backend-Doku-Lücken aufdeckt und als `docs/CLIENT.md` festschreibt,
3. ein arbeitsfähiges Godot-Projekt-Skelett hinterlässt, auf dem der spätere Tier-3-Sprint aufsetzen kann.

Kein Production-Client, keine Sprites, kein Gameplay-Feature. Bewusst minimal.

## 2. Nicht-Ziele

- **Keine** Tasks, HUD, Sabotagen, Voting, Endscreen, Sounds, Animations.
- **Keine** Tilemap, keine Sprites, keine Asset-Pipeline (Tier 3.0.x).
- **Kein** Web-Export, keine CI-Integration des Godot-Builds.
- **Keine** Änderung am Browser-Client oder am Backend-Verhalten.
- **Kein** Vorziehen von Tier 2 — Among-Us-Features bleiben im Browser geplant.

## 3. Architektur-Verortung

> Python entscheidet. Der Client zeigt nur an.

Der Spike erweitert *nicht* das Backend. Er konsumiert das existierende WebSocket-Protokoll als zweiter Client neben dem Browser. Server bleibt autoritativ; Godot rendert empfangene Snapshots, sendet Inputs.

## 4. Repo-Layout

Mono-Repo. Begründung: Protokoll-Drift zwischen Server und Client ist das größte Risiko eines Spikes, dessen Zweck Protokoll-Validierung ist. Mono-Repo eliminiert es.

```
godot/
├── project.godot
├── .gitignore
├── README.md
├── scenes/
│   ├── main.tscn           # Entry: Connect-UI + Lobby-Log
│   └── debug_world.tscn    # Map-Linien + Spieler-Boxen
├── scripts/
│   ├── ws_client.gd        # WebSocketPeer-Wrapper
│   ├── protocol.gd         # Konstanten, Message-Type-Strings
│   └── debug_renderer.gd   # _draw() für Map + Players
```

**Top-Level `.gitignore`** ergänzen um `godot/.godot/` und `godot/exports/`. Der `.godot/`-Ordner ist der Editor-Cache und wird nicht versioniert. `*.import`-Files werden **bewusst committet** — sie enthalten persistente UID-Referenzen, ohne die Asset-Links beim Klonen brechen.

**Godot-Version:** 4.3 LTS. Tier 3 wird ein langer Sprint, LTS reduziert Breakage. Web-Export (Tier 3.13) ist in 4.3 stabil verfügbar.

**Branch:** `slice/godot-spike`. **Worktree:** `.worktrees/godot-spike/` (per Repo-Konvention).

## 5. `docs/CLIENT.md` — neue Doku

**Name:** `CLIENT.md`, nicht `GODOT.md`. Inhalte sind Server-Erwartungen an *jeden* Client. Der Browser-Client soll auch gegen diese Doku verifizierbar sein; eine Godot-spezifische Doku würde fragmentieren.

**Inhalt im Spike-Scope:**

### 5.1 Koordinaten- & Skalierungs-Konvention

- Server-Welt: 4800×3200 Pixel (siehe Tier 1.0 Roadmap-Eintrag), Origin oben-links, Y wächst nach unten.
- Godot-Default: identisch — Origin oben-links, Y-Achse nach unten. Keine Y-Flip nötig.
- Spike-Render: `Camera2D` mit Zoom-Faktor, 1 Server-Pixel = 1 Godot-Pixel. Keine Tilemap.
- Player-Kollisions-Radius (20 px) und Task-Interaction-Radius (40 px) als Konstanten in `scripts/protocol.gd`.
- Tilemap-Cell-Size, Tilemap-Layer-Strategie: **bewusst offen** — kommt mit Tier 3.3.

### 5.2 Tick- & Interpolations-Modell

- Server tickt 20 Hz: ein `game_state` alle ~50 ms.
- Client darf Bewegung **nicht** simulieren. Server ist autoritativ.
- Render-Strategie: Buffer der letzten 2 Snapshots, lerp zwischen ihnen über die 50-ms-Lücke.
- `player_input` darf max. 20 Hz raus (Throttle). Senden bei Input-Change *oder* spätestens jeden 50-ms-Tick.

### 5.3 Reconnect-Verhalten

- Server bewahrt Spieler-Identität 30 s nach Disconnect (siehe Slice 0.10).
- Client-Erwartung: bei Reconnect erneut `join_room(roomCode, playerName)` schicken — Server reaktiviert die Session statt neuen Spieler anzulegen.
- `room_joined.playerId` nach Reconnect kann sich ändern. Spike testet das explizit.
- Verhalten nach 30+ s Disconnect: Spike beobachtet und doku'd.

### 5.4 Bewusst ausgeklammert (eigene Slices)

- **Asset-Mapping** (Sprites/Animations pro Spieler/Task/Sabotage) → Tier 3.0.1–3.0.3.
- **Sound-Trigger-Liste** (welches Server-Event triggert welchen SFX) → Tier 3.11.

`docs/CLIENT.md` ist normativ. Wenn Server-Verhalten widerspricht, ist eines von beiden falsch — wir entscheiden bewusst, was angepasst wird.

## 6. Spike-Implementierung — vier inkrementelle Schritte

Jeder Schritt einzeln testbar, jeder eigener Commit, jeder muss grün gegen lokalen `uvicorn` laufen, bevor der nächste startet.

### Schritt 1: Connect + Lobby (Konsole-only)

**Ziel:** Protokoll-Handshake validieren.

- `ws_client.gd`: Wrapper um `WebSocketPeer` mit `connect_to_url(url)`, `send(type, payload)`, Signal `message_received(type, payload)`.
- `main.tscn`: minimaler UI mit Eingabefeldern Raumcode + Name + Connect-Button + Log-Bereich.
- Nach Connect: `join_room` senden, `room_joined` und `lobby_state` ins Log schreiben.
- WS-URL aus UI-Feld oder Env-Variable, **nicht** hartcoded. Default `ws://localhost:8000/ws`.

**Acceptance:** Browser-Tab + Godot-Client joinen denselben lokalen Raum, beide sehen sich in der Browser-Spielerliste, Godot-Log zeigt beide Namen aus `lobby_state`.

### Schritt 2: Map-Debug-Render (kein Movement)

**Ziel:** Koordinaten-Konvention real validieren.

- `debug_world.tscn` lädt nach `room_joined` die `map`-Payload aus dem Cache.
- `debug_renderer.gd` zeichnet via `_draw()`:
  - Räume als dünne weiße Rechtecke, Label = `roomId`.
  - Walls als rote Linien.
  - Spawn-Punkte als grüne Kreuze.
  - Task-Anker als gelbe Kreise.
- `Camera2D` zentriert auf den ersten Spawn-Punkt, Zoom so dass Map vollständig im Viewport ist.

**Acceptance:** Godot-Fenster zeigt das gleiche Map-Layout wie der Browser-Editor unter `/editor`. Visueller Vergleich ergibt keine verzerrten Wände, keine off-by-one-Fehler beim Skalieren.

### Schritt 3: Player-Boxen

**Ziel:** Snapshot-Render-Pipeline validieren ohne Interpolations-Komplexität.

- Pro Spieler aus `game_state.players` eine farbige Box (20×20 px, Farbe = `player.color`) mit Namen darüber.
- Eigene Box durch `room_joined.playerId` identifiziert, leicht hervorgehoben (Outline).
- **Keine Interpolation** in diesem Schritt — direkter Snapshot-Render. Ruckelig ist gewollt.

**Acceptance:** Browser-Player bewegt sich, Godot-Box folgt an gleicher Position (visueller Vergleich).

### Schritt 4: Input + Interpolation

**Ziel:** Tick-/Interpolations-Modell validieren.

- Eingabe (WASD, Pfeiltasten optional) → State-Objekt `{up, down, left, right}` an Server mit 20-Hz-Throttle.
- Snapshot-Buffer: letzte 2 `game_state`-Frames behalten, Render-Position = lerp zwischen ihnen über 50 ms (`(now - prev_snapshot_time) / 50ms`).
- Throttle-Strategie für `player_input`: Senden bei Input-Change ODER spätestens alle 50 ms, je nachdem was zuerst kommt.

**Acceptance:** Godot-Player bewegt sich auf Browser-Tab korrekt sichtbar; Browser-Player bewegt sich in Godot smooth (kein wahrnehmbares Stottern bei 20-Hz-Tick).

## 7. Test-Setup

- **Lokales Backend:** `uv run uvicorn app.main:app --reload` auf Port 8000. Godot connectet zu `ws://localhost:8000/ws`.
- **Manueller Test pro Schritt:** ein Browser-Tab als Host, ein Godot-Client als zweiter Spieler.
- **Live-Smoke:** finaler Test gegen `wss://game.prod-is-lava.dev/ws` — nur als Sanity-Check, nicht für Iteration.
- **Keine automatisierten Godot-Tests im Spike.** GUT-Framework wäre Overkill für vier Acceptance-Pfade.

## 8. Erwarteter Output

Nach Spike-Abschluss im Repo:

1. **`docs/CLIENT.md`** populiert mit *real validierten* Werten:
   - Bestätigte Camera2D-Zoom-Werte für 4800×3200 → typische Viewport-Größen.
   - Tatsächlich gemessene Throttle-Frequenz für `player_input`.
   - Reconnect-Verhalten innerhalb 30 s und nach 30+ s, in beiden Fällen verifiziert.
   - Liste der **Backend-Doku-Lücken**, die der Spike aufgedeckt hat, als Folge-Slices vorgeschlagen.

2. **`godot/`** funktionierendes Skelett:
   - Öffnet in Godot 4.3 Editor ohne Fehler.
   - `scenes/main.tscn` als Entry-Point, Connect-Flow funktioniert lokal *und* gegen Live.
   - Code-Dokumentation auf einem Niveau, dass ein anderer Dev die Anbindung versteht.

3. **`godot/README.md`** — fünfzeiler: Projekt öffnen, Connect lokal/live, Tasten-Bindings im Spike, aktuelle Limitationen.

4. **Commit-Hygiene:**
   - Branch `slice/godot-spike` in Worktree `.worktrees/godot-spike/`.
   - Konventionelle Commits pro Schritt 1–4 plus separate Doku-Commits.
   - Kein Merge zu `main` ohne Roadmap-Update + User-Review.

## 9. Done-Kriterium

- Sven kann `cd godot && godot --editor .` öffnen, „Run" drücken, sieht die Map gerendert und kann seinen Spieler bewegen, der auch im parallel offenen Browser-Tab korrekt erscheint.
- `docs/CLIENT.md` ist von echten Beobachtungen geprägt, nicht von Spekulation.
- Liste der „vor Tier 3 in der Backend-Doku zu schließenden Lücken" existiert in `docs/CLIENT.md`.

## 10. Folge-Arbeit (nicht Teil des Spikes)

- **Tier 1.9** (In-Game-Menü) und **Tier 2** (Among-Us-Features im Browser) wie in der Roadmap geplant.
- **Tier 3.0.1** Asset-Pipeline-Entscheidung erst wenn Tier 2 fertig.
- **Tier 3-Sprint** verwendet den Spike als Fundament — Schritt 1–4 werden zu Tier 3.1–3.4 ausgebaut, Asset-Pipeline und Among-Us-Features kommen oben drauf.
- **`docs/ROADMAP.md`** wird nach Spike-Abschluss um ein „Spike-Erkenntnisse"-Kapitel ergänzt, das Tier 3 schärft. Der Spike ersetzt nichts; er verbessert die Tier-3-Spec.

## 11. Risiken und offene Fragen

- **Risiko:** Camera2D-Zoom-Strategie könnte bei späterer Tilemap-Migration (Tier 3.3) nicht 1:1 übernehmbar sein. *Mitigation:* In `docs/CLIENT.md` notieren, dass Spike-Strategie debug-only ist, Tilemap-Strategie offen.
- **Risiko:** Reconnect-Test übersieht Edge-Case (z.B. Reconnect während Phase MEETING). *Mitigation:* Spike testet Reconnect explizit in PLAYING-Phase, MEETING-Phase als Folge-Slice.
- **Offen:** WebSocketPeer-API hat in Godot 4.x mehrere Iterationen durchlaufen. Der GDScript-Beispielcode in `docs/PROTOCOL.md §10` muss gegen 4.3 verifiziert werden — falls API-Drift, Beispiel im Spike aktualisieren und PROTOCOL.md fixen.
