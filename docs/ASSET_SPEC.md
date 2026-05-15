# Asset-Spec — Godot 3D Client

> **Zweck:** Konventions-Dokument für die Asset-Pipeline. Definiert
> verbindlich, in welchem Format neue 3D-Meshes ins Repo landen, damit
> Editor-3D-Vorschau und Godot-Client beide automatisch upgepicken —
> ohne pro Asset einen Code-Patch.
>
> **Status:** Pipeline ist live (25/25 Kinds gestaged via KayKit-Default-
> Sweep). Dieses Doc dokumentiert die etablierten Konventionen; Updates
> per PR wenn sie sich in der Praxis ändern müssen.

---

## 1. Übersicht

Die `MapObject`-Pipeline hat eine einzige Quelle der Wahrheit:
[`maps/kinds.json`](../maps/kinds.json). Pro Kind steht dort ein Block
mit `category`, `label`, `default_size`, `blocks_movement`, `browser_2d`
(2D-Renderer-Hint), `godot_asset` (Pfad zum 3D-Mesh) und `kaykit_source`
(Asset-Pack-Provenance).

Vier Konsumenten lesen die Datei live:

1. **Backend** — Pydantic-Validator auf `MapObject.kind` rejected
   unbekannte Kinds (`app/game/kinds_registry.py`).
2. **Editor-Palette** — `static/editor/editor-kinds.js` baut die
   Tool-Palette aus dem Registry.
3. **Browser-Renderer** — `static/render.js` zeichnet 2D-Boxen mit der
   `browser_2d`-Style-Info.
4. **Godot-Client** — `godot-3d/scripts/map_builder.gd` lädt die in
   `godot_asset` referenzierten `.gltf`-Files; fehlende Pfade fallen
   auf eine farbige Box zurück.

**Konsequenz:** Wenn ein neues Mesh ins Repo kommt, ist die
**ausschließliche** Code-Änderung das Hinzufügen eines Eintrags in
`maps/kinds.json`. Editor-Code und Godot-Code bleiben unangetastet.

---

## 2. Sources of Truth

