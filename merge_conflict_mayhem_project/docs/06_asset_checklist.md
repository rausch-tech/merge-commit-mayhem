# 06 – Asset Checklist

## Produktions-Checklist für das MVP-Asset-Pack

Legende:

| Priorität | Bedeutung |
|---|---|
| P0 | Muss für den ersten spielbaren MVP vorhanden sein |
| P1 | Wichtig für eine schöne interne Demo |
| P2 | Nice-to-have / späterer Polish |

---

# 1. Branding & Logo

| Asset | Beschreibung | Format | Priorität |
|---|---|---:|---:|
| Game Logo | „Merge Conflict Mayhem“ Hauptlogo | PNG transparent, optional SVG | P0 |
| Subtitle Badge | „Lunch Break Edition“ separat | PNG transparent | P1 |
| Small Header Logo | Kleine Version für HUD oben links | PNG transparent | P0 |
| App Icon | Launcher / Browser Tab | 512×512 PNG | P1 |
| Favicon | Browser-Favicon | 32×32 / 64×64 PNG | P1 |
| Splash Screen Logo | Startscreen | PNG transparent | P1 |

---

# 2. UI-Grundelemente

| Asset | Beschreibung | Format | Priorität |
|---|---|---:|---:|
| Top HUD Panel | Obere Statusleiste | 9-slice PNG oder Godot StyleBox | P0 |
| Left Sidebar Panel | Taskliste links | 9-slice PNG / StyleBox | P0 |
| Right Sidebar Panel | Eventfeed rechts | 9-slice PNG / StyleBox | P0 |
| Bottom Action Bar | Leiste für Buttons unten | 9-slice PNG / StyleBox | P1 |
| Small Stat Card | Progress, Coffee, Incidents etc. | 9-slice PNG / StyleBox | P0 |
| Tooltip Box | Infobox bei Hover | 9-slice PNG / StyleBox | P1 |
| Popup Panel | Allgemeines Modal-Fenster | 9-slice PNG / StyleBox | P0 |
| Meeting Overlay | Meeting-/Voting-Screen | 9-slice PNG / StyleBox | P0 |
| Endscreen Card | Ergebnis-/Scorecard | 9-slice PNG / StyleBox | P1 |
| Alert Card | Warnmeldung / Incident Card | 9-slice PNG / StyleBox | P1 |

---

# 3. Buttons

| Asset | Beschreibung | Format | Priorität |
|---|---|---:|---:|
| Primary Button | Hauptaktion | Godot Theme / PNG | P0 |
| Secondary Button | Nebenaktion | Godot Theme / PNG | P0 |
| Danger Button | Rauswerfen / Sabotage | Godot Theme / PNG | P0 |
| Confirm Button | Bestätigen | Godot Theme / PNG | P0 |
| Cancel Button | Abbrechen / Skip | Godot Theme / PNG | P0 |
| Icon Button | Quadratisch mit Icon | PNG / Theme | P1 |
| Ability Button | Button unten | PNG / Theme | P1 |
| Disabled State | Deaktiviert | Theme-State | P0 |
| Hover State | Mouseover | Theme-State | P1 |
| Pressed State | Klickzustand | Theme-State | P1 |
| Selected State | Aktiv ausgewählt | Theme-State | P1 |

Empfehlung: Buttons primär in Godot per Theme bauen, Icons separat als PNG.

---

# 4. Status Icons

| Icon | Bedeutung | Farbe | Priorität |
|---|---|---:|---:|
| Release Progress | Fortschritt / Deploy | Grün | P0 |
| Pipeline Stability | Server / Shield / Wrench | Blau | P0 |
| Incidents | Bug / Sirene / Alert | Rot | P0 |
| Coffee | Tasse / Kaffeemaschine | Orange | P0 |
| Timer | Uhr / Countdown | Weiß / Gelb | P0 |
| Players | Spieleranzahl | Weiß / Blau | P1 |
| Connection | Netzwerkstatus | Blau / Rot | P1 |
| Ping / Latency | Remote-Status | Blau | P2 |
| Settings | Zahnrad | Grau | P0 |
| Chat | Sprechblase | Grau / Blau | P1 |
| Audio | Speaker | Grau | P2 |

