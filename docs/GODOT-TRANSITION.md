# Godot-Transition

**Stand:** 2026-04-25
**Ziel:** Browser-Client bleibt als Referenz und Web-Fallback. Der "echte" Client wird ein Godot-4-Projekt, das das gleiche WebSocket-Protokoll spricht. Visuelles Ziel: **Among-Us-Niveau** an Polish (Tilemap, Charakter-Animationen, Sound-Mixing, smoothes Movement).

Dieses Dokument ist der gemeinsame Plan für den Übergang. Es ist nicht in Stein gemeißelt — Entscheidungen aus Abschnitt 3 müssen wir explizit zusammen treffen, bevor wir den Godot-Sprint starten.

---

## 0. Was wir aktuell haben

- Funktionierendes Backend (FastAPI + Pydantic + WebSocket), 207 Tests grün
- Server-autoritativ für allen State, Map als JSON-Daten in `maps/default.json`, an Client per `room_joined` mitgeschickt
- Browser-Client als Plain-HTML/JS-Canvas-Implementierung
- Volle Spielmechanik: Lobby, Tasks, Sabotagen, Walls + Türen, Scrolling-Camera, Voting + Emergency Meeting, Win/Lose, Endscreen
- Hosting: AWS EC2 t4g.nano in eu-central-1 mit Caddy + sslip.io HTTPS — `https://mcm.3-78-184-97.sslip.io`

Der aktuelle Browser-Client ist **funktional vollständig, aber visuell rudimentär** (Rechtecke, Kreise, Comic-Sprites aus AI-generierten Composite-PNGs). Die Spielmechanik beweist sich; das Spielgefühl ist Prototype-Niveau.

---

## 1. Was VORHER stabil sein muss

Bevor wir mit Godot anfangen, sollte das hier abgeschlossen sein, sonst portieren wir mehrfach (Browser → Godot zweimal für jedes neue Feature).

| Punkt | Wo aktuell | Aufwand | Warum vor Godot |
|---|---|---|---|
| **Protokoll fixiert + dokumentiert** | In Pydantic-Modellen + Specs pro Slice. Kein konsolidiertes `docs/protocol.md`. | 0.5 Tag | Godot-Implementierer braucht den vollständigen Vertrag. Wenn das Protokoll während des Godot-Sprints noch wackelt, doppelte Arbeit. |
| **Map-Format fixiert** | `maps/default.json` + Pydantic-Modelle in `app/game/game_map.py`. | 0.5 Tag | Falls wir Felder ergänzen wollen (Tile-Layer, Background-Bilder, Spawn-Orientierung), jetzt klären. Sonst muss Godot später re-laden. |
| **Map-Editor (Phase 1)** | Existiert nicht. Maps sind handgeschriebene JSONs. | 2–3 Tage | Sonst hängt Godot auf der Standardmap fest und wir können das Spielgefühl nicht über mehrere Maps validieren. |
| **Tier-1-Mechaniken (Take-Down + Eventfeed + Incidents)** | Geplant, nicht gebaut. | 2–3 Tage | Im Browser bauen ist billig. Sonst muss Godot diese Features selber bauen oder warten. |
| **Asset-Pipeline-Entscheidung** | Offen. | 1 Tag Research + Diskussion | Asset-Stil bestimmt den ganzen Godot-Sprint. Falsche Entscheidung = neuer Anlauf. |

**Vor-Godot-Block:** ca. 1–2 Wochen. Anschließend ist die Browser-Version "feature-frozen" für eine Weile, neue Features kommen direkt im Godot-Client.

---

## 2. Was Godot bringt (und was sonst schmerzhaft wäre)

