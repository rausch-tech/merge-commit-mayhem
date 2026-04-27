// Editor-Slice-5: undo/redo. Snapshots the serialized map before each
// mutation; undo() restores the latest snapshot and pushes the current
// state onto the redo stack. Capped depth so a long session doesn't
// grow unbounded.

import { beforeEach, describe, expect, it } from "vitest";
import { History } from "../static/editor/editor-history.js";
import { blankMap } from "../static/editor/editor-state.js";

function makeMap(overrides = {}) {
  return { ...blankMap(), ...overrides };
}

describe("History", () => {
  let history;
  beforeEach(() => {
    history = new History({ maxDepth: 5 });
  });

  it("starts empty — nothing to undo or redo", () => {
    expect(history.canUndo()).toBe(false);
    expect(history.canRedo()).toBe(false);
    expect(history.size()).toBe(0);
  });

  it("push adds a snapshot to the past stack", () => {
    history.push(makeMap({ name: "first" }));
    expect(history.canUndo()).toBe(true);
    expect(history.size()).toBe(1);
  });

  it("undo restores the snapshot and moves it to redo", () => {
    const a = makeMap({ name: "a" });
    history.push(a);
    const b = makeMap({ name: "b" });
    const restored = history.undo(b);
    expect(restored.name).toBe("a");
    expect(history.canRedo()).toBe(true);
    expect(history.canUndo()).toBe(false);
  });

  it("redo restores the future snapshot and moves it back to past", () => {
    const a = makeMap({ name: "a" });
    history.push(a);
    const b = makeMap({ name: "b" });
    history.undo(b); // a is back, b is in future
    const c = makeMap({ name: "a" }); // current state == "a"
    const redone = history.redo(c);
    expect(redone.name).toBe("b");
    expect(history.canUndo()).toBe(true);
    expect(history.canRedo()).toBe(false);
  });

  it("dedups consecutive identical snapshots — drag jitter doesn't bloat history", () => {
    const m = makeMap({ name: "x" });
    history.push(m);
    history.push(m);
    history.push(m);
    expect(history.size()).toBe(1);
  });

  it("caps depth at maxDepth — oldest snapshot is dropped", () => {
    for (let i = 0; i < 7; i++) {
      history.push(makeMap({ name: `step-${i}` }));
    }
    expect(history.size()).toBe(5);
  });

  it("a fresh push after undo clears the redo stack", () => {
    history.push(makeMap({ name: "a" }));
    history.undo(makeMap({ name: "b" }));
    expect(history.canRedo()).toBe(true);
    history.push(makeMap({ name: "c" })); // diverges
    expect(history.canRedo()).toBe(false);
  });

  it("undo() on empty history returns null", () => {
    const out = history.undo(makeMap());
    expect(out).toBeNull();
  });

  it("redo() on empty future returns null", () => {
    const out = history.redo(makeMap());
    expect(out).toBeNull();
  });

  it("clear() empties both stacks", () => {
    history.push(makeMap({ name: "a" }));
    history.undo(makeMap({ name: "b" }));
    history.clear();
    expect(history.canUndo()).toBe(false);
    expect(history.canRedo()).toBe(false);
  });

  it("a full round-trip through undo + redo preserves arbitrary map fields", () => {
    const original = makeMap({
      name: "original",
      rooms: [{ id: "r1", title: "R1", x: 0, y: 0, width: 100, height: 100, color: "#000000" }],
    });
    history.push(original);
    const mutated = makeMap({
      name: "mutated",
      rooms: [{ id: "r2", title: "R2", x: 50, y: 50, width: 200, height: 200, color: "#ffffff" }],
    });
    const undone = history.undo(mutated);
    expect(undone.name).toBe("original");
    expect(undone.rooms[0].id).toBe("r1");
    const redone = history.redo(undone);
    expect(redone.name).toBe("mutated");
    expect(redone.rooms[0].id).toBe("r2");
  });
});
