// Tier 3.6 — SprintTrim renderer.
//
// View shape (server public_view):
//   { tickets: [{id, title, points, priority, removed}], budget, remainingPoints }
// Spieler tippt Tickets, um sie aus dem Sprint zu nehmen. Priority-Tickets
// (rot markiert) duerfen NICHT entfernt werden — Tap ist Soft-Reset.

export class SprintTrimRenderer {
  constructor(containerEl, sendInput) {
    this.root = containerEl;
    this.sendInput = sendInput;
    this.progressEl = null;
    this.listEl = null;
  }

  onStart(view) {
    this.root.innerHTML = "";
    this.root.classList.add("mini-game-sprint-root");
    const desc = document.createElement("p");
    desc.className = "mini-game-progress";
    desc.textContent =
      "Tippe Tickets, um sie aus dem Sprint zu nehmen. Rote Priority-Tickets nicht anfassen.";
    this.progressEl = document.createElement("p");
    this.progressEl.className = "mini-game-progress";
    this.listEl = document.createElement("ul");
    this.listEl.className = "mini-game-sprint-list";
    this.root.appendChild(desc);
    this.root.appendChild(this.progressEl);
    this.root.appendChild(this.listEl);
    this.onUpdate(view);
  }

  onUpdate(view) {
    if (!this.listEl) return;
    const overBudget = view.remainingPoints > view.budget;
    this.progressEl.textContent = `Restpunkte: ${view.remainingPoints} / Sprint-Budget ${view.budget}`;
    this.progressEl.classList.toggle("status-success", !overBudget);
    this.listEl.innerHTML = "";
    for (const t of view.tickets) {
      const li = document.createElement("li");
      li.className = "mini-game-sprint-ticket";
      if (t.priority) li.classList.add("priority");
      if (t.removed) li.classList.add("removed");
      const points = document.createElement("span");
      points.className = "mini-game-sprint-points";
      points.textContent = `${t.points} SP`;
      const title = document.createElement("span");
      title.className = "mini-game-sprint-title";
      title.textContent = t.title;
      const tag = document.createElement("span");
      tag.className = "mini-game-sprint-tag";
      tag.textContent = t.priority ? "PRIORITY" : t.removed ? "OUT" : "IN";
      li.appendChild(points);
      li.appendChild(title);
      li.appendChild(tag);
      li.addEventListener("click", () => {
        this.sendInput("toggle", { ticketId: t.id });
      });
      this.listEl.appendChild(li);
    }
  }

  onComplete(_success, _reason) {}
}
