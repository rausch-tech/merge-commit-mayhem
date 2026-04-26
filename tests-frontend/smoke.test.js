// Smoke test: every module under static/ loads without throwing.
//
// happy-dom gives us window/document/Image so the modules can run their
// top-level side effects (sprite preloads, etc.) without a real browser.
import { describe, expect, it } from "vitest";

const modules = [
  "../static/audio.js",
  "../static/endscreen.js",
  "../static/eventfeed.js",
  "../static/hud.js",
  "../static/input.js",
  "../static/meetings.js",
  "../static/menu.js",
  "../static/render.js",
  "../static/report.js",
  "../static/sabotages.js",
  "../static/sprites.js",
  "../static/takedown.js",
  "../static/tasks.js",
  "../static/ws.js",
  "../static/minigames/base.js",
  "../static/minigames/registry.js",
  "../static/minigames/test_suite_repair.js",
];

describe("static module smoke", () => {
  for (const path of modules) {
    it(`imports ${path}`, async () => {
      const mod = await import(path);
      expect(mod).toBeDefined();
    });
  }
});
