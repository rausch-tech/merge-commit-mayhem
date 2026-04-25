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
  }

  render(tasks) {
    if (!this.root) return;
    this.root.innerHTML = "";
    if (!tasks || !tasks.length) return;
    const heading = document.createElement("h3");
    heading.textContent = "Tasks";
    this.root.appendChild(heading);
    const ul = document.createElement("ul");
    for (const t of tasks) {
      const li = document.createElement("li");
      li.className = `task-row task-row-${t.status}`;
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
