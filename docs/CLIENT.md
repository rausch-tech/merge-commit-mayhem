# Client Expectations

> Server-seitige Erwartungen an *jeden* Client (Browser jetzt, Godot ab Tier 3).
> Diese Doku ist normativ. Wenn Client-Verhalten widerspricht, ist eines von beiden
> falsch — wir entscheiden bewusst, welches angepasst wird.
>
> Diese Datei wird durch den Godot-Spike (siehe `superpowers/specs/2026-04-26-godot-spike-design.md`)
> mit *real gemessenen* Werten gefüllt. Sektionen mit `[VERIFY:Phase-X]` werden im Spike validiert.

## 1. Koordinaten- und Skalierungs-Konvention

- **Server-Welt:** 4800×3200 Pixel (`maps/default.json` → `size`).
- **Origin:** oben-links (0,0). X wächst nach rechts, Y wächst nach unten.
- **Godot-Default:** identisch — Origin oben-links, Y nach unten. Keine Y-Flip nötig.
- **Render-Strategie (Spike):** `Camera2D` mit Zoom-Faktor, 1 Server-Pixel = 1 Godot-Pixel. Keine Tilemap.
- **Default-Zoom-Faktor (Spike, Viewport 1280×720):** `Vector2(0.225, 0.225)` zeigt die Map vollständig zentriert. `[VERIFY:Phase-3]`
- **Player-Kollisions-Radius:** 20 px (siehe `app/game/walls.py:PLAYER_COLLISION_RADIUS`).
- **Task-Interaction-Radius:** 40 px (siehe `app/game/tasks.py:TASK_INTERACTION_RADIUS`).
- **Tilemap-Cell-Size:** offen, kommt mit Tier 3.3.

## 2. Tick- und Interpolations-Modell

- **Server-Tick:** 20 Hz → ein `game_state` alle ~50 ms (`app/main.py:TICK_HZ`).
- **Client-Regel:** Bewegung NICHT simulieren. Server ist autoritativ.
- **Render-Strategie:** Snapshot-Buffer (letzte 2 Frames) + lerp über die 50-ms-Lücke. `[VERIFY:Phase-5]`
- **`player_input` Throttle:** max. 20 Hz (alle 50 ms). Senden bei Input-Change ODER spätestens jeden 50-ms-Tick. `[VERIFY:Phase-5]`

## 3. Reconnect-Verhalten

- **Server-Verhalten:** behält Spieler-Identität 30 s nach Disconnect (Slice 0.10, `RECONNECT_GRACE_SECONDS`).
- **Client-API:**
  - **Erst-Join:** `join_room` mit `roomCode` + `playerName`.
  - **Reconnect:** `rejoin` mit `roomCode` + `playerId` (NICHT erneutes `join_room`). `[VERIFY:Phase-6]`
- **Reconnect-Antwort:** `room_joined` mit derselben `playerId`, gefolgt von `private_role` (falls mid-round) und phasenpassend `lobby_state` ODER `game_state`.
- **Client-Empfehlung:** `playerId` nach jedem `room_joined` lokal speichern (Browser: `localStorage`, Godot: `user://`-Datei). Bei Verbindungsverlust → reconnect → `rejoin` mit gespeichertem Wert. Wenn Server `REJOIN_NOT_AVAILABLE` meldet, Fallback auf `join_room`.
- **Verhalten nach 30+ s:** Server lehnt `rejoin` mit `REJOIN_NOT_AVAILABLE` ab. `[VERIFY:Phase-6]`

## 4. Bewusst ausgeklammert (eigene Slices)

- **Asset-Mapping** (Sprites/Animations pro Spieler/Task/Sabotage) → Tier 3.0.1–3.0.3.
- **Sound-Trigger-Liste** (welches Server-Event triggert welchen SFX) → Tier 3.11.

## 5. Backend-Doku-Lücken (vom Spike entdeckt)

Pre-Spike wurden bereits folgende Lücken in `docs/PROTOCOL.md` und `docs/maps.md` geschlossen (Commit `19ecbbf` auf `main`):

- Map-Größe in `docs/maps.md` korrigiert (4800×3200 statt 2400×1600).
- `rejoin`-Message in `docs/PROTOCOL.md §4` ergänzt.
- `lobby_state`-Schema um `availableMaps`/`selectedMapId`/`map` erweitert (Multi-Map seit Tier 1.8).
- `game_state` um `incidents`, `events`, `bodies`, `players.isConnected` erweitert.
- `private_state`-Message neu dokumentiert (per-Chaos-Take-Down-Cooldown).
- `REJOIN_NOT_AVAILABLE` in der Error-Code-Tabelle ergänzt.

Weitere Lücken, die der Spike *neu* entdeckt, werden hier aufgelistet (Phase 6 füllt das nach Spike-Ende).
