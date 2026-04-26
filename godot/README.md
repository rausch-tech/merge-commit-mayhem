# MCM Godot Spike

Bootstrapping-Spike für den späteren Tier-4-Godot-Client.

> **Hinweis (2026-04-27):** Die Roadmap wurde nach Spike-Erstellung restrukturiert
> — Mini-Games sind jetzt Tier 3 (auf `main` shipped), Godot-Migration ist Tier 4.
> Funktional ändert das am Spike nichts. `docs/ROADMAP.md` zeigt den aktuellen Stand.

## Was das ist

Schmaler Godot-4.3-Client, der gegen den existierenden FastAPI-Backend
WebSocket spricht. Validiert Protokoll-Erwartungen, kein Gameplay.

Vollständige Doku: `../docs/superpowers/specs/2026-04-26-godot-spike-design.md`
und `../docs/CLIENT.md` (inkl. Test-Plan in Sektion 6).

## Voraussetzungen

- **Godot 4.3 LTS** ([Download](https://godotengine.org/download))
- **MCM-Backend** läuft lokal: `cd .. && uv run uvicorn app.main:app --reload`

## Projekt öffnen

1. Godot 4.3 starten.
2. Project Manager → "Import" → `godot/project.godot` wählen.
3. "Import & Edit".

## Spike starten

Im Editor: F5 (Run Project). Es öffnet sich ein Fenster mit Connect-UI.

- **WebSocket URL:** `ws://localhost:8000/ws` (default; oder `wss://game.prod-is-lava.dev/ws` für Live-Smoke)
- **Room Code:** vier Buchstaben, z.B. `ABCD`
- **Player Name:** beliebig
- **Connect** klicken

Browser-Tab parallel öffnen unter `http://localhost:8000/`, mit gleichem
Room Code joinen — beide Clients sehen sich gegenseitig.

## Tasten-Bindings (im Spiel)

- **WASD** oder **Pfeiltasten:** Bewegung

## Was der Spike kann

- WebSocket-Connect, `join_room`, `room_joined`, `lobby_state` lesen
- Map als Debug-Linien rendern (Räume, Wände, Spawns, Task-Anker)
- `game_state.players` als farbige Boxen mit Namen rendern, Self-Highlight
- `player_input` mit 20-Hz-Throttle senden
- Snapshot-Interpolation für smoothes Movement

## Was der Spike NICHT kann

- Tasks halten, Sabotagen triggern, Voting, Endscreen
- Sprites, Animationen, Tilemaps
- Sound
- Web-Export-Build
- Auto-Reconnect (Test 4b in `docs/CLIENT.md` § 6 zeigt manuelles Vorgehen)

## Code-Struktur

- `scenes/main.tscn` — Connect-UI (Entry-Point)
- `scenes/debug_world.tscn` — World mit Camera2D, Renderer, Input-Sender
- `scripts/protocol.gd` — Konstanten und Message-Type-Strings
- `scripts/ws_client.gd` — WebSocketPeer-Wrapper mit Signals
- `scripts/main.gd` — Connect-UI-Driver, Message-Routing, World-Switch
- `scripts/debug_renderer.gd` — `_draw()` für Map und Spieler, Snapshot-Buffer
- `scripts/input_sender.gd` — Tastatur-Capture mit 20-Hz-Throttle

## Nächste Schritte (Tier 4)

Siehe `../docs/ROADMAP.md` Tier 4. Der Spike ist die Basis — Tier 4.1
übernimmt Connect+Lobby aus diesem Skelett, Tier 4.3 ersetzt den
DebugRenderer durch Tilemap, Tier 4.4 ersetzt Player-Boxen durch Sprites,
Tier 4.6 implementiert das in Tier 3 etablierte Mini-Game-API in Godot.
