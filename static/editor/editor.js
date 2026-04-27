// MCM Map-Editor — main module.
//
// Wires up:
//   - the in-memory map model (editor-state.js)
//   - the per-tool pointer logic (editor-tools.js)
//   - canvas rendering (zoom-to-fit) and props sidebar
//   - file I/O (new / load JSON / download JSON)
//
// This page is fully standalone — it must NOT import any game modules.

import {
  blankMap,
  deserializeMap,
  serializeMap,
  validateMap,
} from "/static/editor/editor-state.js";
import { History } from "/static/editor/editor-history.js";
import {
  KIND_BY_NAME,
  KIND_CATALOGUE,
  KIND_CATEGORIES,
  initKindsCatalogue,
} from "/static/editor/editor-kinds.js";
import { snap, TOOLS } from "/static/editor/editor-tools.js";
// 3D-Preview is loaded lazily so a CDN-blocked dev environment still gets
// a working 2D editor. Errors are shown in the preview status bar.
let MapPreview3D = null;

// Layers the user can hide. Each key matches a draw-call below; toggling
// hides the layer in the canvas without removing the data from the model.
const DEFAULT_LAYERS = {
  rooms: true,
  walls: true,
  doors: true,
  objects: true,
  spawns: true,
  tasks: true,
  panels: true,
  vents: true,
};

const LAYER_LABELS = {
  rooms: "Räume",
  walls: "Wände",
  doors: "Türen",
  objects: "Objekte",
  spawns: "Spawns",
  tasks: "Tasks",
  panels: "Sabotage",
  vents: "Vents",
};

const state = {
  map: blankMap(),
  tool: "select",
  toolInstance: null,
  selection: null, // { kind, index } or null
  pendingKind: null, // active kind from the library palette (used by ObjectTool)
  dirty: false,
  shiftHeld: false,
  view: { scale: 1, offsetX: 0, offsetY: 0 },
  layers: { ...DEFAULT_LAYERS },
};

const history = new History();

const dom = {
  canvas: document.getElementById("editor-canvas"),
  topbar: document.getElementById("editor-topbar"),
  mapName: document.getElementById("map-name"),
  mapWidth: document.getElementById("map-width"),
  mapHeight: document.getElementById("map-height"),
  warRoomSelect: document.getElementById("war-room-select"),
  btnNew: document.getElementById("btn-new"),
  btnLoad: document.getElementById("btn-load"),
  btnDownload: document.getElementById("btn-download"),
  btnLoadServer: document.getElementById("btn-load-server"),
  btnSaveServer: document.getElementById("btn-save-server"),
  fileInput: document.getElementById("file-input"),
  dirtyFlag: document.getElementById("dirty-flag"),
  statusFlash: document.getElementById("status-flash"),
  cursorCoords: document.getElementById("cursor-coords"),
  propsEmpty: document.getElementById("props-empty"),
  propsContent: document.getElementById("props-content"),
  kindLibrary: document.getElementById("kind-library"),
  kindPending: document.getElementById("kind-library-pending"),
  kindPendingName: document.getElementById("kind-library-pending-name"),
  kindClear: document.getElementById("kind-library-clear"),
  btnUndo: document.getElementById("btn-undo"),
  btnRedo: document.getElementById("btn-redo"),
  layerToggles: document.getElementById("layer-toggles"),
  validationStrip: document.getElementById("validation-strip"),
  editorMain: document.getElementById("editor-main"),
  preview3DHost: document.getElementById("preview-3d-host"),
  previewStats: document.getElementById("preview-stats"),
  toggle3DPreview: document.getElementById("toggle-3d-preview"),
  serverLoadModal: document.getElementById("server-load-modal"),
  serverLoadList: document.getElementById("server-load-list"),
  serverLoadClose: document.getElementById("server-load-close"),
};

const ctx2d = dom.canvas.getContext("2d");

// --- Tool context exposed to per-tool classes ------------------------------

const toolContext = {
  get map() {
    return state.map;
  },
  get pendingKind() {
    return state.pendingKind;
  },
  setSelection(sel) {
    state.selection = sel;
    renderPropsSidebar();
    requestRender();
  },
  markDirty() {
    state.dirty = true;
    dom.dirtyFlag.classList.remove("hidden");
    refreshValidationStrip();
    requestRender();
  },
  pushUndo() {
    history.push(state.map);
    refreshUndoButtons();
  },
  refreshWarRoomChoices() {
    refreshWarRoomChoices();
  },
  refreshPropsSidebar() {
    renderPropsSidebar();
  },
  requestRender,
};

// --- Tool selection --------------------------------------------------------

function setTool(name) {
  state.tool = name;
  const ToolClass = TOOLS[name] || TOOLS.select;
  state.toolInstance = new ToolClass();
  // Switching tools clears any in-progress drag, but not the current selection.
  if (name !== "object") {
    // Pending kind is only meaningful for the Object tool — clear it so the
    // library highlight goes away when the user picks a different tool.
    state.pendingKind = null;
    renderKindPending();
  }
  updateCanvasCursor();
  requestRender();
}

function updateCanvasCursor() {
  if (state.tool === "select") dom.canvas.style.cursor = "default";
  else if (state.tool === "object" && !state.pendingKind) dom.canvas.style.cursor = "not-allowed";
  else dom.canvas.style.cursor = "crosshair";
}

document.querySelectorAll('input[name="tool"]').forEach((input) => {
  input.addEventListener("change", (e) => {
    if (e.target.checked) setTool(e.target.value);
  });
});

// --- Canvas: viewport (zoom-to-fit) ---------------------------------------

function fitCanvas() {
  const parent = dom.canvas.parentElement;
  const w = parent.clientWidth;
  const h = parent.clientHeight - 28; // leave room for status bar
  dom.canvas.width = w;
  dom.canvas.height = h;
  computeFitView();
  requestRender();
}

function computeFitView() {
  const cw = dom.canvas.width;
  const ch = dom.canvas.height;
  const mw = state.map.size.width;
  const mh = state.map.size.height;
  const margin = 40;
  const sx = (cw - margin * 2) / mw;
  const sy = (ch - margin * 2) / mh;
  const scale = Math.max(0.05, Math.min(sx, sy));
  state.view.scale = scale;
  state.view.offsetX = (cw - mw * scale) / 2;
  state.view.offsetY = (ch - mh * scale) / 2;
}

function screenToMap(sx, sy) {
  return {
    x: (sx - state.view.offsetX) / state.view.scale,
    y: (sy - state.view.offsetY) / state.view.scale,
  };
}

window.addEventListener("resize", fitCanvas);

// --- Pan / Zoom on the 2D canvas ------------------------------------------
//
// The shared layout (220px / 1fr / 480px) makes the 2D pane narrower than
// before, so a fit-to-view defaults to a tiny map. Wheel-zoom around the
// cursor + middle-mouse-drag pan + a "fit" hotkey give designers room to
// breathe without resizing the panes.

const VIEW_MIN_SCALE = 0.05;
const VIEW_MAX_SCALE = 5;

