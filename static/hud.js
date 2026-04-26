import { applySprite } from "./sprites.js";

/**
 * HUD bindings for the four live stats (release, pipeline, coffee, timer)
 * plus the player's private role pill. All elements are looked up once;
 * handlers only touch the value span (or the entire pill for the role).
 */
export class Hud {
  constructor() {
    this.release = document.querySelector("#hud-release .hud-value");
    this.pipeline = document.querySelector("#hud-pipeline .hud-value");
    this.coffee = document.querySelector("#hud-coffee .hud-value");
    this.incidents = document.querySelector("#hud-incidents .hud-value");
    this.timer = document.querySelector("#hud-timer .hud-value");
    this.roleEl = document.getElementById("hud-role");
    // Tier 3.5: own coffee energy pill (per-player).
    this.myCoffeePill = document.getElementById("hud-my-coffee");
    this.myCoffee = document.querySelector("#hud-my-coffee .hud-value");
  }

  setStats({ releaseProgress, pipelineStability, coffeeLevel, incidents }) {
    if (typeof releaseProgress === "number") {
      this.release.textContent = `${releaseProgress}%`;
    }
    if (typeof pipelineStability === "number") {
      this.pipeline.textContent = `${pipelineStability}%`;
    }
    if (typeof coffeeLevel === "number") {
      this.coffee.textContent = `${coffeeLevel}%`;
    }
    if (typeof incidents === "number") {
      this.incidents.textContent = `${incidents}%`;
    }
  }

  setTimer(seconds) {
    const m = Math.max(0, Math.floor(seconds / 60));
    const s = Math.max(0, Math.floor(seconds % 60));
    this.timer.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  setRole(roleOrTitle, team) {
    // roleOrTitle is now the display title (e.g. "DevOps Engineer") since
    // Tier 3.5; for unknown values we still print whatever we got.
    const label = roleOrTitle || "—";
    this.roleEl.classList.add("with-badge");
    this.roleEl.innerHTML = "";
    const badge = document.createElement("span");
    badge.className = "role-badge";
    // Sprite mapping is keyed by canonical role id; fall back gracefully
    // when only the title is available.
    if (roleOrTitle) applySprite(badge, `role_${roleOrTitle.toLowerCase().replace(/\s+/g, "_")}`);
    const text = document.createElement("span");
    text.textContent = `Rolle: ${label}`;
    this.roleEl.appendChild(badge);
    this.roleEl.appendChild(text);
    if (team === "chaos_agents") {
      this.roleEl.style.background = "#4a1e1e";
    } else {
      this.roleEl.style.background = "";
    }
  }

  /** Tier 3.5: the player's own coffee_energy (0..max). Pill turns red and
   * pulses below 15 — that's where the speed penalty kicks in. */
  setMyCoffee(energy, max) {
    if (!this.myCoffee || !this.myCoffeePill) return;
    const e = Math.max(0, Math.round(Number(energy) || 0));
    this.myCoffee.textContent = `${e}`;
    this.myCoffeePill.classList.toggle("coffee-low", e < 15);
    if (max && Number(max) > 0) {
      this.myCoffeePill.title = `Eigene Kaffee-Energy (${e}/${Math.round(max)})`;
    }
  }
}
