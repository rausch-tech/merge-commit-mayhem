// Per-tool interaction logic for the MCM Map-Editor.
//
// Each tool gets a chance to handle pointer events on the canvas. Tools call
// back into the editor (via the `ctx` parameter) to mutate the map model and
// trigger a re-render. Coordinates passed in are already mapped from screen
// space to map space (and snapped, unless Shift is held).

import { KIND_BY_NAME } from "/static/editor/editor-kinds.js";

const SNAP = 50;
const DRAG_THRESHOLD_PX = 4; // movement below this is treated as a click, not a drag
const DOOR_HIT_BAND_PX = 14; // half-width of the band around a door rectangle
const DOOR_PLACEMENT_BAND_PX = 28; // distance from a shared edge that still counts as "on it"
const DOOR_DEFAULT_WIDTH = 240;
const DOOR_DEFAULT_KIND = "office_door";

export function snap(value, enabled) {
  if (!enabled) return Math.round(value);
  return Math.round(value / SNAP) * SNAP;
}

// --- Shared-edge geometry --------------------------------------------------
//
// A door lives on the shared edge between two adjacent rooms. Several places
// in the editor need the same geometry: hit-testing, drawing, drag-clamping,
// and door creation. Put it here once.

/** Find the shared edge between rooms a and b, if any. */
export function findSharedEdge(a, b) {
  if (a.x + a.width === b.x || b.x + b.width === a.x) {
    const position = a.x + a.width === b.x ? b.x : a.x;
    const start = Math.max(a.y, b.y);
    const end = Math.min(a.y + a.height, b.y + b.height);
    if (start < end) return { axis: "x", position, start, end };
  }
  if (a.y + a.height === b.y || b.y + b.height === a.y) {
    const position = a.y + a.height === b.y ? b.y : a.y;
    const start = Math.max(a.x, b.x);
    const end = Math.min(a.x + a.width, b.x + b.width);
    if (start < end) return { axis: "y", position, start, end };
  }
  return null;
}

/**
 * Find the shared edge nearest to (mx, my) within `threshold`. Returns
 * `{ axis, position, start, end, roomA, roomB, projection }` or null.
 * `projection` is the cursor projected onto the edge (the door position).
 */
export function findNearestSharedEdge(map, mx, my, threshold = DOOR_PLACEMENT_BAND_PX) {
  const rooms = map.rooms || [];
  let best = null;
  let bestDist = threshold + 1;
  for (let i = 0; i < rooms.length; i++) {
    for (let j = i + 1; j < rooms.length; j++) {
      const edge = findSharedEdge(rooms[i], rooms[j]);
      if (!edge) continue;
      let dist;
      let projection;
      if (edge.axis === "x") {
        // Vertical edge: cursor must be near edge.position in x and inside [start,end] in y.
        dist = Math.abs(mx - edge.position);
        projection = Math.max(edge.start, Math.min(edge.end, my));
        if (my < edge.start - threshold || my > edge.end + threshold) continue;
      } else {
        dist = Math.abs(my - edge.position);
        projection = Math.max(edge.start, Math.min(edge.end, mx));
        if (mx < edge.start - threshold || mx > edge.end + threshold) continue;
      }
      if (dist < bestDist) {
        bestDist = dist;
        best = { ...edge, roomA: rooms[i].id, roomB: rooms[j].id, projection };
      }
    }
  }
  return best;
}

/** Recompute the shared edge for an existing door (rooms may have moved). */
export function doorEdge(map, door) {
  const rooms = map.rooms || [];
  const a = rooms.find((r) => r.id === door.betweenRoomA);
  const b = rooms.find((r) => r.id === door.betweenRoomB);
  if (!a || !b) return null;
  return findSharedEdge(a, b);
}

// --- Hit-test --------------------------------------------------------------

/** Point-in-rectangle helper for axis-aligned door bands. */
function _hitDoor(door, edge, mx, my) {
  if (!edge) return false;
  const half = Math.floor((door.width || DOOR_DEFAULT_WIDTH) / 2);
  if (edge.axis === "x") {
    return (
      Math.abs(mx - edge.position) <= DOOR_HIT_BAND_PX &&
      my >= door.position - half &&
      my <= door.position + half
    );
  }
  return (
    Math.abs(my - edge.position) <= DOOR_HIT_BAND_PX &&
    mx >= door.position - half &&
    mx <= door.position + half
  );
}

