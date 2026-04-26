# Godot-Bootstrapping-Spike — Stand und Resume-Notes

**Datum der Pause:** 2026-04-26
**Letztes Update:** 2026-04-27 (main mit Tier 0.3 / 1.9 / 2.x / 3.x reingeholt, Roadmap-Restructure: Godot ist jetzt **Tier 4**, Tier 3 sind Mini-Games)
**Branch:** `slice/godot-spike` im Worktree `.worktrees/godot-spike/`
**Spec:** `docs/superpowers/specs/2026-04-26-godot-spike-design.md`
**Plan:** `docs/superpowers/plans/2026-04-26-godot-spike.md`

---

## TL;DR

Der gesamte **Spike-Code ist geschrieben und committet** auf `slice/godot-spike` (mittlerweile 10+ Commits, gebrancht von `main`). Was noch fehlt, ist **Runtime-Verification mit echtem Godot 4.6 Editor** (Test-Plan in `docs/CLIENT.md §6`). Backend ist nicht angefasst. Pre-Spike-Doku-Lücken in `docs/PROTOCOL.md` und `docs/maps.md` wurden auf `main` gefixt.

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

**Sven's Setup:** Windows + WSL2. Backend (`uv run uvicorn`) läuft in WSL, Godot-Editor auf Windows. Claude hat nur Zugriff auf WSL — Iteration-Loop ist: du siehst was in Windows-Godot passiert, sagst mir Bescheid, ich fixe Code in WSL, du F5 nochmal.

1. **Godot 4.6 auf Windows installieren**, falls noch nicht: <https://godotengine.org/download> (Standard-Variante reicht, kein .NET-Build nötig).
2. **In WSL: in den Worktree wechseln und Status prüfen:**
   ```bash
   cd /home/sr/se/mcm/.worktrees/godot-spike
   git status     # erwartet: clean, on slice/godot-spike
   ```
3. **In WSL: Backend in einem zweiten Terminal starten** (Backend-Code lebt auf `main`, nicht auf dem Spike-Branch):
   ```bash
   cd /home/sr/se/mcm
   uv run uvicorn app.main:app --reload
   ```
4. **Auf Windows: Godot-Project-Manager → Import →** UNC-Pfad eingeben:
   `\\wsl.localhost\Ubuntu\home\sr\se\mcm\.worktrees\godot-spike\godot\project.godot`
   (`wsl -l` in PowerShell zeigt deine Distros, falls "Ubuntu" nicht passt).
5. **Test-Plan abarbeiten:** `docs/CLIENT.md §6` listet vier konkrete Akzeptanzpfade (Connect, Map-Layout, Movement, Reconnect). Die ersten drei sind je < 2 Minuten, Reconnect-Test ca. 5 Minuten.

Erwartetes Ergebnis: alles grün, ggf. ein oder zwei kleinere Bugs (typische Godot-4-Quirks bei der ersten echten Ausführung) plus möglicherweise ein WSL-Networking-Issue (siehe nächste Sektion).

---

## Windows + WSL2 — Setup-Spezifika

- **File-Access:** Windows-Godot greift auf WSL-Files via UNC-Pfad zu (`\\wsl.localhost\<Distro>\...`). Funktioniert nativ ohne Mount, ist aber langsamer als lokal. Für einen Spike vollkommen OK; falls Editor-Hänger frustrieren, Worktree einmal nach `C:\` kopieren (Backend bleibt in WSL — nur die Godot-Dateien müssen auf Windows-FS liegen). Aber: zuerst UNC versuchen.
- **WebSocket-Connect:** WSL2 forwarded `localhost:8000` standardmäßig nach Windows. Connect-URL bleibt `ws://localhost:8000/ws`. Falls der Connect failt:
  - In WSL: `ip addr show eth0 | grep inet` → `inet 172.x.x.x/...`-Zeile, die IP nehmen.
  - Im Godot-Connect-UI: `ws://172.x.x.x:8000/ws` statt `localhost`.
  - Oder `ip route show | grep -i default` zeigt die Windows-Host-IP — die ist auch erreichbar.
  - Falls das auch nicht klappt: Windows-Firewall könnte inbound TCP 8000 blocken; uvicorn zusätzlich auf `0.0.0.0` binden: `uv run uvicorn app.main:app --host 0.0.0.0 --reload`.
- **Path-Limit:** Windows hat eine 260-Zeichen-Path-Limitation by default. Der UNC-Pfad oben + Godot-Cache-Files im `.godot/`-Subfolder kann das überschreiten. Falls beim Editor-Import seltsame "path too long"-Fehler kommen: in Windows long-paths aktivieren (`gpedit.msc` → Computer Configuration → Administrative Templates → System → Filesystem → "Enable Win32 long paths"), oder Worktree näher an die Wurzel verschieben.
- **Iteration-Loop:** Du testest in Windows-Godot. Wenn was kaputt ist, sagst du mir genau was (Editor-Fehler, Verbindung scheitert, Box rendert falsch). Ich edite die Files in WSL — Windows-Godot sieht die Änderungen sofort, Auto-Reload funktioniert oft, sonst Editor neu laden. F5 nochmal.

---

## Was im Branch liegt (Übersicht)

```
godot/                          # NEU: Godot-Subfolder
├── project.godot               # 4.6-Konfig, gl_compatibility-Renderer (Web-Export-tauglich)
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

**Eine kleine Plan-Abweichung in `main.gd::_switch_to_world()`:** Statt `_ws.reparent(world)` und Mein-Self-Hide nutze ich `add_child.call_deferred(world) + await get_tree().process_frame`. Begründung: Reparent in Godot 4.x kann während Signal-Dispatch Crashes verursachen wenn der WSClient gerade ein Message-Signal feuert. Das ist die robustere Variante. Der Plan ist hier theoretisch, mein Code praktisch.

---

## Offene Punkte (P3.4)

In Reihenfolge der Priorität:

1. **Godot lokal installieren.** Godot 4.6 (aktuelle stable, Stand 2026-04-27). Eine ursprüngliche Version der Spec hatte „4.3 LTS" — das war ein Fehler von Claude, Godot hat kein offizielles LTS-Programm.
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

- **Godot 4.x `Dictionary.hash()` in `input_sender.gd`:** Ich verlasse mich darauf, dass zwei Dictionaries mit gleichen Keys/Values gleichen Hash haben. In Godot 4 ist das so — falls nicht, fallback auf direkten Vergleich der vier Bool-Felder.
- **`Color(hex)` mit `#RRGGBB`-Strings:** Funktioniert in Godot 4 ab 4.0 — sollte safe sein.
- **`draw_string` ohne expliziten Font:** `ThemeDB.fallback_font` ist die korrekte 4.x-API (war in 3.x `Theme.get_default_font()`).
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
- **Godot-Version-Entscheidung (revidiert 2026-04-27):** Godot 4.6 (aktuell stable). Original-Spec hatte „4.3 LTS" mit dem Argument „LTS reduziert Breakage" — beides falsch: Godot hat kein offizielles LTS-Programm, und für ein neu beginnendes Skelett ist die aktuelle stable das Richtige (frischste Bug-Fixes, Community-Docs/Tutorials). Sven hat den Fehler bemerkt, korrigiert in Commit nach `8fff9bd`.
- **Implementation-Style-Entscheidung:** Inline statt Subagent-Driven. Begründung: Subagent-Overhead (Implementer + 2 Reviews pro Task) lohnt sich nicht für Spike-Code, der eh visuelle Acceptance braucht.
