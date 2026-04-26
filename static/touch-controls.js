// Quick-hack mobile touch controls.
//
// Virtual joystick (left) → drives the same WASD axes as keyboard input,
// piggy-backing on the existing player_input WS message. Four action buttons
// (right) handle Task/Repair/Vent/Menu. We do NOT replace the keyboard
// handlers; we add a parallel input source. Server is oblivious.
//
// Visibility is gated by a CSS @media (pointer: coarse) — desktops never see
// the overlay.

const JOYSTICK_DEAD_ZONE = 0.18; // 0..1; below this the axis is considered idle

export class TouchControls {
  constructor(rootEl, callbacks) {
    this.root = rootEl;
    this.callbacks = callbacks; // { onMove(state), onTaskDown, onTaskUp, onRepair, onVent, onMenu }
    this.joystickEl = rootEl.querySelector("#touch-joystick");
    this.knobEl = rootEl.querySelector("#touch-joystick-knob");
    this.taskBtn = rootEl.querySelector("#touch-btn-task");
    this.repairBtn = rootEl.querySelector("#touch-btn-repair");
    this.ventBtn = rootEl.querySelector("#touch-btn-vent");
    this.menuBtn = rootEl.querySelector("#touch-btn-menu");

    this.activeJoyTouchId = null;
    this.lastAxisState = { up: false, down: false, left: false, right: false };

    this._wireJoystick();
    this._wireActionButtons();
  }

  _wireJoystick() {
    const onStart = (e) => {
      if (this.activeJoyTouchId !== null) return;
      const t = e.changedTouches[0];
      this.activeJoyTouchId = t.identifier;
      this._updateKnob(t.clientX, t.clientY);
      e.preventDefault();
    };
    const onMove = (e) => {
      for (const t of e.changedTouches) {
        if (t.identifier !== this.activeJoyTouchId) continue;
        this._updateKnob(t.clientX, t.clientY);
        e.preventDefault();
        return;
      }
    };
    const onEnd = (e) => {
      for (const t of e.changedTouches) {
        if (t.identifier !== this.activeJoyTouchId) continue;
        this.activeJoyTouchId = null;
        this._resetKnob();
        e.preventDefault();
        return;
      }
    };
    this.joystickEl.addEventListener("touchstart", onStart, { passive: false });
    this.joystickEl.addEventListener("touchmove", onMove, { passive: false });
    this.joystickEl.addEventListener("touchend", onEnd, { passive: false });
    this.joystickEl.addEventListener("touchcancel", onEnd, { passive: false });
  }

  _updateKnob(touchX, touchY) {
    const rect = this.joystickEl.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const r = rect.width / 2;
    let dx = (touchX - cx) / r;
    let dy = (touchY - cy) / r;
    const len = Math.hypot(dx, dy);
    if (len > 1) {
      dx /= len;
      dy /= len;
    }
    // Position knob visually.
    this.knobEl.style.transform = `translate(${dx * r * 0.65}px, ${dy * r * 0.65}px)`;
    // Map to discrete axes — same shape as the keyboard input_state.
    const state = {
      up: dy < -JOYSTICK_DEAD_ZONE,
      down: dy > JOYSTICK_DEAD_ZONE,
      left: dx < -JOYSTICK_DEAD_ZONE,
      right: dx > JOYSTICK_DEAD_ZONE,
    };
    this._emitAxis(state);
  }

  _resetKnob() {
    this.knobEl.style.transform = "";
    this._emitAxis({ up: false, down: false, left: false, right: false });
  }

  _emitAxis(state) {
    const prev = this.lastAxisState;
    if (
      prev.up === state.up &&
      prev.down === state.down &&
      prev.left === state.left &&
      prev.right === state.right
    ) {
      return;
    }
    this.lastAxisState = state;
    this.callbacks.onMove?.(state);
  }

  _wireActionButtons() {
    // Task button mirrors keyboard E: hold-down/hold-up.
    this.taskBtn.addEventListener(
      "touchstart",
      (e) => {
        e.preventDefault();
        this.callbacks.onTaskDown?.();
      },
      { passive: false }
    );
    this.taskBtn.addEventListener(
      "touchend",
      (e) => {
        e.preventDefault();
        this.callbacks.onTaskUp?.();
      },
      { passive: false }
    );
    this.taskBtn.addEventListener(
      "touchcancel",
      (e) => {
        e.preventDefault();
        this.callbacks.onTaskUp?.();
      },
      { passive: false }
    );

    // Repair / Vent / Menu = single-tap.
    const tap = (btn, cb) => {
      btn.addEventListener(
        "touchstart",
        (e) => {
          e.preventDefault();
          cb?.();
        },
        { passive: false }
      );
    };
    tap(this.repairBtn, this.callbacks.onRepair);
    tap(this.ventBtn, this.callbacks.onVent);
    tap(this.menuBtn, this.callbacks.onMenu);
  }
}
