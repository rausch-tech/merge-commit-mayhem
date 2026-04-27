// Editor-Slice-2: Kind library is the single source of truth for which
// MapObject kinds the editor offers. The catalogue must include every kind
// the placeholder palette in render.js handles so the editor and the
// browser game agree on what placement options exist.
//
// Post-2026-04-27: kinds come from maps/kinds.json via /api/kinds. Tests
// load the on-disk file and seed the editor facade synchronously so they
// don't need a real /api/kinds endpoint.

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { beforeAll, describe, expect, it } from "vitest";
import {
  KIND_BY_NAME,
  KIND_CATALOGUE,
  KIND_CATEGORIES,
  _seedFromRegistryForTests,
} from "../static/editor/editor-kinds.js";

beforeAll(() => {
  const here = dirname(fileURLToPath(import.meta.url));
  const path = resolve(here, "../maps/kinds.json");
  const registry = JSON.parse(readFileSync(path, "utf-8"));
  _seedFromRegistryForTests(registry);
});

describe("KIND_CATALOGUE", () => {
  it("has at least the documented vocabulary entries", () => {
    // Sanity floor: docs/maps.md ships a 24-row catalogue. We don't assert an
    // exact count here so future additions don't break the test, but every
    // map area should be represented.
    expect(KIND_CATALOGUE.length).toBeGreaterThanOrEqual(20);
  });

  it("includes the canonical office furniture", () => {
    const required = [
      "desk",
      "desk_large",
      "chair_desk",
      "monitor",
      "server_rack",
      "monitoring_panel",
      "meeting_table",
      "kitchen_counter",
      "fridge",
      "coffee_machine",
      "plant_cactus",
      "crate",
    ];
    for (const kind of required) {
      expect(KIND_BY_NAME.has(kind), `missing kind: ${kind}`).toBe(true);
    }
  });

  it("every entry has the editor-required fields", () => {
    for (const entry of KIND_CATALOGUE) {
      expect(typeof entry.kind).toBe("string");
      expect(entry.kind.length).toBeGreaterThan(0);
      expect(typeof entry.label).toBe("string");
      expect(typeof entry.category).toBe("string");
      expect(typeof entry.width).toBe("number");
      expect(typeof entry.height).toBe("number");
      expect(entry.width).toBeGreaterThan(0);
      expect(entry.height).toBeGreaterThan(0);
      expect(typeof entry.blocksMovement).toBe("boolean");
      expect(typeof entry.fill).toBe("string");
      expect(entry.fill).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });

  it("KIND_CATEGORIES lists each category exactly once and in catalogue order", () => {
    const seenInOrder = [];
    const seen = new Set();
    for (const e of KIND_CATALOGUE) {
      if (seen.has(e.category)) continue;
      seen.add(e.category);
      seenInOrder.push(e.category);
    }
    expect(KIND_CATEGORIES).toEqual(seenInOrder);
  });

  it("kind names are unique", () => {
    const seen = new Set();
    for (const entry of KIND_CATALOGUE) {
      expect(seen.has(entry.kind), `duplicate kind: ${entry.kind}`).toBe(false);
      seen.add(entry.kind);
    }
  });
});
