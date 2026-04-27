// Per-tool interaction logic for the MCM Map-Editor.
//
// Each tool gets a chance to handle pointer events on the canvas. Tools call
// back into the editor (via the `ctx` parameter) to mutate the map model and
// trigger a re-render. Coordinates passed in are already mapped from screen
// space to map space (and snapped, unless Shift is held).

const SNAP = 50;

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
  // Wall lines: hit a thin band around the line.
  const bandHalf = 12;
  for (let i = (map.wallLines || []).length - 1; i >= 0; i--) {
    const wl = map.wallLines[i];
    if (wl.axis === "x") {
      if (Math.abs(mx - wl.position) <= bandHalf && my >= 0 && my <= map.size.height) {
        return { kind: "wall", index: i };
      }
    } else {
      if (Math.abs(my - wl.position) <= bandHalf && mx >= 0 && mx <= map.size.width) {
        return { kind: "wall", index: i };
      }
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

// --- Select tool ------------------------------------------------------------

export class SelectTool {
  onDown(ctx, mx, my) {
    const hit = hitTest(ctx.map, mx, my);
    ctx.setSelection(hit);
  }
  onMove() {}
  onUp() {}
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

// --- Wall tool: click two points (snaps to nearest axis) -------------------

export class WallTool {
  constructor() {
    this.firstX = null;
    this.firstY = null;
    this.curX = null;
    this.curY = null;
  }
  onDown(ctx, mx, my) {
    if (this.firstX === null) {
      this.firstX = mx;
      this.firstY = my;
      this.curX = mx;
      this.curY = my;
      ctx.requestRender();
    } else {
      // Decide axis from dominant delta.
      const dx = Math.abs(mx - this.firstX);
      const dy = Math.abs(my - this.firstY);
      let axis;
      let position;
      if (dy > dx) {
        // Vertical wall — runs along Y, fixed X position.
        axis = "x";
        position = this.firstX;
      } else {
        axis = "y";
        position = this.firstY;
      }
      this.firstX = null;
      this.firstY = null;
      this.curX = null;
      this.curY = null;
      ctx.map.wallLines.push({ axis, position, doors: [] });
      ctx.markDirty();
      ctx.setSelection({ kind: "wall", index: ctx.map.wallLines.length - 1 });
    }
  }
  onMove(ctx, mx, my) {
    if (this.firstX === null) return;
    this.curX = mx;
    this.curY = my;
    ctx.requestRender();
  }
  onUp() {}
  drawPreview(ctx2d, ctx) {
    if (this.firstX === null) return;
    const dx = Math.abs((this.curX || 0) - this.firstX);
    const dy = Math.abs((this.curY || 0) - this.firstY);
    ctx2d.save();
    ctx2d.strokeStyle = "#88ccff";
    ctx2d.lineWidth = 2;
    ctx2d.setLineDash([6, 4]);
    ctx2d.beginPath();
    if (dy > dx) {
      ctx2d.moveTo(this.firstX, 0);
      ctx2d.lineTo(this.firstX, ctx.map.size.height);
    } else {
      ctx2d.moveTo(0, this.firstY);
      ctx2d.lineTo(ctx.map.size.width, this.firstY);
    }
    ctx2d.stroke();
    ctx2d.restore();
  }
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

// --- Object tool: click + prompt for kind (Tier 4 props) -------------------
//
// Default size: 80x40 (desk-sized). Adjust via JSON afterward — the editor
// MVP keeps placement-only; rotation is settable in JSON, future polish
// adds resize handles + rotate-shortcut to the editor.

const DEFAULT_OBJECT_KIND = "desk";
const DEFAULT_OBJECT_SIZE = { width: 80, height: 40 };

export class ObjectTool {
  onDown(ctx, mx, my) {
    const kind = (window.prompt("Object-Kind", DEFAULT_OBJECT_KIND) || "").trim();
    if (!kind) return;
    if (!Array.isArray(ctx.map.mapObjects)) ctx.map.mapObjects = [];
    const id = `obj-${ctx.map.mapObjects.length + 1}`;
    ctx.map.mapObjects.push({
      id,
      x: mx,
      y: my,
      width: DEFAULT_OBJECT_SIZE.width,
      height: DEFAULT_OBJECT_SIZE.height,
      kind,
      rotation: 0,
      blocksMovement: true,
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
  wall: WallTool,
  spawn: SpawnTool,
  task: TaskAnchorTool,
  object: ObjectTool,
};
