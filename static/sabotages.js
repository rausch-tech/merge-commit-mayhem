import { applySprite } from "./sprites.js";

const TITLE_LABELS = {
  ci_cd_red: "CI/CD Rot",
  coffee_outage: "Kaffee leer",
  mandatory_meeting: "Mandatory Meeting",
};

export class SabotagePanel {
  constructor(rootEl, wsClient) {
    this.root = rootEl;
    this.ws = wsClient;
    this.buttons = new Map(); // sabotage_id -> { btn, cdEl, fillEl }
    this.availableIds = [];
    this.totalCooldowns = {}; // sabotage_id -> total seconds (for ring fraction)
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
   * Buttons not in availableIds are ignored.
   */
  updateFromGameState(sabotages) {
    if (!sabotages || this.availableIds.length === 0) return;
    for (const sab of sabotages) {
      const entry = this.buttons.get(sab.id);
      if (!entry) continue;
      const cd = Math.max(0, sab.cooldownRemaining || 0);
      const total = this._cooldownTotal(sab.id, cd);
      entry.btn.disabled = cd > 0;
      entry.cdEl.textContent = cd > 0 ? `${Math.ceil(cd)}s` : "";
      // Fill height represents ratio of remaining to total cooldown.
      const ratio = total > 0 && cd > 0 ? Math.min(1, cd / total) : 0;
      entry.fillEl.style.height = `${ratio * 100}%`;
      // Active state visual cue.
      entry.btn.classList.toggle("sabotage-active", !!sab.active);
    }
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