dom.canvas.addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    const rect = dom.canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const mapPt = screenToMap(cx, cy);
    const next = Math.max(VIEW_MIN_SCALE, Math.min(VIEW_MAX_SCALE, state.view.scale * factor));
    state.view.scale = next;
    // Re-anchor: the same map point should stay under the cursor.
    state.view.offsetX = cx - mapPt.x * next;
    state.view.offsetY = cy - mapPt.y * next;
    requestRender();
  },
  { passive: false }
);

let panState = null;

dom.canvas.addEventListener(
  "mousedown",
  (e) => {
    // Middle-mouse-button OR Space+left starts panning. Capture-phase so we
    // can stopPropagation before per-tool handlers see the event.
    const isPan = e.button === 1 || (e.button === 0 && e.shiftKey === false && state._spaceHeld);
    if (!isPan) return;
    e.preventDefault();
    e.stopPropagation();
    panState = {
      startX: e.clientX,
      startY: e.clientY,
      baseOffsetX: state.view.offsetX,
      baseOffsetY: state.view.offsetY,
    };
    dom.canvas.style.cursor = "grabbing";
  },
  true
);

window.addEventListener("mousemove", (e) => {
  if (!panState) return;
  state.view.offsetX = panState.baseOffsetX + (e.clientX - panState.startX);
  state.view.offsetY = panState.baseOffsetY + (e.clientY - panState.startY);
  requestRender();
});

window.addEventListener("mouseup", () => {
  if (!panState) return;
  panState = null;
  updateCanvasCursor();
});

// Space-bar acts as a temporary pan modifier. Track in state so the
// middle-button check above can use it without re-reading the keyboard.
window.addEventListener("keydown", (e) => {
  if (e.code === "Space" && !state._spaceHeld) {
    state._spaceHeld = true;
    if (!panState) dom.canvas.style.cursor = "grab";
  }
  // Strg+0 / Cmd+0 = fit-to-view reset.
  if ((e.ctrlKey || e.metaKey) && e.code === "Digit0") {
    e.preventDefault();
    computeFitView();
    requestRender();
  }
});

window.addEventListener("keyup", (e) => {
  if (e.code === "Space") {
    state._spaceHeld = false;
    if (!panState) updateCanvasCursor();
  }
});

// --- Rendering -------------------------------------------------------------

let renderQueued = false;
function requestRender() {
  if (renderQueued) return;
  renderQueued = true;
  requestAnimationFrame(() => {
    renderQueued = false;
    render();
    // 3D preview live-syncs off the same RAF tick. Cheap rebuild; with
    // <500 nodes the cost stays well below 16 ms.
    syncPreview3D();
  });
}

// --- 3D-Preview-Pane -------------------------------------------------------

let preview3D = null;
let preview3DLoadFailed = false;

async function ensurePreview3D() {
  if (preview3D || preview3DLoadFailed) return preview3D;
  if (!dom.preview3DHost) return null;
  try {
    if (!MapPreview3D) {
      const mod = await import("/static/editor/editor-preview-3d.js");
      MapPreview3D = mod.MapPreview3D;
    }
    preview3D = new MapPreview3D(dom.preview3DHost);
    return preview3D;
  } catch (err) {
    preview3DLoadFailed = true;
    if (dom.previewStats) {
      dom.previewStats.textContent = `3D-Vorschau nicht verfügbar (${err.message ?? err})`;
    }
    return null;
  }
}

function syncPreview3D() {
  if (!preview3D) return;
  const result = preview3D.applyMap(state.map);
  if (dom.previewStats && result?.stats) {
    const s = result.stats;
    dom.previewStats.textContent =
      `${s.rooms} Räume · ${s.doors} Türen · ${s.walls} Wände · ` +
      `${s.mapObjects} Objekte (${s.meshLoaded} Mesh / ${s.meshFallback} Fallback) · ` +
      `${s.taskAnchors} Tasks`;
  }
}

function setPreview3DEnabled(on) {
  if (!dom.editorMain) return;
  dom.editorMain.classList.toggle("preview-off", !on);
  if (on) {
    ensurePreview3D().then((preview) => {
      if (preview) syncPreview3D();
    });
  }
}

dom.toggle3DPreview?.addEventListener("change", (e) => {
  setPreview3DEnabled(e.target.checked);
});

