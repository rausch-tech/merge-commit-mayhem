import { beforeEach, describe, expect, it } from "vitest";

import { EventFeed } from "../static/eventfeed.js";

describe("EventFeed", () => {
  let root;
  beforeEach(() => {
    document.body.innerHTML = '<aside id="event-feed"></aside>';
    root = document.getElementById("event-feed");
  });

  it("renders an empty-state list when given no events", () => {
    const feed = new EventFeed(root);
    feed.render([]);
    // EventFeed paints its own empty placeholder rather than leaving the
    // sidebar blank; we just want to verify it does not throw.
    expect(root.querySelectorAll("li").length).toBeGreaterThan(0);
  });

  it("renders one row per event", () => {
    const feed = new EventFeed(root);
    feed.render([
      { seq: 1, severity: "info", message: "Release-Fenster offen." },
      { seq: 2, severity: "warn", message: "Pipeline instabil." },
      { seq: 3, severity: "danger", message: "PagerDuty-Storm!" },
    ]);
    const rows = [...root.querySelectorAll("li")].filter((li) => /event-row/.test(li.className));
    expect(rows.length).toBe(3);
  });

  it("preserves order: latest events render last", () => {
    const feed = new EventFeed(root);
    feed.render([
      { seq: 1, severity: "info", message: "first" },
      { seq: 2, severity: "info", message: "second" },
    ]);
    const items = [...root.querySelectorAll("li")].map((li) => li.textContent);
    expect(items[0]).toContain("first");
    expect(items[1]).toContain("second");
  });
});
