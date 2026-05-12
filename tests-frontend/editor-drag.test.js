// Editor-Slice-2: SelectTool supports drag-to-move on rooms, spawns, task
// anchors, and map objects. Before the slice the user could only edit
// positions via the props sidebar — clumsy for layout work.
//
// ObjectTool reads default-size + blocks_movement from KIND_BY_NAME, which
// post-2026-04-27 comes from /api/kinds. Seed the registry from the
// on-disk maps/kinds.json so that lookup matches production.

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { _seedFromRegistryForTests } from "../static/editor/editor-kinds.js";
import { ObjectTool, SelectTool, hitTest } from "../static/editor/editor-tools.js";

beforeAll(() => {
  const here = dirname(fileURLToPath(import.meta.url));
  const path = resolve(here, "../maps/kinds.json");
  _seedFromRegistryForTests(JSON.parse(readFileSync(path, "utf-8")));
});

function makeMap() {
  return {
    name: "test",
    size: { width: 1000, height: 1000 },
    rooms: [{ id: "r1", title: "R1", x: 100, y: 100, width: 200, height: 200, color: "#3a4560" }],
    spawnPoints: [{ x: 50, y: 50 }],
    taskAnchors: [{ taskId: "t1", x: 600, y: 600 }],
    mapObjects: [{ id: "o1", x: 400, y: 400, width: 80, height: 40, kind: "desk", rotation: 0 }],
    doors: [],
    sabotagePanels: [],
    vents: [],
    warRoomId: "r1",
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

describe("hitTest", () => {
  it("hits the room when clicked inside its rect", () => {
    const map = makeMap();
    const hit = hitTest(map, 150, 150);
    expect(hit).toEqual({ kind: "room", index: 0 });
  });

  it("hits the spawn before the room when overlapping", () => {
    const map = makeMap();
    map.rooms[0].x = 0;
    map.rooms[0].y = 0;
    const hit = hitTest(map, 50, 50);
    expect(hit?.kind).toBe("spawn");
  });

  it("hits a map object via its bounding box", () => {
    const map = makeMap();
    const hit = hitTest(map, 400, 400);
    expect(hit).toEqual({ kind: "object", index: 0 });
  });

  it("returns null when the click misses everything", () => {
    const map = makeMap();
    const hit = hitTest(map, 990, 990);
    expect(hit).toBeNull();
  });
});

describe("SelectTool drag", () => {
  let map, ctx, tool;
  beforeEach(() => {
    map = makeMap();
    ctx = makeCtx(map);
    tool = new SelectTool();
  });

  it("clears selection when clicking on empty space", () => {
    tool.onDown(ctx, 990, 990);
    expect(ctx.setSelection).toHaveBeenCalledWith(null);
  });

  it("selects a room without moving it on a click (no drag)", () => {
    tool.onDown(ctx, 200, 200);
    tool.onUp(ctx, 200, 200);
    expect(ctx.setSelection).toHaveBeenCalledWith({ kind: "room", index: 0 });
    expect(map.rooms[0].x).toBe(100);
    expect(map.rooms[0].y).toBe(100);
    expect(ctx.markDirty).not.toHaveBeenCalled();
  });

  it("ignores tiny mouse jitter below the drag threshold", () => {
    tool.onDown(ctx, 200, 200);
    tool.onMove(ctx, 201, 201); // < 4px
    tool.onUp(ctx, 201, 201);
    expect(map.rooms[0].x).toBe(100);
    expect(ctx.markDirty).not.toHaveBeenCalled();
  });

  it("drags a room: releases at offset to maintain click position", () => {
    // Click at (200,200) on a room whose top-left is (100,100). Offset = (100,100).
    tool.onDown(ctx, 200, 200);
    tool.onMove(ctx, 350, 280); // movement well above threshold
    expect(map.rooms[0].x).toBe(250);
    expect(map.rooms[0].y).toBe(180);
    expect(ctx.markDirty).toHaveBeenCalled();
    tool.onUp(ctx, 350, 280);
  });

  it("drags a spawn point", () => {
    tool.onDown(ctx, 50, 50);
    tool.onMove(ctx, 120, 80);
    expect(map.spawnPoints[0].x).toBe(120);
    expect(map.spawnPoints[0].y).toBe(80);
  });

  it("drags a map object by its center", () => {
    tool.onDown(ctx, 400, 400);
    tool.onMove(ctx, 500, 450);
    expect(map.mapObjects[0].x).toBe(500);
    expect(map.mapObjects[0].y).toBe(450);
  });

  it("drags a task anchor", () => {
    tool.onDown(ctx, 600, 600);
    tool.onMove(ctx, 700, 700);
    expect(map.taskAnchors[0].x).toBe(700);
    expect(map.taskAnchors[0].y).toBe(700);
  });

  it("releasing the drag clears the internal handle so subsequent moves are no-ops", () => {
    tool.onDown(ctx, 200, 200);
    tool.onMove(ctx, 300, 300);
    tool.onUp(ctx, 300, 300);
    map.rooms[0].x = 999;
    tool.onMove(ctx, 400, 400); // no active drag → no mutation
    expect(map.rooms[0].x).toBe(999);
  });
});

describe("ObjectTool uses pending kind from context", () => {
  it("places a desk with catalogue defaults when pendingKind=desk", () => {
    const map = makeMap();
    map.mapObjects = [];
    const ctx = makeCtx(map);
    ctx.pendingKind = "desk";
    const tool = new ObjectTool();
    tool.onDown(ctx, 600, 600);
    expect(map.mapObjects).toHaveLength(1);
    const obj = map.mapObjects[0];
    expect(obj.kind).toBe("desk");
    expect(obj.x).toBe(600);
    expect(obj.y).toBe(600);
    expect(obj.width).toBe(110);
    expect(obj.height).toBe(60);
    expect(obj.blocksMovement).toBe(true);
  });

  it("respects blocksMovement=false from the catalogue (e.g. plant_cactus)", () => {
    const map = makeMap();
    map.mapObjects = [];
    const ctx = makeCtx(map);
    ctx.pendingKind = "plant_cactus";
    const tool = new ObjectTool();
    tool.onDown(ctx, 100, 100);
    expect(map.mapObjects[0].blocksMovement).toBe(false);
  });

  it("alerts and places nothing when no pendingKind is set", () => {
    const map = makeMap();
    map.mapObjects = [];
    const ctx = makeCtx(map);
    const tool = new ObjectTool();
    // vitest 4 / happy-dom 20: window.alert ist nicht mehr default-definiert,
    // vi.spyOn(window, "alert") wirft "can only spy on a function".
    // vi.stubGlobal arbeitet auf undefined-Globals und ist forward-compatible.
    const alertFn = vi.fn();
    vi.stubGlobal("alert", alertFn);
    tool.onDown(ctx, 600, 600);
    expect(map.mapObjects).toHaveLength(0);
    expect(alertFn).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