| Was | Warum wichtig | Browser-Equivalent (jetzt) |
|---|---|---|
| **Echte Tilemap statt Rechtecke** | Räume haben Boden-Tiles, Möbel, Deko. Among-Us-Map hat Schreibtische, Computer, Fenster. | `ctx.fillRect()` mit einer einzigen Farbe pro Raum |
| **Charakter-Animationen** (idle, walk, run, mehrere Richtungen) | Spieler sieht lebendig aus, nicht wie ein Comic-Standbild. Among-Us-Charaktere watscheln, idle-bobben, reagieren. | Statisches Composite-PNG aus `figuren.png` |
| **Smoothes Movement-Interpolation** | Zwischen 20-Hz-Server-Snapshots interpolieren, damit Bewegung nicht ruckelt. | Keiner — Frames springen jeden Tick |
| **Particle-Effects** | Funken bei CI/CD-Rot, Sparks beim Reparieren, Scanline beim Legacy-System. | Keiner |
| **Sound-Mixing** | Footsteps + Ambient + UI-SFX + Music gleichzeitig sauber gemixt. | `new Audio().play()` ohne Bus-Mixing |
| **Saubere UI-Animationen** | Panels die reinsliden, Buttons die popen, Voting-Overlay mit Schlieren-Effekt. | `transition: opacity 200ms` |
| **Asset-Pipeline** | Sprite-Sheets, Tilesets, Animationen werden als Assets getrackt; Drag-and-drop im Editor. | Composite-PNGs mit CSS `background-position` |
| **Web-Export** | Browser-Run via WASM aus demselben Projekt. | — (Browser-Client bleibt der Web-Run) |

Der Browser-Client wird nicht überflüssig — er bleibt der **Plain-Web-Fallback** und das **Reference-Implement** für Protokoll-Tests.

---

## 3. Design-Entscheidungen die JETZT fallen müssen

Diese Fragen blocken den Godot-Sprint. Sven entscheidet, das Doc dokumentiert die Optionen.

### 3.1 Among-Us-Feature-Set übernehmen?

**Optionen:**
- **(a) Voll Among-Us:** Vents (Chaos teleportiert), Body-Discovery + Report-Button (führt zum Meeting), Kill-Animationen (1.5 s Cutscene), Lights-Sabotage (alle sehen reduzierte Sicht), Comms-Sabotage (deaktiviert Tasks/Sicht).
- **(b) Eigener Twist:** Nur unsere DevOps-Mechanik (Tasks, Sabotagen, Voting, Take-Down), keine Vents, keine Bodies. Eliminierung passiert anonym wie aktuell.

Empfehlung: (b) für die erste Godot-Beta. (a) als optionale Phase-2 wenn (b) sich gut spielt. Among-Us-Features sind viel Aufwand und lenken vom DevOps-Charme ab.

### 3.2 Mobile-Target?

**Optionen:**
- **(a) Nur Desktop / Web:** Godot exportiert HTML5 + Linux/Mac/Windows. Tastatur-Maus-Steuerung.
- **(b) + Mobile:** Touch-Controls zusätzlich entwickeln (Joystick + Kontext-Buttons). Aufwand: +1–2 Wochen.

Empfehlung: (a) erstmal. Among Us ist zwar Mobile-First, aber unser Zielpublikum sind Tech-Teams in der Mittagspause am Laptop.

### 3.3 Art-Stil

**Optionen:**
- **(a) Pixel Art:** Klassische 16×16 oder 32×32 Tiles + Sprite-Sheets. Einfachste Pipeline, viele freie Asset-Packs. „Stardew Valley" / „Among Us"-Look.
- **(b) Flat/Vector-Cartoon:** Wie unsere aktuellen Composite-PNGs. Schwerer in Tilemaps zu arbeiten, aber zum aktuellen Look kompatibel.
- **(c) 3D-Isometric:** Aufwand explodiert (Modeling, Animation, Lighting). Out-of-scope.

Empfehlung: (a). Pixel-Art-Look ist nostalgisch, dev-thematisch passend, und es gibt riesige Asset-Pools.

### 3.4 Art-Quelle

