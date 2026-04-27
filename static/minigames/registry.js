// Tier 3.1 — Mini-Game renderer registry.
//
// Each mini-game id is mapped to a Renderer class. The MiniGameModal looks
// up the class on mini_game_started and delegates lifecycle callbacks. New
// mini-games are wired here and have no other touch point in main.js.

import { CablePairingRenderer } from "./cable_pairing.js";
import { CoffeePourRenderer } from "./coffee_pour.js";
import { DiffReviewRenderer } from "./diff_review.js";
import { LogFilterRenderer } from "./log_filter.js";
import { ReleaseNotesRenderer } from "./release_notes.js";
import { SprintTrimRenderer } from "./sprint_trim.js";
import { StabilityBalanceRenderer } from "./stability_balance.js";
import { TestSuiteRepairRenderer } from "./test_suite_repair.js";

export const MINI_GAME_RENDERERS = {
  test_suite_repair: TestSuiteRepairRenderer,
  cable_pairing: CablePairingRenderer,
  coffee_pour: CoffeePourRenderer,
  log_filter: LogFilterRenderer,
  sprint_trim: SprintTrimRenderer,
  diff_review: DiffReviewRenderer,
  stability_balance: StabilityBalanceRenderer,
  release_notes: ReleaseNotesRenderer,
};