---

# 5. Task Icons

| Icon | Verwendung | Farbe | Priorität |
|---|---|---:|---:|
| Fix Unit Tests | Task | Grün | P0 |
| Review Pull Request | Task | Lila | P0 |
| Refill Coffee | Task | Orange | P0 |
| Calm Legacy System | Task | Giftgrün | P0 |
| Repair Deployment | Task | Blau | P0 |
| Analyze Logs | Task | Blau | P1 |
| Reduce Scope | Task | Lila | P1 |
| Write Release Notes | Task | Grün / Blau | P1 |
| Restart Server | Task | Blau | P1 |
| Update Dependency | Task | Grün / Gelb | P2 |
| Close Ticket | Task | Grün | P2 |
| Find Missing Semicolon | Task | Gelb | P2 |
| Decode Customer Requirement | Task | Lila / Gelb | P2 |
| Stop Cronjob | Task | Giftgrün | P2 |

MVP-Minimum:

- Fix Unit Tests
- Review Pull Request
- Refill Coffee
- Calm Legacy System
- Repair Deployment

---

# 6. Sabotage Icons

| Icon | Sabotage | Farbe | Priorität |
|---|---|---:|---:|
| CI/CD Red | Pipeline beschädigen | Rot | P0 |
| Coffee Outage | Kaffee leer | Orange / Rot | P0 |
| Mandatory Meeting | Meeting erzwingen | Lila / Rot | P0 |
| Merge Conflict Storm | neue Konflikte spawnen | Rot / Lila | P1 |
| Fake Customer Request | unnötiger Task | Gelb / Rot | P1 |
| Legacy Awakening | Legacy-System wecken | Giftgrün / Rot | P1 |
| Flaky Tests | Tasks instabil | Rot / Gelb | P2 |
| Scope Creep | Umfang wächst | Lila / Rot | P2 |
| Network Lag | Spieler verlangsamen | Blau / Rot | P2 |
| Main Branch Damage | Hauptbranch beschädigen | Rot | P2 |
| Shadow Admin Override | Rechte missbrauchen | Dunkelrot | P2 |
| Documentation Delete | Docs löschen | Rot / Grau | P2 |

MVP-Minimum:

- CI/CD Red
- Coffee Outage
- Mandatory Meeting

---

# 7. Action / Ability Icons

| Icon | Aktion | Farbe | Priorität |
|---|---|---:|---:|
| Ping | Position markieren | Blau | P0 |
| Interact | Objekt benutzen | Weiß / Blau | P0 |
| Report | Verdacht melden | Rot | P0 |
| Emergency Meeting | Meeting starten | Rot / Lila | P0 |
| Vote | Abstimmen | Weiß / Gelb | P0 |
| Skip Vote | Voting überspringen | Grau | P0 |
| Distract | Ablenkung | Lila | P1 |
| Speed Boost | schneller laufen | Grün | P1 |
| Coffee Run | Kaffee-Buff | Orange | P1 |
| Emote | Reaktion | Gelb | P1 |
| Rollback | Sabotage rückgängig | Blau | P1 |
| Scan Logs | Raum prüfen | Blau | P1 |
| Auto Fix Bot | KI-Helfer | Cyan / Grün | P2 |
| Focus Mode | Task schneller | Grün | P2 |

---

# 8. Role Badges

