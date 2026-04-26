# Godot-Bootstrapping-Spike — Stand und Resume-Notes

**Datum der Pause:** 2026-04-26
**Letztes Update:** 2026-04-27 (main mit Tier 0.3 / 1.9 / 2.x / 3.x reingeholt, Roadmap-Restructure: Godot ist jetzt **Tier 4**, Tier 3 sind Mini-Games)
**Branch:** `slice/godot-spike` im Worktree `.worktrees/godot-spike/`
**Spec:** `docs/superpowers/specs/2026-04-26-godot-spike-design.md`
**Plan:** `docs/superpowers/plans/2026-04-26-godot-spike.md`

---

## TL;DR

Der gesamte **Spike-Code ist geschrieben und committet** auf `slice/godot-spike` (6 Commits, gebrancht von `main`). Was noch fehlt, ist **Runtime-Verification mit echtem Godot 4.3 Editor** (Test-Plan in `docs/CLIENT.md §6`). Backend ist nicht angefasst. Pre-Spike-Doku-Lücken in `docs/PROTOCOL.md` und `docs/maps.md` wurden auf `main` gefixt.

**Nichts wurde gepusht.** Branch ist lokal.

---

## Was sich seit Pause geändert hat (Merge-Update 2026-04-27)

Während der Spike pausierte, wurden auf `main` 14 Commits gemerged:

- **Tier 0.3 done:** Vitest + happy-dom Frontend-Smoke-Tests (27 Tests grün)
- **Tier 1.9 done:** In-Game-Menü
- **Tier 2.x done:** Take-Down (2.1), Body-Discovery + Spectator (2.2/2.6), Vents (2.3), Lights-Sabotage (2.4), Comms-Sabotage (2.5)
- **Tier 3 = Mini-Games (NEU)**, statt der ursprünglichen Godot-Migration:
  - 3.1 Mini-Game-Framework (Server + WS-API + pluggable Modal): done
  - 3.2 „Test-Suite reparieren" Mini-Game für `fix_unit_tests`: done
- **Godot-Migration ist von Tier 3 auf Tier 4 gewandert** — alles im Spike, was vorher „Tier 3.x" hieß, heißt jetzt „Tier 4.x".
- Marketing-Landing-Page unter `/`, Logo, Asset-Lizenz-Doku
- Bugfixes: Speed-Skalierung, Editor-TDZ, Vent-Persistierung

**Was das für den Spike heißt:**

- **Pre-Tier-3 → Pre-Tier-4** Sektion in `docs/ROADMAP.md`. Phasen `P3.x` → `P4.x`.
- **Backend ist jetzt fetter:** `game_state` enthält jetzt auch Mini-Game-Status (`mini_game_*`-Messages auf der WS), Vents, Body-Reports, Spectator-Player-Lists. Der Spike-Code ignoriert all das (Default-Case im `match` loggt nur) — das ist beabsichtigt und für den Test-Plan unkritisch.
- **Neuer Doku-Abschnitt in `docs/CLIENT.md §4`** erwähnt das Mini-Game-API als Tier-4-Anforderung, die im Spike bewusst nicht implementiert wird.
- **`docs/PROTOCOL.md` auf `main`** hat seit dem Merge zusätzliche Messages (`mini_game_started/_input/_state/_completed`, evtl. Body-Report-Erweiterungen). Vor Runtime-Test mit Godot ist es sinnvoll, einmal `git diff main..slice/godot-spike -- docs/PROTOCOL.md` zu checken — wir hatten unsere eigenen Doku-Fixes pre-Spike, die auch in main eingelaufen sind, aber Mini-Game-Messages sind seit Tier 3.1 dort dokumentiert.
- **Merge-Commit:** `ffdf038 Merge branch 'main' into slice/godot-spike`. Folge-Commit für Tier-3 → Tier-4-Renumbering der Spike-Doku ist der Commit unmittelbar danach.

---

## Wenn du wieder einsteigst — die ersten 10 Minuten

1. **Godot 4.3 LTS installieren**, falls noch nicht: <https://godotengine.org/download/archive/4.3-stable/>. Linux-AppImage reicht.
2. **In den Worktree wechseln:**
   ```bash
   cd /home/sr/se/mcm/.worktrees/godot-spike
   git status     # erwartet: clean, on slice/godot-spike
   ```
3. **Backend in einem zweiten Terminal vom Main-Repo aus starten** (Backend-Code lebt auf `main`, nicht auf dem Spike-Branch):
   ```bash
   cd /home/sr/se/mcm
   uv run uvicorn app.main:app --reload
   ```
4. **Test-Plan abarbeiten:** `docs/CLIENT.md §6` listet vier konkrete Akzeptanzpfade (Connect, Map-Layout, Movement, Reconnect). Die ersten drei sind je < 2 Minuten, Reconnect-Test ca. 5 Minuten.

