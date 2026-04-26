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

export function attachInput(wsClient) {
  const state = { up: false, down: false, left: false, right: false };

  const send = () => wsClient.send("player_input", { ...state });

  const setAxis = (axis, value) => {
    if (state[axis] === value) return false;
    state[axis] = value;
    return true;
  };

  window.addEventListener("keydown", (e) => {
    const axis = KEY_MAP[e.code];
    if (!axis) return;
    if (e.repeat) return;
    if (setAxis(axis, true)) send();
  });

  window.addEventListener("keyup", (e) => {
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
 */
export function attachTaskInteraction(wsClient, renderer) {
  let currentTaskId = null;

  const tryStart = () => {
    if (currentTaskId !== null) return; // already holding
    const taskId = renderer.localPlayerInRange;
    if (!taskId) return;
    currentTaskId = taskId;
    wsClient.send("task_hold_start", { taskId });
  };

  const stop = () => {
    if (currentTaskId === null) return;
    const taskId = currentTaskId;
    currentTaskId = null;
    wsClient.send("task_hold_stop", { taskId });
  };

  window.addEventListener("keydown", (e) => {
    if (e.code !== "KeyE" && e.code !== "Space") return;
    if (e.repeat) return;
    e.preventDefault();
    tryStart();
  });

  window.addEventListener("keyup", (e) => {
    if (e.code !== "KeyE" && e.code !== "Space") return;
    e.preventDefault();
    stop();
  });

  window.addEventListener("blur", stop);
}

/**
 * F-key triggers a one-shot repair on the sabotage panel the local player is
 * currently next to. The renderer exposes that target via
 * `localPlayerNearPanel` (set during _draw), so the input layer stays free of
 * world-state knowledge.
 */
export function attachRepairInteraction(wsClient, renderer) {
  window.addEventListener("keydown", (e) => {
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
