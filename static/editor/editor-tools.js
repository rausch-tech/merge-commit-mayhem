// Per-tool interaction logic for the MCM Map-Editor.
//
// Each tool gets a chance to handle pointer events on the canvas. Tools call
// back into the editor (via the `ctx` parameter) to mutate the map model and
// trigger a re-render. Coordinates passed in are already mapped from screen
// space to map space (and snapped, unless Shift is held).

import { KIND_BY_NAME } from "/static/editor/editor-kinds.js";

const SNAP = 50;
const DRAG_THRESHOLD_PX = 4; // movement below this is treated as a click, not a drag

export function snap(value, enabled) {
  if (!enabled) return Math.round(value);
  return Math.round(value / SNAP) * SNAP;
}

// Hit-test helpers. Returned object describes a selection: { kind, index }.
export function hitTest(map, mx, my) {
  // Spawns + task anchors first (they're small).
  const radius = 18;
  for (let i = (map.spawnPoints || []).length - 1; i >= 0; i--) {
    const s = map.spawnPoints[i];
    if (Math.hypot(s.x - mx, s.y - my) <= radius) {
      return { kind: "spawn", index: i };
    }
  }
  for (let i = (map.taskAnchors || []).length - 1; i >= 0; i--) {
    const t = map.taskAnchors[i];
    if (Math.hypot(t.x - mx, t.y - my) <= radius) {
      return { kind: "task", index: i };
    }
  }
  // Map objects: hit-test against their bounding box (after rotation swap).
  for (let i = (map.mapObjects || []).length - 1; i >= 0; i--) {
    const o = map.mapObjects[i];
    const dw = o.rotation === 90 || o.rotation === 270 ? o.height : o.width;
    const dh = o.rotation === 90 || o.rotation === 270 ? o.width : o.height;
    if (mx >= o.x - dw / 2 && mx <= o.x + dw / 2 && my >= o.y - dh / 2 && my <= o.y + dh / 2) {
      return { kind: "object", index: i };
    }
  }
  // Rooms last (largest).
  for (let i = (map.rooms || []).length - 1; i >= 0; i--) {
    const r = map.rooms[i];
    if (mx >= r.x && mx <= r.x + r.width && my >= r.y && my <= r.y + r.height) {
      return { kind: "room", index: i };
    }
  }
  return null;
}

// --- Select tool: click to select, drag to move ----------------------------
//
// Drag works for rooms, spawns, task anchors, map objects. The handle records
// the click point relative to the entity's reference point (top-left for
// rooms, center for everything else) so the drag motion stays consistent.
// Doors are not draggable here — Slice-4 owns the door UX.

export class SelectTool {
  constructor() {
    this.drag = null; // { kind, index, offsetX, offsetY, downX, downY, moved }
  }
  onDown(ctx, mx, my) {
    const hit = hitTest(ctx.map, mx, my);
    if (!hit) {
      ctx.setSelection(null);
      this.drag = null;
      return;
    }
    ctx.setSelection(hit);
    this.drag = {
      kind: hit.kind,
      index: hit.index,
      offsetX: 0,
      offsetY: 0,
      downX: mx,
      downY: my,
      moved: false,
    };
    if (hit.kind === "room") {
      const r = ctx.map.rooms[hit.index];
      this.drag.offsetX = mx - r.x;
      this.drag.offsetY = my - r.y;
    } else if (hit.kind === "spawn") {
      const s = ctx.map.spawnPoints[hit.index];
      this.drag.offsetX = mx - s.x;
      this.drag.offsetY = my - s.y;
    } else if (hit.kind === "task") {
      const t = ctx.map.taskAnchors[hit.index];
      this.drag.offsetX = mx - t.x;
      this.drag.offsetY = my - t.y;
    } else if (hit.kind === "object") {
      const o = ctx.map.mapObjects[hit.index];
      this.drag.offsetX = mx - o.x;
      this.drag.offsetY = my - o.y;
    }
  }
  onMove(ctx, mx, my) {
    if (!this.drag) return;
    if (
      !this.drag.moved &&
      Math.hypot(mx - this.drag.downX, my - this.drag.downY) < DRAG_THRESHOLD_PX
    ) {
      return;
    }
    this.drag.moved = true;
    const nx = mx - this.drag.offsetX;
    const ny = my - this.drag.offsetY;
    if (this.drag.kind === "room") {
      const r = ctx.map.rooms[this.drag.index];
      if (!r) return;
      r.x = nx;
      r.y = ny;
    } else if (this.drag.kind === "spawn") {
      const s = ctx.map.spawnPoints[this.drag.index];
      if (!s) return;
      s.x = nx;
      s.y = ny;
    } else if (this.drag.kind === "task") {
      const t = ctx.map.taskAnchors[this.drag.index];
      if (!t) return;
      t.x = nx;
      t.y = ny;
    } else if (this.drag.kind === "object") {
      const o = ctx.map.mapObjects[this.drag.index];
      if (!o) return;
      o.x = nx;
      o.y = ny;
    }
    ctx.markDirty();
    ctx.refreshPropsSidebar();
  }
  onUp() {
    this.drag = null;
  }
  drawPreview() {}
}