function render() {
  const cw = dom.canvas.width;
  const ch = dom.canvas.height;
  ctx2d.fillStyle = "#14161a";
  ctx2d.fillRect(0, 0, cw, ch);

  ctx2d.save();
  ctx2d.translate(state.view.offsetX, state.view.offsetY);
  ctx2d.scale(state.view.scale, state.view.scale);

  // Map background bounds.
  ctx2d.fillStyle = "#1d2026";
  ctx2d.fillRect(0, 0, state.map.size.width, state.map.size.height);

  // Grid (every 100 map units; lighter every 50).
  drawGrid();

  // Rooms.
  if (state.layers.rooms) {
    for (const r of state.map.rooms) {
      ctx2d.fillStyle = r.color || "#3a4560";
      ctx2d.fillRect(r.x, r.y, r.width, r.height);
      ctx2d.strokeStyle = "rgba(255, 255, 255, 0.15)";
      ctx2d.lineWidth = 1 / state.view.scale;
      ctx2d.strokeRect(r.x, r.y, r.width, r.height);
      // Label.
      ctx2d.fillStyle = "#ffffff";
      ctx2d.font = `${Math.max(14, 18 / state.view.scale)}px system-ui`;
      ctx2d.fillText(r.title || r.id, r.x + 8, r.y + 22 / state.view.scale);
    }
  }

  // Walls (Slice-3): auto-derived from room edges minus doors.
  // Editor mirrors what the server computes so the user sees the live
  // result of moving rooms or adding/removing doors.
  if (state.layers.walls) drawAutoWalls();
  if (state.layers.doors) drawDoors();

  // Spawn points.
  if (state.layers.spawns)
    for (let i = 0; i < state.map.spawnPoints.length; i++) {
      const s = state.map.spawnPoints[i];
      ctx2d.fillStyle = "#3aa850";
      ctx2d.beginPath();
      ctx2d.arc(s.x, s.y, 14, 0, Math.PI * 2);
      ctx2d.fill();
      ctx2d.strokeStyle = "#1f5028";
      ctx2d.lineWidth = 2 / state.view.scale;
      ctx2d.stroke();
    }

  // Task anchors (orange diamonds).
  if (state.layers.tasks)
    for (let i = 0; i < state.map.taskAnchors.length; i++) {
      const t = state.map.taskAnchors[i];
      ctx2d.fillStyle = "#e0902a";
      ctx2d.beginPath();
      ctx2d.moveTo(t.x, t.y - 18);
      ctx2d.lineTo(t.x + 18, t.y);
      ctx2d.lineTo(t.x, t.y + 18);
      ctx2d.lineTo(t.x - 18, t.y);
      ctx2d.closePath();
      ctx2d.fill();
      ctx2d.strokeStyle = "#7a4f15";
      ctx2d.lineWidth = 2 / state.view.scale;
      ctx2d.stroke();
      ctx2d.fillStyle = "#ffffff";
      ctx2d.font = `${Math.max(11, 14 / state.view.scale)}px monospace`;
      ctx2d.fillText(t.taskId, t.x + 22, t.y + 4);
    }

  // Map objects (Tier 4 props — drawn as bounding-box rectangles with kind
  // label so the editor matches the in-game placeholder render).
  if (state.layers.objects && Array.isArray(state.map.mapObjects)) {
    for (let i = 0; i < state.map.mapObjects.length; i++) {
      const o = state.map.mapObjects[i];
      const dw = o.rotation === 90 || o.rotation === 270 ? o.height : o.width;
      const dh = o.rotation === 90 || o.rotation === 270 ? o.width : o.height;
      ctx2d.fillStyle = o.blocksMovement === false ? "rgba(120, 130, 160, 0.4)" : "#5b6478";
      ctx2d.fillRect(o.x - dw / 2, o.y - dh / 2, dw, dh);
      ctx2d.strokeStyle = "#0a0a0a";
      ctx2d.lineWidth = 1 / state.view.scale;
      ctx2d.strokeRect(o.x - dw / 2, o.y - dh / 2, dw, dh);
      ctx2d.fillStyle = "#ffffff";
      ctx2d.font = `${Math.max(10, 12 / state.view.scale)}px monospace`;
      ctx2d.textAlign = "center";
      ctx2d.textBaseline = "middle";
      ctx2d.fillText(o.kind || "?", o.x, o.y);
      ctx2d.textAlign = "left";
      ctx2d.textBaseline = "alphabetic";
    }
  }

  // Sabotage panels (Tier 2.4 — repair points). Read-only marker for now;
  // no edit tool yet, but at least visible so the data isn't invisible
  // when authoring a map.
  if (state.layers.panels && Array.isArray(state.map.sabotagePanels)) {
    for (const p of state.map.sabotagePanels) {
      ctx2d.save();
      ctx2d.fillStyle = "#dc2626";
      ctx2d.beginPath();
      ctx2d.arc(p.x, p.y, 14, 0, Math.PI * 2);
      ctx2d.fill();
      ctx2d.strokeStyle = "#7f1d1d";
      ctx2d.lineWidth = 2 / state.view.scale;
      ctx2d.stroke();
      ctx2d.fillStyle = "#fef2f2";
      ctx2d.font = `${Math.max(9, 11 / state.view.scale)}px monospace`;
      ctx2d.textAlign = "left";
      ctx2d.textBaseline = "middle";
      ctx2d.fillText("PANEL " + p.sabotageId, p.x + 18, p.y);
      ctx2d.restore();
    }
  }

  // Vents (Tier 2.3 — chaos teleport). Read-only diamond marker plus
  // dotted lines to connected destinations, so the network is visible.
  if (state.layers.vents && Array.isArray(state.map.vents)) {
    const ventById = new Map(state.map.vents.map((v) => [v.id, v]));
    // Draw connection lines first so the diamonds sit on top.
    ctx2d.save();
    ctx2d.strokeStyle = "rgba(96, 165, 250, 0.45)";
    ctx2d.lineWidth = 2 / state.view.scale;
    ctx2d.setLineDash([10 / state.view.scale, 6 / state.view.scale]);
    for (const v of state.map.vents) {
      for (const targetId of v.connectedTo || []) {
        const target = ventById.get(targetId);
        if (!target) continue;
        // Draw each edge once (compare ids lexicographically so we don't
        // double-draw the symmetric pair).
        if (v.id >= targetId) continue;
        ctx2d.beginPath();
        ctx2d.moveTo(v.x, v.y);
        ctx2d.lineTo(target.x, target.y);
        ctx2d.stroke();
      }
    }
    ctx2d.setLineDash([]);
    ctx2d.restore();
    for (const v of state.map.vents) {
      ctx2d.save();
      ctx2d.fillStyle = "#94a3b8";
      ctx2d.beginPath();
      ctx2d.moveTo(v.x, v.y - 16);
      ctx2d.lineTo(v.x + 16, v.y);
      ctx2d.lineTo(v.x, v.y + 16);
      ctx2d.lineTo(v.x - 16, v.y);
      ctx2d.closePath();
      ctx2d.fill();
      ctx2d.strokeStyle = "#475569";
      ctx2d.lineWidth = 2 / state.view.scale;
      ctx2d.stroke();
      ctx2d.fillStyle = "#0b0f1f";
      ctx2d.font = `${Math.max(9, 11 / state.view.scale)}px monospace`;
      ctx2d.textAlign = "center";
      ctx2d.textBaseline = "middle";
      ctx2d.fillText("V", v.x, v.y);
      ctx2d.fillStyle = "#cbd5e1";
      ctx2d.textAlign = "left";
      ctx2d.fillText(v.id, v.x + 22, v.y);
      ctx2d.restore();
    }
  }

  // Selection highlight.
  drawSelectionHighlight();

  // Tool preview (e.g. drag rectangle).
  if (state.toolInstance && state.toolInstance.drawPreview) {
    state.toolInstance.drawPreview(ctx2d, toolContext);
  }

  ctx2d.restore();

  // Coordinate axes overlay (top-left corner of map).
  drawAxesLabel();
}

function drawGrid() {
  const w = state.map.size.width;
  const h = state.map.size.height;
  ctx2d.strokeStyle = "rgba(255, 255, 255, 0.04)";
  ctx2d.lineWidth = 1 / state.view.scale;
  for (let x = 0; x <= w; x += 100) {
    ctx2d.beginPath();
    ctx2d.moveTo(x, 0);
    ctx2d.lineTo(x, h);
    ctx2d.stroke();
  }
  for (let y = 0; y <= h; y += 100) {
    ctx2d.beginPath();
    ctx2d.moveTo(0, y);
    ctx2d.lineTo(w, y);
    ctx2d.stroke();
  }
}

// Slice-3: walls auto-derived from room edges (no more wallLines).
// Mirrors render.js:computeWallsClient — keep in sync with the server's
// app/game/game_map.compute_walls.

function _intervalSubtract(start, end, cutouts) {
  if (start >= end) return [];
  if (!cutouts.length) return [[start, end]];
  const clipped = cutouts
    .map(([a, b]) => [Math.max(a, start), Math.min(b, end)])
    .filter(([a, b]) => a < b)
    .sort((p, q) => p[0] - q[0]);
  const out = [];
  let cursor = start;
  for (const [a, b] of clipped) {
    if (a > cursor) out.push([cursor, a]);
    cursor = Math.max(cursor, b);
  }
  if (cursor < end) out.push([cursor, end]);
  return out;
}

function _edgeOverlap(other, axis, edgePos, start, end) {
  if (axis === "x") {
    if (other.x !== edgePos && other.x + other.width !== edgePos) return null;
    const a = Math.max(start, other.y);
    const b = Math.min(end, other.y + other.height);
    return a < b ? [a, b] : null;
  }
  if (other.y !== edgePos && other.y + other.height !== edgePos) return null;
  const a = Math.max(start, other.x);
  const b = Math.min(end, other.x + other.width);
  return a < b ? [a, b] : null;
}