Erwartetes Ergebnis: alles grün, ggf. ein oder zwei kleinere Bugs (typische Godot-4-Quirks bei der ersten echten Ausführung).

---

## Was im Branch liegt (Übersicht)

```
godot/                          # NEU: Godot-Subfolder
├── project.godot               # 4.3-Konfig, gl_compatibility-Renderer (Web-Export-tauglich)
├── icon.svg                    # Platzhalter
├── README.md                   # How-to-run
├── scenes/
│   ├── main.tscn               # Connect-UI (Entry)
│   └── debug_world.tscn        # Camera2D + Renderer + InputSender
└── scripts/
    ├── protocol.gd             # Konstanten + Message-Type-Strings
    ├── ws_client.gd            # WebSocketPeer-Wrapper
    ├── main.gd                 # Connect-Driver, World-Switch
    ├── debug_renderer.gd       # _draw() + Snapshot-Buffer + lerp
    └── input_sender.gd         # Keyboard-Capture mit 20-Hz-Throttle

docs/
├── CLIENT.md                   # NEU: normative Client-Doku + Test-Plan §6
├── ROADMAP.md                  # MODIFIZIERT: neue Pre-Tier-4-Sektion vor Tier 4 (Tier 3 = Mini-Games seit Restructure)
└── superpowers/
    ├── specs/2026-04-26-godot-spike-design.md   (auf main)
    ├── plans/2026-04-26-godot-spike.md          (auf main)
    └── notes/2026-04-26-godot-spike-resume.md   (dieses Dokument)
```

`.gitignore` (top-level) ergänzt um `godot/.godot/` und `godot/exports/`.

---

## Commits auf `slice/godot-spike`

```
a6fd462 docs(godot-spike): CLIENT.md test-plan, godot/README, ROADMAP entry
1ed763e feat(godot): send player_input at 20 Hz with input throttling
bc7a2f6 feat(godot): add debug renderer with map, player boxes, snapshot interpolation
d2d5841 feat(godot): connect-flow with join_room and lobby logging
ed7dec6 docs(client): CLIENT.md initial draft for Godot spike
b32601b chore(godot): scaffold Godot 4.3 project skeleton
```

**Pre-Spike auf `main` (commits `19ecbbf` + `97877d4`):**
- `docs/PROTOCOL.md`: `rejoin`, multi-map `lobby_state`, erweitertes `game_state`, `private_state`-Message, `REJOIN_NOT_AVAILABLE`
- `docs/maps.md`: Map-Größe auf 4800×3200 korrigiert
- `docs/superpowers/specs/2026-04-26-godot-spike-design.md`: Spec
- `docs/superpowers/plans/2026-04-26-godot-spike.md`: Implementation-Plan

---

## Adaptationen vs. ursprünglicher Plan

Wir haben den Plan zwar als Skript benutzt, aber inline implementiert (kein Subagent-Driven mit dreifachem Review pro Task). Das hat zu Bündelungen geführt:

| Plan-Tasks | Tatsächlicher Commit | Begründung                                                                |
| ---------- | -------------------- | ------------------------------------------------------------------------- |
| 1, 2, 3    | `b32601b`            | Worktree + Skelett + .gitignore in einem chore-Commit                     |
| 4          | `ed7dec6`            | CLIENT.md initial — wie geplant                                           |
| 5, 6, 7    | `d2d5841`            | protocol.gd + ws_client.gd + main.tscn + main.gd zusammen (alle pre-Render) |
| 8, 9, 10, 12 | `bc7a2f6`          | debug_renderer.gd komplett (inkl. Player-Render und Interpolation), debug_world.tscn, main.gd-Update zusammen |
| 11         | `1ed763e`            | input_sender.gd + debug_world.tscn-Update + main.gd-Hook                  |
| 13, 14, 15, 16 | `a6fd462`        | CLIENT.md §6 Test-Plan + godot/README + ROADMAP-Update zusammen           |

Funktional identisch zum Plan. Nur weniger Atomicity, dafür schnellere Iteration. Falls Runtime-Tests Bugs aufdecken, einfach Fix-Commits oben drauf.

**Eine kleine Plan-Abweichung in `main.gd::_switch_to_world()`:** Statt `_ws.reparent(world)` und Mein-Self-Hide nutze ich `add_child.call_deferred(world) + await get_tree().process_frame`. Begründung: Reparent in Godot 4.3 kann während Signal-Dispatch Crashes verursachen wenn der WSClient gerade ein Message-Signal feuert. Das ist die robustere Variante. Der Plan ist hier theoretisch, mein Code praktisch.

---

## Offene Punkte (P3.4)

In Reihenfolge der Priorität:

