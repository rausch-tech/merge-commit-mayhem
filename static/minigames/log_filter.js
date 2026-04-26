// Tier 3.5 — LogFilter renderer.
//
// View shape (server public_view):
//   { lines: [{id, level, message, marked}], totalErrors, markedErrors }
// Spieler markiert die `error`-Zeilen. Klick auf `warn` oder `info`
// loest serverseitigen Soft-Reset aus, der via onUpdate ankommt.

const LEVEL_LABEL = {
  error: "ERROR",
  warn: "WARN",
  info: "INFO",
};

export class LogFilterRenderer {
  constructor(containerEl, sendInput) {
    this.root = containerEl;
    this.sendInput = sendInput;
    this.progressEl = null;
    this.listEl = null;
  }

  onStart(view) {
    this.root.innerHTML = "";
    this.root.classList.add("mini-game-log-root");
    const desc = document.createElement("p");
    desc.className = "mini-game-progress";
    desc.textContent = "Markiere alle ERROR-Zeilen. Klick auf WARN/INFO setzt zurueck.";
    this.progressEl = document.createElement("p");
    this.progressEl.className = "mini-game-progress";
    this.listEl = document.createElement("ul");
    this.listEl.className = "mini-game-log-list";
    this.root.appendChild(desc);
    this.root.appendChild(this.progressEl);
    this.root.appendChild(this.listEl);
    this.onUpdate(view);
  }

  onUpdate(view) {
    if (!this.listEl) return;
    this.progressEl.textContent = `${view.markedErrors} / ${view.totalErrors} ERRORs markiert`;
    this.listEl.innerHTML = "";
    for (const line of view.lines) {
      const li = document.createElement("li");
      li.className =
        "mini-game-log-line mini-game-log-" + line.level + (line.marked ? " marked" : "");
      const tag = document.createElement("span");
      tag.className = "mini-game-log-tag";
      tag.textContent = LEVEL_LABEL[line.level] || line.level.toUpperCase();
      const msg = document.createElement("span");
      msg.className = "mini-game-log-msg";
      msg.textContent = line.message;
      li.appendChild(tag);
      li.appendChild(msg);
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
