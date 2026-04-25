# Images

Composite spritesheets + single-asset images für MCM. Generiert per AI nach den Prompts in `merge_conflict_mayhem_project/docs/05_asset_pack_master_prompt.md`.

## Aktiv genutzt

| Datei                | Verwendung                                                        |
| -------------------- | ----------------------------------------------------------------- |
| `logo.png`           | Header in der Lobby (`static/index.html` `#lobby-logo`)           |
| `figuren.png`        | Charakter-Sprites auf der Spielkarte (5×2 Grid, color-keyed)      |
| `sabotage_icons.png` | Drei Sabotage-Buttons unten rechts (5×2 Grid, erste 3 oben links) |
| `ui_icon_set.png`    | Task-Marker auf der Map (4×3 Grid)                                |
| `role_badges.png`    | Rolle-Badge in HUD + Endscreen (5×2 Grid)                         |

Tile-Mapping liegt in `static/sprites.js` als `SPRITES`-Objekt.

## Reserviert (noch nicht integriert)

Diese Sheets sind im Repo damit sie verfügbar sind, wenn die passenden Features kommen:

| Datei                     | Wofür gedacht                                                    | Wann integriert |
| ------------------------- | ---------------------------------------------------------------- | --------------- |
| `buttons.png`             | UI-Buttons mit echten Sprites statt CSS                          | Tier 4 Polish   |
| `pansels_ui_frames.png`   | Panel-/Frame-Hintergründe (Lobby, Endscreen, Sidebar)            | Tier 4 Polish   |
| `room_labels.png`         | In-World-Schilder über Räumen (statt Text-Overlay auf Canvas)    | Tier 3 Godot    |
| `action_ability_icons.png` | Spezial-Fähigkeiten der erweiterten Rollen (Ping, Distract, Speed Boost, etc.) | Tier 5 erweiterte Rollen |
| `cover.png`               | Splash-Screen / Loading-Screen                                   | Tier 4 Polish   |
| `ingame.png`              | Reference-Visualisierung — kein Asset, sondern Look-Ziel         | Vorlage für Godot Tilemap-Stil |

## Hinweise

- **Keine Bildbearbeitung committen ohne Notiz.** Diese Sheets sind die einzige Quelle. Wenn du sie zerschnipselst (z. B. einzelne Tiles als separate PNGs), benenn die Originale nicht um.
- **Sprite-Coords stehen im Code**, nicht in den Sheets. Wenn du ein Sheet ergänzt oder neu generierst, prüf gegen `static/sprites.js` ob die `SPRITES`-Einträge noch passen.
- **Lizenz:** AI-generiert von Sven für dieses Projekt. Keine externe Verwendung ohne Rücksprache.
