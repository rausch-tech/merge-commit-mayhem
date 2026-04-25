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
    this.timer = document.querySelector("#hud-timer .hud-value");
    this.roleEl = document.getElementById("hud-role");
  }

  setStats({ releaseProgress, pipelineStability, coffeeLevel }) {
    if (typeof releaseProgress === "number") {
      this.release.textContent = `${releaseProgress}%`;
    }
    if (typeof pipelineStability === "number") {
      this.pipeline.textContent = `${pipelineStability}%`;
    }
    if (typeof coffeeLevel === "number") {
      this.coffee.textContent = `${coffeeLevel}%`;
    }
  }

  setTimer(seconds) {
    const m = Math.max(0, Math.floor(seconds / 60));
    const s = Math.max(0, Math.floor(seconds % 60));
    this.timer.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  setRole(role, team) {
    const label = role === "vibe_coder" ? "Vibe Coder (Chaos)" : role;
    this.roleEl.textContent = `Rolle: ${label}`;
    if (team === "chaos_agents") {
      this.roleEl.style.background = "#4a1e1e";
    } else {
      this.roleEl.style.background = "";
    }
  }
}