| Was             | Wo                                                               |
| --------------- | ---------------------------------------------------------------- |
| Kind-Liste      | [`maps/kinds.json`](../maps/kinds.json)                          |
| Schema          | [`docs/maps.md`](maps.md)                                        |
| Asset-Files     | `godot-3d/assets/` (3D), `images/` (2D)                          |
| Lizenzen        | [`ASSET_LICENSE.md`](../ASSET_LICENSE.md)                        |
| Pydantic-Modell | [`app/game/game_map.py`](../app/game/game_map.py) — `MapObject`  |
| Server-Endpoint | `GET /api/kinds` (Live unter https://prod-is-lava.dev/api/kinds) |

---

## 3. File-Layout

Neue Meshes landen unter `godot-3d/assets/<category>/<asset_id>.gltf`
(separates `.bin` ist OK, bleibt im selben Ordner). Texturen liegen
neben den `.gltf` im selben Verzeichnis und werden von der `.gltf` per
relativem Pfad referenziert.

```
godot-3d/
└── assets/
    ├── furniture/                    ← Workstation-, Meeting-, Decor-Kinds
    │   ├── desk.gltf
    │   ├── desk.bin
    │   ├── chair_desk_A.gltf
    │   ├── chair_desk_A.bin
    │   ├── monitor.gltf
    │   ├── monitor.bin
    │   └── furniturebits_texture.png
    ├── server/                       ← Server-Kinds (neu für 4.0.x)
    │   ├── server_rack.gltf
    │   └── monitoring_panel.gltf
    ├── kitchen/                      ← Kitchen-Kinds (neu für 4.0.x)
    │   ├── kitchen_counter.gltf
    │   ├── coffee_machine.gltf
    │   └── ...
    ├── character/
    │   └── kenney_mini/              ← 6 Player-Character-Meshes
    └── audio/
        ├── footsteps/                ← 5 Carpet-Variants
        ├── sting/                    ← 4 Event-Stings
        └── ui/                       ← UI-SFX
```

`category`-Namen (Workstation/Server/Meeting/Kitchen/Decor/Legacy)
spiegeln die Editor-Palette-Gruppen aus `kinds.json`. Subdirs unter
`assets/` sind Lower-Snake-Case der Category.

**Keine Asset-ZIPs im Repo** — die Quell-Packs (KayKit, Quaternius,
Kenney) liegen außerhalb des Repos und sind in `ASSET_LICENSE.md`
verlinkt. Nur die tatsächlich genutzten Files landen im Repo.

---

## 4. Naming-Convention

### Asset-File-Name

- **Pattern:** `<asset_id>.gltf` (mit begleitender `.bin`-Datei).
- **`asset_id`:** lowercase, snake_case, deskriptiv. Optional Suffix
  `_A` / `_B` für Varianten desselben Sockels.
- **Beispiele:** `desk.gltf`, `desk_large.gltf`, `chair_desk_A.gltf`,
  `kitchen_counter_straight.gltf`, `server_rack.gltf`.

### Kind-Name (kinds.json-Top-Level-Key)

- **Pattern:** lowercase, snake_case, **synchron mit `asset_id`** (oder
  ein `kaykit_source`-spezifischer Subname, siehe `chair_desk` ↔
  `chair_desk_A.gltf`).
- **Stabil:** Kind-Namen sind in geschriebenen Maps eingefroren. Eine
  Umbenennung bricht alle existierenden `mapObjects[]`-Einträge.
- **Reservierte Prefixe:** Top-Level-Keys mit Underscore-Prefix
  (`_meta`) sind Metadaten, nicht Kinds.

### Material- und Texture-Naming

- **Atlas-Texturen:** `<pack>bits_texture.png` (z.B.
  `furniturebits_texture.png`) — bleibt mit dem KayKit-Naming
  kompatibel, vermeidet Renames.
- **Per-Asset-Texturen:** `<asset_id>_albedo.png`, `<asset_id>_normal.png`
  — nur wenn nicht über einen Atlas geteilt.

---

## 5. Pivot-Convention

> **Pivot ist (X-Center, Y-Bottom, Z-Center).** Die Mesh-Origin sitzt
> in der Mitte des Footprints am Boden, NICHT in der Mitte des
> Bounding-Box-Volumens.

Begründung: Server schickt MapObject-Positionen als CENTER-Koordinaten
auf der 2D-Ebene. Der `map_builder.gd` setzt das Mesh auf
`(x*WORLD_SCALE, 0, y*WORLD_SCALE)`. Wenn Pivot nicht am Boden sitzt,
schwebt das Mesh in der Luft oder schneidet durch den Boden.

**Test:** In Blender vor dem Export `Object > Set Origin > Origin to 3D
Cursor` mit Cursor auf `(0, 0, 0)` und Mesh am Origin platziert.

**Rotation:** 0° = Mesh blickt in +Z-Richtung. Server-Rotation 90/270
swapt nur den AABB-Footprint server-seitig (`map_object_aabb()`). Im
Godot-Client wird das Mesh um die Y-Achse rotiert; im Three.js-Editor
analog.

---

## 6. WORLD_SCALE

> **1 Server-Pixel = 0.01 Godot-Units.** Eine 4800-Pixel-Map ist 48
> Godot-Units breit. Ein 110×60-Pixel-Desk ist 1.10×0.60 Godot-Units in
> der XZ-Ebene.

Konsequenzen:

- Mesh-Größe in Blender muss diesem Maßstab entsprechen. Eine
  realistische Schreibtisch-Höhe (~0.75 m IRL) ist im Godot-Coord-System
  einfach **0.75 Y-Units**. Schau auf `kinds.json:default_size` — die
  Werte sind in **Server-Pixeln**, multipliziert mit 0.01 ergibt die
  Footprint-Größe.
- Charakter-Größe: Kenney Mini Characters sind klein (~30 cm raw), wir
  scalen sie im Code auf `2.2x` damit sie ~1.7 m ergeben (siehe
  `character.gd:CHARACTER_SCALE`). Bei eigenen Charakter-Meshes:
  liefere im finalen Maßstab, dann fällt das Scaling weg.

---

## 7. Polycount + Material-Budget

Pro Mesh ist ein realistisches Budget:

| Klasse                 | Max-Tris | Beispiel                                 |
| ---------------------- | -------- | ---------------------------------------- |
| **Hero-Asset**         | ~5000    | Coffee-Maschine, charakteristischer Body |
| **Standard-Furniture** | ~2000    | Desk, Chair, Cabinet                     |
| **Decor**              | ~500     | Plant, Picture-Frame, Rug                |
| **Player-Character**   | ~3000    | Kenney Mini ist ~1500 — gutes Beispiel   |

Begründung: Web-Export-Build muss mobile-renderer-tauglich bleiben. Der
3D-Editor-Preview rendert dieselben Files via Three.js — gleiche
Constraints.

**Materials:** PBR mit `baseColor + metallic + roughness`. Ein
geteilter Texture-Atlas pro Asset-Pack bevorzugt (siehe
`furniturebits_texture.png`). Pro Mesh max 2 Material-Slots.

**No animations bei Furniture.** Animationen sind nur für Character
und VFX (z.B. spinning server LED) erwartet.

---

## 8. kinds.json: neuen Kind hinzufügen

Wenn ein neuer Kind nötig ist (z.B. ein "rack-mounted networking
switch", den keine der 25 existierenden Kinds abdeckt):

1. **Mesh nach `godot-3d/assets/<category>/<asset_id>.gltf`** legen.
2. **Eintrag in `maps/kinds.json`** anlegen:
   ```json
   "networking_switch": {
     "category": "Server",
     "label": "Networking Switch",
     "default_size": [120, 30],
     "blocks_movement": true,
     "browser_2d": { "fill": "#1e293b", "label": "SWITCH" },
     "godot_asset": "res://assets/server/networking_switch.gltf",
     "kaykit_source": null
   }
   ```
3. **`docs/maps.md`** Kind-Catalogue-Tabelle ergänzen (alphabetische
   Reihenfolge nach `category`).
4. **PR aufmachen** mit beiden Änderungen + dem Mesh-File. CI läuft:
   pytest validiert dass alle Maps weiterhin laden, prettier checked
   die JSON.
5. **Editor + Godot-Client picken automatisch auf**, sobald der PR
   gemerged + deployed ist. Kein zusätzlicher Code-Touch.

**`browser_2d.label`-Konvention:** ≤ 7 Zeichen, all-caps, sinngebend.
Leerstring (`""`) bedeutet "kein Label, nur Farbe" — für Decor-Kinds
wo das Label visuell stört.

**`godot_asset = null`** ist erlaubt während die Asset-Pipeline
hochfährt — der Kind ist dann im Editor-Palette wählbar, rendert aber
als Box. Sobald das Mesh kommt, Pfad eintragen.

---

## 9. PR-Workflow für neue Assets

```
git checkout -b feat/assets-<batch-name>
# 1. Meshes nach godot-3d/assets/<category>/ kopieren
# 2. maps/kinds.json updaten (Top-Level-Eintrag pro neuem Kind)
# 3. docs/maps.md Kind-Catalogue-Tabelle ergänzen
# 4. ASSET_LICENSE.md ergänzen falls neue Asset-Pack-Quelle

git add -A
git commit -m "feat(assets): <kategorie> meshes (<n> kinds)"
git push -u origin feat/assets-<batch-name>
gh pr create --title "feat(assets): <kategorie> meshes" --body ...
```

CI-Gates die für Assets relevant sind:

- **prettier** — JSON-Format der `kinds.json`
- **pytest** — `tests/test_kinds_registry.py:test_all_repo_maps_round_trip`
  prüft dass alle existierenden Maps weiterhin validieren
- **godot-check** — Headless-Parse-Check der GDScripts (sollte
  unbeeinflusst sein, weil keine Code-Änderungen)

**Asset-File-Größe:** Single-Mesh `.gltf+.bin` typisch 50–200 KB. Wenn
ein Asset > 1 MB ist, kurz mit Sven abklären (Web-Export-Bandbreite).

---

## 10. Quality-Bar

Vor dem PR durchgehen:

- [ ] Pivot ist `(X-Center, Y-Bottom, Z-Center)`?
- [ ] Mesh sitzt im richtigen WORLD_SCALE?
- [ ] Polycount unter Budget?
- [ ] Texturen sind mit dem Pack-Atlas konsistent?
- [ ] PBR-Material mit albedo + metallic + roughness?
- [ ] `.gltf` lädt im Three.js-Editor-Preview ohne Console-Warnung?
- [ ] `.gltf` lädt im Godot-Editor ohne Import-Warnung?
- [ ] `kinds.json`-Eintrag hat alle Pflicht-Felder?
- [ ] `docs/maps.md` Catalogue ergänzt?
- [ ] Lizenz in `ASSET_LICENSE.md` korrekt zugeordnet?

Wenn alles ✅: PR rausschicken, im Body kurz auflisten welche Kinds
bedient werden + ein Vorher-/Nachher-Screenshot aus der
`/editor`-3D-Preview als Sanity-Check.

---

## 11. Rollback-Pfad

Wenn ein Asset Probleme im Live macht (z.B. zu hoher Polycount, Crash
im Web-Export):

1. **Nicht das `kinds.json`-Schema brechen.** Top-Level-Key bleibt
   stehen. Setze stattdessen `godot_asset: null` — Editor + Godot
   fallen automatisch auf Box-Fallback zurück.
2. PR mit JSON-Patch reicht; das alte Mesh-File kann erstmal im Repo
   bleiben (Cleanup separat).
3. Maps mit dem betroffenen Kind funktionieren weiter — sie zeigen
   Boxen statt Meshes, aber das Schema validiert.

---

## 12. Kontakt

- **Backend / Schema / Editor:** Sven + Backend-Team
- **Godot-Client / Pipeline:** Externes Godot-Team
- **Asset-Pipeline-Entscheidung (Tier 4.0.1):** ✅ KayKit + Eigenproduktion
- **Aktuelle Pipeline (Tier 4.0.2):** in progress, dieses Doc ist die
  Vorab-Vereinbarung