// Returned object describes a selection: { kind, index }.
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
  // Doors: test before objects so they're easier to grab on busy maps.
  for (let i = (map.doors || []).length - 1; i >= 0; i--) {
    const door = map.doors[i];
    const edge = doorEdge(map, door);
    if (_hitDoor(door, edge, mx, my)) return { kind: "door", index: i };
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
// Drag works for rooms, spawns, task anchors, map objects, and doors. The
// handle records the click point relative to the entity's reference point
// so the drag motion stays consistent. Doors are constrained to slide
// along their shared edge (clamped to the edge range minus half door
// width), so the user can't drag a door off the wall.

export class SelectTool {
  constructor() {
    this.drag = null;
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
      offsetPos: 0,
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
    } else if (hit.kind === "door") {
      const door = ctx.map.doors[hit.index];
      const edge = doorEdge(ctx.map, door);
      if (edge) {
        const cursorAlong = edge.axis === "x" ? my : mx;
        this.drag.offsetPos = cursorAlong - door.position;
      }
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
    if (this.drag.kind === "room") {
      const r = ctx.map.rooms[this.drag.index];
      if (!r) return;
      r.x = mx - this.drag.offsetX;
      r.y = my - this.drag.offsetY;
    } else if (this.drag.kind === "spawn") {
      const s = ctx.map.spawnPoints[this.drag.index];
      if (!s) return;
      s.x = mx - this.drag.offsetX;
      s.y = my - this.drag.offsetY;
    } else if (this.drag.kind === "task") {
      const t = ctx.map.taskAnchors[this.drag.index];
      if (!t) return;
      t.x = mx - this.drag.offsetX;
      t.y = my - this.drag.offsetY;
    } else if (this.drag.kind === "object") {
      const o = ctx.map.mapObjects[this.drag.index];
      if (!o) return;
      o.x = mx - this.drag.offsetX;
      o.y = my - this.drag.offsetY;
    } else if (this.drag.kind === "door") {
      const door = ctx.map.doors[this.drag.index];
      if (!door) return;
      const edge = doorEdge(ctx.map, door);
      if (!edge) return;
      const cursorAlong = edge.axis === "x" ? my : mx;
      const half = Math.floor((door.width || DOOR_DEFAULT_WIDTH) / 2);
      const minPos = edge.start + half;
      const maxPos = edge.end - half;
      let target = cursorAlong - this.drag.offsetPos;
      if (maxPos >= minPos) {
        target = Math.max(minPos, Math.min(maxPos, target));
      }
      door.position = target;
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

// --- Door tool: click on a shared edge to add a door -----------------------
//
// Doors are gaps in the shared edge between two rooms. The user picks the
// Door tool, clicks anywhere near a shared edge, and a door is placed at
// the projected cursor position. If the click isn't near any shared edge
// the user gets a hint.

export class DoorTool {
  onDown(ctx, mx, my) {
    const edge = findNearestSharedEdge(ctx.map, mx, my);
    if (!edge) {
      window.alert(
        "Türen können nur auf gemeinsamen Wänden zwischen zwei Räumen platziert werden. Klicke näher an eine geteilte Wand."
      );
      return;
    }
    if (!Array.isArray(ctx.map.doors)) ctx.map.doors = [];
    // Clamp position so a default-width door fits on the edge — otherwise
    // the door visualizer would draw outside the wall.
    const half = Math.floor(DOOR_DEFAULT_WIDTH / 2);
    const minPos = edge.start + half;
    const maxPos = edge.end - half;
    let position = edge.projection;
    if (maxPos >= minPos) {
      position = Math.max(minPos, Math.min(maxPos, position));
    }
    const id = `d${ctx.map.doors.length + 1}`;
    ctx.map.doors.push({
      id,
      betweenRoomA: edge.roomA,
      betweenRoomB: edge.roomB,
      position,
      width: DOOR_DEFAULT_WIDTH,
      doorKind: DOOR_DEFAULT_KIND,
    });
    ctx.markDirty();
    ctx.setSelection({ kind: "door", index: ctx.map.doors.length - 1 });
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
  door: DoorTool,
};
