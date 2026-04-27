# Asset License

Unless explicitly stated otherwise, all game assets in this repository, including
logos, artwork, sprites, sounds, music, UI graphics, role icons, and branding
materials, are copyright (c) 2026 RAUSCH Technology GmbH.

They may be used for contributing to this project, but may not be reused,
redistributed, sublicensed, or used in other projects without explicit
permission.

Third-party assets are listed alongside the asset directories with their
respective licenses, e.g. `sounds/CREDITS.md` for audio attributions and
`images/README.md` for image notes.

## Asset-Pack-Quellen für Tier 4 (Godot-Migration)

Die Roh-Pakete liegen NICHT im Repo (~140 MB ZIPs, Git ist nicht für Binaries
optimiert). Sie werden lokal vorgehalten; nur die tatsächlich verwendeten
Files landen unter `godot/assets/` mit dieser Datei als Lizenz-Anker.

Vier Packs als Quelle, alle **CC0 / Public Domain Dedication**:

- **KayKit Bits Bundle 1 (v1.1)** — Kay Lousberg, [kaylousberg.com](https://www.kaylousberg.com).
  CC0. Sub-Packs: City Builder, Furniture, Halloween, Restaurant, Space Base
  (Prototype-Character + Animations sind durch Kenney Mini Characters ersetzt).
- **KayKit Bits Bundle 1 (v1.1) SOURCE** — Kay Lousberg. CC0. Blender-Sources zur
  Anpassung der Modelle falls nötig.
- **Ultimate Modular Sci-Fi Pack (Feb 2021)** — Quaternius, [quaternius.com](https://www.quaternius.com).
  CC0 1.0. Server-Room-Equipment.
- **Ultimate House Interior Pack (June 2020)** — Quaternius. CC0 1.0. Wohn-/Office-Möbel.
- **Kenney UI Audio** — [kenney.nl](https://kenney.nl/assets/ui-audio). CC0 1.0. UI-Klicks/Switches.
- **Kenney Impact Sounds** — [kenney.nl](https://kenney.nl/assets/impact-sounds). CC0 1.0. Footsteps (carpet).
- **Kenney Sci-Fi Sounds** — [kenney.nl](https://kenney.nl/assets/sci-fi-sounds). CC0 1.0. Event-Stings (role-reveal, meeting, kill, task-complete).
- **Kenney Mini Characters** — [kenney.nl](https://kenney.nl/assets/mini-characters). CC0 1.0. 6 Charakter-Meshes für die 6 Hauptfarben. Liefert eigene Animationen mit (idle, walk, sprint, etc.) — ersetzt das KayKit-Dummy-Setup.

Attribution ist bei CC0 nicht erforderlich, aber wir tun's freiwillig — Kay
Lousberg, Quaternius und Kenney Vleugels haben hochwertige Pakete bereitgestellt.

### Welche Files sind aus welchem Pack vendored?

`godot-3d/assets/` ist die Single-Source-of-Truth für 3D-Assets im Repo. Pro
Subdir liegt ein License-Anker:

- `godot-3d/assets/KAYKIT_LICENSE.txt` — KayKit Bits Bundle 1 v1.1 (CC0). Wird
  von `furniture/`, `kitchen/` und `server/` referenziert.
- `godot-3d/assets/character/kenney_mini/` — Kenney Mini Characters (CC0).
- `godot-3d/assets/audio/{footsteps,sting,ui}/` — Kenney Impact / Sci-Fi /
  UI-Audio (CC0).

Welche Source-Pack-Files genau für welchen MapObject-Kind kopiert werden, hält
`maps/kinds.json` im Feld `kaykit_source` fest. `scripts/import_kaykit_assets.py`
ist die Pipeline, die aus diesem Mapping `godot-3d/assets/` neu erzeugt — siehe
[`docs/maps.md`](docs/maps.md) für die Kind-Spec.

The source code of this project is licensed separately under the MIT License;
see `LICENSE`.
