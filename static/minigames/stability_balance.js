// Tier 3.7 — StabilityBalance renderer (calm_legacy_service task).
//
// View shape (server public_view):
//   { cpu, mem, queue, greenLow, greenHigh }
//
// Drei horizontale Bars mit grünem Band. Pro Metrik zwei Buttons (- / +).
// Klick sendet ``adjust`` mit metric + direction; Server berechnet die
// Rotation (cpu→mem→queue→cpu, Gegenrichtung) und schickt das neue
// public_view via mini_game_state. Modal schliesst sich serverseitig
// sobald alle drei Bars im grünen Band liegen.

const METRICS = [
  { key: "cpu", label: "CPU" },
  { key: "mem", label: "Memory" },
  { key: "queue", label: "Queue" },
];

export class StabilityBalanceRenderer {
  constructor(containerEl, sendInput) {
    this.root = containerEl;
    this.sendInput = sendInput;
    this.descEl = null;
    this.barEls = {}; // {cpu: { bar, fill, label, minus, plus }, ...}
  }

  onStart(view) {
    this.root.innerHTML = "";
    this.root.classList.add("mini-game-stability-root");
    this.descEl = document.createElement("p");
    this.descEl.className = "mini-game-progress";
    this.descEl.textContent =
      "Halte alle drei Metriken im gruenen Band [40, 60]. Jede Korrektur drueckt die naechste Metrik leicht weg.";
    this.root.appendChild(this.descEl);

    const grid = document.createElement("div");
    grid.className = "mini-game-stability-grid";
    for (const m of METRICS) {
      const row = document.createElement("div");
      row.className = "mini-game-stability-row";

      const minusBtn = document.createElement("button");
      minusBtn.className = "mini-game-stability-btn";
      minusBtn.type = "button";
      minusBtn.textContent = "-";
      minusBtn.addEventListener("click", () => {
        this.sendInput("adjust", { metric: m.key, direction: "down" });
      });

      const labelWrap = document.createElement("div");
      labelWrap.className = "mini-game-stability-labelwrap";
      const label = document.createElement("span");
      label.className = "mini-game-stability-label";
      label.textContent = m.label;
      const value = document.createElement("span");
      value.className = "mini-game-stability-value";
      labelWrap.appendChild(label);
      labelWrap.appendChild(value);

      const bar = document.createElement("div");
      bar.className = "mini-game-stability-bar";
      const greenBand = document.createElement("div");
      greenBand.className = "mini-game-stability-green";
      const fill = document.createElement("div");
      fill.className = "mini-game-stability-fill";
      bar.appendChild(greenBand);
      bar.appendChild(fill);

      const plusBtn = document.createElement("button");
      plusBtn.className = "mini-game-stability-btn";
      plusBtn.type = "button";
      plusBtn.textContent = "+";
      plusBtn.addEventListener("click", () => {
        this.sendInput("adjust", { metric: m.key, direction: "up" });
      });

      row.appendChild(minusBtn);
      row.appendChild(labelWrap);
      row.appendChild(bar);
      row.appendChild(plusBtn);
      grid.appendChild(row);

      this.barEls[m.key] = { bar, fill, value, greenBand };
    }
    this.root.appendChild(grid);
    this.onUpdate(view);
  }

  onUpdate(view) {
    if (!this.barEls.cpu) return;
    const greenLow = view.greenLow ?? 40;
    const greenHigh = view.greenHigh ?? 60;
    for (const m of METRICS) {
      const value = view[m.key] ?? 0;
      const els = this.barEls[m.key];
      els.fill.style.width = `${value}%`;
      const inGreen = value >= greenLow && value <= greenHigh;
      els.fill.classList.toggle("in-green", inGreen);
      els.value.textContent = String(value);
      // Mark green-band overlay position once (constant, but cheap to redo).
      els.greenBand.style.left = `${greenLow}%`;
      els.greenBand.style.width = `${greenHigh - greenLow}%`;
    }
  }

  onComplete(_success, _reason) {}
}
