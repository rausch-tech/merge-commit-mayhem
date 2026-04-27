# Tier-4 nach Main-Rebase — Anpassungs-Plan + Map-Komplexitäts-Bewertung

**Datum:** 2026-04-27
**Trigger:** Sven hat 13 neue main-Commits gepullt; Tier-4-Branch wurde auf neuestes main rebased (alter Commit `e03a1c2 PROTOCOL.md/maps.md` wurde geskippt, weil Backend einen vollständigen `802ff81 docs(protocol): rewrite to current state (post-Tier-3.4 truth)` hat).

Plus: Sven fragt zur Map-Komplexität (Korridore, mehr als 6 Räume).

---

## 1. Was sich auf main geändert hat (relevante Highlights)

| Commit    | Was                                                              | Tier-4-Impact                                              |
| --------- | ---------------------------------------------------------------- | ---------------------------------------------------------- |
| `b4374f7` | **Persona-System:** Rollen + persönliche Tasks + Coffee-Energie  | `private_role`/`private_state`-Felder erweitert; HUD-Update |
| `5ad79c6` | **Sabotage-Object-Binding** — Chaos muss an Console stehen       | Out-of-scope für Demo (keine Sabotagen in Tier-4-Demo)     |
| `4c456a0` `7f669b9` | 4 neue **Mini-Games** (cable_pairing, coffee_pour, log_filter, sprint_trim) | Out-of-scope (Tier 4.6 später) |
| `2242ddb` | **Minimap-Overlay** im Browser-HUD                              | Idee fürs Tier-4-HUD übernehmen                            |
| `aad6d8a` | **Mobile**: off-canvas drawers + compact HUD                    | Out-of-scope                                                |
| `802ff81` | **PROTOCOL.md rewrite** (post-Tier-3.4)                          | Mein Vor-Spike-Doku-Fix obsolet, neue Wahrheit nutzen      |
| `1da8da2` | fix(meetings): vote-button DOM preserve                         | Backend-only, kein Tier-4-Impact                            |
| `f141208` | docs(overview): GAME_OVERVIEW.md                                | Lese-Material, kein Code                                   |
| `9b55b39` | docs: AGENTS.md SSOT für AI-Agents                              | Lese-Material                                              |
| `3f80905` | docs(landing): /spielprinzip subpage                             | Browser-Frontend, kein Tier-4-Impact                       |

## 2. Was tatsächlich für die Demo angepasst werden muss

**Backend-Schema-Check (gerade verifiziert):**

- `game_state.players` hat unverändert: `{id, name, x, y, color, isHost, isAlive, isConnected}` — mein Tier-4-Code matcht. **Kein Fix nötig.**
- `private_role` hat neue Felder: `title`, `shortBlurb`, `strengthCategories`, `weakCategories`, `abilityId`, `abilityLabel`, `abilityHint`, `maxCoffee`, `assignedTaskIds`. Mein Code speichert die gesamte Payload als Dict, HUD nutzt nur `role`+`team` — funktioniert weiterhin. **Optional: Title + Blurb im HUD anzeigen für Persona-Wow.**
- `private_state` hat neue Felder: `coffeeEnergy`, `coffeeMax`, `abilityUsed`. Coffee ist jetzt **per-Spieler** (nicht globaler Coffee-Level). **Optional fix:** Coffee-Bar im HUD aus `private_state` füttern statt aus `game_state.coffeeLevel`. Aber: globaler `coffeeLevel` existiert noch im `game_state` — also kein Bruch.

**Konkrete Aktionen für die Demo:**

| Prio  | Aktion                                                                                                                  |
| ----- | ----------------------------------------------------------------------------------------------------------------------- |
| Low   | HUD-Erweiterung: Persona-Titel anzeigen (z.B. "Prinzipal-Engineer" statt nur "Developer")                              |
| Low   | HUD-Erweiterung: persönliche Coffee-Energy aus `private_state` als zweite kleine Bar                                   |
| Low   | Minimap-Overlay (Tier-3.5-Pattern aus `static/render.js`) als zweites HUD-Element bringen — wäre echt nice für die Demo |
| Optional | Persona-Cover für Chaos: "Prinzipal-Engineer" als Camouflage-Rolle anzeigen — aber nur falls Spec passt                |

Keine davon sind blocking für die Demo — der aktuelle Tier-4-Stand läuft auch ohne. Nice-to-have wenn Zeit ist.

---

## 3. Map-Komplexität — Bewertung und Empfehlung

### Sven's Frage in einem Satz
> Können wir komplexere Karten als nur 6 Räume? Korridore? Das muss vom Server kommen, oder?

### Antwort: Ja, vom Server. Drei Komplexitäts-Stufen.

#### Stufe 1 — Mehr Räume + Korridore mit dem aktuellen Schema (sofort möglich)

Das aktuelle `maps/<name>.json`-Schema (siehe `docs/maps.md`) kann **bereits**:

- Beliebig viele rectangles (Räume) mit beliebigen Größen + Positionen
- Beliebig viele Wand-Linien mit beliebig vielen Door-Cutouts pro Linie
- Beliebig viele Spawn-Punkte + Task-Anker + Vents + Sabotage-Panels

**Korridore ARE rechteckige Räume.** Ein 200×1600-px schmaler Raum zwischen zwei größeren Räumen IST ein Korridor. Wand-Linien-Setup definiert wo Türen sind.

Beispiel: 12-Räume-Map mit Korridoren

