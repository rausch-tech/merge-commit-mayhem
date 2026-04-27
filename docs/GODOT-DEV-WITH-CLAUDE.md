# Godot-Entwicklung mit Claude Code

> **Zielgruppe:** KI-Agenten (Claude Code), die am Godot-Client unter
> `godot-3d/` arbeiten. Sven liest das auch — die Workflows funktionieren
> für menschliche Entwickler 1:1.
>
> **Was hier fehlt absichtlich:** Architektur, Protocol, Game-Mechanik —
> das steht in [`GODOT_HANDOFF.md`](GODOT_HANDOFF.md). Hier geht's um
> _wie man als KI-Agent produktiv am Godot-Client arbeitet_.

---

## Quick-Map: Was liegt wo

| Pfad | Was |
|---|---|
| `godot-3d/` | Godot 4.6 Mobile-Renderer Projekt (Tier-4 Client) |
| `godot-3d/scripts/` | GDScripts — alle Spielobjekte (character, world, hud, …) |
| `godot-3d/scenes/` | `.tscn`-Dateien — meist nur Root-Node + Script-Anhang |
| `godot-3d/assets/` | KayKit + Kenney CC0 Assets (siehe `ASSET_LICENSE.md`) |
| `godot-3d/maps/` | Kopien von `maps/` für Demo-Szenen ohne Backend |
| `app/` | Server (FastAPI, Pydantic v2) — **autoritativ für allen Spielstate** |
| `maps/` | Server-side Map-JSONs (Schema in `docs/maps.md`) |
| `static/` | 2D HTML/Canvas-Frontend (Referenz, was der Server-Output rendert) |
| `scripts/godot-check.sh` | Headless GDScript-Parse-Check (CI + lokal) |

**Wichtig:** Server schickt Map und State an den Client per WebSocket. Im
realen Spiel gibt's also keine lokale Map-Datei im Godot-Client. Die Files
in `godot-3d/maps/` sind nur für die Demo-Szenen ohne laufendes Backend.

---

## Setup: Tools die ein Claude Code Agent braucht

Auf der WSL/Linux-Devbox vorinstalliert (Sven hat das eingerichtet):

- **Godot 4.6** als `~/.local/bin/godot` (Symlink auf `Godot_v4.6-stable_linux.x86_64`)
- **xvfb** (`apt install xvfb`) — virtuelles X-Display fürs Headless-Rendern
- **ImageMagick** (`magick`) — Pixel-Vergleiche, Frame-Stripes bauen
- **uv** für Python (Server-Tests)

Schnellcheck:

```bash
godot --version          # 4.6.stable.official.89cea1439 oder neuer
xvfb-run --help | head   # xvfb-run muss installed sein
magick -version | head   # ImageMagick 7.x
```

---

## Workflow 1: Parse-Check (vor jedem Commit)

**Tool:** `scripts/godot-check.sh` (oder `-v` für verbose)

```bash
scripts/godot-check.sh
```

Erwartete Ausgabe (Stand 2026-04-27):

```
OK    godot-3d/scripts/character.gd
OK    godot-3d/scripts/demo_world.gd
…
12/12 scripts OK.
```

Fehler werden mit `FAIL` markiert + Parse-Error-Zeile ausgegeben. Exit-Code
`1` bei Fehlern, `0` sonst — auch in CI nutzbar.

**Wann benutzen:** Immer bevor du committest. GDScript wird sonst erst beim
Editor-Start oder beim Run gecheckt — KI-Agenten haben aber keinen Editor.

CI läuft denselben Check als `godot-check`-Job (`.github/workflows/ci.yml`).

---

## Workflow 2: Headless Visual-Test (vor jedem nicht-trivialen Change)

Du kannst den Client renderen, ohne dass jemand vor dem Bildschirm sitzt.
Output landet in `/tmp/godot-shots/frame00000000.png … frameNNNNN.png`.

```bash
rm -rf /tmp/godot-shots && mkdir -p /tmp/godot-shots && \
  timeout 30 xvfb-run --auto-servernum --server-args="-screen 0 1280x720x24" \
    godot --path /home/sr/se/mcm/godot-3d \
    --rendering-driver opengl3 \
    --scene res://scenes/demo_world_followcam.tscn \
    --write-movie /tmp/godot-shots/frame.png \
    --quit-after 60 --fixed-fps 20
```

