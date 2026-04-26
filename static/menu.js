// Tier 1.9 — In-Game-Menu (ESC-overlay).
//
// Surfaces from anywhere via the ESC key. Hosts a slim role/task recap, the
// audio controls (relocated from the top bar), and the lifecycle actions
// "Leave room" (always available once the player is in a room) and
// "Abort round" (host only, only during PLAYING/MEETING).
//
// All side effects flow through callbacks injected by main.js so this module
// stays free of WS / state imports.

const ROLE_LABELS = {
  release_engineer: "Release Engineer",
  qa_lead: "QA Lead",
  scrum_master: "Scrum Master",
  vibe_coder: "Vibe Coder",
  rogue_consultant: "Rogue Consultant",
};

function _humanRole(roleId) {
  if (!roleId) return "—";
  return ROLE_LABELS[roleId] || roleId;
}

function _humanTeam(team) {
  if (team === "release_team") return "Release-Team";
  if (team === "chaos_agents") return "Chaos-Agenten";
  return "—";
}

export class InGameMenu {
  constructor(rootEl, audioControlsEl, callbacks) {
    this.root = rootEl;
    this.card = rootEl.querySelector("#in-game-menu-card");
    this.recap = rootEl.querySelector("#menu-recap");
    this.roleLine = rootEl.querySelector("#menu-role-line");
    this.taskList = rootEl.querySelector("#menu-task-list");
    this.audioSlot = rootEl.querySelector("#menu-audio-slot");
    this.leaveBtn = rootEl.querySelector("#menu-leave-btn");
    this.abortBtn = rootEl.querySelector("#menu-abort-btn");
    this.closeBtn = rootEl.querySelector("#menu-close-btn");
    this.audioControls = audioControlsEl;
    this.callbacks = callbacks;
    this._open = false;

    // Permanently relocate the audio controls into the menu card. The
    // top-bar wrapper stays in the DOM but now lives under the menu — its
    // `position: fixed` is overridden in CSS while inside the slot.
    if (this.audioControls && this.audioSlot) {
      this.audioSlot.appendChild(this.audioControls);
    }

    this.leaveBtn.addEventListener("click", () => {
      this.callbacks.onLeave?.();
      this.hide();
    });
    this.abortBtn.addEventListener("click", () => {
      this.callbacks.onAbort?.();
      this.hide();
    });
    this.closeBtn.addEventListener("click", () => this.hide());

    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      // Don't fight other modals (meeting, endscreen) — let them own ESC if
      // they're up. Heuristic: skip when any other modal is visible.
      const blockers = ["meeting-overlay", "endscreen"];
      for (const id of blockers) {
        const el = document.getElementById(id);
        if (el && !el.classList.contains("hidden")) return;
      }
      // Don't open while typing into an input (join form etc.).
      const tag = (e.target && e.target.tagName) || "";
      if (this._open || (tag !== "INPUT" && tag !== "TEXTAREA")) {
        e.preventDefault();
        this.toggle();
      }
    });
  }

  toggle() {
    if (this._open) this.hide();
    else this.show();
  }

  show() {
    this.root.classList.remove("hidden");
    this._open = true;
  }

  hide() {
    this.root.classList.add("hidden");
    this._open = false;
  }

  isOpen() {
    return this._open;
  }

  /** Refresh visibility + content based on current state. */
  update({ inRoom, isHost, phase, ownRole, tasks }) {
    // Leave button shows whenever the player is in a room.
    this.leaveBtn.classList.toggle("hidden", !inRoom);
    // Abort only during a live round, host only.
    const canAbort = isHost && (phase === "playing" || phase === "meeting");
    this.abortBtn.classList.toggle("hidden", !canAbort);

    // Recap: only during/after the round, when the player has been told
    // their role.
    if (ownRole && ownRole.role) {
      this.recap.classList.remove("hidden");
      this.roleLine.textContent = `${_humanRole(ownRole.role)} — ${_humanTeam(ownRole.team)}`;
      this._renderTasks(tasks || []);
    } else {
      this.recap.classList.add("hidden");
    }
  }

  _renderTasks(tasks) {
    this.taskList.innerHTML = "";
    if (tasks.length === 0) {
      const li = document.createElement("li");
      li.className = "menu-task-row";
      li.textContent = "Keine Aufgaben aktiv.";
      this.taskList.appendChild(li);
      return;
    }
    for (const t of tasks) {
      const li = document.createElement("li");
      li.className = "menu-task-row";
      const name = document.createElement("span");
      name.textContent = t.title;
      const status = document.createElement("span");
      status.className = "menu-task-status";
      status.textContent =
        t.status === "cooldown"
          ? "fertig"
          : t.status === "in_progress"
            ? `${Math.round((t.progress || 0) * 100)}%`
            : "offen";
      li.appendChild(name);
      li.appendChild(status);
      this.taskList.appendChild(li);
    }
  }
}