function drawAutoWalls() {
  const rooms = state.map.rooms || [];
  const doors = state.map.doors || [];
  const mapW = state.map.size.width;
  const mapH = state.map.size.height;
  const isMapEdge = (axis, edgePos) =>
    axis === "x" ? edgePos === 0 || edgePos === mapW : edgePos === 0 || edgePos === mapH;
  const processed = new Set();
  ctx2d.fillStyle = "#0a0a0a";
  for (const room of rooms) {
    const edges = [
      ["y", room.y, room.x, room.x + room.width],
      ["y", room.y + room.height, room.x, room.x + room.width],
      ["x", room.x, room.y, room.y + room.height],
      ["x", room.x + room.width, room.y, room.y + room.height],
    ];
    for (const [axis, edgePos, start, end] of edges) {
      const sharedList = [];
      for (const other of rooms) {
        if (other.id === room.id) continue;
        const ovl = _edgeOverlap(other, axis, edgePos, start, end);
        if (ovl) sharedList.push([other.id, ovl]);
      }
      for (const [otherId, ovl] of sharedList) {
        const pairKey = [room.id, otherId].sort();
        const key = `${axis}|${edgePos}|${pairKey[0]}|${pairKey[1]}|${ovl[0]}|${ovl[1]}`;
        if (processed.has(key)) continue;
        processed.add(key);
        const cutouts = [];
        for (const door of doors) {
          const dPair = [door.betweenRoomA, door.betweenRoomB].sort();
          if (dPair[0] !== pairKey[0] || dPair[1] !== pairKey[1]) continue;
          if (door.position < ovl[0] || door.position > ovl[1]) continue;
          const half = Math.floor((door.width || 240) / 2);
          cutouts.push([door.position - half, door.position + half]);
        }
        for (const [a, b] of _intervalSubtract(ovl[0], ovl[1], cutouts)) {
          if (axis === "x") ctx2d.fillRect(edgePos - 8, a, 16, b - a);
          else ctx2d.fillRect(a, edgePos - 8, b - a, 16);
        }
      }
      if (!isMapEdge(axis, edgePos)) {
        const sharedCuts = sharedList.map(([, ovl]) => ovl);
        for (const [a, b] of _intervalSubtract(start, end, sharedCuts)) {
          if (axis === "x") ctx2d.fillRect(edgePos - 8, a, 16, b - a);
          else ctx2d.fillRect(a, edgePos - 8, b - a, 16);
        }
      }
    }
  }
}

function drawDoors() {
  const rooms = state.map.rooms || [];
  const doors = state.map.doors || [];
  const roomById = new Map(rooms.map((r) => [r.id, r]));
  ctx2d.save();
  ctx2d.lineWidth = 2 / state.view.scale;
  for (const d of doors) {
    const a = roomById.get(d.betweenRoomA);
    const b = roomById.get(d.betweenRoomB);
    if (!a || !b) continue;
    // Determine the shared edge between rooms a and b (axis + position).
    const edge = _findSharedEdge(a, b);
    if (!edge) continue;
    const half = Math.floor((d.width || 240) / 2);
    if (edge.axis === "x") {
      // Vertical edge — door is a horizontal gap on x=edge.position.
      ctx2d.fillStyle = "#facc15";
      ctx2d.fillRect(edge.position - 8, d.position - half, 16, half * 2);
      ctx2d.strokeStyle = "#a16207";
      ctx2d.strokeRect(edge.position - 8, d.position - half, 16, half * 2);
      ctx2d.fillStyle = "#1a1a1a";
      ctx2d.font = `${Math.max(9, 11 / state.view.scale)}px monospace`;
      ctx2d.textAlign = "left";
      ctx2d.textBaseline = "middle";
      ctx2d.fillText(d.id, edge.position + 14, d.position);
    } else {
      ctx2d.fillStyle = "#facc15";
      ctx2d.fillRect(d.position - half, edge.position - 8, half * 2, 16);
      ctx2d.strokeStyle = "#a16207";
      ctx2d.strokeRect(d.position - half, edge.position - 8, half * 2, 16);
      ctx2d.fillStyle = "#1a1a1a";
      ctx2d.font = `${Math.max(9, 11 / state.view.scale)}px monospace`;
      ctx2d.textAlign = "center";
      ctx2d.textBaseline = "top";
      ctx2d.fillText(d.id, d.position, edge.position + 12);
    }
  }
  ctx2d.restore();
}

function _findSharedEdge(a, b) {
  // Vertical shared edge: a.right == b.left or a.left == b.right.
  if (a.x + a.width === b.x) return { axis: "x", position: b.x };
  if (b.x + b.width === a.x) return { axis: "x", position: a.x };
  // Horizontal shared edge.
  if (a.y + a.height === b.y) return { axis: "y", position: b.y };
  if (b.y + b.height === a.y) return { axis: "y", position: a.y };
  return null;
}

function drawSelectionHighlight() {
  const sel = state.selection;
  if (!sel) return;
  ctx2d.save();
  ctx2d.strokeStyle = "#ffd166";
  ctx2d.lineWidth = 3 / state.view.scale;
  ctx2d.setLineDash([8 / state.view.scale, 6 / state.view.scale]);
  if (sel.kind === "room") {
    const r = state.map.rooms[sel.index];
    if (r) ctx2d.strokeRect(r.x - 2, r.y - 2, r.width + 4, r.height + 4);
  } else if (sel.kind === "spawn") {
    const s = state.map.spawnPoints[sel.index];
    if (s) {
      ctx2d.beginPath();
      ctx2d.arc(s.x, s.y, 22, 0, Math.PI * 2);
      ctx2d.stroke();
    }
  } else if (sel.kind === "task") {
    const t = state.map.taskAnchors[sel.index];
    if (t) {
      ctx2d.strokeRect(t.x - 24, t.y - 24, 48, 48);
    }
  } else if (sel.kind === "object") {
    const o = state.map.mapObjects?.[sel.index];
    if (o) {
      const dw = o.rotation === 90 || o.rotation === 270 ? o.height : o.width;
      const dh = o.rotation === 90 || o.rotation === 270 ? o.width : o.height;
      ctx2d.strokeRect(o.x - dw / 2 - 4, o.y - dh / 2 - 4, dw + 8, dh + 8);
    }
  } else if (sel.kind === "door") {
    const d = state.map.doors?.[sel.index];
    if (d) {
      const a = state.map.rooms.find((r) => r.id === d.betweenRoomA);
      const b = state.map.rooms.find((r) => r.id === d.betweenRoomB);
      if (a && b) {
        const edge = _findSharedEdge(a, b);
        if (edge) {
          const half = Math.floor((d.width || 240) / 2);
          if (edge.axis === "x") {
            ctx2d.strokeRect(edge.position - 12, d.position - half - 4, 24, half * 2 + 8);
          } else {
            ctx2d.strokeRect(d.position - half - 4, edge.position - 12, half * 2 + 8, 24);
          }
        }
      }
    }
  }
  ctx2d.restore();
}

function drawAxesLabel() {
  ctx2d.save();
  ctx2d.fillStyle = "rgba(255, 255, 255, 0.4)";
  ctx2d.font = "11px monospace";
  ctx2d.fillText("(0,0)", state.view.offsetX + 4, state.view.offsetY + 12);
  const xMaxScreen = state.view.offsetX + state.map.size.width * state.view.scale;
  const yMaxScreen = state.view.offsetY + state.map.size.height * state.view.scale;
  ctx2d.fillText(
    `(${state.map.size.width},${state.map.size.height})`,
    xMaxScreen - 80,
    yMaxScreen + 14
  );
  ctx2d.restore();
}

