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
import { snap, TOOLS } from "/static/editor/editor-tools.js";

const state = {
  map: blankMap(),
  tool: "select",
  toolInstance: null,
  selection: null, // { kind, index } or null
  dirty: false,
  shiftHeld: false,
  view: { scale: 1, offsetX: 0, offsetY: 0 },
};

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
  fileInput: document.getElementById("file-input"),
  dirtyFlag: document.getElementById("dirty-flag"),
  cursorCoords: document.getElementById("cursor-coords"),
  propsEmpty: document.getElementById("props-empty"),
  propsContent: document.getElementById("props-content"),
};

const ctx2d = dom.canvas.getContext("2d");

// --- Tool context exposed to per-tool classes ------------------------------

const toolContext = {
  get map() {
    return state.map;
  },
  setSelection(sel) {
    state.selection = sel;
    renderPropsSidebar();
    requestRender();
  },
  markDirty() {
    state.dirty = true;
    dom.dirtyFlag.classList.remove("hidden");
    requestRender();
  },
  refreshWarRoomChoices() {
    refreshWarRoomChoices();
  },
  requestRender,
};

// --- Tool selection --------------------------------------------------------

function setTool(name) {
  state.tool = name;
  const ToolClass = TOOLS[name] || TOOLS.select;
  state.toolInstance = new ToolClass();
  // Switching tools clears any in-progress drag, but not the current selection.
  requestRender();
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

// --- Rendering -------------------------------------------------------------

let renderQueued = false;
function requestRender() {
  if (renderQueued) return;
  renderQueued = true;
  requestAnimationFrame(() => {
    renderQueued = false;
    render();
  });
}

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

  // Wall lines: solid black where wall, gray where door cutout.
  for (const wl of state.map.wallLines) {
    drawWallLine(wl);
  }

  // Spawn points.
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

function drawWallLine(wl) {
  const w = state.map.size.width;
  const h = state.map.size.height;
  const thickness = 8;
  ctx2d.lineWidth = thickness / state.view.scale;
  if (wl.axis === "x") {
    // Vertical line at x=position.
    const segments = computeSegments(0, h, wl.doors || []);
    for (const [a, b] of segments.solid) {
      ctx2d.strokeStyle = "#0a0a0a";
      ctx2d.beginPath();
      ctx2d.moveTo(wl.position, a);
      ctx2d.lineTo(wl.position, b);
      ctx2d.stroke();
    }
    for (const [a, b] of segments.gaps) {
      ctx2d.strokeStyle = "#555a64";
      ctx2d.beginPath();
      ctx2d.moveTo(wl.position, a);
      ctx2d.lineTo(wl.position, b);
      ctx2d.stroke();
    }
  } else {
    const segments = computeSegments(0, w, wl.doors || []);
    for (const [a, b] of segments.solid) {
      ctx2d.strokeStyle = "#0a0a0a";
      ctx2d.beginPath();
      ctx2d.moveTo(a, wl.position);
      ctx2d.lineTo(b, wl.position);
      ctx2d.stroke();
    }
    for (const [a, b] of segments.gaps) {
      ctx2d.strokeStyle = "#555a64";
      ctx2d.beginPath();
      ctx2d.moveTo(a, wl.position);
      ctx2d.lineTo(b, wl.position);
      ctx2d.stroke();
    }
  }
}

function computeSegments(start, end, doors) {
  // Returns { solid: [[a,b], ...], gaps: [[a,b], ...] } over [start, end].
  const sorted = [...doors].sort((x, y) => x.center - y.center);
  const solid = [];
  const gaps = [];
  let cursor = start;
  for (const d of sorted) {
    const a = d.center - d.width / 2;
    const b = d.center + d.width / 2;
    if (a > cursor) solid.push([cursor, a]);
    gaps.push([Math.max(start, a), Math.min(end, b)]);
    cursor = Math.max(cursor, b);
  }
  if (cursor < end) solid.push([cursor, end]);
  return { solid, gaps };
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
  } else if (sel.kind === "wall") {
    const wl = state.map.wallLines[sel.index];
    if (wl) {
      ctx2d.beginPath();
      if (wl.axis === "x") {
        ctx2d.moveTo(wl.position, 0);
        ctx2d.lineTo(wl.position, state.map.size.height);
      } else {
        ctx2d.moveTo(0, wl.position);
        ctx2d.lineTo(state.map.size.width, wl.position);
      }
      ctx2d.stroke();
    }
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
  if (e.key === "Delete" || e.key === "Backspace") {
    if (document.activeElement && document.activeElement.tagName === "INPUT") return;
    if (document.activeElement && document.activeElement.tagName === "SELECT") return;
    deleteSelection();
  }
});
window.addEventListener("keyup", (e) => {
  if (e.key === "Shift") state.shiftHeld = false;
});

