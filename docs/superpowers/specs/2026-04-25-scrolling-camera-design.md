# Scrolling Camera

**Datum:** 2026-04-25
**Auftrag:** Sven, „Map muss größer als der Bildschirm werden — sonst sieht man wer sabotiert"

## Ziel

Map signifikant vergrößern, Canvas-Viewport bleibt unverändert (900×400), Kamera folgt dem lokalen Spieler. Distante Spieler sind off-canvas → natürliche Sichtbeschränkung ohne expliziten Fog-of-War-Layer.

## Konkrete Werte (aus Sven-Auswahl A)

| Wert | Vorher | Nachher |
|---|---:|---:|
| Map-Breite | 900 | 2400 |
| Map-Höhe | 400 | 1600 |
| Räume | 6 × 300×200 | 6 × 800×800 |
| Layout | 3 cols × 2 rows | 3 cols × 2 rows (gleich) |
| Normal-Speed | 120 px/s | 150 px/s |
| Coffee-Slow-Speed | 60 px/s | 80 px/s |
| Round-Timer | 600 s | 720 s |
| Canvas-Viewport | 900×400 | unverändert |

## Raum-Layout (neu)

```
+------------------+------------------+------------------+
|  Open Space      |  Meeting Room    |  Kitchen         |
|  (0,0) 800×800   |  (800,0) 800×800 |  (1600,0) 800×800|
+------------------+------------------+------------------+
|  Server Room     |  War Room        |  Legacy Basement |
|  (0,800) 800×800 |  (800,800) ...   |  (1600,800) ...  |
+------------------+------------------+------------------+
```

## Task-Positionen (neu, wieder in der Mitte ihrer Räume)

| Task | Raum | Neue Position | Reward |
|---|---|---|---|
| `fix_unit_tests` | open_space | (200, 200) | release +10 |
| `review_pr` | open_space | (550, 600) | release +8 |
| `repair_deployment` | server_room | (400, 1200) | pipeline +15 |
| `refill_coffee` | kitchen | (2000, 400) | coffee = 100 |

Open Space hat zwei Tasks → die werden voneinander getrennt platziert (oben links + unten mittig), nicht beide nebeneinander, damit ein Spieler sich entscheiden muss.

## Spawn-Positionen (neu)

Sechs Spawn-Punkte verteilt im Open Space (800×800):

```python
_START_POSITIONS = [
    (200.0, 200.0),
    (400.0, 200.0),
    (600.0, 200.0),
    (200.0, 400.0),
    (400.0, 400.0),
    (600.0, 400.0),
]
```

## Camera-Transform (Frontend)

In `render.js` vor jedem Frame:

```javascript
const local = this._localPlayer();
const cameraX = local
  ? clamp(local.x - canvas.width / 2, 0, MAP_WIDTH - canvas.width)
  : 0;
const cameraY = local
  ? clamp(local.y - canvas.height / 2, 0, MAP_HEIGHT - canvas.height)
  : 0;
ctx.save();
ctx.translate(-cameraX, -cameraY);
// ... draw rooms / tasks / players in WORLD coords ...
ctx.restore();
```

Vor und nach dem Frame: `ctx.save() / ctx.restore()` um globale UI-Overlays nicht zu verschieben.

`MAP_WIDTH` und `MAP_HEIGHT` werden in `render.js` als Konstanten ergänzt (gespiegelt vom Backend). Sprint-4-JSON-Config wird das später eliminieren.

## Was NICHT in dieser Slice ist

- Minimap (würde das Verstecken-Gefühl untergraben)
- Fog-of-War-Layer (Canvas-Viewport reicht)
- Wand-basierte Sichtblockierung (zwischen Räumen sieht man durch wenn beide im Viewport sind)
- Dynamische Map-Größe (bleibt bei 2400×1600)
- Spielerlisten-Geo-Updates (Lobby zeigt weiter alle Namen, das ist ok)

## Test-Plan

Existierende 140 Tests müssen grün bleiben:

- Task-Positions-Tests (`test_definitions.py`) müssen die NEUEN Positionen erwarten
- Win-Condition-Tests sind unabhängig von der Map-Größe → bleiben
- `test_game_room` Movement-Tests verwenden hardcodierte Koordinaten → müssen evtl. angepasst werden (Speed 120 → 150)
- WS-Integration-Tests sollten unverändert bleiben

Neu:
- `test_definitions.py`: prüft dass Task-Positionen weiter innerhalb der NEUEN Räume liegen
- Manueller Test im Browser: drei Tabs, jeder sieht die Karte zentriert auf den eigenen Spieler

## Konkrete Implementierungs-Schritte

1. **Backend-Konstanten anpassen** (`rooms.py`, `sabotages.py`, `game_room.py`)
2. **Task-Positionen aktualisieren** (`tasks.py`)
3. **Bestehende Backend-Tests reparieren** (Movement-Tests, Position-Tests)
4. **Frontend-Renderer mit Camera erweitern** (`render.js`)
5. **MAP_WIDTH/MAP_HEIGHT-Konstanten in `render.js` synchron**
6. **Manuelle Verifikation**

Ein Bundle, ein Commit (hängt nicht von B-XYZ-Sequenzen wie der Game-Loop-Sprint).

## Bewusste Entscheidungen

| Entscheidung | Wahl | Alternative | Begründung |
|---|---|---|---|
| Räume quadratisch 800×800 | 800×800 | 900×600 (aspect ratio gewahrt) | Ergibt sauber 2400×1600; Räume gleichgroß, einfacher |
| Speed +25% (120→150) | linear mit Map-Größe? | Nein, +25% reicht | Spieler sollen sich nicht „verloren" fühlen |
| Timer +20% (600→720) | linear mit Speed/Map? | bleibt 600 | Bei größerer Map länger spielen, sonst Mantra „in 10 Min releasen" funktioniert nicht mehr |
| Task-Counts unverändert | 4 Tasks | mehr Tasks für sparser Map | Slice-Fokus ist Camera, nicht Content. Tasks aufstocken als separate Slice |
| Keine Wand-Kollisionen | weiter durchlaufbar | Walls + colliders | Out of scope; Sprint nach diesem |