```
┌─────────┬─────────┬─────────┐
│ Office1 │ Office2 │ Kitchen │
├──┐   ┌──┴──┐   ┌──┴───┐    │
│  │   │     │   │      │    │
│Cor1   Cor2     Cor3   ▼   ◄ Vent
│  │   │     │   │      │    │
├──┘   └──┬──┘   └──┬───┘    │
│ Server  │  WarRm  │ Legacy │
└─────────┴─────────┴────────┘
```

**Aufwand:** ~30 min für eine handgeschriebene 8-12-Räume-Map mit echten Korridoren. Server lädt sie automatisch (Multi-Map-Support seit Tier 1.8 — Host wählt in der Lobby).

**Limitation:** Räume sind axis-aligned Rectangles. L-Shaped oder T-Shaped Rooms gehen nur als zwei separate Rectangles, was am Server-Walls-Algorithmus halbwegs gut hinhaut. Diagonale Wände gehen nicht.

#### Stufe 2 — Schema-Erweiterung für L-Shapes + Decoration-Hints (~1 Slice)

**Was JSON-Schema lernen müsste:**

```jsonc
{
  "rooms": [
    {
      "id": "open_space",
      "title": "Open Space",
      "shape": "polygon",        // statt nur Rectangle
      "polygon": [
        {"x": 0,    "y": 0},
        {"x": 1600, "y": 0},
        {"x": 1600, "y": 800},
        {"x": 800,  "y": 800},
        {"x": 800,  "y": 1600},
        {"x": 0,    "y": 1600}
      ],
      "color": "#3a4560",
      "decorationStyle": "office"  // Hint für Möbel-Auswahl
    }
  ],
  "wallLines": [
    // bestehende axis-aligned wallLines bleiben
    // PLUS: explizite Wall-Polygone für komplexe Geometrie
    {
      "axis": "polygon",
      "points": [{"x": 800, "y": 800}, {"x": 1200, "y": 800}, {"x": 1200, "y": 1200}],
      "doors": [{"position": 0.5, "width": 240}]  // 50% entlang der Linie
    }
  ],
  "decorations": [
    {"type": "plant_large", "x": 200, "y": 200, "rotation": 0},
    {"type": "poster",      "x": 800, "y": 0,   "rotation": 0, "wall": true}
  ],
  "lighting": {
    "ambient": "#5a6b85",
    "warmth": 0.7,
    "rooms": {
      "server_room": {"tint": "#0066ff", "energy": 0.3}
    }
  }
}
```

**Server-Aufwand:** Wall-Computation-Algorithmus muss Polygon-Walls verstehen. Validation strikter. Map-Editor (Browser, Tier 1.7) muss erweitert werden — aber das ist Tier 5/6 Material.

**Client-Aufwand:** map_builder.gd erweitert um Polygon-Floors + Polygon-Walls. Decorations-Liste statt Heuristic.

**Aufwand:** 1-2 Tage Backend, 1 Tag Client. Sinnvoll als Tier-4-Folge-Slice.

#### Stufe 3 — Multi-Floor / Stockwerke (groß)

**Idee:** Office hat zwei Etagen, Treppe verbindet sie. Server-Welt hat eine `floor`-Property pro Spieler. Map-JSON hat `floors: [{name, walls, rooms, ...}, ...]` plus `connections: [{from_floor, to_floor, x, y}]`.

**Server-Aufwand:** Spieler-Position um floor-Index erweitern. Movement quer über connections (Treppen). Rendering: sicht-blockierende Decken. Win-Conditions evtl. floor-aware.

**Client-Aufwand:** mehrere Floor-Levels stacked rendern. Camera-Switch oder Cutaway-View.

**Aufwand:** 1-2 Wochen Backend, 1 Woche Client. **Empfehlung: nicht für Tier 4.** Eher Tier 6+ wenn Community-Maps das wollen.

### Empfehlung: Stufe 1 jetzt, Stufe 2 nach der Demo

**Heute/morgen (vor Demo):**
1. Eine zweite, deutlich größere Map (`maps/office_complex.json` o.ä.) mit ~10-12 Räumen + Korridoren, alles im aktuellen Schema. Host kann sie via Multi-Map-Dropdown wählen.
2. KayKit Furniture-Vielfalt: aktuell drei Möbel-Typen, könnte auf 8-10 erweitert werden (`bed`, `couch`, `armchair`, `cabinet`, `shelf`, `pictureframe` aus dem Bundle). Server nicht betroffen, nur `map_builder.gd::_decorate_rooms` erweitern.

**Tier-4-Folge-Slice:**
3. Schema-Erweiterung Stufe 2 (Polygon-Räume + Decorations). Browser-Editor und Godot-Map-Builder synchron erweitern.

**Später:**
4. Stufe 3 nur wenn Multi-Floor-Game-Design (Treppen-Mechanik, Sicht-Mechanik) zustimmt — das ist eine grosse Game-Design-Entscheidung.

---

## 4. Was ich konkret jetzt mache (parallel zu Sven's Klick-Bug-Test)

Nach diesem Doku-Commit:

1. **Beispiel-Map** `maps/office_complex.json` mit ~10-12 Räumen + Korridoren bauen — server-side ohne Code-Änderung lauffähig (Multi-Map-Support existiert).
2. **Tier-4-Demo** kann diese Map dann zeigen (Host wählt sie in der Browser-Lobby).
3. **map_builder.gd** evtl. Floor-Texture-Differenzierung verbessern (aktuell uniform tints, könnte Floor-Patterns pro Raum-Typ haben).

Pro Aktion: kurzer Commit, push. Sven kann zu jedem Zeitpunkt einsteigen und live testen.