// --- Pointer events --------------------------------------------------------

function pointerCoords(evt) {
  const rect = dom.canvas.getBoundingClientRect();
  const sx = evt.clientX - rect.left;
  const sy = evt.clientY - rect.top;
  const m = screenToMap(sx, sy);
  const snapEnabled = !state.shiftHeld;
  return { x: snap(m.x, snapEnabled), y: snap(m.y, snapEnabled), rawX: m.x, rawY: m.y };
}

dom.canvas.addEventListener("mousedown", (e) => {
  if (e.button !== 0) return;
  const p = pointerCoords(e);
  // Snapshot for undo BEFORE the tool runs. Even pure clicks that just change
  // selection are cheap to record and the History dedups identical snapshots.
  toolContext.pushUndo();
  if (state.toolInstance && state.toolInstance.onDown) {
    state.toolInstance.onDown(toolContext, p.x, p.y);
  }
  requestRender();
});

dom.canvas.addEventListener("mousemove", (e) => {
  const p = pointerCoords(e);
  dom.cursorCoords.textContent = `${p.x}, ${p.y}`;
  if (state.toolInstance && state.toolInstance.onMove) {
    state.toolInstance.onMove(toolContext, p.x, p.y);
  }
});

dom.canvas.addEventListener("mouseup", (e) => {
  if (e.button !== 0) return;
  const p = pointerCoords(e);
  if (state.toolInstance && state.toolInstance.onUp) {
    state.toolInstance.onUp(toolContext, p.x, p.y);
  }
  requestRender();
});

window.addEventListener("keydown", (e) => {
  if (e.key === "Shift") state.shiftHeld = true;
  // Most shortcuts must NOT fire while a form field is focused — typing
  // "z" in the map-name input would trigger undo otherwise.
  const inField =
    document.activeElement &&
    (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "SELECT");
  if (e.key === "Delete" || e.key === "Backspace") {
    if (inField) return;
    deleteSelection();
    return;
  }
  if ((e.ctrlKey || e.metaKey) && !e.shiftKey && (e.key === "z" || e.key === "Z")) {
    if (inField) return;
    e.preventDefault();
    performUndo();
    return;
  }
  if ((e.ctrlKey || e.metaKey) && (e.key === "y" || e.key === "Y")) {
    if (inField) return;
    e.preventDefault();
    performRedo();
    return;
  }
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "z" || e.key === "Z")) {
    if (inField) return;
    e.preventDefault();
    performRedo();
    return;
  }
  if ((e.ctrlKey || e.metaKey) && (e.key === "s" || e.key === "S")) {
    e.preventDefault(); // even when in field — save is a global shortcut
    triggerDownload();
    return;
  }
});
window.addEventListener("keyup", (e) => {
  if (e.key === "Shift") state.shiftHeld = false;
});

function deleteSelection() {
  const sel = state.selection;
  if (!sel) return;
  toolContext.pushUndo();
  if (sel.kind === "room") {
    const removed = state.map.rooms.splice(sel.index, 1)[0];
    if (removed && state.map.warRoomId === removed.id) state.map.warRoomId = "";
    // Drop any doors that referenced the removed room — they have nowhere
    // to live anymore. Slice-4 will offer a UI to keep them attached when
    // the user drags an adjacent edge instead.
    if (removed) {
      state.map.doors = (state.map.doors || []).filter(
        (d) => d.betweenRoomA !== removed.id && d.betweenRoomB !== removed.id
      );
    }
  } else if (sel.kind === "spawn") {
    state.map.spawnPoints.splice(sel.index, 1);
  } else if (sel.kind === "task") {
    state.map.taskAnchors.splice(sel.index, 1);
  } else if (sel.kind === "object") {
    state.map.mapObjects.splice(sel.index, 1);
  } else if (sel.kind === "door") {
    state.map.doors.splice(sel.index, 1);
  }
  state.selection = null;
  toolContext.markDirty();
  refreshWarRoomChoices();
  renderPropsSidebar();
  syncTopbarFields();
}

// --- Topbar / props sidebar -------------------------------------------------

function syncTopbarFields() {
  dom.mapName.value = state.map.name;
  dom.mapWidth.value = state.map.size.width;
  dom.mapHeight.value = state.map.size.height;
  refreshWarRoomChoices();
}

function refreshWarRoomChoices() {
  const select = dom.warRoomSelect;
  const current = state.map.warRoomId;
  select.innerHTML = "";
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "(keiner)";
  select.appendChild(blank);
  for (const r of state.map.rooms) {
    const opt = document.createElement("option");
    opt.value = r.id;
    opt.textContent = r.title ? `${r.id} (${r.title})` : r.id;
    select.appendChild(opt);
  }
  select.value = current;
}

dom.mapName.addEventListener("input", () => {
  state.map.name = dom.mapName.value;
  toolContext.markDirty();
});
dom.mapWidth.addEventListener("change", () => {
  const v = parseInt(dom.mapWidth.value, 10);
  if (Number.isFinite(v) && v > 0) {
    state.map.size.width = v;
    toolContext.markDirty();
    computeFitView();
    requestRender();
  }
});
dom.mapHeight.addEventListener("change", () => {
  const v = parseInt(dom.mapHeight.value, 10);
  if (Number.isFinite(v) && v > 0) {
    state.map.size.height = v;
    toolContext.markDirty();
    computeFitView();
    requestRender();
  }
});
dom.warRoomSelect.addEventListener("change", () => {
  state.map.warRoomId = dom.warRoomSelect.value;
  toolContext.markDirty();
});

function renderPropsSidebar() {
  const sel = state.selection;
  if (!sel) {
    dom.propsEmpty.classList.remove("hidden");
    dom.propsContent.classList.add("hidden");
    dom.propsContent.innerHTML = "";
    return;
  }
  dom.propsEmpty.classList.add("hidden");
  dom.propsContent.classList.remove("hidden");
  dom.propsContent.innerHTML = "";
  if (sel.kind === "room") return renderRoomProps(sel.index);
  if (sel.kind === "spawn") return renderSpawnProps(sel.index);
  if (sel.kind === "task") return renderTaskProps(sel.index);
  if (sel.kind === "object") return renderObjectProps(sel.index);
  if (sel.kind === "door") return renderDoorProps(sel.index);
}

function makeField(label, value, onChange, type = "text") {
  const wrap = document.createElement("label");
  wrap.textContent = label;
  const input = document.createElement("input");
  input.type = type;
  input.value = value;
  input.addEventListener("input", () => onChange(input.value));
  wrap.appendChild(input);
  return wrap;
}