| Badge | Rolle | Team | Priorität |
|---|---|---:|---:|
| Developer | Standard-Teamrolle | Release-Team | P0 |
| DevOps Engineer | Infrastruktur | Release-Team | P0 |
| AI Engineer | KI-Tasks / Bot | Release-Team | P0 |
| Vibe Coder | Chaos-Agent | Chaos | P0 |
| Data Wizard | Analyse / Logs | Release-Team | P1 |
| Consultant | Meetings / Scope Creep | Chaos | P1 |
| Shadow Admin | Server-Sabotage | Chaos | P1 |
| Incident Commander | Repair / Koordination | Release-Team | P2 |
| Caffeine Collector | Kaffee-Buffs | Release-Team | P2 |
| Bug Squasher | Testfixes | Release-Team | P2 |
| Legacy Oracle | Legacy-Erkennung | Neutral / Team | P2 |
| Scrum Master | Buffs / Meetings | Ambivalent | P2 |

---

# 9. Character Assets

| Asset | Beschreibung | Format | Priorität |
|---|---|---:|---:|
| Base Character Idle | neutrale Figur | Sprite PNG | P0 |
| Base Character Walk | einfache Laufanimation | Sprite Sheet | P0 |
| Developer Variant | Hoodie / Laptop-Vibe | Sprite Sheet | P1 |
| DevOps Variant | Cap / Headset / Wrench | Sprite Sheet | P1 |
| AI Engineer Variant | Hoodie / Chip / Bot-Vibe | Sprite Sheet | P1 |
| Vibe Coder Variant | dunkler Hoodie / sus | Sprite Sheet | P1 |
| Color Variants | 6–8 Spielerfarben | Palette / Shader | P0 |
| Nameplate Background | Hintergrund für Namen | PNG / Theme | P0 |
| Suspicion Marker | Warnsymbol | PNG | P0 |
| Eliminated Ghost | ausgeschiedener Spieler | Sprite | P2 |

---

# 10. Room Labels

| Label | Raum | Farbe | Priorität |
|---|---|---:|---:|
| Open Space | Bürobereich | Blau-Grau | P0 |
| Server Room | Serverraum | Blau | P0 |
| Meeting Room | Meetingraum | Lila | P0 |
| Kitchen | Küche | Orange | P0 |
| Legacy Basement | Keller | Giftgrün | P0 |
| War Room | Kommandozentrale | Blau / Cyan | P0 |

---

# 11. Environment Assets

## Boden / Wände / Türen

| Asset | Beschreibung | Priorität |
|---|---|---:|
| Office Floor Tile | neutraler Büroboden | P0 |
| Server Floor Tile | dunkler Technikboden | P0 |
| Kitchen Floor Tile | heller Fliesenboden | P0 |
| Meeting Carpet Tile | lila/blauer Teppich | P1 |
| Legacy Floor Tile | dunkler Kellerboden | P1 |
| Wall Segment | Standardwand | P0 |
| Corner Wall | Wandecke | P0 |
| Door Open | offene Tür | P0 |
| Door Closed | geschlossene Tür | P1 |
| Window / Glass Wall | Meetingraum-Glas | P1 |
| Stairs | Legacy-Keller-Treppe | P2 |

## Open Space Props

| Asset | Priorität |
|---|---:|
| Desk | P0 |
| Office Chair | P0 |
| Monitor | P0 |
| Laptop | P0 |
| Bookshelf / Cabinet | P1 |
| Whiteboard | P1 |
| Sticky Notes | P1 |
| Rubber Duck | P2 |
| Plant | P1 |

## Server Room Props

| Asset | Priorität |
|---|---:|
| Server Rack | P0 |
| Cable Bundle | P0 |
| Network Switch | P1 |
| Warning Light | P1 |
| Broken Server Panel | P1 |
| Spark VFX | P1 |

## Kitchen Props

| Asset | Priorität |
|---|---:|
| Coffee Machine | P0 |
| Coffee Machine Broken | P1 |
| Coffee Cup | P0 |
| Fridge | P1 |
| Counter | P0 |
| Donut Box | P2 |
| Mate Crate | P2 |
| Coffee Spill | P1 |

## Meeting Room Props

| Asset | Priorität |
|---|---:|
| Meeting Table | P0 |
| Meeting Chairs | P0 |
| Presentation Board | P0 |
| Pie Chart Board | P1 |
| Agenda Paper | P1 |
| Projector | P2 |