**Optionen:**
- **(a) Asset-Pack kaufen** (z.B. itch.io, Humble Bundle, Synty). Stunde Suchen, ~$20–80 für ein gutes Pack. Konsistente Qualität, Lizenz-fragen geklärt.
- **(b) AI generieren** (wie aktuelle Composite-PNGs). Schwer für Tilesets weil Tile-Konsistenz an Kanten hart ist. Charaktere geht.
- **(c) Commission** (Pixel-Art-Künstler:in beauftragen). $200–2000+ je nach Umfang. Maßgeschneidert für unsere DevOps-Themen.
- **(d) Selber zeichnen** mit Aseprite/Pyxel. Zeit-intensiv aber vollständig kontrolliert.

Empfehlung: **(a) für Tiles + Basis-Charaktere, (b) für DevOps-Spezial-Sprites** (Coffee-Maschinen, Server-Racks, etc. die in Standard-Packs nicht drin sind). Hybrid.

### 3.5 Account-System

**Optionen:**
- **(a) Kein Account:** Spieler sind nur Name + Raumcode wie jetzt.
- **(b) Light-Persistenz:** Profil mit Skin-Auswahl, Win-Stats, optional aber empfohlen für Wiederkehrer.
- **(c) Volles Account-System:** Login, Friends, Matchmaking. Out-of-scope für Beta.

Empfehlung: (a) bis zum echten Release-Druck. Bei mehr als 50 internen Spielern lohnt (b) eventuell.

### 3.6 Multi-Map-Support

**Optionen:**
- **(a) Nur die default-Map:** Einfach, aber repetitiv.
- **(b) 2–3 Maps zur Auswahl:** Lobby-Dropdown, Host wählt. Erfordert den Map-Editor aus 1.

Empfehlung: (b). Die Editor-Phase-1 aus 1 macht das billig.

---

## 4. Godot-Sprint: Arbeitspakete

Wenn alle Entscheidungen aus 3 gefallen sind:

| # | Paket | Aufwand |
|--:|---|---|
| 1 | Godot 4 Projekt-Setup, Web-Export-Config, WebSocketPeer-Anbindung an Backend | 1 Tag |
| 2 | Lobby-Scene (UI, Raumcode-Input, Spielerliste, Map-Auswahl, Start-Button) | 1–2 Tage |
| 3 | Map-Loader: liest unser Map-JSON, baut Tilemap-Layer dynamisch (oder lädt vor-gebaute Tilemaps pro Map-ID) | 2 Tage |
| 4 | Charakter-Scene: Sprite + Animationen (idle/walk) + Movement-Interpolation aus `game_state` | 2–3 Tage |
| 5 | HUD-Scene: 4 Stat-Pills, Rolle, Timer, mit Tween-Animationen | 1 Tag |
| 6 | Task-Interaktion: Hold-E mit Animation, Progress-Ring, Completion-VFX | 1 Tag |
| 7 | Sabotage-Buttons (Chaos-only) mit Cooldown-Anzeige | 1 Tag |
| 8 | Voting-Overlay + Voting-Result-Toast mit Slide-Animationen | 1 Tag |
| 9 | Endscreen mit Rollen-Reveal + Stats + Confetti-Particles | 1 Tag |
| 10 | Sound-Integration (Footsteps, UI-SFX, optional BGM) | 1 Tag |
| 11 | Polish + Animationen + Bug-Fixes | 3–5 Tage |
| 12 | (optional) Among-Us-Features: Vents, Body+Report, Kill-Anim | 5–8 Tage |
| 13 | Web-Export auf gleiche EC2 oder neuer Bucket | 0.5 Tag |

**Total Godot-Sprint:**
- ohne (12): **3–4 Wochen** Vollzeit
- mit (12): **5–6 Wochen** Vollzeit

Mit Asset-Pack statt Custom-Art ist alles ca. 30 % schneller.

---

## 5. Empfohlene Reihenfolge

