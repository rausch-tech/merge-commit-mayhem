# 07 – Visual Direction

## Ziel

Dieses Dokument beschreibt die visuelle Richtung für Pitch-Visuals, MVP-Grafik und spätere Godot-Umsetzung.

---

# 1. Zwei visuelle Ebenen

## 1. Marketing / Pitch Visuals

Diese Visuals dürfen übertreiben:

- Cover-Art
- Team-Pitch
- Stimmung verkaufen
- Chaos, Humor, Energie
- viele Details
- hohe visuelle Dichte

Sie sind nicht 1:1 das echte Ingame-Ziel.

## 2. Realistischer MVP-Look

Dieser Look muss baubar sein:

- isometrische oder top-down-isometrische Tilemap
- klare Räume
- wenige Props
- wiederverwendbare Assets
- einfache Figuren
- lesbare UI
- keine Asset-Hölle

---

# 2. Cover-Art-Ziel

Cover soll zeigen:

- großes Logo „Merge Conflict Mayhem“
- Subtitle „Lunch Break Edition“
- chaotisches Softwarebüro
- Serverraum mit roter Pipeline
- Kaffeemaschine als kritische Infrastruktur
- Meetingraum
- Legacy-Keller
- War Room
- verdächtiger Saboteur
- mehrere Entwicklerfiguren

Tagline:

> Save the release. Find the saboteur.

---

# 3. MVP-Ingame-Look

Der MVP-Look sollte deutlich einfacher sein als das Cover.

## Anforderungen

- 16:9 Screenshot-kompatibel
- Top-down-isometrische Kamera
- sechs klar erkennbare Räume
- UI klar lesbar
- wenige, aber starke Icons
- einfache Charakter-Sprites
- Raumlabels
- Taskmarker
- Eventfeed

## Visuelle Qualität

Realistisches Ziel:

```text
60–70 % der Detaildichte des Mockups,
aber 100 % Spielbarkeit und Lesbarkeit.
```

---

# 4. Farbsystem

| Bedeutung | Farbe |
|---|---|
| UI Base | Dunkles Navy / Charcoal |
| Erfolg / Tasks | Grün |
| Infrastruktur | Blau |
| Kaffee / Utility | Orange |
| Gefahr / Incidents | Rot |
| Meetings / Social | Lila |
| Legacy | Giftgrün / Gelbgrün |
| Highlights | Gelb |

---

# 5. UI Direction

Das UI soll aussehen wie ein frühes, aber polish-taugliches Indie-Game:

- dunkle Panels
- klare Icons
- farbkodierte Statuswerte
- runde oder leicht bevelige Panels
- gute Lesbarkeit
- keine übertriebene Sci-Fi-Optik
- Humor über Texte und Icons, nicht über visuelle Unordnung

## Haupt-UI

- Top HUD: globale Werte
- links: Taskliste
- rechts: Eventfeed
- unten: Actionbar
- Mitte: Spielwelt

---

# 6. Ingame-Welt

## Open Space

- Schreibtische
- Monitore
- Pflanzen
- Whiteboard
- Sticky Notes

## Serverraum

- Server Racks
- Kabel
- kleine Warnlichter
- technische Blautöne

## Meetingraum

- Tisch
- Stühle
- Whiteboard
- lila Akzente

## Küche

- Kaffeemaschine
- Counter
- Kühlschrank
- orange Akzente

## Legacy-Keller

- altes Terminal
- Kabel
- Rohre
- grüne Beleuchtung
- „Do not touch“-Vibe

## War Room

- Dashboard
- großer Tisch
- Whiteboard
- blaue Kommando-Ästhetik

---

# 7. Prompt für MVP-Ingame-Mockup

```text
Create a realistic MVP in-game screenshot mockup for the internal multiplayer game "Merge Conflict Mayhem: Lunch Break Edition".

Do NOT make a high-detail marketing poster. Instead, render an achievable MVP look for a real Godot game in development: simpler, cleaner, tile-based, more buildable, with fewer props, repeated assets, and a clear game-production aesthetic.

Show a 2D isometric or top-down-isometric office map with six clearly labeled rooms: "Open Space", "Server Room", "Meeting Room", "Kitchen", "Legacy Basement", and "War Room". The rooms should be visually distinct but simple. Use a limited, cohesive color palette and clean lighting. Include a few desks, monitors, server racks, a coffee machine, meeting table, and a retro legacy computer setup, but keep the environment minimal and realistic for an MVP.

Show 4–5 small player characters with simple readable sprites and name tags, such as "CommitNinja", "HotfixHero", "BugSquasher", and "SneakySyntax". Include a suspicious saboteur near the server room. Put a few simple task icons above interactable locations.

Add a practical game HUD that looks like a real playable prototype:
- top status bar with "Release Progress 61%", "Pipeline Stability 74%", "Incidents 1", "Coffee 52%", and "Timer 07:18"
- left sidebar task list with 4 tasks
- right sidebar event feed with 3–4 short entries
- bottom-right action buttons for a few abilities

The overall feel should be fun, clean, readable, and believable as a Godot MVP vertical slice. Keep the UI crisp and legible. Make it look like a real screenshot from an early but polished indie multiplayer game, not a poster, not concept art, and not overly detailed. Preserve the humorous dev-office vibe.
```

---

# 8. Prompt für Cover-Art

```text
Create an original, high-energy indie game cover for a fictional multiplayer game titled "MERGE CONFLICT MAYHEM" with the subtitle "Lunch Break Edition". The cover should feel exciting, humorous, polished, and instantly pitch the game to a team of software engineers.

Visual concept: a dynamic isometric office-and-server-room scene in controlled chaos. Show a compact tech-office environment with six recognizable zones blended into one dramatic cover composition: open office desks, server room racks, meeting room, kitchen/coffee corner, war room, and a spooky legacy-system basement corner. Several stylized developer characters are running around trying to save a software release. One suspicious character is subtly sabotaging things in the background. Include strong story moments: a big monitor showing a red CI/CD pipeline alert, floating error windows, a broken coffee machine, sticky notes, glowing logs, and a war-room dashboard. The team should look like humorous tech nerds, diverse and expressive, wearing hoodies, headphones, glasses, or casual office attire. One character should look sneaky or suspicious.

Mood and style: vibrant, modern, playful, high-detail digital illustration, original game-cover art, slightly comic-book / indie-game aesthetic, dramatic lighting, clean composition, premium finish. Emphasize action, chaos, and team collaboration. Use a bold color palette with deep navy, electric blue, warm orange, coral-red alerts, and bright screen glows. Make it feel like a clever office-chaos party game, not dark horror.

Typography: prominently place the game title "MERGE CONFLICT MAYHEM" in large bold stylish lettering at the top. Place the subtitle "Lunch Break Edition" smaller beneath it. The typography should feel modern and game-like. Optionally include a short teaser line near the bottom such as: "Save the release. Find the saboteur." Ensure all text is clean, legible, and professionally integrated.

Composition: cover art layout suitable for a game cover / Steam capsule style, portrait orientation. Make the title clearly readable and the central artwork eye-catching. No company logos. No platform logos. No age rating badge. Fully original artwork.
```

---

# 9. Realistische Einschätzung

Das detaillierte Mockup ist ein Nordstern, aber kein Sprint-1-Ziel.

Godot kann den Stil grundsätzlich darstellen. Der Aufwand liegt hauptsächlich in:

- Asset-Erstellung
- Animationen
- konsistentem UI
- Props und Tilemaps
- Polish

Für den MVP ist eine reduzierte Version deutlich sinnvoller.

