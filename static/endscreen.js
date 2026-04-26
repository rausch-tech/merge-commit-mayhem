import { applySprite } from "./sprites.js";

const ROLE_LABELS = {
  developer: "Developer",
  devops_engineer: "DevOps Engineer",
  qa_lead: "QA Lead",
  scrum_master: "Scrum Master",
  caffeine_collector: "Caffeine Collector",
  vibe_coder: "Vibe Coder",
  rogue_consultant: "Rogue Consultant",
  shadow_admin: "Shadow Admin",
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
    // Tier 3.7 endscreen extras (awards + AI postmortem text).
    this.awardsBlock = rootEl.querySelector("#endscreen-awards-block");
    this.awardsList = rootEl.querySelector("#endscreen-awards");
    this.postmortemBlock = rootEl.querySelector("#endscreen-postmortem-block");
    this.postmortemEl = rootEl.querySelector("#endscreen-postmortem");
    this.resetBtn.addEventListener("click", () => {
      this.ws.send("return_to_lobby", {});
    });
  }

  /** Tier 3.7: enrich the endscreen with awards + AI postmortem from the
   * server-side final_summary blob. Idempotent — passing null clears them. */
  applyFinalSummary(summary) {
    if (!summary) {
      this.awardsBlock?.classList.add("hidden");
      this.postmortemBlock?.classList.add("hidden");
      return;
    }
    const awards = summary.awards || [];
    if (awards.length > 0 && this.awardsBlock) {
      this.awardsList.innerHTML = "";
      for (const a of awards) {
        const li = document.createElement("li");
        li.innerHTML = `<strong>${a.title}</strong> — ${a.playerName}: ${a.reason}`;
        this.awardsList.appendChild(li);
      }
      this.awardsBlock.classList.remove("hidden");
    } else {
      this.awardsBlock?.classList.add("hidden");
    }
    if (summary.postmortem && this.postmortemBlock) {
      this.postmortemEl.textContent = summary.postmortem;
      this.postmortemBlock.classList.remove("hidden");
    } else {
      this.postmortemBlock?.classList.add("hidden");
    }
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