function renderRoomProps(i) {
  const r = state.map.rooms[i];
  if (!r) return;
  const root = dom.propsContent;
  root.appendChild(
    makeField("ID", r.id, (v) => {
      const old = r.id;
      r.id = v;
      if (state.map.warRoomId === old) state.map.warRoomId = v;
      toolContext.markDirty();
      refreshWarRoomChoices();
      requestRender();
    })
  );
  root.appendChild(
    makeField("Titel", r.title, (v) => {
      r.title = v;
      toolContext.markDirty();
      refreshWarRoomChoices();
      requestRender();
    })
  );
  root.appendChild(
    makeField(
      "x",
      r.x,
      (v) => {
        const n = parseInt(v, 10);
        if (Number.isFinite(n)) {
          r.x = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  root.appendChild(
    makeField(
      "y",
      r.y,
      (v) => {
        const n = parseInt(v, 10);
        if (Number.isFinite(n)) {
          r.y = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  root.appendChild(
    makeField(
      "Breite",
      r.width,
      (v) => {
        const n = parseInt(v, 10);
        if (Number.isFinite(n) && n > 0) {
          r.width = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  root.appendChild(
    makeField(
      "Höhe",
      r.height,
      (v) => {
        const n = parseInt(v, 10);
        if (Number.isFinite(n) && n > 0) {
          r.height = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  root.appendChild(
    makeField(
      "Farbe",
      r.color || "#3a4560",
      (v) => {
        r.color = v;
        toolContext.markDirty();
        requestRender();
      },
      "color"
    )
  );
  appendDeleteButton(root);
}

function renderSpawnProps(i) {
  const s = state.map.spawnPoints[i];
  if (!s) return;
  const root = dom.propsContent;
  root.appendChild(
    makeField(
      "x",
      s.x,
      (v) => {
        const n = parseFloat(v);
        if (Number.isFinite(n)) {
          s.x = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  root.appendChild(
    makeField(
      "y",
      s.y,
      (v) => {
        const n = parseFloat(v);
        if (Number.isFinite(n)) {
          s.y = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  appendDeleteButton(root);
}

function renderTaskProps(i) {
  const t = state.map.taskAnchors[i];
  if (!t) return;
  const root = dom.propsContent;
  root.appendChild(
    makeField("Task-ID", t.taskId, (v) => {
      t.taskId = v;
      toolContext.markDirty();
      requestRender();
    })
  );
  root.appendChild(
    makeField(
      "x",
      t.x,
      (v) => {
        const n = parseFloat(v);
        if (Number.isFinite(n)) {
          t.x = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  root.appendChild(
    makeField(
      "y",
      t.y,
      (v) => {
        const n = parseFloat(v);
        if (Number.isFinite(n)) {
          t.y = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  appendDeleteButton(root);
}

function renderObjectProps(i) {
  const o = state.map.mapObjects?.[i];
  if (!o) return;
  const root = dom.propsContent;
  const numField = (label, key) =>
    root.appendChild(
      makeField(
        label,
        o[key],
        (v) => {
          const n = parseFloat(v);
          if (Number.isFinite(n)) {
            o[key] = n;
            toolContext.markDirty();
            requestRender();
          }
        },
        "number"
      )
    );
  const strField = (label, key) =>
    root.appendChild(
      makeField(label, o[key] || "", (v) => {
        o[key] = v.trim() || null;
        toolContext.markDirty();
        requestRender();
      })
    );
  strField("ID", "id");
  strField("Kind", "kind");
  numField("x (Center)", "x");
  numField("y (Center)", "y");
  numField("width", "width");
  numField("height", "height");
  // Rotation: only 0/90/180/270.
  const rotWrap = document.createElement("label");
  rotWrap.textContent = "Rotation";
  const rotSel = document.createElement("select");
  for (const r of [0, 90, 180, 270]) {
    const opt = document.createElement("option");
    opt.value = String(r);
    opt.textContent = `${r}°`;
    if ((o.rotation || 0) === r) opt.selected = true;
    rotSel.appendChild(opt);
  }
  rotSel.addEventListener("change", () => {
    o.rotation = parseInt(rotSel.value, 10) || 0;
    toolContext.markDirty();
    requestRender();
  });
  rotWrap.appendChild(rotSel);
  root.appendChild(rotWrap);
  // blocksMovement checkbox.
  const blkWrap = document.createElement("label");
  const blkInput = document.createElement("input");
  blkInput.type = "checkbox";
  blkInput.checked = o.blocksMovement !== false;
  blkInput.addEventListener("change", () => {
    o.blocksMovement = blkInput.checked;
    toolContext.markDirty();
    requestRender();
  });
  blkWrap.appendChild(blkInput);
  blkWrap.appendChild(document.createTextNode(" blockt Bewegung"));
  root.appendChild(blkWrap);
  // Optional bindings.
  strField("task_id (optional)", "taskId");
  strField("sabotage_repair_id (optional)", "sabotageRepairId");
  strField("object_type (optional, Tier 2.7 sabotage trigger)", "objectType");
  appendDeleteButton(root);
}

function renderDoorProps(i) {
  const d = state.map.doors?.[i];
  if (!d) return;
  const root = dom.propsContent;
  // Read-only room labels — door reassignment isn't allowed via the props
  // sidebar. To "move" a door to a different shared edge, delete it and
  // re-create it with the door tool. Shows the labels so the user can see
  // which two rooms are connected.
  const a = state.map.rooms.find((r) => r.id === d.betweenRoomA);
  const b = state.map.rooms.find((r) => r.id === d.betweenRoomB);
  const info = document.createElement("p");
  info.className = "props-empty";
  info.style.color = "#a0a4a8";
  info.textContent = `Verbindet: ${a?.title || d.betweenRoomA} ↔ ${b?.title || d.betweenRoomB}`;
  root.appendChild(info);

  root.appendChild(
    makeField(
      "ID",
      d.id,
      (v) => {
        d.id = v.trim();
        toolContext.markDirty();
        requestRender();
      },
      "text"
    )
  );
  root.appendChild(
    makeField(
      "Position (entlang Wand)",
      d.position,
      (v) => {
        const n = parseInt(v, 10);
        if (Number.isFinite(n)) {
          d.position = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  root.appendChild(
    makeField(
      "Breite",
      d.width,
      (v) => {
        const n = parseInt(v, 10);
        if (Number.isFinite(n) && n > 0) {
          d.width = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  // doorKind is a Godot scene key — kept simple as a select with the
  // currently-supported values from docs/maps.md.
  const kindWrap = document.createElement("label");
  kindWrap.textContent = "Tür-Typ (Godot)";
  const kindSel = document.createElement("select");
  for (const k of ["office_door", "glass_panel", "vault", "none"]) {
    const opt = document.createElement("option");
    opt.value = k;
    opt.textContent = k;
    if ((d.doorKind || "office_door") === k) opt.selected = true;
    kindSel.appendChild(opt);
  }
  kindSel.addEventListener("change", () => {
    d.doorKind = kindSel.value;
    toolContext.markDirty();
    requestRender();
  });
  kindWrap.appendChild(kindSel);
  root.appendChild(kindWrap);
  appendDeleteButton(root);
}

function appendDeleteButton(root) {
  const btn = document.createElement("button");
  btn.textContent = "Löschen";
  btn.className = "danger";
  btn.addEventListener("click", deleteSelection);
  root.appendChild(btn);
}

// --- File ops --------------------------------------------------------------

function confirmIfDirty() {
  if (!state.dirty) return true;
  return window.confirm("Ungesicherte Änderungen verwerfen?");
}

dom.btnNew.addEventListener("click", () => {
  if (!confirmIfDirty()) return;
  state.map = blankMap();
  state.selection = null;
  state.dirty = false;
  dom.dirtyFlag.classList.add("hidden");
  history.clear();
  refreshUndoButtons();
  syncTopbarFields();
  renderPropsSidebar();
  refreshValidationStrip();
  computeFitView();
  requestRender();
});

dom.btnLoad.addEventListener("click", () => {
  if (!confirmIfDirty()) return;
  dom.fileInput.value = "";
  dom.fileInput.click();
});

dom.fileInput.addEventListener("change", async () => {
  const file = dom.fileInput.files && dom.fileInput.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    const map = deserializeMap(text);
    state.map = map;
    state.selection = null;
    state.dirty = false;
    dom.dirtyFlag.classList.add("hidden");
    history.clear();
    refreshUndoButtons();
    syncTopbarFields();
    renderPropsSidebar();
    refreshValidationStrip();
    computeFitView();
    requestRender();
  } catch (err) {
    window.alert("JSON konnte nicht geladen werden:\n" + err.message);
  }
});

dom.btnDownload.addEventListener("click", () => triggerDownload());

function triggerDownload() {
  const warnings = validateMap(state.map);
  if (warnings.length > 0) {
    const msg =
      "Folgende Probleme wurden erkannt:\n\n- " +
      warnings.join("\n- ") +
      "\n\nTrotzdem herunterladen?";
    if (!window.confirm(msg)) return;
  }
  const text = serializeMap(state.map);
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const safeName = (state.map.name || "untitled").replace(/[^a-z0-9_-]+/gi, "_");
  a.download = `${safeName}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 0);
  state.dirty = false;
  dom.dirtyFlag.classList.add("hidden");
}

window.addEventListener("beforeunload", (e) => {
  if (state.dirty) {
    e.preventDefault();
    e.returnValue = "";
  }
});

// --- Kind library ----------------------------------------------------------
//
// Build a sidebar palette of all known MapObject kinds, grouped by category.
// Clicking a tile activates the Object tool with that kind pre-filled — no
// more typing kind names into a prompt. The tile palette uses the same fill
// color as the in-game placeholder so the editor visually matches the
// browser render.

function renderKindLibrary() {
  const root = dom.kindLibrary;
  if (!root) return;
  root.innerHTML = "";
  for (const category of KIND_CATEGORIES) {
    const section = document.createElement("div");
    section.className = "kind-category";
    const heading = document.createElement("h4");
    heading.textContent = category;
    section.appendChild(heading);
    const grid = document.createElement("div");
    grid.className = "kind-grid";
    for (const entry of KIND_CATALOGUE) {
      if (entry.category !== category) continue;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "kind-tile";
      btn.dataset.kind = entry.kind;
      btn.title = `${entry.kind} — ${entry.width}×${entry.height}${
        entry.blocksMovement ? " (blockt)" : ""
      }`;
      const swatch = document.createElement("div");
      swatch.className = "kind-tile-swatch";
      swatch.style.background = entry.fill;
      btn.appendChild(swatch);
      const name = document.createElement("div");
      name.className = "kind-tile-name";
      name.textContent = entry.kind;
      btn.appendChild(name);
      const meta = document.createElement("div");
      meta.className = "kind-tile-meta";
      meta.textContent = `${entry.width}×${entry.height}${entry.blocksMovement ? "" : " · open"}`;
      btn.appendChild(meta);
      btn.addEventListener("click", () => activateKind(entry.kind));
      grid.appendChild(btn);
    }
    section.appendChild(grid);
    root.appendChild(section);
  }
}

function activateKind(kind) {
  state.pendingKind = kind;
  if (state.tool !== "object") {
    const radio = document.querySelector('input[name="tool"][value="object"]');
    if (radio) radio.checked = true;
    setTool("object");
  } else {
    updateCanvasCursor();
  }
  renderKindPending();
}

function clearPendingKind() {
  state.pendingKind = null;
  renderKindPending();
  updateCanvasCursor();
}

function renderKindPending() {
  if (!dom.kindPending) return;
  if (state.pendingKind && KIND_BY_NAME.has(state.pendingKind)) {
    dom.kindPending.classList.remove("hidden");
    dom.kindPendingName.textContent = state.pendingKind;
  } else {
    dom.kindPending.classList.add("hidden");
    dom.kindPendingName.textContent = "";
  }
  // Highlight the active tile.
  if (dom.kindLibrary) {
    for (const tile of dom.kindLibrary.querySelectorAll(".kind-tile")) {
      tile.classList.toggle("selected", tile.dataset.kind === state.pendingKind);
    }
  }
}

dom.kindClear?.addEventListener("click", clearPendingKind);

// --- Layer toggles ---------------------------------------------------------

function renderLayerToggles() {
  const root = dom.layerToggles;
  if (!root) return;
  root.innerHTML = "";
  for (const key of Object.keys(DEFAULT_LAYERS)) {
    const wrap = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = state.layers[key] !== false;
    cb.addEventListener("change", () => {
      state.layers[key] = cb.checked;
      requestRender();
    });
    wrap.appendChild(cb);
    wrap.appendChild(document.createTextNode(" " + (LAYER_LABELS[key] || key)));
    root.appendChild(wrap);
  }
}

// --- Undo / redo wiring ----------------------------------------------------

function performUndo() {
  if (!history.canUndo()) return;
  const restored = history.undo(state.map);
  if (!restored) return;
  applyRestoredMap(restored);
}

function performRedo() {
  if (!history.canRedo()) return;
  const restored = history.redo(state.map);
  if (!restored) return;
  applyRestoredMap(restored);
}

function applyRestoredMap(map) {
  state.map = map;
  state.selection = null;
  state.dirty = true;
  dom.dirtyFlag.classList.remove("hidden");
  syncTopbarFields();
  renderPropsSidebar();
  refreshValidationStrip();
  refreshUndoButtons();
  computeFitView();
  requestRender();
}

function refreshUndoButtons() {
  if (dom.btnUndo) dom.btnUndo.disabled = !history.canUndo();
  if (dom.btnRedo) dom.btnRedo.disabled = !history.canRedo();
}

dom.btnUndo?.addEventListener("click", performUndo);
dom.btnRedo?.addEventListener("click", performRedo);

// --- Validation strip ------------------------------------------------------

function refreshValidationStrip() {
  if (!dom.validationStrip) return;
  const warnings = validateMap(state.map);
  if (warnings.length === 0) {
    dom.validationStrip.classList.add("ok");
    dom.validationStrip.classList.remove("empty");
    dom.validationStrip.textContent = "Validierung: alles gut";
    dom.validationStrip.title = "";
    return;
  }
  dom.validationStrip.classList.remove("ok");
  dom.validationStrip.classList.remove("empty");
  const summary =
    warnings.length === 1 ? warnings[0] : `${warnings.length} Warnungen — ${warnings[0]}`;
  dom.validationStrip.textContent = summary;
  dom.validationStrip.title = warnings.join("\n");
}

// --- Server-side Map storage ------------------------------------------------
//
// Designers should be able to push the current map straight into the live
// registry so a host picks it up in the lobby without a download/commit/
// deploy round-trip. Save is **ephemeral** — the maps/ directory belongs
// to the deployed snapshot and gets overwritten on the next deploy. So a
// "saved on server" map still needs its JSON downloaded + committed for
// permanence. The "JSON herunterladen" button stays the source of truth
// for git-tracked maps.

function slugifyMapId(name) {
  return (name || "")
    .toString()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^[_-]+|[_-]+$/g, "")
    .slice(0, 40);
}

let cachedServerMaps = []; // [{ id, name }]

async function fetchServerMaps() {
  const r = await fetch("/api/maps");
  if (!r.ok) throw new Error(`GET /api/maps → ${r.status}`);
  const data = await r.json();
  cachedServerMaps = Array.isArray(data.maps) ? data.maps : [];
  return cachedServerMaps;
}

async function fetchServerMap(mapId) {
  const r = await fetch("/api/maps/" + encodeURIComponent(mapId));
  if (!r.ok) throw new Error(`GET /api/maps/${mapId} → ${r.status}`);
  return await r.json();
}

async function putServerMap(mapId, payload) {
  const r = await fetch("/api/maps/" + encodeURIComponent(mapId), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : r.statusText);
  }
  return await r.json();
}

async function onSaveToServer() {
  const baseName = dom.mapName?.value?.trim() || state.map.name || "";
  const mapId = slugifyMapId(baseName);
  if (!mapId) {
    flashStatus("Bitte einen Map-Namen vergeben.", true);
    return;
  }
  // Refresh cache so the overwrite check is accurate (someone else might
  // have pushed in the meantime).
  try {
    await fetchServerMaps();
  } catch (err) {
    flashStatus("Server nicht erreichbar: " + err.message, true);
    return;
  }
  const exists = cachedServerMaps.some((m) => m.id === mapId);
  if (exists) {
    const ok = window.confirm(
      `Karte "${mapId}" existiert bereits auf dem Server.\n\nÜberschreiben?`
    );
    if (!ok) return;
  }
  let payload;
  try {
    payload = JSON.parse(serializeMap(state.map));
  } catch (err) {
    flashStatus("Map serialisieren fehlgeschlagen: " + err.message, true);
    return;
  }
  try {
    const result = await putServerMap(mapId, payload);
    state.dirty = false;
    dom.dirtyFlag.classList.add("hidden");
    flashStatus(`In Spiel gespeichert: ${result.id} (${result.name})`);
    fetchServerMaps().catch(() => {});
  } catch (err) {
    flashStatus("Speichern fehlgeschlagen: " + err.message, true);
  }
}

async function onLoadFromServerOpen() {
  if (!dom.serverLoadModal) return;
  dom.serverLoadModal.classList.remove("hidden");
  dom.serverLoadList.innerHTML = '<p class="server-load-empty">Lade…</p>';
  try {
    const maps = await fetchServerMaps();
    renderServerLoadList(maps);
  } catch (err) {
    dom.serverLoadList.innerHTML = `<p class="server-load-empty">Server nicht erreichbar: ${err.message}</p>`;
  }
}

function renderServerLoadList(maps) {
  if (!maps.length) {
    dom.serverLoadList.innerHTML = '<p class="server-load-empty">Keine Karten auf dem Server.</p>';
    return;
  }
  const frag = document.createDocumentFragment();
  for (const m of maps) {
    const row = document.createElement("div");
    row.className = "server-map-row";
    row.dataset.id = m.id;
    const left = document.createElement("div");
    left.innerHTML = `<strong>${escapeHtml(m.name)}</strong>`;
    const meta = document.createElement("span");
    meta.className = "server-map-meta";
    meta.textContent = m.id;
    row.appendChild(left);
    row.appendChild(meta);
    row.addEventListener("click", () => loadServerMapInto(m.id));
    frag.appendChild(row);
  }
  dom.serverLoadList.innerHTML = "";
  dom.serverLoadList.appendChild(frag);
}

async function loadServerMapInto(mapId) {
  if (state.dirty) {
    const ok = window.confirm(
      "Es gibt nicht gespeicherte Änderungen. Trotzdem laden und verwerfen?"
    );
    if (!ok) return;
  }
  try {
    const json = await fetchServerMap(mapId);
    const text = JSON.stringify(json);
    state.map = deserializeMap(text);
    state.selection = null;
    state.dirty = false;
    history.reset?.();
    history.push?.(state.map);
    dom.dirtyFlag.classList.add("hidden");
    syncTopbarFields();
    renderPropsSidebar();
    refreshValidationStrip();
    refreshUndoButtons();
    computeFitView();
    requestRender();
    closeServerLoadModal();
    flashStatus(`Karte geladen: ${mapId}`);
  } catch (err) {
    flashStatus("Laden fehlgeschlagen: " + err.message, true);
  }
}

function closeServerLoadModal() {
  dom.serverLoadModal?.classList.add("hidden");
}

function escapeHtml(s) {
  return String(s).replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

let flashTimer = null;
function flashStatus(message, isError = false) {
  if (!dom.statusFlash) return;
  clearTimeout(flashTimer);
  dom.statusFlash.textContent = message;
  dom.statusFlash.classList.remove("hidden", "fading");
  dom.statusFlash.classList.toggle("error", !!isError);
  flashTimer = window.setTimeout(() => {
    dom.statusFlash.classList.add("fading");
    flashTimer = window.setTimeout(() => {
      dom.statusFlash.classList.add("hidden");
      dom.statusFlash.classList.remove("fading");
    }, 400);
  }, 3500);
}

dom.btnSaveServer?.addEventListener("click", onSaveToServer);
dom.btnLoadServer?.addEventListener("click", onLoadFromServerOpen);
dom.serverLoadClose?.addEventListener("click", closeServerLoadModal);
dom.serverLoadModal?.addEventListener("click", (e) => {
  if (e.target === dom.serverLoadModal) closeServerLoadModal();
});
window.addEventListener("keydown", (e) => {
  if (
    e.code === "Escape" &&
    dom.serverLoadModal &&
    !dom.serverLoadModal.classList.contains("hidden")
  ) {
    closeServerLoadModal();
  }
});

// --- Boot ------------------------------------------------------------------
//
// Kinds catalogue is fetched async from /api/kinds. Everything that
// reads KIND_CATALOGUE / KIND_BY_NAME / KIND_CATEGORIES (palette,
// validation, props sidebar) runs AFTER the init resolves so the
// catalogue is populated. On fetch failure we still bring the editor
// up — palette will be empty, designer sees the toast, fixes deploy.

(async () => {
  try {
    await initKindsCatalogue();
  } catch (err) {
    flashStatus(`Kind-Catalogue nicht geladen: ${err.message}`, true);
  }
  renderKindLibrary();
  renderLayerToggles();
  setTool("select");
  syncTopbarFields();
  renderPropsSidebar();
  refreshValidationStrip();
  refreshUndoButtons();
  fitCanvas();
  // 3D preview is on by default (toggle is checked in HTML). Lazy-load + first
  // render fires once the module resolves.
  if (dom.toggle3DPreview?.checked) {
    setPreview3DEnabled(true);
  }
})();
