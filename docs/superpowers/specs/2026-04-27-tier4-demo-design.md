# Tier 4 Demo-Durchstich — Design

**Status:** Implementation läuft (Nacht-Spike, autonom).
**Datum:** 2026-04-27
**Roadmap-Verortung:** Tier 4 (Godot-Migration), Demo-fähiges MVP — nicht der vollständige Tier-4-Sprint.
**Branch:** `slice/tier4-3d-demo`, abgeleitet von `slice/godot-3d-spike` (rebased auf main).

---

## 1. Ziel

Bis morgen früh ein **demo-fähiger 3D-Godot-Client**, mit dem Sven seinem Team eine technische Vision von Tier 4 zeigen kann. Wow-Faktor priorisiert: Spielfeld, Charaktere, Bewegung sollen visuell überzeugen und „echt aussehen".

**Demo-MVP (Must-Have):**

1. **Lobby-Scene** — Connect zu Backend (Raumcode + Name), Spielerliste live aus `lobby_state`, Host-Spielstart-Button.
2. **3D-Office-Welt** — alle 6 Räume aus `maps/default.json` (Open Space, Meeting Room, Kitchen, Server Room, War Room, Legacy Basement) mit Walls, Floors, Door-Cutouts. Zonen visuell differenziert via Floor-Materialien und Möblierung.
3. **Charakter-System** — KayKit Dummy mit AnimationLibrary aus `Rig_Medium_MovementBasic.glb`. Idle ↔ Walk Transition basierend auf Bewegung. Multi-Player aus `game_state.players`.
4. **Smooth Movement** — WASD lokal, Server-autoritative Position via `player_input` + `game_state`-Snapshot-Interpolation.
5. **HUD-Overlay** — Stats (Release-Progress, Pipeline-Stability, Coffee-Level, Incidents, Timer), Rolle, Spielerliste am Rand.
6. **In-Game-Menü** — ESC öffnet Overlay mit Lobby verlassen / (Host: Runde beenden).
7. **Web-Export-Build** — fertig deployt-fähiges HTML-Bundle für die Demo.

**Out-of-Scope für die Nacht (kommen mit folgenden Tier-4-Slices):**

- Task-Hold-Mechanik + Mini-Game-Modale (Tier 4.6)
- Sabotage-Buttons (Tier 4.7)
- Voting-Overlay (Tier 4.8)
- Endscreen mit Stats (Tier 4.9)
- Vents / Lights / Comms (Tier 4.10)
- Sound-Integration (Tier 4.11)

Server-seitig wird **nichts** angefasst — der existierende FastAPI-Backend bleibt unverändert. Demo-Mode ist via Browser-Lobby aktivierbar (überspringt 4-Spieler-Check).

---

## 2. Architektur

> **Python entscheidet. Der Client zeigt nur an.** (unverändert)