## Legacy Basement Props

| Asset | Priorität |
|---|---:|
| Retro Terminal | P0 |
| Green CRT Screen | P0 |
| Old Server Box | P1 |
| Pipe Segment | P1 |
| Cable Mess | P1 |
| Warning Sign „Do Not Touch“ | P1 |
| Skull / Skeleton Gag | P2 |
| Toxic Glow VFX | P2 |
| Cobweb | P2 |

## War Room Props

| Asset | Priorität |
|---|---:|
| Dashboard Screen | P0 |
| War Room Table | P0 |
| Laptop | P0 |
| Big Whiteboard | P1 |
| Pipeline Chart | P1 |
| Pizza Box | P2 |
| Incident Clipboard | P2 |

---

# 12. Task Interaction Marker

| Marker | Bedeutung | Farbe | Priorität |
|---|---|---:|---:|
| Available Task Marker | Task verfügbar | Grün | P0 |
| In Progress Marker | Task läuft | Blau | P0 |
| Completed Marker | Task fertig | Grün | P0 |
| Sabotage Marker | Sabotage aktiv | Rot | P0 |
| Repair Marker | Reparatur nötig | Blau / Gelb | P0 |
| Meeting Marker | Meeting möglich | Lila | P0 |
| Locked Marker | nicht verfügbar | Grau | P1 |
| Cooldown Marker | im Cooldown | Grau / Blau | P1 |
| Warning Pulse | Gefahr | Rot | P1 |

---

# 13. VFX

| Effekt | Beschreibung | Priorität |
|---|---|---:|
| Task Progress Glow | Glow bei Task | P0 |
| Completion Spark | Erfolgseffekt | P1 |
| Sabotage Pulse | roter Puls | P0 |
| Warning Flash | rotes Blinken | P0 |
| Server Spark | Funken im Serverraum | P1 |
| Coffee Steam | Dampf bei Kaffee | P1 |
| Legacy Green Glow | Keller-Effekt | P1 |
| Meeting Dim Overlay | Spiel wird gedimmt | P0 |
| Voting Highlight | Auswahl leuchtet | P0 |
| Player Ping Ring | Ping-Kreis | P0 |

---

# 14. Minimalstes MVP-Asset-Pack

## UI

- 1 Logo
- 5 Status Icons
- 5 Task Icons
- 3 Sabotage Icons
- 5 Action Icons
- 3 Panel-Stile
- 3 Button-Stile

## World

- 5 Boden-/Wand-Tiles
- 10 Props
- 6 Room Labels
- 1 Character Base
- 5 Character-Farben
- 4 Marker

Das reicht für eine erste interne Demo.

---

# 15. Ordnerstruktur

```text
assets/
  branding/
    logo_main.png
    logo_hud.png
    icon_app.png

  ui/
    panels/
    buttons/
    icons/
      status/
      tasks/
      sabotages/
      actions/
      roles/

  world/
    tiles/
    props/
    labels/

  characters/
    base/
    roles/

  vfx/
```

---

# 16. Dateinamen-Konvention

```text
icon_task_fix_unit_tests.png
icon_task_review_pull_request.png
icon_sabotage_ci_cd_red.png
icon_sabotage_coffee_outage.png
icon_action_emergency_meeting.png
badge_role_vibe_coder.png
prop_server_rack_01.png
tile_floor_office_01.png
panel_eventfeed_default.png
button_primary_hover.png
```

---

# 17. Empfohlene Größen

| Assettyp | Größe |
|---|---:|
| UI Icons | 256×256 px |
| HUD Icons | 128×128 px |
| Buttons | 512×128 px |
| Square Ability Buttons | 256×256 px |
| Panels | 512×512 oder 1024×256 px |
| Props | 256×256 oder 512×512 px |
| Characters | 128×128 oder 256×256 px |
| Isometrische Tiles | 128×64 oder 256×128 px |
| Top-down Tiles | 64×64 oder 128×128 px |