function deleteSelection() {
  const sel = state.selection;
  if (!sel) return;
  if (sel.kind === "room") {
    const removed = state.map.rooms.splice(sel.index, 1)[0];
    if (removed && state.map.warRoomId === removed.id) state.map.warRoomId = "";
  } else if (sel.kind === "wall") {
    state.map.wallLines.splice(sel.index, 1);
  } else if (sel.kind === "spawn") {
    state.map.spawnPoints.splice(sel.index, 1);
  } else if (sel.kind === "task") {
    state.map.taskAnchors.splice(sel.index, 1);
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
  if (sel.kind === "wall") return renderWallProps(sel.index);
  if (sel.kind === "spawn") return renderSpawnProps(sel.index);
  if (sel.kind === "task") return renderTaskProps(sel.index);
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

function renderWallProps(i) {
  const wl = state.map.wallLines[i];
  if (!wl) return;
  const root = dom.propsContent;
  root.appendChild(
    makeField("Achse (x|y)", wl.axis, (v) => {
      if (v === "x" || v === "y") {
        wl.axis = v;
        toolContext.markDirty();
        requestRender();
      }
    })
  );
  root.appendChild(
    makeField(
      "Position",
      wl.position,
      (v) => {
        const n = parseInt(v, 10);
        if (Number.isFinite(n)) {
          wl.position = n;
          toolContext.markDirty();
          requestRender();
        }
      },
      "number"
    )
  );
  const doorsSection = document.createElement("div");
  doorsSection.className = "doors-section";
  const heading = document.createElement("strong");
  heading.textContent = "Türen";
  doorsSection.appendChild(heading);
  for (let di = 0; di < (wl.doors || []).length; di++) {
    const d = wl.doors[di];
    const row = document.createElement("div");
    row.className = "door-row";
    const cInput = document.createElement("input");
    cInput.type = "number";
    cInput.value = d.center;
    cInput.title = "Mittelpunkt";
    cInput.addEventListener("input", () => {
      const n = parseInt(cInput.value, 10);
      if (Number.isFinite(n)) {
        d.center = n;
        toolContext.markDirty();
        requestRender();
      }
    });
    const wInput = document.createElement("input");
    wInput.type = "number";
    wInput.value = d.width;
    wInput.title = "Breite";
    wInput.addEventListener("input", () => {
      const n = parseInt(wInput.value, 10);
      if (Number.isFinite(n) && n > 0) {
        d.width = n;
        toolContext.markDirty();
        requestRender();
      }
    });
    const removeBtn = document.createElement("button");
    removeBtn.textContent = "x";
    removeBtn.className = "danger";
    removeBtn.addEventListener("click", () => {
      wl.doors.splice(di, 1);
      toolContext.markDirty();
      renderPropsSidebar();
      requestRender();
    });
    row.append("c=", cInput, "w=", wInput, removeBtn);
    doorsSection.appendChild(row);
  }
  const addBtn = document.createElement("button");
  addBtn.textContent = "+ Tür";
  addBtn.addEventListener("click", () => {
    const max = wl.axis === "x" ? state.map.size.height : state.map.size.width;
    wl.doors = wl.doors || [];
    wl.doors.push({ center: Math.round(max / 2), width: 240 });
    toolContext.markDirty();
    renderPropsSidebar();
    requestRender();
  });
  doorsSection.appendChild(addBtn);
  root.appendChild(doorsSection);
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
  syncTopbarFields();
  renderPropsSidebar();
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
    syncTopbarFields();
    renderPropsSidebar();
    computeFitView();
    requestRender();
  } catch (err) {
    window.alert("JSON konnte nicht geladen werden:\n" + err.message);
  }
});

dom.btnDownload.addEventListener("click", () => {
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
});

window.addEventListener("beforeunload", (e) => {
  if (state.dirty) {
    e.preventDefault();
    e.returnValue = "";
  }
});

// --- Boot ------------------------------------------------------------------

setTool("select");
syncTopbarFields();
renderPropsSidebar();
fitCanvas();
