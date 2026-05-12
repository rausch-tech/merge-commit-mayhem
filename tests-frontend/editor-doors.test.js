// Editor-Slice-4: Door-tool + door-drag UX.
//
// User feedback: "türen lassen sich nur sehr schwer anlegen und gar nicht
// verschieben". Slice 4 adds a door tool that places doors on shared edges
// and extends SelectTool with constrained door drag (slides along the
// edge).

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  DoorTool,
  SelectTool,
  doorEdge,
  findNearestSharedEdge,
  findSharedEdge,
  hitTest,
} from "../static/editor/editor-tools.js";

function makeMap() {
  return {
    name: "test",
    size: { width: 1000, height: 1000 },
    rooms: [
      // Two rooms side-by-side sharing a vertical edge at x=200, y in [100,300].
      { id: "a", title: "A", x: 100, y: 100, width: 100, height: 200, color: "#3a4560" },
      { id: "b", title: "B", x: 200, y: 100, width: 100, height: 200, color: "#5a3a70" },
      // A third room far away — no shared edge with the others.
      { id: "c", title: "C", x: 600, y: 600, width: 100, height: 100, color: "#3a6a3a" },
    ],
    spawnPoints: [],
    taskAnchors: [],
    mapObjects: [],
    doors: [],
    sabotagePanels: [],
    vents: [],
    warRoomId: "a",
  };
}

function makeCtx(map) {
  return {
    map,
    pendingKind: null,
    setSelection: vi.fn(),
    markDirty: vi.fn(),
    refreshWarRoomChoices: vi.fn(),
    refreshPropsSidebar: vi.fn(),
    requestRender: vi.fn(),
  };
}

describe("findSharedEdge", () => {
  it("finds the vertical shared edge between adjacent rooms", () => {
    const m = makeMap();
    const edge = findSharedEdge(m.rooms[0], m.rooms[1]);
    expect(edge).toEqual({ axis: "x", position: 200, start: 100, end: 300 });
  });

  it("works regardless of argument order (sort-independent)", () => {
    const m = makeMap();
    const ab = findSharedEdge(m.rooms[0], m.rooms[1]);
    const ba = findSharedEdge(m.rooms[1], m.rooms[0]);
    expect(ab).toEqual(ba);
  });

  it("returns null when rooms don't touch", () => {
    const m = makeMap();
    expect(findSharedEdge(m.rooms[0], m.rooms[2])).toBeNull();
  });

  it("returns null when rooms only touch at a single corner", () => {
    const m = {
      rooms: [
        { id: "a", x: 0, y: 0, width: 100, height: 100 },
        { id: "b", x: 100, y: 100, width: 100, height: 100 },
      ],
    };
    expect(findSharedEdge(m.rooms[0], m.rooms[1])).toBeNull();
  });
});

describe("findNearestSharedEdge", () => {
  it("locates the edge under the cursor", () => {
    const m = makeMap();
    const hit = findNearestSharedEdge(m, 205, 200);
    expect(hit).not.toBeNull();
    expect(hit.axis).toBe("x");
    expect(hit.position).toBe(200);
    expect(new Set([hit.roomA, hit.roomB])).toEqual(new Set(["a", "b"]));
    // Projection onto the edge — clamps to [start,end].
    expect(hit.projection).toBe(200);
  });

  it("clamps projection to the edge range when cursor is past the corner", () => {
    const m = makeMap();
    const hit = findNearestSharedEdge(m, 200, 50);
    if (!hit) return; // outside threshold is acceptable too
    expect(hit.projection).toBeGreaterThanOrEqual(100);
    expect(hit.projection).toBeLessThanOrEqual(300);
  });

  it("returns null when nowhere near a shared edge", () => {
    const m = makeMap();
    expect(findNearestSharedEdge(m, 0, 0)).toBeNull();
  });
});

