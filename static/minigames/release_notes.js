// Tier 3.7 — ReleaseNotes renderer (write_release_notes task).
//
// View shape (server public_view):
//   { commits: [{id, message, assigned}], categories, totalCommits,
//     assignedCount }
//
// Click-to-cycle: jeder Klick auf einen Commit cycelt seine Kategorie
// durch (None → feature → bugfix → breaking → noprod → None …).
// Submit-Button ist erst aktiv wenn alle Commits zugewiesen sind.
// Server validiert beim Submit; bei Fehler droppt er alle Zuweisungen
// (Soft-Reset) — der Client sieht das per onUpdate.

const CATEGORY_LABEL = {
  feature: "Feature",
  bugfix: "Bugfix",
  breaking: "Breaking",
  noprod: "Don't mention",
};

const CATEGORY_CLASS = {
  feature: "cat-feature",
  bugfix: "cat-bugfix",
  breaking: "cat-breaking",
  noprod: "cat-noprod",
};

export class ReleaseNotesRenderer {
  constructor(containerEl, sendInput) {
    this.root = containerEl;
    this.sendInput = sendInput;
    this.descEl = null;
    this.listEl = null;
    this.submitBtn = null;
  }

  onStart(view) {
    this.root.innerHTML = "";
    this.root.classList.add("mini-game-release-root");
    this.descEl = document.createElement("p");
    this.descEl.className = "mini-game-progress";
    this.descEl.textContent =
      "Sortiere jeden Commit in eine Kategorie. Klick wechselt durch Feature → Bugfix → Breaking → Don't mention.";
    this.root.appendChild(this.descEl);

    this.listEl = document.createElement("ol");
    this.listEl.className = "mini-game-release-list";
    this.root.appendChild(this.listEl);

    this.submitBtn = document.createElement("button");
    this.submitBtn.className = "mini-game-release-submit";
    this.submitBtn.type = "button";
    this.submitBtn.textContent = "Release Notes einreichen";
    this.submitBtn.addEventListener("click", () => {
      this.sendInput("submit", {});
    });
    this.root.appendChild(this.submitBtn);

    this.onUpdate(view);
  }

  onUpdate(view) {
    if (!this.listEl) return;
    this.descEl.textContent = `Sortiere jeden Commit (${view.assignedCount} / ${view.totalCommits} zugewiesen).`;

    this.listEl.innerHTML = "";
    for (const commit of view.commits) {
      const li = document.createElement("li");
      li.className = "mini-game-release-row";
      const code = document.createElement("span");
      code.className = "mini-game-release-msg";
      code.textContent = commit.message;
      const badge = document.createElement("span");
      badge.className = "mini-game-release-badge";
      if (commit.assigned) {
        badge.classList.add(CATEGORY_CLASS[commit.assigned]);
        badge.textContent = CATEGORY_LABEL[commit.assigned];
      } else {
        badge.classList.add("cat-unassigned");
        badge.textContent = "(klick mich)";
      }
      li.appendChild(code);
      li.appendChild(badge);
      li.addEventListener("click", () => {
        this.sendInput("cycle", { commitId: commit.id });
      });
      this.listEl.appendChild(li);
    }

    const allAssigned = view.assignedCount >= view.totalCommits;
    this.submitBtn.disabled = !allAssigned;
    this.submitBtn.classList.toggle("ready", allAssigned);
  }

  onComplete(_success, _reason) {}
}
