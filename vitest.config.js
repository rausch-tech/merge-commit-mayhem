// Tier 0.3 — Frontend smoke tests. Runs every static/*.js module under
// happy-dom so canvas/document/window are available without spinning up a
// real browser.
export default {
  test: {
    environment: "happy-dom",
    include: ["tests-frontend/**/*.test.js"],
    globals: false,
    reporters: ["default"],
  },
};
