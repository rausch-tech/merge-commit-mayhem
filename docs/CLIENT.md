# Client Expectations

> Server-seitige Erwartungen an *jeden* Client (Browser jetzt, Godot ab Tier 4).
> Diese Doku ist normativ. Wenn Client-Verhalten widerspricht, ist eines von beiden
> falsch — wir entscheiden bewusst, welches angepasst wird.
>
> Diese Datei wird durch den Godot-Spike (siehe `superpowers/specs/2026-04-26-godot-spike-design.md`)
> mit *real gemessenen* Werten gefüllt. Sektionen mit `[VERIFY:Phase-X]` werden im Spike validiert.
>
> **Status (Stand 2026-04-27):** Spike-Code auf `slice/godot-spike`, runtime-verifiziert in
> Godot 4.6 (Sven's Setup: WSL2 = Backend, Windows = Godot). Test 1 (Connect), Test 2
> (Map-Layout), Test 3 (Movement) sind grün durchgelaufen. Test 4 (Reconnect) noch offen.
> Werte unten sind real gemessen, nicht mehr theoretisch.

## 1. Koordinaten- und Skalierungs-Konvention

- **Server-Welt:** 4800×3200 Pixel (`maps/default.json` → `size`).
- **Origin:** oben-links (0,0). X wächst nach rechts, Y wächst nach unten.
- **Godot-Default:** identisch — Origin oben-links, Y nach unten. Keine Y-Flip nötig.
- **Render-Strategie (Spike):** `Camera2D` mit dynamisch berechnetem Zoom, 1 Server-Pixel = 1 Godot-Pixel. Keine Tilemap.
- **Spike-Viewport:** 1080×720 (1.5:1, gleiche Aspect-Ratio wie Map 4800×3200). Bei 16:9-Viewport entstand 16% Whitespace links/rechts — durch absichtliche Aspect-Anpassung vermieden.
- **Camera-Fit-Formel:** `zoom = min(viewport_w/map_w, viewport_h/map_h)`. Aktueller Wert: `Vector2(0.225, 0.225)` → Map fillt 100% beider Achsen. Siehe `godot/scripts/debug_renderer.gd::_fit_camera_to_map`.
- **Player-Kollisions-Radius:** 20 px (siehe `app/game/walls.py:PLAYER_COLLISION_RADIUS`).
- **Task-Interaction-Radius:** 40 px (siehe `app/game/tasks.py:TASK_INTERACTION_RADIUS`).
- **Tilemap-Cell-Size:** offen, kommt mit Tier 4.3 (Map-Loader → Tilemap-Layer).

## 2. Tick- und Interpolations-Modell

- **Server-Tick:** 20 Hz → ein `game_state` alle ~50 ms (`app/main.py:TICK_HZ`).
- **Client-Regel:** Bewegung NICHT simulieren. Server ist autoritativ.
- **Render-Strategie (validiert im Spike):** Snapshot-Buffer (letzte 2 Frames) + lerp zwischen prev und curr mit `alpha = clamp((now - curr_t) / dt + 1.0, 0, 1)`. Bewegung visuell smooth bei 20-Hz-Server-Tick. Siehe `godot/scripts/debug_renderer.gd::_process()`.
- **`player_input` Throttle (validiert im Spike):** Sende-Bedingung `(input geändert) UND (>= 50 ms seit letztem Send)`. Bei stillem Input kein Spam, bei Input-Change max. 50 ms Latenz. Siehe `godot/scripts/input_sender.gd::SEND_INTERVAL`.

## 3. Reconnect-Verhalten

- **Server-Verhalten:** behält Spieler-Identität 30 s nach Disconnect (Slice 0.10, `RECONNECT_GRACE_SECONDS`).
- **Client-API:**
  - **Erst-Join:** `join_room` mit `roomCode` + `playerName`.
  - **Reconnect:** `rejoin` mit `roomCode` + `playerId` (NICHT erneutes `join_room`). `[VERIFY:Phase-6]`
- **Reconnect-Antwort:** `room_joined` mit derselben `playerId`, gefolgt von `private_role` (falls mid-round) und phasenpassend `lobby_state` ODER `game_state`.
- **Client-Empfehlung:** `playerId` nach jedem `room_joined` lokal speichern (Browser: `localStorage`, Godot: `user://`-Datei). Bei Verbindungsverlust → reconnect → `rejoin` mit gespeichertem Wert. Wenn Server `REJOIN_NOT_AVAILABLE` meldet, Fallback auf `join_room`.
- **Verhalten nach 30+ s:** Server lehnt `rejoin` mit `REJOIN_NOT_AVAILABLE` ab. `[VERIFY:Phase-6]`

## 4. Bewusst ausgeklammert (eigene Slices)

- **Asset-Mapping** (Sprites/Animations pro Spieler/Task/Sabotage) → Tier 4.0.1–4.0.3.
- **Sound-Trigger-Liste** (welches Server-Event triggert welchen SFX) → Tier 4.11.
- **Mini-Game-API** (Tier 3, seit 2026-04-27 auf `main`): die WS-Messages `mini_game_started` / `mini_game_input` / `mini_game_state` / `mini_game_completed` sowie das pluggable Modal-Pattern (`static/minigames/`) sind Browser-only. Der Godot-Client muss in Tier 4.6 das gleiche API umsetzen — bis dahin ignoriert der Spike Mini-Game-Messages.

## 5. Backend-Doku-Lücken (vom Spike entdeckt)

Pre-Spike wurden bereits folgende Lücken in `docs/PROTOCOL.md` und `docs/maps.md` geschlossen (Commit `19ecbbf` auf `main`):

- Map-Größe in `docs/maps.md` korrigiert (4800×3200 statt 2400×1600).
- `rejoin`-Message in `docs/PROTOCOL.md §4` ergänzt.
- `lobby_state`-Schema um `availableMaps`/`selectedMapId`/`map` erweitert (Multi-Map seit Tier 1.8).
- `game_state` um `incidents`, `events`, `bodies`, `players.isConnected` erweitert.
- `private_state`-Message neu dokumentiert (per-Chaos-Take-Down-Cooldown).
- `REJOIN_NOT_AVAILABLE` in der Error-Code-Tabelle ergänzt.

**Während des Runtime-Tests neu entdeckt (2026-04-27):**

- **`localhost` IPv6-Falle bei uvicorn-Default:** Windows resolved `localhost` zu `::1` (IPv6) zuerst. uvicorn bindet per Default nur IPv4 (`127.0.0.1` oder `0.0.0.0`). Godot's WebSocketPeer wartet ~50 s auf TCP-Timeout bevor er auf IPv4-Resolve zurückfällt. **Empfehlung für `docs/PROTOCOL.md §10` (Godot-Implementation):** Clients sollten `127.0.0.1` (oder die WSL-IP) statt `localhost` benutzen, oder uvicorn zusätzlich auf IPv6 binden lassen (`uv run uvicorn app.main:app --host ::`). Spike's Connect-UI hat `ws://127.0.0.1:8000/ws` als Default.

## 7. Godot-Setup-Lessons-Learned (für Tier 4)

Diese Punkte sind nicht „Backend-Doku-Lücken", sondern Godot-spezifische Stolpersteine, die der Spike aufgedeckt hat. Tier 4.1 sollte sie direkt richtig setzen:

- **`display/window/subwindows/embed_subwindows = false`:** Godot 4 default-embedded Run-Window im Editor hebelt `stretch_mode` aus und macht das Spike-Fenster eingeengt. Mit `false` startet das Spiel als separates OS-Window.
- **`display/window/size/mode = 2` (Maximized):** Spike startet maximiert, gibt der Map maximalen Platz.
- **`stretch_mode = "viewport"` + matching Aspect-Ratio:** Map ist 4800×3200 (1.5:1). Wenn Viewport-Aspect davon abweicht, gibt's Whitespace. Wir haben `viewport_width=1080, viewport_height=720` (1.5:1) gesetzt. Tier 4 mit Tilemap kann das überdenken (z.B. 16:9-Viewport mit HUD-Overlay rechts neben der Map).
- **`get_viewport_rect()` vs. `get_window().size`:** Mit `stretch_mode=viewport` ist `get_viewport_rect()` die richtige Größe für Camera-Fit (= konfigurierte Viewport-Größe). Mit `stretch_mode=canvas_items` würde man `get_window().size` nehmen müssen. Wechselwirkung dokumentiert in `godot/scripts/debug_renderer.gd::_fit_camera_to_map`.
- **Project-Reload nach Code-Changes:** Godot cached compiled GDScript-Classes hartnäckig. Nach `class_name`-Ergänzungen oder Method-Signatur-Änderungen: **Project → Reload Current Project** oder gar Editor neu starten. Sonst läuft alter Code.
- **WSL-File-Access via UNC:** Performance ist OK für Spike-Größe, aber bei großen Asset-Importen (Tier 4.0.x mit Sprite-Packs) lieber Repo lokal nach `C:\` clonen. Backend bleibt in WSL — nur Godot-Files müssen schnell zugreifbar sein.

## 8. Headless Godot in WSL (CI + Pre-Commit-Checks)

Zusätzlich zum visuellen Editor auf Windows läuft eine **Headless-Godot-Binary in WSL** für schnelle Parse-/Syntax-Checks ohne F5-Cycle. Catched 80% der Fehler die sonst erst im Editor auftauchen würden (`class_name`-Cache, Type-Mismatches, Method-Signaturen).

### Install (einmalig, ~2 Minuten)

```bash
mkdir -p ~/godot-headless && cd ~/godot-headless
curl -L -o godot.zip "https://github.com/godotengine/godot/releases/download/4.6-stable/Godot_v4.6-stable_linux.x86_64.zip"
unzip -q godot.zip && rm godot.zip
ln -sf ~/godot-headless/Godot_v4.6-stable_linux.x86_64 ~/.local/bin/godot
godot --version   # erwartet: 4.6.stable.official.<sha>
```

`~/.local/bin` muss in `$PATH` sein (Fedora/Ubuntu-Default).

### Helper-Script

`scripts/godot-check.sh` läuft `--check-only` über alle GDScript-Files im Spike:

```bash
./scripts/godot-check.sh           # silent ok / verbose fail
./scripts/godot-check.sh -v        # zeigt Engine-Banner pro Datei
```

Exit-Code 0 = alle OK, 1 = mindestens ein Parse-Error. CI-tauglich.

### Was der Headless-Godot kann

- **Parse-Check** (`--check-only --script foo.gd`): catcht Syntax/Type-Errors, fehlende Methoden, falsche Class-Refs.
- **Project-Boot-Check** (`--headless --path . --quit`): prüft ob `project.godot` valide ist und alle `class_name`-Globals registriert werden.
- **Headless-Runs** (für Tier 4): Scenes mit `--quit-after N` starten, Logs greppen — automatisierte Acceptance ohne menschen-im-Loop.

### Was er NICHT kann

- Kein Rendering (kein GPU, kein Display in WSL2 ohne WSLg). Visuelle Tests bleiben Sven-am-Editor.
- Kein WebSocket-Connect-Test in WSL → Backend (würde gehen, aber overkill für reinen Parse-Check).

## 6. Test-Plan (für Runtime-Verification mit Godot)

Sobald Godot 4.6 lokal installiert ist, einmal alle vier Akzeptanzpfade durchlaufen und die Marker oben mit gemessenen Werten ersetzen. Voraussetzung: Backend läuft (`uv run uvicorn app.main:app --reload`), Browser-Tab unter `http://localhost:8000/` joint Raum `ABCD` mit Name "Browser".

**Sven's Setup (Windows + WSL2, Distro `FedoraLinux-43`):** Backend in WSL, Godot-Editor auf Windows. Project-Path im Godot-Project-Manager: `\\wsl.localhost\FedoraLinux-43\home\sr\se\mcm\.worktrees\godot-spike\godot\project.godot`. Connect-URL bleibt `ws://localhost:8000/ws` (WSL2 forwarded localhost). Falls Connect failed: in WSL `ip addr show eth0` → `inet`-IP statt `localhost` verwenden. Details siehe `godot/README.md`.

### Test 1 — Connect & Lobby (validiert §1, §3 partiell)
1. Godot-Editor → Project Manager → Import `godot/project.godot`.
2. F5. Im Spike-Fenster URL `ws://localhost:8000/ws`, Room `ABCD`, Name `Godot`, Connect.
3. **Erwartung:** Log zeigt `[ws] connected`, `[room_joined]`, `[lobby_state] players=[Browser, Godot]`. Browser-Tab zeigt zwei Spieler in der Lobby.

### Test 2 — Map-Layout (validiert §1)
1. Test 1 muss durchgelaufen sein.
2. **Erwartung:** Spike-Fenster zeigt 6 farbige Räume, rote Wand-Linien, blaue Door-Marker, grüne Spawn-Kreuze, gelbe Task-Anker. Layout entspricht dem Browser-Editor unter `http://localhost:8000/editor`.
3. **Falls verzerrt:** Camera2D-Zoom in `godot/scenes/debug_world.tscn` justieren, gemessenen Wert in §1 (Default-Zoom-Faktor) eintragen.

### Test 3 — Player + Movement (validiert §2)
1. Browser-Host: "Spielstart" mit Demo-Mode (oder weitere Tabs joinen).
2. **Erwartung:** Im Spike erscheinen farbige Boxen mit Namen. Eigene Box hat weißen Outline.
3. WASD/Pfeiltasten halten — eigene Box bewegt sich smooth, Browser-Box folgt smooth.
4. **Falls ruckelig:** Snapshot-Buffer-Logik in `debug_renderer.gd::_process()` debuggen.

### Test 4 — Reconnect (validiert §3)
1. Spike laufen lassen, im Log `playerId=<X>` notieren.
2. **Test 4a:** Spike schließen, sofort neu starten mit gleichem Namen → wird derselbe Spieler reaktiviert? Ergebnis in §3 eintragen.
3. **Test 4b:** `main.gd::_on_connected` temporär auf `rejoin` umstellen mit hartcodierter `playerId`, neu testen.
4. **Test 4c:** 35 s warten nach Spike-Schließen, dann neu starten — `REJOIN_NOT_AVAILABLE`?

Nach allen vier Tests:
- `[VERIFY:Phase-X]`-Marker durch echte Werte ersetzen
- Sektion 5 um neu entdeckte Lücken erweitern
- `main.gd` zurück auf `join_room` reverten falls für Test 4b geändert
