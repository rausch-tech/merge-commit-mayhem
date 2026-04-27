// MCM Map-Editor — Kind catalogue.
//
// Single source of truth for the editor's object library. Each entry maps a
// MapObject `kind` to the editor-side defaults (size, blocks-movement) plus a
// presentation hint (label + fill) so the library palette can show a small
// preview tile that matches the in-game placeholder render.
//
// Stays in lockstep with `static/render.js:MAP_OBJECT_STYLE` and the
// catalogue table in `docs/maps.md`. When the Godot client gets a new
// asset, add the kind here AND in render.js so editor + browser game see
// the same list.

export const KIND_CATALOGUE = [
  // --- Workstation cluster -----------------------------------------------
  {
    kind: "desk",
    label: "Desk",
    category: "Workstation",
    width: 110,
    height: 60,
    blocksMovement: true,
    fill: "#7c5a3a",
  },
  {
    kind: "desk_large",
    label: "Desk (groß)",
    category: "Workstation",
    width: 180,
    height: 80,
    blocksMovement: true,
    fill: "#7c5a3a",
  },
  {
    kind: "desk_decorated",
    label: "Desk (decorated)",
    category: "Workstation",
    width: 110,
    height: 60,
    blocksMovement: true,
    fill: "#7c5a3a",
  },
  {
    kind: "chair_desk",
    label: "Chair (desk)",
    category: "Workstation",
    width: 50,
    height: 50,
    blocksMovement: false,
    fill: "#3f3128",
  },
  {
    kind: "monitor",
    label: "Monitor",
    category: "Workstation",
    width: 60,
    height: 30,
    blocksMovement: false,
    fill: "#1f2937",
  },
  {
    kind: "keyboard",
    label: "Keyboard",
    category: "Workstation",
    width: 50,
    height: 20,
    blocksMovement: false,
    fill: "#1f2937",
  },
  {
    kind: "mug",
    label: "Mug",
    category: "Workstation",
    width: 20,
    height: 20,
    blocksMovement: false,
    fill: "#a16207",
  },
  {
    kind: "lamp_desk",
    label: "Desk lamp",
    category: "Workstation",
    width: 30,
    height: 30,
    blocksMovement: false,
    fill: "#fbbf24",
  },

  // --- Server room --------------------------------------------------------
  {
    kind: "server_rack",
    label: "Server rack",
    category: "Server",
    width: 80,
    height: 100,
    blocksMovement: true,
    fill: "#1e293b",
  },
  {
    kind: "monitoring_panel",
    label: "Monitoring panel",
    category: "Server",
    width: 200,
    height: 60,
    blocksMovement: false,
    fill: "#0ea5e9",
  },
  {
    kind: "cabinet",
    label: "Cabinet",
    category: "Server",
    width: 80,
    height: 80,
    blocksMovement: true,
    fill: "#3f3f46",
  },

  // --- Meeting / War Room -------------------------------------------------
  {
    kind: "meeting_table",
    label: "Meeting table",
    category: "Meeting",
    width: 480,
    height: 140,
    blocksMovement: true,
    fill: "#52525b",
  },
  {
    kind: "presentation_screen",
    label: "Presentation screen",
    category: "Meeting",
    width: 200,
    height: 30,
    blocksMovement: false,
    fill: "#1e1b4b",
  },
  {
    kind: "chair_meeting",
    label: "Chair (meeting)",
    category: "Meeting",
    width: 50,
    height: 50,
    blocksMovement: false,
    fill: "#3f3128",
  },

  // --- Kitchen ------------------------------------------------------------
  {
    kind: "kitchen_counter",
    label: "Kitchen counter",
    category: "Kitchen",
    width: 320,
    height: 80,
    blocksMovement: true,
    fill: "#9ca3af",
  },
  {
    kind: "kitchen_corner",
    label: "Kitchen corner",
    category: "Kitchen",
    width: 120,
    height: 120,
    blocksMovement: true,
    fill: "#9ca3af",
  },
  {
    kind: "kitchen_sink",
    label: "Kitchen sink",
    category: "Kitchen",
    width: 120,
    height: 80,
    blocksMovement: true,
    fill: "#94a3b8",
  },
  {
    kind: "coffee_machine",
    label: "Coffee machine",
    category: "Kitchen",
    width: 90,
    height: 90,
    blocksMovement: false,
    fill: "#854d0e",
  },
  {
    kind: "fridge",
    label: "Fridge",
    category: "Kitchen",
    width: 100,
    height: 130,
    blocksMovement: true,
    fill: "#cbd5e1",
  },
  {
    kind: "chair_stool",
    label: "Stool",
    category: "Kitchen",
    width: 50,
    height: 50,
    blocksMovement: false,
    fill: "#3f3128",
  },

  // --- Decor --------------------------------------------------------------
  {
    kind: "plant_cactus",
    label: "Plant (cactus)",
    category: "Decor",
    width: 60,
    height: 60,
    blocksMovement: false,
    fill: "#15803d",
  },
  {
    kind: "picture_frame",
    label: "Picture frame",
    category: "Decor",
    width: 80,
    height: 30,
    blocksMovement: false,
    fill: "#a78bfa",
  },
  {
    kind: "rug",
    label: "Rug",
    category: "Decor",
    width: 200,
    height: 120,
    blocksMovement: false,
    fill: "#7e22ce",
  },

  // --- Legacy basement ----------------------------------------------------
  {
    kind: "crate",
    label: "Crate",
    category: "Legacy",
    width: 70,
    height: 70,
    blocksMovement: true,
    fill: "#78350f",
  },
  {
    kind: "old_workstation",
    label: "Old workstation",
    category: "Legacy",
    width: 110,
    height: 60,
    blocksMovement: true,
    fill: "#44403c",
  },
];

export const KIND_BY_NAME = new Map(KIND_CATALOGUE.map((k) => [k.kind, k]));

export const KIND_CATEGORIES = (() => {
  const out = [];
  const seen = new Set();
  for (const entry of KIND_CATALOGUE) {
    if (seen.has(entry.category)) continue;
    seen.add(entry.category);
    out.push(entry.category);
  }
  return out;
})();
