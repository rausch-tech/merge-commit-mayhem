// Tier 3.1 — Mini-Game modal wrapper.
//
// Subscribes to mini_game_started / mini_game_state / mini_game_completed
// frames, looks up the renderer for the active miniGameId and forwards
// lifecycle calls. Plugins write to an injected container and never touch
// the modal chrome themselves.

import { MINI_GAME_RENDERERS } from "./registry.js";

export class MiniGameModal {
  constructor(rootEl, ws) {
    this.root = rootEl;
    this.titleEl = rootEl.querySelector("#mini-game-title");
    this.bodyEl = rootEl.querySelector("#mini-game-body");
    this.cancelBtn = rootEl.querySelector("#mini-game-cancel-btn");
    this.ws = ws;
    this.activeRenderer = null;
    this.activeTaskId = null;

    this.cancelBtn.addEventListener("click", () => this._cancel());
  }

  isOpen() {
    return !this.root.classList.contains("hidden");
  }

  /** Plugins call sendInput(action, params); we wrap with the WS envelope. */
  _makeSender() {
    return (action, params = {}) => {
      this.ws.send("mini_game_input", { action, params });
    };
  }

  onStarted(payload) {
    const RendererCls = MINI_GAME_RENDERERS[payload.miniGameId];
    if (!RendererCls) {
      console.warn(`No renderer for mini-game ${payload.miniGameId}`);
      this._close();
      return;
    }
    this.titleEl.textContent = payload.title || payload.miniGameId;
    this.bodyEl.innerHTML = "";
    this.activeTaskId = payload.taskId;
    this.activeRenderer = new RendererCls(this.bodyEl, this._makeSender());
    this.activeRenderer.onStart?.(payload.view);
    this.root.classList.remove("hidden");
  }

  onState(payload) {
    if (!this.activeRenderer || payload.taskId !== this.activeTaskId) return;
    this.activeRenderer.onUpdate?.(payload.view);
  }

  onCompleted(payload) {
    if (this.activeRenderer && payload.taskId === this.activeTaskId) {
      this.activeRenderer.onComplete?.(payload.success, payload.reason);
    }
    this._close();
  }

  _cancel() {
    if (!this.activeTaskId) return;
    // Tier 3.1: cancel reuses task_hold_stop (server checks if a mini-game is
    // active for this player and routes accordingly).
    this.ws.send("task_hold_stop", { taskId: this.activeTaskId });
  }

  _close() {
    this.root.classList.add("hidden");
    this.activeRenderer = null;
    this.activeTaskId = null;
    this.bodyEl.innerHTML = "";
  }
}
