import { applySprite } from "./sprites.js";

const TITLE_LABELS = {
  ci_cd_red: "CI/CD Rot",
  coffee_outage: "Kaffee leer",
  mandatory_meeting: "Mandatory Meeting",
  merge_conflict_storm: "Merge Conflict Storm",
  fake_customer_request: "Fake Customer Request",
  flaky_tests: "Flaky Tests",
  lights_out: "PagerDuty-Storm",
  comms_outage: "Slack-Down",
};

export class SabotagePanel {
  constructor(rootEl, wsClient) {
    this.root = rootEl;
    this.ws = wsClient;
    this.buttons = new Map(); // sabotage_id -> { btn, cdEl, fillEl }
    this.availableIds = [];
    this.totalCooldowns = {}; // sabotage_id -> total seconds (for ring fraction)
    this.consoleAvailable = true; // Tier 2.7: defaults true so legacy maps without consoles still work
  }

  /**
   * Tier 2.7: when the local chaos player is in reach of a Sabotage-Console
   * (or the map has none), buttons are tappable. Otherwise we show them
   * disabled with a hint, so the player doesn't waste time on rejected taps.
   */
  updateConsoleAvailability(available) {
    const next = !!available;
    if (this.consoleAvailable === next) return;
    this.consoleAvailable = next;
    this.root.classList.toggle("sabotage-console-out-of-range", !next);
    // Force a refresh of all button disabled states from the latest known
    // sabotage snapshot — we cache it on the entry during update.
    for (const entry of this.buttons.values()) {
      this._applyDisabledState(entry);
    }
  }

  /**
   * Show or hide the panel based on the chaos role's availableSabotages.
   * Builds the button DOM the first time it's enabled.
   */
  setAvailable(ids) {
    this.availableIds = ids || [];
    if (this.availableIds.length === 0) {
      this.root.classList.add("hidden");
      return;
    }
    this.root.classList.remove("hidden");
    if (this.buttons.size === 0) this._buildButtons();
  }

  _buildButtons() {
    this.root.innerHTML = "";
    const heading = document.createElement("h3");
    heading.textContent = "Sabotage";
    this.root.appendChild(heading);
    const grid = document.createElement("div");
    grid.className = "sabotage-grid";
    for (const id of this.availableIds) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "sabotage-btn sabotage-btn-icon";
      btn.dataset.sabotageId = id;
      // Sprite icon as a <span> with background-image inside the button.
      const iconEl = document.createElement("span");
      iconEl.className = "sabotage-icon";
      applySprite(iconEl, `sabotage_${id}`);
      const fillEl = document.createElement("span");
      fillEl.className = "sabotage-cooldown-fill";
      const labelEl = document.createElement("span");
      labelEl.className = "sabotage-label";
      labelEl.textContent = TITLE_LABELS[id] || id;
      const cdEl = document.createElement("span");
      cdEl.className = "sabotage-cooldown";
      cdEl.textContent = "";
      btn.appendChild(fillEl);
      btn.appendChild(iconEl);
      btn.appendChild(labelEl);
      btn.appendChild(cdEl);
      btn.addEventListener("click", () => {
        if (btn.disabled) return;
        this.ws.send("trigger_sabotage", { sabotageId: id });
      });
      grid.appendChild(btn);
      this.buttons.set(id, { btn, cdEl, fillEl });
    }
    this.root.appendChild(grid);
  }

  /**
   * Update each button from a fresh game_state.payload.sabotages array.
   * Buttons not in availableIds are ignored. When `disabledByOwnDeath` is true
   * (Tier 2.6 spectator-mode), every button is force-disabled regardless of
   * cooldown — ghosts cannot sabotage even if they were chaos. When
   * `disabledByCommsDown` is true (Tier 2.5), every button is also disabled
   * except `comms_outage` itself, since the server gates other sabotages.
   */
  updateFromGameState(sabotages, opts = {}) {
    if (!sabotages || this.availableIds.length === 0) return;
    this._lastDisabledByOwnDeath = !!opts.disabledByOwnDeath;
    this._lastDisabledByCommsDown = !!opts.disabledByCommsDown;
    for (const sab of sabotages) {
      const entry = this.buttons.get(sab.id);
      if (!entry) continue;
      const cd = Math.max(0, sab.cooldownRemaining || 0);
      const total = this._cooldownTotal(sab.id, cd);
      entry.lastCooldown = cd;
      entry.lastSabotageId = sab.id;
      this._applyDisabledState(entry);
      entry.cdEl.textContent = cd > 0 ? `${Math.ceil(cd)}s` : "";
      // Fill height represents ratio of remaining to total cooldown.
      const ratio = total > 0 && cd > 0 ? Math.min(1, cd / total) : 0;
      entry.fillEl.style.height = `${ratio * 100}%`;
      // Active state visual cue.
      entry.btn.classList.toggle("sabotage-active", !!sab.active);
    }
  }

  _applyDisabledState(entry) {
    const cd = entry.lastCooldown || 0;
    const blockedByComms =
      !!this._lastDisabledByCommsDown && entry.lastSabotageId !== "comms_outage";
    const blockedByConsole = !this.consoleAvailable;
    entry.btn.disabled =
      cd > 0 || !!this._lastDisabledByOwnDeath || blockedByComms || blockedByConsole;
  }

  _cooldownTotal(id, currentCd) {
    // Server doesn't send the original total. Cache the highest cd we've seen
    // (which is the moment of trigger) and use that as the ratio denominator.
    if (currentCd > (this.totalCooldowns[id] || 0)) {
      this.totalCooldowns[id] = currentCd;
    }
    return this.totalCooldowns[id] || 1;
  }
}
