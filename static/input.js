// WASD + Arrow Keys → {up,down,left,right}. Edge-triggered: only send when
// the state actually changes. Reset on window blur to avoid stuck keys.

const KEY_MAP = {
  KeyW: "up", ArrowUp: "up",
  KeyS: "down", ArrowDown: "down",
  KeyA: "left", ArrowLeft: "left",
  KeyD: "right", ArrowRight: "right",
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