1. **Godot lokal installieren.** Godot 4.3 LTS, nicht 4.4 (LTS-Argument für langen Tier-4-Sprint).
2. **Test-Plan durchlaufen** (`docs/CLIENT.md §6`):
   - Test 1 (Connect+Lobby): erwartet grün out-of-the-box.
   - Test 2 (Map-Layout): wahrscheinlich grün, Camera2D-Zoom evtl. justieren wenn der Browser-Editor-Vergleich zeigt dass Map nicht zentriert ist.
   - Test 3 (Movement): erwartet grün, Reibungspunkte typischerweise bei Snapshot-Buffer-Edge-Cases.
   - Test 4 (Reconnect): Test 4a + 4c sollten ohne Code-Änderung grün sein. Test 4b (rejoin mit gespeicherter playerId) braucht eine temporäre Änderung in `main.gd::_on_connected`. Anweisung steht im Test-Plan.
3. **`[VERIFY:Phase-X]`-Marker in `docs/CLIENT.md` durch gemessene Werte ersetzen.**
4. **Sektion 5 von `docs/CLIENT.md`** um neu entdeckte Doku-Lücken erweitern (falls welche auftauchen).
5. **`docs/ROADMAP.md` Pre-Tier-4 P4.4 auf `done` setzen.**
6. **Branch-Decision:** Wenn alles grün → `git push origin slice/godot-spike` + GitHub-PR, oder direkt `git merge slice/godot-spike` auf main, oder Branch liegen lassen bis Tier 4 startet.

---

## Bekannte Risiken / mögliche Stolpersteine bei Runtime-Verify

- **Godot 4.3 `Dictionary.hash()` in `input_sender.gd`:** Ich verlasse mich darauf, dass zwei Dictionaries mit gleichen Keys/Values gleichen Hash haben. In Godot 4 ist das so — falls nicht, fallback auf direkten Vergleich der vier Bool-Felder.
- **`Color(hex)` mit `#RRGGBB`-Strings:** Funktioniert in Godot 4 ab 4.0 — sollte safe sein.
- **`draw_string` ohne expliziten Font:** `ThemeDB.fallback_font` ist die korrekte 4.3-API (war früher `Theme.get_default_font()`).
- **`World`-Scene-Reparent:** Die `call_deferred + process_frame`-Logik in `_switch_to_world()` sollte sauber sein, aber wenn der Spike beim Connect crashed, ist das der erste Verdächtige.
- **WSClient-Signals nach `add_child(world)`:** Da `_ws` Kind von Main bleibt (wir hängen NICHT um), bleiben Signals zu `_on_message` verbunden. Renderer-Updates laufen über `_renderer`-Referenz. Sollte funktionieren.

---

## Wenn etwas anders weitergeht

- **Godot-Install dauert / kommt nicht:** Spike-Branch liegen lassen, mit Tier 1.9 (In-Game-Menü) und Tier 2 (Among-Us-Features im Browser) weitermachen. Nichts hängt blockierend davon ab — die Pre-Spike-Doku-Fixes auf `main` sind bereits drin.
- **Spike wird trashed:** Branch löschen, Worktree entfernen (`git worktree remove .worktrees/godot-spike && git branch -D slice/godot-spike`). Der Spec/Plan/Notes auf `main` bleiben als Lessons-Learned. Auf `main` müsste man dann nur `docs/superpowers/specs|plans|notes/2026-04-26-godot-spike*` ggf. archivieren.
- **Spike wird zur Tier-4-Basis:** Die Phasen 4.1–4.4 aus der Roadmap übernehmen die Strukturen aus `godot/scripts/` direkt (Protocol, WSClient, Main bleiben — DebugRenderer wird durch Tilemap + Charakter-Sprites ersetzt). Phase 4.6 (Task-Interaktion) implementiert das Mini-Game-API aus Tier 3 (`mini_game_started/_input/_state/_completed`) — der Spike kennt das API noch nicht.

---

## Konversationskontext (für Future-Claude oder Future-Sven)

- **Brainstorming-Entscheidung war:** Mono-Repo, nicht separates Repo (Begründung in Spec §4: Protokoll-Drift wäre größtes Risiko).
- **Spike-Scope-Entscheidung:** Option C (Connect + Lobby + Map + Player + Interpolation), nicht A oder B. Begründung: ohne Map-Render-Validation wäre Koordinaten-Konvention nur theoretisch.
- **Godot-Version-Entscheidung:** 4.3 LTS, nicht 4.4 latest. Begründung: Tier 4 ist langer Sprint (~5–7 Wochen), LTS reduziert Breakage.
- **Implementation-Style-Entscheidung:** Inline statt Subagent-Driven. Begründung: Subagent-Overhead (Implementer + 2 Reviews pro Task) lohnt sich nicht für Spike-Code, der eh visuelle Acceptance braucht.
