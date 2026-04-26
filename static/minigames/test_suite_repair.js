// Tier 3.2 — TestSuiteRepair renderer.
//
// View shape from server (public_view):
//   { tests: [{id, label, order, status}], nextOrder, totalTests }
// Spieler klickt Test-Items in numerischer Reihenfolge; falscher Klick
// löst serverseitig einen Soft-Reset aus, der dann via onUpdate ankommt.

export class TestSuiteRepairRenderer {
  constructor(containerEl, sendInput) {
    this.root = containerEl;
    this.sendInput = sendInput;
    this.progressEl = null;
    this.listEl = null;
  }

  onStart(view) {
    this.root.innerHTML = "";
    const desc = document.createElement("p");
    desc.className = "mini-game-progress";
    desc.textContent = "Klicke die fehlerhaften Tests in numerischer Reihenfolge.";
    this.progressEl = document.createElement("p");
    this.progressEl.className = "mini-game-progress";
    this.listEl = document.createElement("ul");
    this.listEl.className = "mini-game-test-list";
    this.root.appendChild(desc);
    this.root.appendChild(this.progressEl);
    this.root.appendChild(this.listEl);
    this.onUpdate(view);
  }

  onUpdate(view) {
    if (!this.listEl) return;
    this.progressEl.textContent = `Als nächstes: #${view.nextOrder} (${
      view.nextOrder - 1
    } / ${view.totalTests} fertig)`;
    // Rebuild list.
    this.listEl.innerHTML = "";
    for (const t of view.tests) {
      const li = document.createElement("li");
      li.className = "mini-game-test" + (t.status === "fixed" ? " fixed" : "");
      const order = document.createElement("span");
      order.className = "order";
      order.textContent = `#${t.order}`;
      const label = document.createElement("span");
      label.textContent = t.label;
      li.appendChild(order);
      li.appendChild(label);
      if (t.status !== "fixed") {
        li.addEventListener("click", () => {
          this.sendInput("click", { testId: t.id });
        });
      }
      this.listEl.appendChild(li);
    }
  }

  onComplete(_success, _reason) {
    // Modal-Close passiert im Wrapper; nichts plugin-spezifisches zu tun.
  }
}