Was hier passiert:

- `xvfb-run --auto-servernum --server-args="-screen 0 WxHx24"` — virtuelles
  X-Display in der gewünschten Auflösung (Godot rendert da rein).
- `--rendering-driver opengl3` — llvmpipe (Software-OpenGL via Mesa).
  **Vulkan funktioniert in xvfb nicht.** Mobile-Renderer kommt mit OpenGL3 klar.
- `--scene <path>` — startet eine spezifische Szene (Demo-Szene siehe unten).
- `--write-movie path.png` — speichert jeden Frame als `frameNNNNNNNN.png`
  + `.wav` mit Audio. Gut zum Vergleichen mehrerer Frames (Animation prüfen).
- `--quit-after N --fixed-fps F` — N Frames bei F fps, dann sauber beenden.
- `timeout 30` — Sicherheitsnetz (z.B. wenn das Script ein nicht-quittendes
  `_process` hat).

**Frame ansehen:** `Read` tool auf `/tmp/godot-shots/frame00000050.png` —
Claude kann PNG direkt anschauen.

**Animation prüfen** (Walking-Loop animiert wirklich?): Stripe aus 3 Frames
bauen:

```bash
magick \( /tmp/godot-shots/frame00000020.png \
         /tmp/godot-shots/frame00000025.png \
         /tmp/godot-shots/frame00000030.png \
         +append \) /tmp/strip.png
```

Dann `Read /tmp/strip.png` — sollte unterschiedliche Posen zeigen wenn die
Anim wirklich läuft.

**Pixel-Vergleich** (z.B. um zu prüfen ob ein UI-Element wirklich weg ist):

```bash
magick /tmp/godot-shots/frame00000040.png \
       -crop 1x1+640+360 +repage \
       -format "%[pixel:p{0,0}]" info:
# Output z.B.: srgba(255,255,255,1) → das ist ein heller Pixel
```

So habe ich das HUD-"graue-Fenster" debuggt — Pixel an erwarteten
Positionen sampeln, mit Erwartung vergleichen.

---

## Workflow 3: Demo-Szenen (Visual Tests ohne Backend)

Da du kein laufendes FastAPI brauchst, gibt's vorgefertigte Demo-Szenen mit
Mock-Players + Mock-State:

| Szene | Was sie zeigt |
|---|---|
| `scenes/demo_world.tscn` | Aerial Top-Down (orthographic, ganze Map sichtbar) |
| `scenes/demo_world_followcam.tscn` | Follow-Cam wie im echten Spiel |

Beide laden per Default `res://maps/default.json`. Möchtest du office_complex
testen, in `demo_world.gd` den Pfad anpassen — oder eine neue Demo-Szene
schreiben.

Mock-Player-Liste in den Demo-Scripts ist hardcoded — beim Testen einer
neuen Map oder eines neuen Char-Mappings einfach Player-Daten anpassen
und re-rendern.

**Eine eigene Demo-Szene zum Testen** ist oft die schnellste Lösung wenn
du was Spezielles brauchst (z.B. nur einen einzigen Char ohne HUD).
Pattern: kleines `.tscn`, kleines `.gd`, in `world.tscn` reparenten oder
direkt `add_child`. Aufräumen nicht vergessen wenn der Test durch ist.

---

## Workflow 4: Asset-Import-Pipeline

Godot generiert `.import`-Files für jedes Asset (GLB, OGG, PNG, …) beim
ersten Editor-Start oder über `--import`. Diese Files sind **gitignored**
(`godot-3d/**/*.import`), werden also nicht mit committed.

**Nach Asset-Add:**

```bash
godot --headless --path /home/sr/se/mcm/godot-3d --import
```

Erzeugt `.import`-Files + cached die Assets in `.godot/imported/`.

**GLB mit externer Textur** (Stolperfalle): Manche Assets (z.B. Kenney Mini
Characters) referenzieren die Textur als relative URI im GLB. Beispiel:
`character-male-a.glb` enthält `uri: "Textures/colormap.png"`.

→ Du musst den Texture-Pfad neben den GLB legen, sonst rendert Godot den
Char als weißen Blob:

