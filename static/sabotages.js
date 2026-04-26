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
    this.buttons = new Map(); // sabotage_id -> { btn, cdEl, fillEl, hintEl }
    this.availableIds = [];
    this.totalCooldowns = {}; // sabotage_id -> total seconds (for ring fraction)
    // Tier 2.7 rework: per-sabotage proximity. Map of sabotage_id → bool.
    // Defaults true so legacy maps without typed anchors stay tappable.
    this.objectAvailability = {};
    // Hint text per sabotage from server payload ("CI-Konsole im Server Room")
    this.objectHints = {};
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
      const hintEl = document.createElement("span");
      hintEl.className = "sabotage-hint";
      hintEl.textContent = "";
      btn.appendChild(fillEl);
      btn.appendChild(iconEl);
      btn.appendChild(labelEl);
      btn.appendChild(cdEl);
      btn.appendChild(hintEl);
      btn.addEventListener("click", () => {
        if (btn.disabled) return;
        this.ws.send("trigger_sabotage", { sabotageId: id });
      });
      grid.appendChild(btn);
      this.buttons.set(id, { btn, cdEl, fillEl, hintEl });
    }
    this.root.appendChild(grid);
  }

  /**
   * Update each button from a fresh game_state.payload.sabotages array.
   * Buttons not in availableIds are ignored. When `disabledByOwnDeath` is true
   * (Tier 2.6 spectator-mode), every button is force-disabled regardless of
   * cooldown — ghosts cannot sabotage even if they were chaos. When
   * `disabledByCommsDown` is true (Tier 2.5), every button is also disabled
   * except `comms_outage` itself.
   *
   * Tier 2.7 rework: opts.objectAvailability is a {sabotage_id: bool} map of
   * "is the local chaos in reach of a matching themed object?". Buttons gray
   * out with a hint when the player is too far.
   */
  updateFromGameState(sabotages, opts = {}) {
    if (!sabotages || this.availableIds.length === 0) return;
    this._lastDisabledByOwnDeath = !!opts.disabledByOwnDeath;
    this._lastDisabledByCommsDown = !!opts.disabledByCommsDown;
    this.objectAvailability = opts.objectAvailability || {};
    // Cache hints from payload so we can re-show them on disabled state.
    for (const sab of sabotages) {
      if (sab.objectHint) this.objectHints[sab.id] = sab.objectHint;
    }
    for (const sab of sabotages) {
      const entry = this.buttons.get(sab.id);
      if (!entry) continue;
      const cd = Math.max(0, sab.cooldownRemaining || 0);
      const total = this._cooldownTotal(sab.id, cd);
      entry.lastCooldown = cd;
      entry.lastSabotageId = sab.id;
      this._applyDisabledState(entry);
      entry.cdEl.textContent = cd > 0 ? `${Math.ceil(cd)}s` : "";
      const ratio = total > 0 && cd > 0 ? Math.min(1, cd / total) : 0;
      entry.fillEl.style.height = `${ratio * 100}%`;
      entry.btn.classList.toggle("sabotage-active", !!sab.active);
      // Hint visible only when out of object range (and not on cooldown).
      const oa = this.objectAvailability[sab.id];
      const outOfRange = oa === false;
      if (outOfRange && cd === 0 && !this._lastDisabledByOwnDeath) {
        entry.hintEl.textContent = `→ ${this.objectHints[sab.id] || "passendes Terminal"}`;
        entry.btn.classList.add("sabotage-out-of-range");
      } else {
        entry.hintEl.textContent = "";
        entry.btn.classList.remove("sabotage-out-of-range");
      }
    }
  }

  _applyDisabledState(entry) {
    const cd = entry.lastCooldown || 0;
    const blockedByComms =
      !!this._lastDisabledByCommsDown && entry.lastSabotageId !== "comms_outage";
    const oa = this.objectAvailability[entry.lastSabotageId];
    // undefined → unknown (e.g. legacy map) → assume available.
    const blockedByObject = oa === false;
    entry.btn.disabled =
      cd > 0 || !!this._lastDisabledByOwnDeath || blockedByComms || blockedByObject;
  }

  _cooldownTotal(id, currentCd) {
    if (currentCd > (this.totalCooldowns[id] || 0)) {
      this.totalCooldowns[id] = currentCd;
    }
    return this.totalCooldowns[id] || 1;
  }
}
