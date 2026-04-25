import { applySprite } from "./sprites.js";

const ROLE_LABELS = {
  developer: "Developer",
  vibe_coder: "Vibe Coder",
};
const TEAM_LABELS = {
  release_team: "Release Team",
  chaos_agents: "Chaos",
};
const WINNER_BANNERS = {
  release_team: "Release-Team gewinnt",
  chaos_agents: "Chaos-Agenten gewinnen",
};

export class EndscreenOverlay {
  constructor(rootEl, wsClient) {
    this.root = rootEl;
    this.ws = wsClient;
    this.bannerEl = rootEl.querySelector("#endscreen-banner");
    this.reasonEl = rootEl.querySelector("#endscreen-reason");
    this.playersEl = rootEl.querySelector("#endscreen-players");
    this.resetBtn = rootEl.querySelector("#endscreen-reset");
    this.resetBtn.addEventListener("click", () => {
      this.ws.send("return_to_lobby", {});
      // Hide will happen via lobby_state -> main.js -> hide()
    });
  }

  show(payload, isHost) {
    const winner = payload.winner;
    this.bannerEl.textContent = WINNER_BANNERS[winner] || winner;
    this.bannerEl.dataset.team = winner;
    this.reasonEl.textContent = payload.reason || "";
    this.playersEl.innerHTML = "";
    for (const p of payload.players || []) {
      const row = document.createElement("li");
      row.className = `endscreen-row endscreen-row-${p.team}`;
      const badge = document.createElement("div");
      badge.className = "role-badge role-badge-lg";
      if (p.role) applySprite(badge, `role_${p.role}`);
      const left = document.createElement("div");
      left.className = "endscreen-name";
      left.textContent = p.name;
      const role = document.createElement("div");
      role.className = "endscreen-role";
      role.textContent = `${ROLE_LABELS[p.role] || p.role} · ${TEAM_LABELS[p.team] || p.team}`;
      const stats = document.createElement("div");
      stats.className = "endscreen-stats";
      stats.textContent = `${p.completedTasks} Tasks · ${p.triggeredSabotages} Sabotagen`;
      row.appendChild(badge);
      row.appendChild(left);
      row.appendChild(role);
      row.appendChild(stats);
      this.playersEl.appendChild(row);
    }
    this.resetBtn.classList.toggle("hidden", !isHost);
    this.root.classList.remove("hidden");
  }

  hide() {
    this.root.classList.add("hidden");
  }
}
