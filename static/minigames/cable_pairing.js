// Tier 3.3 — CablePairing renderer.
//
// View shape (server public_view):
//   { sources:[{id,color}], destinations:[{id,color}],
//     connections:{sourceId: destinationId}, totalPairs }
//
// Spieler tippt eine Source links, dann eine Destination rechts. Der lokale
// Renderer haelt nur die UI-Selektion; jeder Verbindungsversuch geht als
// `connect`-Action an den Server, der ueber Farbgleichheit entscheidet.

export class CablePairingRenderer {
  constructor(containerEl, sendInput) {
    this.root = containerEl;
    this.sendInput = sendInput;
    this.selectedSourceId = null;
    this.lastView = null;
    this.headerEl = null;
    this.boardEl = null;
    this.linesEl = null;
  }

  onStart(view) {
    this.root.innerHTML = "";
    this.root.classList.add("mini-game-cable-root");

    const desc = document.createElement("p");
    desc.className = "mini-game-progress";
    desc.textContent = "Verbinde jeden Stecker mit der gleichfarbigen Buchse.";
    this.root.appendChild(desc);

    this.headerEl = document.createElement("p");
    this.headerEl.className = "mini-game-progress";
    this.root.appendChild(this.headerEl);

    this.boardEl = document.createElement("div");
    this.boardEl.className = "mini-game-cable-board";
    // Three columns: sources | svg overlay | destinations.
    this.sourcesCol = document.createElement("div");
    this.sourcesCol.className = "mini-game-cable-col mini-game-cable-col-src";
    this.linesEl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    this.linesEl.classList.add("mini-game-cable-lines");
    this.linesEl.setAttribute("preserveAspectRatio", "none");
    this.destsCol = document.createElement("div");
    this.destsCol.className = "mini-game-cable-col mini-game-cable-col-dst";
    this.boardEl.appendChild(this.sourcesCol);
    this.boardEl.appendChild(this.linesEl);
    this.boardEl.appendChild(this.destsCol);
    this.root.appendChild(this.boardEl);

    this.onUpdate(view);
  }

  onUpdate(view) {
    if (!this.boardEl) return;
    this.lastView = view;
    const conns = view.connections || {};
    const connectedSources = new Set(Object.keys(conns));
    const connectedDests = new Set(Object.values(conns));

    // Drop selection if it just got connected (or wiped by soft-reset).
    if (this.selectedSourceId && connectedSources.has(this.selectedSourceId)) {
      this.selectedSourceId = null;
    }

    this.headerEl.textContent = `Verbunden: ${Object.keys(conns).length} / ${view.totalPairs}`;

    this._renderColumn(this.sourcesCol, view.sources, "src", connectedSources);
    this._renderColumn(this.destsCol, view.destinations, "dst", connectedDests);
    // Defer line draw to after layout settles so getBoundingClientRect is
    // accurate for the freshly-added/updated nodes.
    requestAnimationFrame(() => this._drawLines(conns));
  }

  onComplete(_success, _reason) {
    // Modal close is owned by the wrapper; nothing plugin-specific to do.
  }

  _renderColumn(colEl, nodes, side, alreadyConnected) {
    colEl.innerHTML = "";
    for (const n of nodes) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "mini-game-cable-node";
      btn.dataset.nodeId = n.id;
      btn.dataset.side = side;
      btn.style.background = n.color;
      if (alreadyConnected.has(n.id)) btn.classList.add("connected");
      if (side === "src" && n.id === this.selectedSourceId) {
        btn.classList.add("selected");
      }
      btn.addEventListener("click", () => this._handleTap(n, side));
      colEl.appendChild(btn);
    }
  }

  _handleTap(node, side) {
    if (!this.lastView) return;
    const conns = this.lastView.connections || {};
    if (side === "src") {
      if (conns[node.id]) return; // already wired — ignore
      this.selectedSourceId = node.id;
      this._refreshSelectionClasses();
    } else {
      if (!this.selectedSourceId) return;
      if (Object.values(conns).includes(node.id)) return; // dest already used
      const sourceId = this.selectedSourceId;
      // Optimistic clear of selection — server's echo will confirm or reset.
      this.selectedSourceId = null;
      this._refreshSelectionClasses();
      this.sendInput("connect", { sourceId, destinationId: node.id });
    }
  }

  _refreshSelectionClasses() {
    if (!this.sourcesCol) return;
    for (const btn of this.sourcesCol.querySelectorAll(".mini-game-cable-node")) {
      btn.classList.toggle("selected", btn.dataset.nodeId === this.selectedSourceId);
    }
  }

  _drawLines(conns) {
    if (!this.linesEl || !this.boardEl) return;
    while (this.linesEl.firstChild) this.linesEl.removeChild(this.linesEl.firstChild);
    const boardRect = this.boardEl.getBoundingClientRect();
    if (boardRect.width <= 0) return;
    this.linesEl.setAttribute(
      "viewBox",
      `0 0 ${boardRect.width} ${boardRect.height}`
    );
    for (const [sourceId, destId] of Object.entries(conns)) {
      const srcEl = this.sourcesCol.querySelector(`[data-node-id="${sourceId}"]`);
      const dstEl = this.destsCol.querySelector(`[data-node-id="${destId}"]`);
      if (!srcEl || !dstEl) continue;
      const sr = srcEl.getBoundingClientRect();
      const dr = dstEl.getBoundingClientRect();
      const x1 = sr.right - boardRect.left;
      const y1 = sr.top + sr.height / 2 - boardRect.top;
      const x2 = dr.left - boardRect.left;
      const y2 = dr.top + dr.height / 2 - boardRect.top;
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", x1);
      line.setAttribute("y1", y1);
      line.setAttribute("x2", x2);
      line.setAttribute("y2", y2);
      line.setAttribute("stroke", srcEl.style.background || "#94a3b8");
      line.setAttribute("stroke-width", "4");
      line.setAttribute("stroke-linecap", "round");
      this.linesEl.appendChild(line);
    }
  }
}
