// Undo/redo for the MCM Map-Editor.
//
// We snapshot the entire serialized map before every mutation. JSON
// serialization is fast enough for editor-scale maps (a few KB) and gives
// us a deep-clone for free. The history is bounded so a long session
// doesn't grow the heap unbounded.

import { deserializeMap, serializeMap } from "/static/editor/editor-state.js";

const DEFAULT_MAX_DEPTH = 100;

export class History {
  constructor({ maxDepth = DEFAULT_MAX_DEPTH } = {}) {
    this.maxDepth = maxDepth;
    this.past = []; // serialized snapshots, oldest first
    this.future = []; // redo stack
  }

  /** Number of states the user can step back to. */
  size() {
    return this.past.length;
  }

  redoSize() {
    return this.future.length;
  }

  canUndo() {
    return this.past.length > 0;
  }

  canRedo() {
    return this.future.length > 0;
  }

  /** Drop all undo + redo state. Used when the user loads a fresh map so
   *  Undo can't accidentally roll the new map back into the previous one. */
  reset() {
    this.past = [];
    this.future = [];
  }

  /**
   * Capture the current state. Call this BEFORE applying a mutation —
   * undo() then restores this snapshot. Pushing also clears the redo
   * stack, since a new branch invalidates the previous future.
   */
  push(map) {
    const snap = serializeMap(map);
    if (this.past.length > 0 && this.past[this.past.length - 1] === snap) {
      // No-op mutations (e.g. drag below threshold) shouldn't bloat history.
      return;
    }
    this.past.push(snap);
    if (this.past.length > this.maxDepth) {
      this.past.shift();
    }
    this.future = [];
  }

  /** Pop the latest snapshot, store the current state for redo, and return it. */
  undo(currentMap) {
    if (!this.canUndo()) return null;
    const last = this.past.pop();
    this.future.push(serializeMap(currentMap));
    if (this.future.length > this.maxDepth) {
      this.future.shift();
    }
    return deserializeMap(last);
  }

  /** Reverse of undo. */
  redo(currentMap) {
    if (!this.canRedo()) return null;
    const next = this.future.pop();
    this.past.push(serializeMap(currentMap));
    if (this.past.length > this.maxDepth) {
      this.past.shift();
    }
    return deserializeMap(next);
  }

  clear() {
    this.past = [];
    this.future = [];
  }
}
