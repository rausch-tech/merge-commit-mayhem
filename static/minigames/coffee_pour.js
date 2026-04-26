// Tier 3.4 — CoffeePour renderer.
//
// View shape (server public_view):
//   { elapsed, cycleSeconds, sweetMin, sweetMax, attempts, lastAttemptFill,
//     complete }
//
// Eine Tasse fuellt sich linear in einem Zyklus von cycleSeconds Sekunden
// und beginnt dann wieder bei 0. Der Spieler tippt einmal STOP. Der Server
// validiert; bei Daneben kommt ein neuer Frame mit elapsed≈0 und einem
// inkrementierten attempts-Counter. Die Animation extrapoliert lokal aus
// der Server-Zeit zwischen Frames — Validierung bleibt serverseitig.

export class CoffeePourRenderer {
  constructor(containerEl, sendInput) {
    this.root = containerEl;
    this.sendInput = sendInput;
    this.cycleSeconds = 3.0;
    this.sweetMin = 0.7;
    this.sweetMax = 1.0;
    this.localT0 = 0; // Date.now()/1000 - elapsed at last frame
    this.lastView = null;
    this._raf = null;
  }

  onStart(view) {
    this.root.innerHTML = "";
    this.root.classList.add("mini-game-coffee-root");

    const desc = document.createElement("p");
    desc.className = "mini-game-progress";
    desc.textContent = "Tippe STOP, wenn die Tasse im gruenen Bereich ist.";
    this.root.appendChild(desc);

    this.statusEl = document.createElement("p");
    this.statusEl.className = "mini-game-progress";
    this.root.appendChild(this.statusEl);

    const stage = document.createElement("div");
    stage.className = "mini-game-coffee-stage";
    this.cupEl = document.createElement("div");
    this.cupEl.className = "mini-game-coffee-cup";
    this.fillEl = document.createElement("div");
    this.fillEl.className = "mini-game-coffee-fill";
    this.sweetEl = document.createElement("div");
    this.sweetEl.className = "mini-game-coffee-sweet";
    this.cupEl.appendChild(this.sweetEl);
    this.cupEl.appendChild(this.fillEl);
    stage.appendChild(this.cupEl);
    this.root.appendChild(stage);

    this.stopBtn = document.createElement("button");
    this.stopBtn.type = "button";
    this.stopBtn.className = "mini-game-coffee-stop-btn";
    this.stopBtn.textContent = "STOP";
    this.stopBtn.addEventListener("click", () => this.sendInput("stop", {}));
    this.root.appendChild(this.stopBtn);

    this.onUpdate(view);
    this._startLoop();
  }

  onUpdate(view) {
    this.cycleSeconds = view.cycleSeconds || this.cycleSeconds;
    this.sweetMin = view.sweetMin ?? this.sweetMin;
    this.sweetMax = view.sweetMax ?? this.sweetMax;
    // Re-anchor the local clock from the latest server-elapsed snapshot.
    this.localT0 = Date.now() / 1000 - (view.elapsed || 0);
    this.lastView = view;

    // Sweet-zone band lives in the cup at sweetMin..sweetMax (vertical % from
    // bottom). We render once on first frame; nothing else moves it.
    this.sweetEl.style.bottom = `${this.sweetMin * 100}%`;
    this.sweetEl.style.height = `${(this.sweetMax - this.sweetMin) * 100}%`;

    if (view.complete) {
      this.statusEl.textContent = "Volltreffer!";
      this.statusEl.classList.add("status-success");
    } else if (view.attempts > 0) {
      const pct = Math.round((view.lastAttemptFill ?? 0) * 100);
      this.statusEl.textContent = `Daneben (${pct}%) — nochmal!`;
      this.statusEl.classList.remove("status-success");
    } else {
      this.statusEl.textContent = "Versuch 1 — warten und tippen.";
      this.statusEl.classList.remove("status-success");
    }
  }

  onComplete(_success, _reason) {
    this._stopLoop();
  }

  _startLoop() {
    const tick = () => {
      this._renderFill();
      this._raf = requestAnimationFrame(tick);
    };
    this._raf = requestAnimationFrame(tick);
  }

  _stopLoop() {
    if (this._raf !== null) {
      cancelAnimationFrame(this._raf);
      this._raf = null;
    }
  }

  _renderFill() {
    if (!this.fillEl) return;
    const elapsed = Date.now() / 1000 - this.localT0;
    const fill = (((elapsed / this.cycleSeconds) % 1.0) + 1.0) % 1.0; // safe modulo
    this.fillEl.style.height = `${fill * 100}%`;
    // Tint the fill green inside the sweet zone for instant feedback.
    if (fill >= this.sweetMin && fill <= this.sweetMax) {
      this.fillEl.classList.add("in-sweet");
    } else {
      this.fillEl.classList.remove("in-sweet");
    }
  }
}
