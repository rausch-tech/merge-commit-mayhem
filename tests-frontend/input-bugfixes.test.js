// Regression tests for two UX bugs Sven reported:
//
// 1) Lobby name input swallows E/F/V because the global game keybindings
//    preventDefault() before the input field can accept the keystroke.
// 2) Releasing E during a mini-game cancels it. The user expects E-press
//    to OPEN the modal and have it stay open until the mini-game is solved
//    or explicitly cancelled via the modal's Cancel button.
//
// Both bugs live in static/input.js — these tests pin the fix without
// spinning up a real Renderer/WS layer.

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  attachInput,
  attachRepairInteraction,
  attachTaskInteraction,
  attachVentInteraction,
} from "../static/input.js";

function fakeWs() {
  const sent = [];
  return {
    sent,
    send(type, payload) {
      sent.push({ type, payload });
    },
  };
}

function fakeRenderer() {
  return {
    localPlayerInRange: null,
    localPlayerNearPanel: null,
    localPlayerNearVent: null,
  };
}

function dispatchKey(type, code, target = window) {
  const evt = new KeyboardEvent(type, { code, bubbles: true, cancelable: true });
  target.dispatchEvent(evt);
  return evt;
}

describe("input bugfixes", () => {
  let nameInput;

  beforeEach(() => {
    // Simulate the lobby's <input id="input-name" type="text"> field.
    nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.id = "input-name";
    document.body.appendChild(nameInput);
  });

  afterEach(() => {
    nameInput.remove();
  });

  // --- Bug 1: lobby input swallows game-keys --------------------------------

  it("attachTaskInteraction does NOT preventDefault while a text input is focused", () => {
    const ws = fakeWs();
    const renderer = fakeRenderer();
    renderer.localPlayerInRange = "fix_unit_tests";
    attachTaskInteraction(ws, renderer);

    nameInput.focus();
    const evt = dispatchKey("keydown", "KeyE");

    expect(evt.defaultPrevented).toBe(false);
    expect(ws.sent).toEqual([]);
  });

  it("attachRepairInteraction skips the F-key while typing", () => {
    const ws = fakeWs();
    const renderer = fakeRenderer();
    renderer.localPlayerNearPanel = "lights_out";
    attachRepairInteraction(ws, renderer);

    nameInput.focus();
    const evt = dispatchKey("keydown", "KeyF");

    expect(evt.defaultPrevented).toBe(false);
    expect(ws.sent).toEqual([]);
  });

  it("attachVentInteraction skips the V-key while typing", () => {
    const ws = fakeWs();
    const renderer = fakeRenderer();
    renderer.localPlayerNearVent = { id: "v1", connectedTo: ["v2"] };
    attachVentInteraction(ws, renderer);

    nameInput.focus();
    const evt = dispatchKey("keydown", "KeyV");

    expect(evt.defaultPrevented).toBe(false);
    expect(ws.sent).toEqual([]);
  });

  it("attachInput does NOT send WASD player_input while a text input is focused", () => {
    const ws = fakeWs();
    attachInput(ws);

    nameInput.focus();
    dispatchKey("keydown", "KeyW");

    expect(ws.sent).toEqual([]);
  });

  it("attachTaskInteraction still works when nothing is focused (lobby cleared)", () => {
    const ws = fakeWs();
    const renderer = fakeRenderer();
    renderer.localPlayerInRange = "fix_unit_tests";
    attachTaskInteraction(ws, renderer);

    nameInput.blur();
    document.body.focus();
    dispatchKey("keydown", "KeyE");

    expect(ws.sent[0].type).toBe("task_hold_start");
    expect(ws.sent[0].payload.taskId).toBe("fix_unit_tests");
  });

  // --- Bug 2: keyup must not cancel an open mini-game -----------------------

  it("does not send task_hold_stop on E-keyup while a mini-game modal is open", () => {
    const ws = fakeWs();
    const renderer = fakeRenderer();
    renderer.localPlayerInRange = "fix_unit_tests";
    let modalOpen = false;
    attachTaskInteraction(ws, renderer, () => modalOpen);

    // Press E → start hold.
    dispatchKey("keydown", "KeyE");
    expect(ws.sent.map((m) => m.type)).toEqual(["task_hold_start"]);

    // Server opens the mini-game; modal becomes visible.
    modalOpen = true;

    // Release E → must NOT send task_hold_stop.
    dispatchKey("keyup", "KeyE");
    expect(ws.sent.map((m) => m.type)).toEqual(["task_hold_start"]);
  });

  it("still sends task_hold_stop on E-keyup for hold-E tasks (no mini-game)", () => {
    const ws = fakeWs();
    const renderer = fakeRenderer();
    renderer.localPlayerInRange = "calm_legacy_service";
    attachTaskInteraction(ws, renderer, () => false);

    dispatchKey("keydown", "KeyE");
    dispatchKey("keyup", "KeyE");

    expect(ws.sent.map((m) => m.type)).toEqual(["task_hold_start", "task_hold_stop"]);
  });

  it("a second E-press after a mini-game opens can still target a fresh task", () => {
    const ws = fakeWs();
    const renderer = fakeRenderer();
    renderer.localPlayerInRange = "fix_unit_tests";
    let modalOpen = false;
    attachTaskInteraction(ws, renderer, () => modalOpen);

    // First press: open mini-game.
    dispatchKey("keydown", "KeyE");
    modalOpen = true;
    dispatchKey("keyup", "KeyE"); // suppressed because modal open

    // Modal closes (e.g. user cancelled it), player walks to another task.
    modalOpen = false;
    renderer.localPlayerInRange = "review_pr";
    dispatchKey("keydown", "KeyE");

    const lastSent = ws.sent[ws.sent.length - 1];
    expect(lastSent.type).toBe("task_hold_start");
    expect(lastSent.payload.taskId).toBe("review_pr");
  });
});
