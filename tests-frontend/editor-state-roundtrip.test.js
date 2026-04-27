// Editor-Slice-1 regression: vents + sabotagePanels + taskAnchor.objectType
// must survive the deserialize → serialize roundtrip. Before this slice the
// editor silently dropped them on save, which would obliterate the chaos
// teleport network and the comms_outage / lights_out repair points.

import { describe, expect, it } from "vitest";
import {
  blankMap,
  deserializeMap,
  serializeMap,
  validateMap,
} from "../static/editor/editor-state.js";

const FIXTURE_MAP = {
  name: "fixture",
  size: { width: 4800, height: 3200 },
  rooms: [
    {
      id: "open_space",
      title: "Open Space",
      x: 0,
      y: 0,
      width: 1600,
      height: 1600,
      color: "#3a4560",
    },
  ],
  wallLines: [],
  spawnPoints: [{ x: 100, y: 100 }],
  taskAnchors: [
    { taskId: "fix_unit_tests", x: 400, y: 400, objectType: "qa_terminal" },
    { taskId: "review_pr", x: 1100, y: 1200 },
  ],
  sabotagePanels: [
    { sabotageId: "lights_out", x: 800, y: 2400 },
    { sabotageId: "comms_outage", x: 4000, y: 2400 },
  ],
  vents: [
    { id: "v_open", x: 600, y: 600, connectedTo: ["v_server"] },
    { id: "v_server", x: 800, y: 2000, connectedTo: ["v_open"] },
  ],
  warRoomId: "open_space",
};

describe("editor-state roundtrip preserves all map sections", () => {
  it("blankMap has the new sections present as empty arrays", () => {
    const m = blankMap();
    expect(Array.isArray(m.sabotagePanels)).toBe(true);
    expect(Array.isArray(m.vents)).toBe(true);
    expect(m.sabotagePanels).toHaveLength(0);
    expect(m.vents).toHaveLength(0);
  });

  it("deserialize then serialize keeps vents intact", () => {
    const json = JSON.stringify(FIXTURE_MAP);
    const model = deserializeMap(json);
    const out = JSON.parse(serializeMap(model));
    expect(out.vents).toHaveLength(2);
    expect(out.vents[0]).toEqual({
      id: "v_open",
      x: 600,
      y: 600,
      connectedTo: ["v_server"],
    });
  });

  it("deserialize then serialize keeps sabotage panels intact", () => {
    const json = JSON.stringify(FIXTURE_MAP);
    const model = deserializeMap(json);
    const out = JSON.parse(serializeMap(model));
    expect(out.sabotagePanels).toHaveLength(2);
    expect(out.sabotagePanels[0]).toEqual({
      sabotageId: "lights_out",
      x: 800,
      y: 2400,
    });
  });

  it("deserialize then serialize keeps taskAnchor.objectType when set", () => {
    const json = JSON.stringify(FIXTURE_MAP);
    const model = deserializeMap(json);
    const out = JSON.parse(serializeMap(model));
    const anchor = out.taskAnchors.find((a) => a.taskId === "fix_unit_tests");
    expect(anchor.objectType).toBe("qa_terminal");
  });

  it("deserialize then serialize omits objectType when not set (no key, not null)", () => {
    const json = JSON.stringify(FIXTURE_MAP);
    const model = deserializeMap(json);
    const out = JSON.parse(serializeMap(model));
    const anchor = out.taskAnchors.find((a) => a.taskId === "review_pr");
    expect("objectType" in anchor).toBe(false);
  });

  it("round-trips a map without any of the new sections (legacy compat)", () => {
    const minimalMap = {
      name: "tiny",
      size: { width: 100, height: 100 },
      rooms: [
        {
          id: "r",
          title: "Room",
          x: 0,
          y: 0,
          width: 100,
          height: 100,
          color: "#333333",
        },
      ],
      warRoomId: "r",
    };
    const model = deserializeMap(JSON.stringify(minimalMap));
    const out = JSON.parse(serializeMap(model));
    expect(out.vents).toEqual([]);
    expect(out.sabotagePanels).toEqual([]);
  });
});

describe("validateMap warns about vent / panel issues", () => {
  it("warns when a vent connectedTo references an unknown id", () => {
    const map = deserializeMap(JSON.stringify(FIXTURE_MAP));
    map.vents[0].connectedTo.push("v_ghost");
    const warnings = validateMap(map);
    expect(warnings.some((w) => w.includes("v_ghost"))).toBe(true);
  });

  it("warns when a vent is positioned outside the map", () => {
    const map = deserializeMap(JSON.stringify(FIXTURE_MAP));
    map.vents[0].x = 99999;
    const warnings = validateMap(map);
    expect(warnings.some((w) => w.includes("v_open") && w.includes("ausserhalb"))).toBe(true);
  });

  it("warns when a sabotage panel is positioned outside the map", () => {
    const map = deserializeMap(JSON.stringify(FIXTURE_MAP));
    map.sabotagePanels[0].y = -50;
    const warnings = validateMap(map);
    expect(warnings.some((w) => w.includes("lights_out"))).toBe(true);
  });
});
