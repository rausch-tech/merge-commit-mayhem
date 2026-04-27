// WASD + Arrow Keys → {up,down,left,right}. Edge-triggered: only send when
// the state actually changes. Reset on window blur to avoid stuck keys.

const KEY_MAP = {
  KeyW: "up",
  ArrowUp: "up",
  KeyS: "down",
  ArrowDown: "down",
  KeyA: "left",
  ArrowLeft: "left",
  KeyD: "right",
  ArrowRight: "right",
};

/**
 * True when the user is typing into a text-input-like control. Prevents the
 * global game keybindings (WASD/E/F/V) from swallowing characters or moving
 * the player while the lobby name input or any other text field is focused.
 */
function isTypingInInput() {
  const ae = document.activeElement;
  if (!ae) return false;
  if (ae.isContentEditable) return true;
  const tag = ae.tagName;
  if (tag === "INPUT") {
    // Allow keys to pass through for non-text inputs (checkbox, button, range,
    // etc.) so radios + buttons still respond to space/enter normally.
    const t = (ae.type || "text").toLowerCase();
    const TEXT_TYPES = new Set(["text", "search", "email", "url", "tel", "password", "number"]);
    return TEXT_TYPES.has(t);
  }
  return tag === "TEXTAREA";
}

export function attachInput(wsClient) {
  const state = { up: false, down: false, left: false, right: false };

  const send = () => wsClient.send("player_input", { ...state });

  const setAxis = (axis, value) => {
    if (state[axis] === value) return false;
    state[axis] = value;
    return true;
  };

  window.addEventListener("keydown", (e) => {
    if (isTypingInInput()) return;
    const axis = KEY_MAP[e.code];
    if (!axis) return;
    if (e.repeat) return;
    if (setAxis(axis, true)) send();
  });

  window.addEventListener("keyup", (e) => {
    if (isTypingInInput()) return;
    const axis = KEY_MAP[e.code];
    if (!axis) return;
    if (setAxis(axis, false)) send();
  });

  window.addEventListener("blur", () => {
    let changed = false;
    for (const axis of ["up", "down", "left", "right"]) {
      if (state[axis]) {
        state[axis] = false;
        changed = true;
      }
    }
    if (changed) send();
  });
}

/**
 * Wire the E-key (and Space as a friendly alternative) to task hold messages.
 * Pulls the currently in-range task id from the renderer; the server
 * authoritatively decides whether the start is accepted (proximity, cooldown).
 *
 * ``isMiniGameOpen`` is an optional callback that returns true when a
 * mini-game modal is currently open. While open, the keyup → ``task_hold_stop``
 * path is suppressed: a mini-game has its own lifecycle (input-driven, modal
 * Cancel button) and must not be cancelled just because the player let go of
 * E. Hold-E tasks without a mini-game keep the original press-and-hold
 * semantics.
 */
export function attachTaskInteraction(wsClient, renderer, isMiniGameOpen = null) {
  let currentTaskId = null;

  const tryStart = () => {
    if (currentTaskId !== null) return; // already holding
    const taskId = renderer.localPlayerInRange;
    if (!taskId) return;
    currentTaskId = taskId;
    wsClient.send("task_hold_start", { taskId });
  };

  const stop = ({ force = false } = {}) => {
    if (currentTaskId === null) return;
    if (!force && isMiniGameOpen && isMiniGameOpen()) {
      // Mini-game still running — let it finish or be cancelled via the
      // modal's Cancel button. Just forget the local hold-tracker so the
      // next E-press can target a different task once the modal closes.
      currentTaskId = null;
      return;
    }
    const taskId = currentTaskId;
    currentTaskId = null;
    wsClient.send("task_hold_stop", { taskId });
  };

  window.addEventListener("keydown", (e) => {
    if (isTypingInInput()) return;
    if (e.code !== "KeyE" && e.code !== "Space") return;
    if (e.repeat) return;
    e.preventDefault();
    tryStart();
  });

  window.addEventListener("keyup", (e) => {
    if (isTypingInInput()) return;
    if (e.code !== "KeyE" && e.code !== "Space") return;
    e.preventDefault();
    stop();
  });

  // Window blur is treated as a real abort: chrome-tab-switch shouldn't
  // leave a hold-E task progressing forever. Mini-games are still safe
  // because the server cancels them on disconnect anyway.
  window.addEventListener("blur", () => stop({ force: true }));
}

/**
 * F-key triggers a one-shot repair on the sabotage panel the local player is
 * currently next to. The renderer exposes that target via
 * `localPlayerNearPanel` (set during _draw), so the input layer stays free of
 * world-state knowledge.
 */
export function attachRepairInteraction(wsClient, renderer) {
  window.addEventListener("keydown", (e) => {
    if (isTypingInInput()) return;
    if (e.code !== "KeyF") return;
    if (e.repeat) return;
    const sabotageId = renderer.localPlayerNearPanel;
    if (!sabotageId) return;
    e.preventDefault();
    wsClient.send("repair_sabotage", { sabotageId });
  });
}

/**
 * V-key vents (Tier 2.3). When the local chaos player is at a vent, V cycles
 * through the connected destinations on each press. Server validates source
 * proximity + target connectivity, so the cycle index is purely client-side
 * convenience.
 */
export function attachVentInteraction(wsClient, renderer) {
  let lastSourceId = null;
  let cycleIndex = 0;
  window.addEventListener("keydown", (e) => {
    if (isTypingInInput()) return;
    if (e.code !== "KeyV") return;
    if (e.repeat) return;
    const vent = renderer.localPlayerNearVent;
    if (!vent || !vent.connectedTo || vent.connectedTo.length === 0) return;
    e.preventDefault();
    if (vent.id !== lastSourceId) {
      lastSourceId = vent.id;
      cycleIndex = 0;
    }
    const targetVentId = vent.connectedTo[cycleIndex % vent.connectedTo.length];
    cycleIndex = (cycleIndex + 1) % vent.connectedTo.length;
    wsClient.send("use_vent", { targetVentId });
  });
}