- **3D-Top-Down-Pattern (Option C aus Spike-2):** Server bleibt 2D (4800×3200 Welt-Koordinaten), Godot rendert 3D-Models. Server schickt `(x, y)`, Godot platziert Player bei `(x, 0, y)`. Wand-Linien werden zu 3D-Wall-Meshes extrudiert.
- **Camera:** Camera3D Orthographic von schräg-oben mit Player-Follow. Bewusst flache Perspektive für „Among-Us-Style", aber leicht angeschrägt damit Charaktere + Möbel räumlich wirken.
- **Asset-Pipeline:** KayKit Bits (CC0) für Floor-Tiles + Furniture + Charakter; Walls + Türen werden procedural aus Map-JSON als Box-Meshes generiert.
- **Coord-System:** Server-Pixel = Godot-World-Units. Bei 4800×3200 Server-Welt ergibt das 4800×3200 Godot-Units — sehr groß. Skalierung-Faktor: `WORLD_SCALE = 0.01` → Map ist 48×32 Godot-Units, Player-Movement-Speed entsprechend skaliert.
- **Animation-Library:** `Rig_Medium_MovementBasic.glb` als `AnimationLibrary` importiert via `.import`-File-Override. AnimationTree nutzt `Walking_A` (oder `Walking_B`) für Bewegung, `T-Pose` als Idle-Fallback (kein Idle-Clip im Bundle, schauen ob's was anderes gibt).

---

## 3. Scene-Struktur

```
godot-3d/
├── scenes/
│   ├── main.tscn               (Entry — Lobby-UI)
│   ├── world.tscn              (3D-Game-World, gespawnt nach Spielstart)
│   ├── character.tscn          (Multi-Player-Spawnable mit AnimationTree)
│   ├── hud.tscn                (Overlay über world.tscn)
│   └── pause_menu.tscn         (ESC-Overlay)
├── scripts/
│   ├── protocol.gd             (Konstanten + Message-Type-Strings, neu)
│   ├── ws_client.gd            (WebSocket-Wrapper, von Spike-1 portiert)
│   ├── main.gd                 (Lobby-UI-Driver, ws-Connect, Spielerliste)
│   ├── world.gd                (Game-Scene, baut Map, spawnt Players, syncs game_state)
│   ├── map_builder.gd          (Map-JSON → 3D-Walls/Floors/Möbel)
│   ├── character.gd            (Player-Node mit AnimationTree, Idle/Walk)
│   ├── input_sender.gd         (WASD → player_input, von Spike-1 portiert)
│   ├── hud.gd                  (Stats, Timer, Rolle, Spielerliste)
│   └── pause_menu.gd           (ESC-Overlay-Logic)
└── assets/
    ├── character/Dummy.glb + Rig_Medium_MovementBasic.glb (CC0)
    ├── floor/floor_kitchen.* (CC0, plus weitere für Raum-Differenzierung)
    └── furniture/{desk,chair,monitor,...} (CC0)
```

---

## 4. Server-Protokoll-Nutzung (existing, unverändert)

Wir nutzen die bereits dokumentierten Messages aus `docs/PROTOCOL.md`:

- **Outgoing:** `join_room`, `start_game`, `player_input`, `return_to_lobby`
- **Incoming:** `room_joined` (mit `map`-Payload), `lobby_state` (mit `availableMaps`/`selectedMapId`/`map`), `private_role`, `game_state` (Phase, Stats, Players, Tasks, Sabotages), `error`
- **Ignoriert für Demo:** `task_hold_*`, `trigger_sabotage`, `cast_vote`, `mini_game_*`, Vents, Bodies, etc. — alle nicht-relevanten Messages werden via Default-Case logged aber nicht verarbeitet.

---

## 5. Wichtige Tech-Entscheidungen

### Animation-Setup

Godot 4.6 unterstützt `AnimationLibrary`-Import via `.import`-File-Setting `import_as_skeleton_bones=false` und `animation/import_as_animation_library=true`. Wir setzen das per Hand für `Rig_Medium_MovementBasic.glb`, dann lädt Godot die Animations als reine `AnimationLibrary` ohne neue Mesh-Skeleton-Hierarchie. Die Library wird auf den `AnimationPlayer` der `Dummy.glb`-Scene angebunden via Code.

### Wall-Extrusion aus Map-JSON

`wallLines` definieren `axis: x|y, position: int, doors: [{center, width}]`. Algorithmus pro WallLine:

1. Volle Wand als ein Box-Mesh erzeugen (Höhe = 2.5 Units, Dicke = 0.2 Units).
2. Pro Door eine Sub-Box ausgeschnitten via `CSGCombiner3D` mit `OPERATION_SUBTRACTION`.
3. Resultat ins `world.tscn` als Wall-Container packen.

Alternativ einfacher: Wand als 3 Segmente zwischen den Doors rendern (kein CSG nötig). Wir gehen mit Variante 2 für Speed of Implementation und Reliability.

### Floor-Tiling pro Raum

Jeder Raum bekommt eine eigene Plane mit eigener Material/Texture. Eine zentrale Textur (`furniturebits_texture.png` oder Custom) reicht für den ersten Wurf; Differenzierung via Modulate-Color pro Raum.

### Character-Sync

Auf jedem `game_state` mit phase=playing iterieren wir `payload.players`:

- Neuer Player → instantiate `character.tscn`, store in `_players_by_id` Dict
- Bestehender Player → push_snapshot mit Position + isAlive
- Player nicht mehr in Liste → free Node, remove aus Dict

Lerp-Interpolation läuft pro Character-Instance basierend auf prev/curr Snapshot (50ms-Tick analog Spike-1).

### Camera

Camera3D als Kind eines `CameraRig` Node3D, das jeden Frame zur Player-Position interpoliert (smooth follow, nicht hart). Camera-Offset von Player: `Vector3(0, 30, 25)` (Welt-Units), `look_at(player.position)`.

### HUD

HUD ist `CanvasLayer` über der `world.tscn`. Reine 2D-UI, separater Render-Layer von 3D-Welt. Updates kommen aus `game_state` via Signal vom `world.gd`.

---

## 6. Demo-Strategie

Sven zeigt morgen:

1. **Lobby:** Browser-Tab + Spike-Client beide joinen `ABCD`. Beide Spielerliste live synced.
2. **Spielstart** mit Demo-Mode (1-Spieler-Modus). Wechsel zu 3D-World.
3. **Map-Render:** alle 6 Räume sichtbar von oben, Möbel platziert, Charakter steht in einem Spawn-Punkt.
4. **Movement:** WASD bewegt smooth, Camera folgt.
5. **HUD:** Timer läuft, Stats sichtbar, Rolle sichtbar.
6. **Multi-Player-Demonstration:** zweiter Browser-Tab joint, Spike zeigt zweiten Charakter live.
7. **Web-Build:** `http://<wsl-ip>:8080/tier4.html` läuft im Browser, gleicher Look-and-Feel.

**Wow-Highlights:**

- KayKit-Charakter mit Walk-Animation (nicht T-Pose-Slide)
- Vollständiges Office mit allen 6 Räumen
- Smooth Camera-Follow
- HUD-Overlay mit echtem Game-State

---

## 7. Risiken und Mitigations

- **AnimationLibrary-Import:** ist Godot-Editor-Klickerei. Mitigation: ich schreibe das `.import`-File händisch (kennen das Format aus Spike-2-Erfahrung) plus fallback auf T-Pose falls Library nicht lädt.
- **CSG-Performance:** CSGCombiner3D ist nicht für Real-time gedacht. Mitigation: Walls werden once-off im `_ready()` gebaut und dann „baked" zu MeshInstance3D via `bake_static_mesh()`. Falls das nicht reicht, fallback auf segmentierte Plain-Boxes.
- **Asset-Loading-Zeit:** mit allen Möbeln + Floors + Charakter könnte initial-Boot lang werden. Mitigation: nur essentielle Möbel pro Demo (~15 Pieces gesamt, nicht 50+).
- **Web-Export-Performance:** Spike-2 hat gezeigt dass Mobile-Renderer im Browser fliegt. Mit mehr Geometry könnte's eng werden. Mitigation: WebGL2 prüfen, ggf. weniger Möbel im Web-Build.
- **WebSocketPeer-Reconnect:** Nach Reload kann Connect haken. Mitigation: explicite `close()` vor neuem `connect_to_url`.

---

## 8. Done-Kriterium

Sven kann morgen früh:

1. `cd .worktrees/tier4-3d-demo && uv run uvicorn app.main:app --reload` (Backend, gleicher main wie heute)
2. Browser-Tab `http://localhost:8000/` → joinen Raum „DEMO"
3. Windows-Godot-Editor → Project öffnen unter `\\wsl.localhost\FedoraLinux-43\home\sr\se\mcm\.worktrees\tier4-3d-demo\godot-3d\project.godot`, F5
4. Spike-Client connectet zu `ws://127.0.0.1:8000/ws`, joint Raum „DEMO" mit Name „Sven"
5. Browser-Host klickt Spielstart (Demo-Mode aktiviert)
6. Spike-Client wechselt zu 3D-World, Charakter spawn'd, WASD-Movement smooth, Walk-Animation läuft
7. HUD zeigt Stats und Timer
8. Optional: 2-3 weitere Browser-Tabs für Multi-Player-Demonstration

Plus: `godot-3d/exports/tier4.html` ist im Web-Browser unter `http://<wsl-ip>:8080/tier4.html` lauffähig.
