const ROOM_LABELS = {
  open_space: "Open Space",
  meeting_room: "Meeting Room",
  kitchen: "Kitchen",
  server_room: "Server Room",
  war_room: "War Room",
  legacy_basement: "Legacy Basement",
};

export class TaskList {
  constructor(rootEl) {
    this.root = rootEl;
    // Tier 3.5: personal-task highlight + strength-category highlight.
    this.personalIds = new Set();
    this.strengthCategories = new Set();
    this.lastTasks = [];
  }

  /** Tier 3.5: which task ids belong to the local player. Highlighted with a
   * star + amber border in the sidebar. Pass a list (real for release, fake
   * for chaos — same UI either way). */
  setPersonal(ids, strengthCategories = []) {
    this.personalIds = new Set(ids || []);
    this.strengthCategories = new Set(strengthCategories || []);
    this.render(this.lastTasks);
  }

  render(tasks) {
    this.lastTasks = tasks || [];
    if (!this.root) return;
    this.root.innerHTML = "";
    if (!tasks || !tasks.length) return;
    const heading = document.createElement("h3");
    heading.textContent = this.personalIds.size > 0 ? "Deine Tasks" : "Tasks";
    this.root.appendChild(heading);
    const ul = document.createElement("ul");
    // Sort: personal tasks first, then by current status.
    const sorted = [...tasks].sort((a, b) => {
      const ap = this.personalIds.has(a.id) ? 0 : 1;
      const bp = this.personalIds.has(b.id) ? 0 : 1;
      return ap - bp;
    });
    for (const t of sorted) {
      const li = document.createElement("li");
      const classes = [`task-row`, `task-row-${t.status}`];
      if (this.personalIds.has(t.id)) classes.push("task-personal");
      if (t.category && this.strengthCategories.has(t.category)) classes.push("task-strength");
      li.className = classes.join(" ");
      const title = document.createElement("div");
      title.className = "task-title";
      title.textContent = t.title;
      const meta = document.createElement("div");
      meta.className = "task-meta";
      let statusLabel = "verfügbar";
      if (t.status === "in_progress") statusLabel = `${Math.floor(t.progress * 100)}%`;
      else if (t.status === "cooldown") statusLabel = `Cooldown ${Math.ceil(t.cooldownRemaining)}s`;
      meta.textContent = `${ROOM_LABELS[t.room] || t.room} · ${statusLabel}`;
      li.appendChild(title);
      li.appendChild(meta);
      ul.appendChild(li);
    }
    this.root.appendChild(ul);
  }
}
