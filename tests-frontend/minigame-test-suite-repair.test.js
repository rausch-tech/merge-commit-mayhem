import { beforeEach, describe, expect, it, vi } from "vitest";

import { TestSuiteRepairRenderer } from "../static/minigames/test_suite_repair.js";

const VIEW = {
  totalTests: 5,
  nextOrder: 1,
  tests: [
    { id: "t0", label: "test_alpha", order: 3, status: "broken" },
    { id: "t1", label: "test_beta", order: 1, status: "broken" },
    { id: "t2", label: "test_gamma", order: 2, status: "broken" },
    { id: "t3", label: "test_delta", order: 4, status: "broken" },
    { id: "t4", label: "test_epsilon", order: 5, status: "broken" },
  ],
};

describe("TestSuiteRepairRenderer", () => {
  let container;
  let send;
  let renderer;

  beforeEach(() => {
    document.body.innerHTML = '<div id="ct"></div>';
    container = document.getElementById("ct");
    send = vi.fn();
    renderer = new TestSuiteRepairRenderer(container, send);
  });

  it("onStart renders one row per test plus a progress line", () => {
    renderer.onStart(VIEW);
    const rows = container.querySelectorAll(".mini-game-test");
    expect(rows.length).toBe(5);
    const progressLines = container.querySelectorAll(".mini-game-progress");
    expect(progressLines[1].textContent).toMatch(/#1/);
  });

  it("clicking a non-fixed row sends mini_game click with the test id", () => {
    renderer.onStart(VIEW);
    const target = container.querySelector(".mini-game-test"); // first row
    target.click();
    expect(send).toHaveBeenCalledWith("click", expect.objectContaining({ testId: "t0" }));
  });

  it("fixed rows render with .fixed and ignore clicks", () => {
    const partial = {
      ...VIEW,
      nextOrder: 2,
      tests: VIEW.tests.map((t) => (t.order === 1 ? { ...t, status: "fixed" } : t)),
    };
    renderer.onStart(partial);
    const fixed = container.querySelector(".mini-game-test.fixed");
    expect(fixed).toBeTruthy();
    fixed.click();
    expect(send).not.toHaveBeenCalled();
  });

  it("onUpdate replaces the list with the new view", () => {
    renderer.onStart(VIEW);
    const advanced = { ...VIEW, nextOrder: 3 };
    renderer.onUpdate(advanced);
    const progressLines = container.querySelectorAll(".mini-game-progress");
    expect(progressLines[1].textContent).toMatch(/#3/);
  });
});
