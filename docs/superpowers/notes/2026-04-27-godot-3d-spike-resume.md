# Godot-3D-Bootstrapping-Spike (Spike-2) — Stand und Resume-Notes

**Branch:** `slice/godot-3d-spike` im Worktree `.worktrees/godot-3d-spike/`
**Datum:** 2026-04-27
**Vorgänger:** Spike-1 (`slice/godot-spike`) — 2D-Debug-Render. Spike-2 testet 3D-Pattern als Alternative für Tier 4.

---

## TL;DR

3D-Top-Down-Pattern (Option C aus dem 2D-vs-3D-Brainstorming) ist **doppelt validiert**:

- **Native Run** in Windows-Godot 4.6: Floor-Tiles + 3 Office-Desks + Char + WASD-Movement + Camera-Follow funktionieren. KayKit-Assets (CC0) rendern sauber, Mobile-Renderer fliegt auf Sven's GPU. Screenshot in `feedback/`.
- **Web-Export** via headless `godot --export-release`: 40 MB Initial-Load (37 MB WASM, 2.5 MB PCK), Browser-Performance vergleichbar zu nativ. SharedArrayBuffer + COEP/COOP-Headers via `scripts/godot-3d-serve.py` als kleiner Python-Server.

**Heißt für Tier 4:** das Risikoreichste (Web-Performance-3D, Asset-Pipeline) ist abgehakt. Tier 4-Plan kann auf 3D-Top-Down umgestellt werden statt 2D-Tilemap.

---

## Wenn du wieder einsteigst

1. **Worktree wechseln:**
   ```bash
   cd /home/sr/se/mcm/.worktrees/godot-3d-spike
   git status     # erwartet: clean
   ```
2. **Native test:** Windows-Godot 4.6 → Project Manager → Import →
   `\\wsl.localhost\FedoraLinux-43\home\sr\se\mcm\.worktrees\godot-3d-spike\godot-3d\project.godot`
   F5 → maximiertes Fenster mit Floor + Möbel + Char, WASD bewegt.
3. **Web-Export:**
   ```bash
   # Setup einmalig:
   # ~/.local/share/godot/export_templates/4.6.stable/ muss befüllt sein
   # (siehe docs/CLIENT.md §8 für die Templates-Install-Anleitung)
   cd /home/sr/se/mcm/.worktrees/godot-3d-spike/godot-3d
   mkdir -p exports
   godot --headless --export-release "Web" exports/spike2.html ./project.godot
   ```
4. **Web-Server starten:**
   ```bash
   cd /home/sr/se/mcm/.worktrees/godot-3d-spike/godot-3d/exports
   python3 ../../scripts/godot-3d-serve.py 8080
   ```
5. **Browser:** `http://localhost:8080/spike2.html` (von Windows-Browser via WSL2-Forwarding).

---

## Was im Branch liegt

```
godot-3d/
├── project.godot               # 4.6, Mobile-Renderer, Maximized, embed_subwindows=false
├── export_presets.cfg          # Web-Export-Preset (handgeschrieben, kein Editor-Override nötig)
├── assets/
│   ├── character/Dummy.glb + Rig_Medium_MovementBasic.glb (KayKit Prototype, CC0)
│   ├── floor/floor_kitchen.{gltf,bin} + restaurantbits_extra.png (KayKit Restaurant, CC0)
│   └── furniture/{desk,chair_desk_A,monitor}.{gltf,bin} + furniturebits_texture.png
├── scenes/test_world.tscn      # Root Node3D + Camera3D (Orthographic, size=18) + Sun
└── scripts/test_world.gd       # baut Floor 12x12, platziert 3 Desks/Chairs/Monitors,
                                # spawnt Dummy, WASD → Position-Update + Y-Rotation,
                                # Camera-Follow

scripts/
└── godot-3d-serve.py           # COEP+COOP Python-HTTP-Server fuer Web-Export

docs/superpowers/notes/
└── 2026-04-27-godot-3d-spike-resume.md   # dieses Dokument
```

---

## Commits (Stand 2026-04-27)

