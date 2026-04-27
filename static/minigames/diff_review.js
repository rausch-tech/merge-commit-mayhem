// Tier 3.7 — DiffReview renderer (review_pr task).
//
// View shape (server public_view):
//   { lines: [{id, text, marked}], totalBugs, markedBugs }
//
// Spieler markiert die zwei Bug-Zeilen. Klick auf eine harmlose Zeile
// loest serverseitigen Soft-Reset aus, der via onUpdate ankommt.
// ``kind`` (bug vs. benign) wird absichtlich NICHT geliefert — der
// Client darf die Lösung nicht kennen.

export class DiffReviewRenderer {
  constructor(containerEl, sendInput) {
    this.root = containerEl;
    this.sendInput = sendInput;
    this.progressEl = null;
    this.listEl = null;
  }

  onStart(view) {
    this.root.innerHTML = "";
    this.root.classList.add("mini-game-diff-root");
    const desc = document.createElement("p");
    desc.className = "mini-game-progress";
    desc.textContent = "Finde die zwei kritischen Code-Zeilen im PR. Falscher Klick setzt zurueck.";
    this.progressEl = document.createElement("p");
    this.progressEl.className = "mini-game-progress";
    this.listEl = document.createElement("ol");
    this.listEl.className = "mini-game-diff-list";
    this.root.appendChild(desc);
    this.root.appendChild(this.progressEl);
    this.root.appendChild(this.listEl);
    this.onUpdate(view);
  }

  onUpdate(view) {
    if (!this.listEl) return;
    this.progressEl.textContent = `${view.markedBugs} / ${view.totalBugs} Bugs markiert`;
    this.listEl.innerHTML = "";
    for (const line of view.lines) {
      const li = document.createElement("li");
      li.className = "mini-game-diff-line" + (line.marked ? " marked" : "");
      const code = document.createElement("code");
      code.className = "mini-game-diff-code";
      code.textContent = line.text;
      li.appendChild(code);
      if (!line.marked) {
        li.addEventListener("click", () => {
          this.sendInput("click", { lineId: line.id });
        });
      }
      this.listEl.appendChild(li);
    }
  }

  onComplete(_success, _reason) {}
}