```
godot-3d/assets/character/kenney_mini/
  character-male-a.glb
  Textures/
    colormap.png
```

Symptom-Check: weiße/helle Char-Silhouetten ohne Detail → Textur fehlt.

**OGG-Loop** (für Ambient/Music) muss explizit aktiviert werden im
`.import`-File:

```ini
[params]
loop=true
```

(Default ist `false`. KI-Agenten müssen das setzen wenn sie Audio-Loops
einbauen.)

---

## Workflow 5: Was-Du-Anpasst-Was-Du-Testest

Lookup-Tabelle für Iteration:

| Was geändert | Erst testen mit |
|---|---|
| GDScript-Syntax/Logik | `scripts/godot-check.sh` |
| HUD/UI-Layout | Headless Render + `Read` auf Frame |
| 3D-Scene/Char-Position | Headless Render + `Read` auf Frame |
| Animation-Mapping | Render mit Bewegung (Demo-Szene mit oszillierenden Coords) + Frame-Stripe |
| Server-Code | `uv run pytest -q` |
| Map-JSON | Demo-Szene mit dem geänderten Map laden, render, Visual prüfen |
| Audio | Lokal in Editor — Headless rendert WAV mit aber Sven muss hören |

---

## Settings für Claude Code (Permission-Setup)

Sven hat `~/.claude/settings.local.json` und `.claude/settings.local.json`
(repo-lokal) so eingerichtet, dass die Agent-Workflows ohne ständige
Permission-Prompts laufen. Wichtigste Allows:

- `Bash(godot *)` — Engine-Calls
- `Bash(xvfb-run *)`, `Bash(Xvfb *)` — Headless-Display
- `Bash(magick *)` — Pixel-Vergleiche
- `Bash(scripts/*)`, `Bash(./scripts/*)` — Eigene Tools
- `Bash(git *)` (außer push origin main, siehe unten)
- `WebFetch`, `WebSearch` — Asset-URLs nachschlagen, Doku checken

**Hard-Deny** (Sicherheitsschalter, **darf nicht überschrieben werden**):

```json
"deny": [
  "Bash(git push origin main)",
  "Bash(git push origin main:*)",
  "Bash(git push * --force *)",
  "Bash(rm -rf /)", "Bash(rm -rf /home*)", …
]
```

→ KI-Agenten können nicht versehentlich main pushen oder das Filesystem
killen. Wenn ein Agent doch mal direkt nach main pushen muss (z.B. weil
Sven es explizit gefragt hat), regelt Sven das durch kurzes Rausnehmen
der Deny-Rule.

**Neue Tools dazu nehmen:** `Skill(update-config)` oder direkt
`.claude/settings.local.json` editen. Das `allow`-Array ist schon ziemlich
voll, einfach am Ende anhängen.

---

## Common Patterns (Stolperfallen-Vermeidung)

### Anchor-Bug in Control-Layouts

`PanelContainer` mit `anchor_right = 1.0` aber **ohne** `anchor_left = 1.0`
streckt sich von `x = -offset_left` bis `x = screen_width + offset_right` —
das war die Quelle des "graues-Fenster"-Bugs Ende April.

**Regel:** Wenn ein Panel an einer Kante hängen soll (z.B. rechts), beide
horizontal-Anchors auf 1.0 setzen. Selbes für vertical.

### Stretch-Mode für scharfe Renders

`project.godot`:

```ini
[display]
window/stretch/mode="canvas_items"   # NICHT "viewport" — sonst pixelig
```

`viewport` rendert intern auf Viewport-Auflösung (z.B. 1280×720) und
skaliert auf die Fenstergröße hoch → pixelig auf 1080p+ Monitoren.
`canvas_items` rendert 3D in nativer Auflösung, Controls skalieren
proportional.

Plus für Edge-Quality:

```ini
[rendering]
anti_aliasing/quality/msaa_3d=2          # 4x MSAA
anti_aliasing/quality/screen_space_aa=1  # FXAA
```

### Animation-Loop muss explizit sein

Kenney-Modelle (und viele andere CC0-Assets) liefern Anims mit
`loop_mode = NONE`. AnimationPlayer.play(name) spielt die einmal durch und
friert dann ein.