```
TBD bce7f26 chore(godot-3d): gitignore top-level feedback/, accept canonicalized project.godot
66e2536 feat(godot-3d): Spike-2 — KayKit 3D test scene with WASD movement
```

Plus zwei pending Files: `godot-3d/export_presets.cfg`, `scripts/godot-3d-serve.py` — kommen mit dem Resume-Notes-Commit.

---

## Was Spike-2 NICHT kann (Tier-4-Themen)

- **Backend-Connect:** keine WebSocket-Anbindung. Server-2D-State → Godot-3D-Position-Mapping ist Tier-4-Aufgabe.
- **Animation:** Dummy gleitet als T-Pose. AnimationLibrary-Setup (Editor-Klickerei oder Import-Hook-Skript) kommt mit Tier 4.4.
- **Walls aus Map-JSON:** Floor ist aktuell hardcoded 12×12 Grid. Wall-Extrusion aus `wallLines` + Door-Cutouts ist Tier 4.3.
- **Multi-Player-Render:** Nur ein Char auf der Map. Player-Liste-Iteration aus `game_state` kommt mit Tier 4.4.
- **Mini-Game-API:** Spike-2 ignoriert es komplett. Tier 4.6 implementiert die `mini_game_*`-Messages für 3D-Modale.

---

## Bekannte Beobachtungen aus dem Live-Test

- **Camera fast top-down:** mit `CAMERA_OFFSET = (0, 14, 10)` ist der Winkel etwa 54°, sieht aber durch Orthographic-Projection flacher aus als gehofft. Tier 4 Camera-Tuning: entweder mehr Z-Anteil im Offset (z.B. `(0, 10, 14)`) oder Perspective-Projection.
- **Floor-Tile-Pattern:** `floor_kitchen` hat schwarz-weiße Streifen — wirkt etwas chaotisch in 12×12. Office-Floor wäre besser. Mögliche Alternativen aus Furniture Bits oder ein simpler Plane mit Custom-Texture.
- **Mobile-Renderer im Browser:** funktioniert sauber, kein Quirk gemeldet. Cross-Origin-Isolation via Python-Server reichte.
- **Web-Export-Templates:** 1.2 GB Download (alle Plattformen), entpackt in `~/.local/share/godot/export_templates/4.6.stable/`. Web-spezifisch: `web_release.zip` ist die relevante Datei.

---

## Folge-Slices wenn Tier 4 startet

1. **Roadmap-Update Tier 4:** „Asset-Pipeline-Entscheidung" auf KayKit + Quaternius CC0 fixieren, Tier 4.3 von „Tilemap-Layer" auf „3D-Wall-Extrusion + Floor-Tiling".
2. **Tier 4.0.x:** Asset-Folder-Struktur + ASSET_LICENSE.md erweitern mit konkret verwendeten Files.
3. **Tier 4.1:** Connect-Flow aus Spike-1 (`godot/scripts/{ws_client,protocol,main}.gd`) übernehmen.
4. **Tier 4.3:** Map-JSON → 3D-Mesh-Generation. Wall-Lines werden zu extrudierten Plane-Meshes mit Door-Cutouts.
5. **Tier 4.4:** Multi-Player-Render + Animation-Setup (AnimationLibrary aus `Rig_Medium_MovementBasic.glb`).
6. **Tier 4.13:** Web-Export-Deploy auf gleiche EC2 — `godot-3d-serve.py`-Pattern oder uvicorn-Static-Mount für die Web-Files.

---

## Konversationskontext

- **Sven's Setup unverändert:** Windows + WSL2 Fedora 43, Backend in WSL, Editor auf Windows.
- **Asset-Pakete:** vier ZIPs unter `merge_conflict_mayhem_project/` (gitignored auf main), alle CC0. Liste in `ASSET_LICENSE.md`.
- **Spike-1 (slice/godot-spike) bleibt als 2D-Reference erhalten** — falls 3D später doch Performance-Probleme auf einer Tier-4-Slice macht, ist der 2D-Plan-Fallback noch da.