// --- Room tool: drag a rectangle -------------------------------------------

export class RoomTool {
  constructor() {
    this.startX = null;
    this.startY = null;
    this.curX = null;
    this.curY = null;
  }
  onDown(ctx, mx, my) {
    this.startX = mx;
    this.startY = my;
    this.curX = mx;
    this.curY = my;
  }
  onMove(ctx, mx, my) {
    if (this.startX === null) return;
    this.curX = mx;
    this.curY = my;
    ctx.requestRender();
  }
  onUp(ctx, mx, my) {
    if (this.startX === null) return;
    const x = Math.min(this.startX, mx);
    const y = Math.min(this.startY, my);
    const w = Math.abs(mx - this.startX);
    const h = Math.abs(my - this.startY);
    this.startX = null;
    this.startY = null;
    this.curX = null;
    this.curY = null;
    if (w < 50 || h < 50) {
      ctx.requestRender();
      return;
    }
    const id = (window.prompt("Raum-ID (snake_case)", "new_room") || "").trim();
    if (!id) {
      ctx.requestRender();
      return;
    }
    const title = (window.prompt("Raum-Titel", id) || id).trim();
    ctx.map.rooms.push({
      id,
      title,
      x,
      y,
      width: w,
      height: h,
      color: defaultRoomColor(ctx.map.rooms.length),
    });
    ctx.markDirty();
    ctx.refreshWarRoomChoices();
    ctx.setSelection({ kind: "room", index: ctx.map.rooms.length - 1 });
  }
  drawPreview(ctx2d, _ctx) {
    if (this.startX === null || this.curX === null) return;
    const x = Math.min(this.startX, this.curX);
    const y = Math.min(this.startY, this.curY);
    const w = Math.abs(this.curX - this.startX);
    const h = Math.abs(this.curY - this.startY);
    ctx2d.save();
    ctx2d.strokeStyle = "#88ccff";
    ctx2d.lineWidth = 2;
    ctx2d.setLineDash([6, 4]);
    ctx2d.strokeRect(x, y, w, h);
    ctx2d.restore();
  }
}

function defaultRoomColor(index) {
  const palette = [
    "#3a4560",
    "#5a3a70",
    "#7a5030",
    "#2a4a70",
    "#2a607a",
    "#3a6a3a",
    "#705030",
    "#503a60",
  ];
  return palette[index % palette.length];
}

// --- Spawn tool: click to add a point --------------------------------------

export class SpawnTool {
  onDown(ctx, mx, my) {
    ctx.map.spawnPoints.push({ x: mx, y: my });
    ctx.markDirty();
    ctx.setSelection({ kind: "spawn", index: ctx.map.spawnPoints.length - 1 });
  }
  onMove() {}
  onUp() {}
  drawPreview() {}
}

// --- Task-anchor tool: click + prompt for taskId ---------------------------

export class TaskAnchorTool {
  onDown(ctx, mx, my) {
    const taskId = (window.prompt("Task-ID", "new_task") || "").trim();
    if (!taskId) return;
    ctx.map.taskAnchors.push({ taskId, x: mx, y: my });
    ctx.markDirty();
    ctx.setSelection({ kind: "task", index: ctx.map.taskAnchors.length - 1 });
  }
  onMove() {}
  onUp() {}
  drawPreview() {}
}

// --- Object tool: click to place a MapObject from the kind library ---------
//
// `ctx.pendingKind` is set when the user clicks an entry in the library
// sidebar. The catalogue entry provides default size and blocks-movement so
// new objects match the in-game look without needing JSON tweaks.

export class ObjectTool {
  onDown(ctx, mx, my) {
    const kind = ctx.pendingKind;
    if (!kind) {
      window.alert(
        "Wähle zuerst einen Objekt-Typ in der Bibliothek (linke Sidebar) und klicke dann auf die Karte."
      );
      return;
    }
    const entry = KIND_BY_NAME.get(kind) || {
      width: 80,
      height: 40,
      blocksMovement: true,
    };
    if (!Array.isArray(ctx.map.mapObjects)) ctx.map.mapObjects = [];
    const id = `obj-${ctx.map.mapObjects.length + 1}`;
    ctx.map.mapObjects.push({
      id,
      x: mx,
      y: my,
      width: entry.width,
      height: entry.height,
      kind,
      rotation: 0,
      blocksMovement: entry.blocksMovement !== false,
    });
    ctx.markDirty();
    ctx.setSelection({ kind: "object", index: ctx.map.mapObjects.length - 1 });
  }
  onMove() {}
  onUp() {}
  drawPreview() {}
}

export const TOOLS = {
  select: SelectTool,
  room: RoomTool,
  spawn: SpawnTool,
  task: TaskAnchorTool,
  object: ObjectTool,
};
