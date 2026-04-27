// Smoke + behaviour tests for the Tier 4 mapObjects render path.
//
// happy-dom doesn't ship a real Canvas2D backend, so we record calls
// against a fake context and assert the renderer issues the right
// fillRect/strokeRect/fillText sequence per object kind.
import { beforeEach, describe, expect, it } from "vitest";
import { Renderer } from "../static/render.js";

function makeFakeContext() {
  const calls = [];
  return {
    calls,
    save() {
      calls.push(["save"]);
    },
    restore() {
      calls.push(["restore"]);
    },
    setTransform(...args) {
      calls.push(["setTransform", ...args]);
    },
    translate(...args) {
      calls.push(["translate", ...args]);
    },
    clearRect(...args) {
      calls.push(["clearRect", ...args]);
    },
    fillRect(...args) {
      calls.push(["fillRect", ...args]);
    },
    strokeRect(...args) {
      calls.push(["strokeRect", ...args]);
    },
    fillText(...args) {
      calls.push(["fillText", ...args]);
    },
    beginPath() {
      calls.push(["beginPath"]);
    },
    arc(...args) {
      calls.push(["arc", ...args]);
    },
    fill() {
      calls.push(["fill"]);
    },
    stroke() {
      calls.push(["stroke"]);
    },
    closePath() {
      calls.push(["closePath"]);
    },
    moveTo() {},
    lineTo() {},
    rect() {},
    clip() {},
    set fillStyle(v) {
      calls.push(["fillStyle", v]);
    },
    set strokeStyle(v) {
      calls.push(["strokeStyle", v]);
    },
    set lineWidth(v) {
      calls.push(["lineWidth", v]);
    },
    set globalAlpha(v) {
      calls.push(["globalAlpha", v]);
    },
    set font(v) {
      calls.push(["font", v]);
    },
    set textAlign(v) {
      calls.push(["textAlign", v]);
    },
    set textBaseline(v) {
      calls.push(["textBaseline", v]);
    },
  };
}

function makeFakeCanvas(ctx) {
  return {
    width: 1280,
    height: 720,
    style: {},
    getContext() {
      return ctx;
    },
    getBoundingClientRect() {
      return { width: 1280, height: 720, left: 0, top: 0 };
    },
  };
}

const TINY_MAP = {
  name: "test",
  size: { width: 1000, height: 800 },
  rooms: [
    {
      id: "r",
      title: "Room",
      x: 0,
      y: 0,
      width: 1000,
      height: 800,
      color: "#333333",
    },
  ],
  wallLines: [],
  spawnPoints: [],
  taskAnchors: [],
  sabotagePanels: [],
  vents: [],
  warRoomId: "r",
};

describe("render map objects", () => {
  let ctx;
  let canvas;
  let renderer;

  beforeEach(() => {
    ctx = makeFakeContext();
    canvas = makeFakeCanvas(ctx);
    renderer = new Renderer(canvas);
  });

  it("draws no MAP-OBJECT rectangles when the map has no mapObjects", () => {
    renderer.setMap(TINY_MAP);
    renderer._draw();
    // The renderer always paints the room + minimap chrome — what we care
    // about is that NO mapObject-style fillStyle leaks into the call log
    // when mapObjects is undefined. The known mapObject palette includes
    // "#7c5a3a" (desk), "#1f2937" (monitor), etc. — none of those should
    // appear in the call log if there are no objects.
    const fills = ctx.calls.filter((c) => c[0] === "fillStyle").map((c) => c[1]);
    const objectColours = ["#7c5a3a", "#1f2937", "#1e293b", "#854d0e"];
    for (const colour of objectColours) {
      expect(fills).not.toContain(colour);
    }
  });

  it("draws a rectangle plus stroke per mapObject", () => {
    const map = {
      ...TINY_MAP,
      mapObjects: [
        {
          id: "d1",
          x: 500,
          y: 400,
          width: 80,
          height: 40,
          kind: "desk",
          rotation: 0,
          blocksMovement: true,
        },
      ],
    };
    renderer.setMap(map);
    renderer._draw();
    const fillRects = ctx.calls.filter((c) => c[0] === "fillRect");
    const strokeRects = ctx.calls.filter((c) => c[0] === "strokeRect");
    // Object adds one fillRect + one strokeRect on top of the room.
    expect(fillRects.length).toBeGreaterThanOrEqual(2);
    expect(strokeRects.length).toBeGreaterThanOrEqual(1);
  });

  it("respects rotation 90 by swapping width and height visually", () => {
    const map = {
      ...TINY_MAP,
      mapObjects: [{ id: "d1", x: 500, y: 400, width: 80, height: 40, kind: "desk", rotation: 90 }],
    };
    renderer.setMap(map);
    renderer._draw();
    const fillRects = ctx.calls.filter((c) => c[0] === "fillRect");
    // Find the object's fillRect (will be drawn at center 500,400 with swapped dims 40x80).
    // x = 500 - 40/2 = 480, y = 400 - 80/2 = 360, w = 40, h = 80.
    const objectFill = fillRects.find(
      (c) => c[1] === 480 && c[2] === 360 && c[3] === 40 && c[4] === 80
    );
    expect(objectFill).toBeTruthy();
  });

  it("uses lower opacity for non-blocking decor objects", () => {
    const map = {
      ...TINY_MAP,
      mapObjects: [
        { id: "rug", x: 500, y: 400, width: 100, height: 60, kind: "rug", blocksMovement: false },
      ],
    };
    renderer.setMap(map);
    renderer._draw();
    const alphas = ctx.calls.filter((c) => c[0] === "globalAlpha").map((c) => c[1]);
    // Decor uses 0.5 alpha to look ghost-y; blocks_movement objects stay full.
    expect(alphas).toContain(0.5);
  });

  it("draws a label when the kind is known and the object is large enough", () => {
    const map = {
      ...TINY_MAP,
      mapObjects: [{ id: "d1", x: 500, y: 400, width: 100, height: 60, kind: "monitoring_panel" }],
    };
    renderer.setMap(map);
    renderer._draw();
    const labels = ctx.calls.filter((c) => c[0] === "fillText").map((c) => c[1]);
    expect(labels).toContain("PANEL");
  });

  it("omits label for tiny objects (< 30px in either dimension)", () => {
    const map = {
      ...TINY_MAP,
      mapObjects: [{ id: "tiny", x: 500, y: 400, width: 20, height: 20, kind: "monitor" }],
    };
    renderer.setMap(map);
    renderer._draw();
    const labels = ctx.calls.filter((c) => c[0] === "fillText").map((c) => c[1]);
    expect(labels).not.toContain("MON");
  });

  it("falls back to grey + kind-as-label for unknown kinds", () => {
    const map = {
      ...TINY_MAP,
      mapObjects: [
        { id: "exotic", x: 500, y: 400, width: 100, height: 60, kind: "spaceship_console" },
      ],
    };
    renderer.setMap(map);
    renderer._draw();
    const fills = ctx.calls.filter((c) => c[0] === "fillStyle").map((c) => c[1]);
    const labels = ctx.calls.filter((c) => c[0] === "fillText").map((c) => c[1]);
    expect(fills).toContain("#475569");
    expect(labels).toContain("spaceship_console");
  });
});