```text
[Tier 1: Sprint 2 abschließen]              ── 1 Woche
   Eventfeed + Incidents + Take-Down (im Browser-Client)

[Tier 3a: Multi-Map + Editor Phase 1]       ── 1 Woche
   Lobby-Map-Auswahl + simpler In-Browser-Editor

[Doku-Block]                                ── 1–2 Tage
   docs/protocol.md komplett
   docs/contribution-guide.md
   asset-pipeline-decision.md (Outcome aus Abschnitt 3)

[Asset-Pipeline-Aufbau]                     ── 1 Woche
   Asset-Pack einkaufen + sortieren
   Tileset für „office"-Theme
   Charakter-Sprite-Sheets mit Animation-Frames
   Sound-Pack
   Lizenz-Doku

[Godot-Sprint]                              ── 3–6 Wochen
   Setup → Lobby → Map → Char → HUD → Tasks → Sabotage → Voting → End → Polish

[Deployment]                                ── 0.5 Tag
   Godot-Web-Export auf EC2 (oder S3 + CloudFront)
```

**Total bis Godot-Beta:** **6–10 Wochen** Vollzeit.

Mit Asset-Pack + ohne Among-Us-Features (bzw. nur Browser-Featureset 1:1): realistisch **5–7 Wochen**.

---

## 6. Was im Browser-Client weiterläuft

Der Browser bleibt aktiv. Konkret:

- **Reference-Implementer:** Wenn wir das WS-Protokoll erweitern, im Browser zuerst implementieren. Ist dort billig + schnell zu testen.
- **Web-Fallback:** Wenn Godot-Web-Export nicht auf jedem Browser läuft (älter Mobile, restriktive Firewalls), bietet der Plain-JS-Client einen Fallback-Pfad.
- **Dev-Tooling:** Backend-Devs können den Browser nutzen, ohne Godot zu öffnen.

Wir hätten dann **zwei Clients gegen einen Backend** — was uns die client-agnostische Architektur seit Sprint 1 schon erlaubt.

---

## 7. Risiken + Open Issues

| Risiko | Mitigation |
|---|---|
| Asset-Stil-Drift zwischen den beiden Clients | Wir kuratieren EIN Asset-Pack für beide; Browser zeigt halt vereinfacht |
| Godot-Web-Export-Performance | Browser-Fallback bleibt, zur Not nur Desktop-Build |
| Protokoll-Drift während Godot-Sprint | Protokoll-Freeze-Phase nach 1.5; Änderungen nur mit Godot-Update |
| Among-Us-Features (Vents/Bodies) verzögern Beta | (12) ist optional und kann später kommen |
| Asset-Lizenzen | Nur Packs mit klarer kommerzieller / interner Nutzungs-Lizenz; dokumentiert in `assets/CREDITS.md` |
| Map-Editor wird komplex | Phase 1 absichtlich klein halten — nur Räume, Wände, Türen, Spawns, Task-Anker |

---

## 8. Was als nächstes konkret zu tun ist

Reihenfolge der Entscheidungen, in dieser Sitzung oder asynchron:

1. **3.1 Among-Us-Features:** (a) ja oder (b) nein? → bestimmt Größe vom Godot-Sprint
2. **3.3 Art-Stil:** (a) Pixel, (b) Flat-Cartoon, (c) Iso-3D? → bestimmt Asset-Pipeline
3. **3.4 Art-Quelle:** (a) Pack, (b) AI, (c) Commission, (d) selber? → bestimmt Vorlauf-Aufwand
4. **3.6 Multi-Map-Support:** (a) eine Map, (b) Auswahl? → bestimmt ob Map-Editor in den Vor-Godot-Block muss

Sobald 1–4 entschieden sind, schätze ich Aufwand + Reihenfolge nochmal exakt und wir planen einen Sprint-Plan mit Milestones.

---

## 9. Wo dieses Dokument lebt

- **Pfad:** `docs/GODOT-TRANSITION.md`
- **Update-Pflicht:** Wenn Entscheidungen aus Abschnitt 3 fallen, hier eintragen, damit künftige Sessions / Mitarbeiter:innen den aktuellen Stand sehen
- **Verlinkt von:** `docs/STATE-AND-ROADMAP.md` (sollte ergänzt werden)