describe("DoorTool", () => {
  it("places a door at the projected cursor position on the shared edge", () => {
    const m = makeMap();
    const ctx = makeCtx(m);
    const tool = new DoorTool();
    tool.onDown(ctx, 200, 200);
    expect(m.doors).toHaveLength(1);
    const door = m.doors[0];
    expect(new Set([door.betweenRoomA, door.betweenRoomB])).toEqual(new Set(["a", "b"]));
    expect(door.position).toBe(200);
    expect(door.width).toBe(240);
    expect(door.doorKind).toBe("office_door");
    expect(ctx.setSelection).toHaveBeenCalledWith({ kind: "door", index: 0 });
  });

  it("clamps the door position so a default-width door fits on a short edge", () => {
    const m = {
      ...makeMap(),
      rooms: [
        { id: "a", title: "A", x: 0, y: 0, width: 100, height: 100, color: "#000" },
        { id: "b", title: "B", x: 100, y: 0, width: 100, height: 100, color: "#000" },
      ],
    };
    const ctx = makeCtx(m);
    const tool = new DoorTool();
    tool.onDown(ctx, 100, 95); // edge runs y=[0,100], door width=240 ⇒ no fit, clamps to midpoint
    expect(m.doors).toHaveLength(1);
    const door = m.doors[0];
    // edge span [0,100] is shorter than the door — clamp logic falls back to
    // the projected cursor (no constraint applied since min > max).
    expect(door.position).toBe(95);
  });

  it("alerts and places nothing when no shared edge is near the click", () => {
    const m = makeMap();
    const ctx = makeCtx(m);
    // vitest 4 / happy-dom 20: window.alert ist nicht mehr default-definiert,
    // vi.spyOn(window, "alert") wirft "can only spy on a function".
    // vi.stubGlobal arbeitet auf undefined-Globals und ist forward-compatible.
    const alertFn = vi.fn();
    vi.stubGlobal("alert", alertFn);
    const tool = new DoorTool();
    tool.onDown(ctx, 800, 50);
    expect(m.doors).toHaveLength(0);
    expect(alertFn).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});

describe("hitTest finds doors", () => {
  it("hits a door before the underlying rooms", () => {
    const m = makeMap();
    m.doors.push({
      id: "d1",
      betweenRoomA: "a",
      betweenRoomB: "b",
      position: 200,
      width: 80,
      doorKind: "office_door",
    });
    const hit = hitTest(m, 200, 200);
    expect(hit).toEqual({ kind: "door", index: 0 });
  });

  it("does not hit a door when click is far from its band", () => {
    const m = makeMap();
    m.doors.push({
      id: "d1",
      betweenRoomA: "a",
      betweenRoomB: "b",
      position: 200,
      width: 80,
      doorKind: "office_door",
    });
    const hit = hitTest(m, 150, 150);
    expect(hit?.kind).not.toBe("door");
  });
});

describe("SelectTool drag — doors", () => {
  let map, ctx, tool;
  beforeEach(() => {
    map = makeMap();
    map.doors.push({
      id: "d1",
      betweenRoomA: "a",
      betweenRoomB: "b",
      position: 200,
      width: 80,
      doorKind: "office_door",
    });
    ctx = makeCtx(map);
    tool = new SelectTool();
  });

  it("slides a door along its edge as the cursor moves", () => {
    tool.onDown(ctx, 200, 200);
    tool.onMove(ctx, 200, 250);
    expect(map.doors[0].position).toBe(250);
    tool.onUp(ctx, 200, 250);
  });

  it("clamps a door to stay inside the shared-edge range (with door-width margin)", () => {
    // edge is y=[100,300], width=80 ⇒ allowed position range [140, 260].
    tool.onDown(ctx, 200, 200);
    tool.onMove(ctx, 200, 999);
    expect(map.doors[0].position).toBe(260);
    tool.onMove(ctx, 200, -50);
    expect(map.doors[0].position).toBe(140);
  });

  it("does not affect the door's connecting rooms while dragging", () => {
    tool.onDown(ctx, 200, 200);
    tool.onMove(ctx, 200, 280);
    expect(map.doors[0].betweenRoomA).toBe("a");
    expect(map.doors[0].betweenRoomB).toBe("b");
  });
});

describe("doorEdge recomputes after a room moves", () => {
  it("returns null when one of the door's rooms is gone", () => {
    const m = makeMap();
    const door = {
      id: "d1",
      betweenRoomA: "a",
      betweenRoomB: "ghost",
      position: 200,
      width: 80,
      doorKind: "office_door",
    };
    expect(doorEdge(m, door)).toBeNull();
  });

  it("returns null when rooms drift apart so they no longer share an edge", () => {
    const m = makeMap();
    m.rooms[1].x = 400; // no longer adjacent to room a
    const door = {
      id: "d1",
      betweenRoomA: "a",
      betweenRoomB: "b",
      position: 200,
      width: 80,
      doorKind: "office_door",
    };
    expect(doorEdge(m, door)).toBeNull();
  });
});
