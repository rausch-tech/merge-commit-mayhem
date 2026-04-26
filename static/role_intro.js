/**
 * Tier 3.5 Role-Intro modal.
 *
 * Shown once per round: when the server delivers a private_role with a fresh
 * role assignment (i.e. game phase has just flipped from lobby → playing),
 * we present a fullscreen card with role title, blurb, description, ability,
 * and the player's 3 personal/fake tasks. Press "Los geht's" or click outside
 * to dismiss — also auto-dismisses after 30s so AFK players still get the
 * controls back.
 */

const _CATEGORY_LABEL = {
  code: "Code",
  infra: "Infra",
  legacy: "Legacy",
  scope: "Scope",
  support: "Support",
  "": "",
};

export class RoleIntroModal {
  constructor(rootEl) {
    this.root = rootEl;
    if (!rootEl) {
      // headless fallback — keep API for tests.
      return;
    }
    this.titleEl = rootEl.querySelector("#role-intro-title");
    this.blurbEl = rootEl.querySelector("#role-intro-blurb");
    this.descEl = rootEl.querySelector("#role-intro-description");
    this.badgeEl = rootEl.querySelector("#role-intro-team-badge");
    this.strengthsBlock = rootEl.querySelector("#role-intro-strengths");
    this.strengthsList = rootEl.querySelector("#role-intro-strength-list");
    this.abilityBlock = rootEl.querySelector("#role-intro-ability");
    this.abilityLine = rootEl.querySelector("#role-intro-ability-line");
    this.tasksHeading = rootEl.querySelector("#role-intro-tasks-heading");
    this.taskList = rootEl.querySelector("#role-intro-task-list");
    this.closeBtn = rootEl.querySelector("#role-intro-close");
    if (this.closeBtn) {
      this.closeBtn.addEventListener("click", () => this.hide());
    }
    rootEl.addEventListener("click", (e) => {
      if (e.target === rootEl) this.hide();
    });
    this._autoTimer = null;
    this._lastRolePresented = null;
  }

  /** Show the modal for the given private_role payload. Idempotent — calling
   * with the same payload shape twice in a row won't re-show after dismiss. */
  show(payload) {
    if (!this.root || !payload) return;
    const sig = `${payload.role}|${payload.team}|${(payload.assignedTaskIds || []).join(",")}`;
    if (sig === this._lastRolePresented) return;
    this._lastRolePresented = sig;

    const isChaos = payload.team === "chaos_agents";
    this.root.classList.toggle("team-chaos", isChaos);
    this.root.classList.toggle("team-release", !isChaos);
    this.badgeEl.textContent = isChaos ? "Chaos-Agent" : "Release-Team";
    this.titleEl.textContent = payload.title || payload.role;
    this.blurbEl.textContent = payload.shortBlurb || "";
    this.descEl.textContent = payload.description || "";

    // Strengths (release only).
    const strengths = payload.strengthCategories || [];
    if (strengths.length > 0 && !isChaos) {
      this.strengthsBlock.classList.remove("hidden");
      this.strengthsList.innerHTML = "";
      for (const cat of strengths) {
        const li = document.createElement("li");
        li.textContent = `${_CATEGORY_LABEL[cat] || cat} — schneller bei diesen Tasks`;
        this.strengthsList.appendChild(li);
      }
    } else {
      this.strengthsBlock.classList.add("hidden");
    }

    // Ability.
    if (payload.abilityId && payload.abilityLabel) {
      this.abilityBlock.classList.remove("hidden");
      this.abilityLine.textContent = `${payload.abilityLabel}: ${payload.abilityHint || ""}`;
    } else {
      this.abilityBlock.classList.add("hidden");
    }

    // Tasks (release: real, chaos: cover persona).
    this.tasksHeading.textContent = isChaos ? "Deine Tarn-Aufgaben" : "Deine Aufgaben";
    this.taskList.innerHTML = "";
    const tasks = payload.assignedTasks || [];
    for (const t of tasks) {
      const li = document.createElement("li");
      const where = t.room ? ` — ${t.room}` : "";
      li.textContent = `${t.title}${where}`;
      this.taskList.appendChild(li);
    }

    this.root.classList.remove("hidden");
    if (this._autoTimer) clearTimeout(this._autoTimer);
    this._autoTimer = setTimeout(() => this.hide(), 30000);
  }

  hide() {
    if (!this.root) return;
    this.root.classList.add("hidden");
    if (this._autoTimer) {
      clearTimeout(this._autoTimer);
      this._autoTimer = null;
    }
  }

  /** Reset on round-end so the next round shows the modal again. */
  reset() {
    this._lastRolePresented = null;
    this.hide();
  }
}
