// Tier 3.1 — Mini-Game renderer registry.
//
// Each mini-game id is mapped to a Renderer class. The MiniGameModal looks
// up the class on mini_game_started and delegates lifecycle callbacks. New
// mini-games are wired here and have no other touch point in main.js.

import { TestSuiteRepairRenderer } from "./test_suite_repair.js";

export const MINI_GAME_RENDERERS = {
  test_suite_repair: TestSuiteRepairRenderer,
};