**Fix:** Nach Anim-Pick `loop_mode = Animation.LOOP_LINEAR` setzen:

```gdscript
var anim: Animation = _anim_player.get_animation(qualified_name)
if anim != null:
    anim.loop_mode = Animation.LOOP_LINEAR
```

Siehe `_force_loop()` in `character.gd`.

### Mouse-Filter für Click-Through-Layers

Jede Background-`ColorRect`/Container, die nicht klickbar sein soll:
`mouse_filter = Control.MOUSE_FILTER_IGNORE`. Sonst frisst der Background
die Klicks und Buttons feuern nicht.

### Color-Identity vs. Body-Tint

In MCM identifiziert die Spielerfarbe einen Spieler. Naive Lösung: Char-
Body in Spielerfarbe tinten. **Bricht** weil Kenney/KayKit-Modelle eigene
Outfit-Farben haben (Hair, Shirt, etc.) — Tint zerstört die Details.

**Pattern (mirrors static/render.js):** Kein Body-Tint, stattdessen einen
flachen Color-Disc unter den Char (per Player-Color). Self-Marker (für den
lokalen Player) als zusätzlicher pulsierender Ring obendrüber. Siehe
`character.gd:_build_color_disc()`.

### Headless-Renderer ist nicht 100% fidelitätsgleich

Mobile-Renderer + opengl3 + llvmpipe rendert leicht anders als Sven's
Vulkan-Forward+ Setup auf Windows. Im Headless können Schatten weicher,
Far-Clipping anders, MSAA effektiv weniger sein. Wenn Sven sagt "auf meinem
Bildschirm sieht's aber anders aus" — Headless-Frames sind ein
Approximation, kein Pixel-Match.

---

## Gotchas-Sammlung (laufend ergänzt)

- **Eine zweite Camera3D mit `current = true`** überschreibt die erste —
  vorher prüfen ob bereits eine existiert.
- **MeshInstance3D.transparency** funktioniert nur mit material das
  `transparency` Mode setzt — sonst wird die Property ignoriert.
- **`game_state` kommt 20 Hz** — beim Scene-Switch muss man unbedingt
  Phase-Transitions guards bauen (`_transitioning = true`), sonst lädt
  man die World-Szene 20× pro Sekunde neu (Sven's "14 stacked instances"-Bug).
- **Worktrees & Worktree-Removal:** `git worktree remove` braucht keinen
  cwd-change, geht aus jedem Verzeichnis.
- **`.import`-Files sind gitignored** — wenn du Assets aus einem PR
  nachziehst, lokal `godot --headless --path godot-3d --import` ausführen.
- **Pre-commit-hooks (`.pre-commit-config.yaml`):** prüfen ruff/prettier.
  GDScript wird NICHT von pre-commit gecheckt — der godot-check ist
  separat (CI + manuell).

---

## Empfohlener Iteration-Loop

```
1. Code via Edit/Write ändern
2. scripts/godot-check.sh                                    # parse-check
3. (bei UI/3D-Änderung) Headless render → Read frame         # visual-check
4. (bei Server-Touch) uv run pytest -q                       # backend-check
5. git status / git diff --stat                              # sanity
6. git add <gezielt> && git commit                            # commit
7. git push origin <branch>  (NICHT main direkt)             # push branch
```

Dauer: 30–90s pro Iteration. Schnell genug für tight loops mit Sven.

---

## Was diese Doku NICHT abdeckt

- **Web-Export** (`exports/spike2.html`): Web-Build siehe alte Spike-Doku.
  Aktuell nicht der primäre Test-Pfad.
- **Live-Server-Integration** (gegen `https://game.prod-is-lava.dev`):
  läuft, aber für Demo-Workflow uninteressant.
- **Wall-Auto-Derivation** aus Map-Doors: Server kann das schon
  (`compute_walls()` in `app/game/game_map.py`), Godot-Client noch nicht
  vollständig — siehe `GODOT_HANDOFF.md` §6.4.
- **Editor-Integration:** Map-Editor läuft im HTML-Frontend (`static/editor/`),
  nicht in Godot.

Bei Fragen: Sven, oder `GODOT_HANDOFF.md`, oder `AGENTS.md`.
