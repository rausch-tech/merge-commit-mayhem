// Take-Down button: visible only when the local player is a chaos agent,
// alive, in PLAYING phase, AND there is at least one alive non-self player
// within TAKEDOWN_RADIUS pixels. Server is authoritative; the client only
// uses the radius to decide whether to show the button.

const TAKEDOWN_RADIUS = 40.0;

export class TakedownButton {
  constructor(btnEl, wsClient) {
    this.btn = btnEl;
    this.ws = wsClient;
    this._cooldown = 0;
    this._players = [];
    this._ownPlayerId = null;
    this.btn.addEventListener("click", () => this._onClick());
  }

  _onClick() {
    if (this.btn.disabled) return;
    if (this._cooldown > 0) return;
    const target = this._closestValidTarget();
    if (!target) return;
    this.ws.send("trigger_takedown", { targetPlayerId: target.id });
  }

  _closestValidTarget() {
    if (!this._ownPlayerId) return null;
    const me = this._players.find((p) => p.id === this._ownPlayerId);
    if (!me) return null;
    let best = null;
    let bestDistSq = TAKEDOWN_RADIUS * TAKEDOWN_RADIUS;
    for (const p of this._players) {
      if (p.id === this._ownPlayerId) continue;
      if (p.isAlive === false) continue;
      if (p.isConnected === false) continue;
      const dx = me.x - p.x;
      const dy = me.y - p.y;
      const distSq = dx * dx + dy * dy;
      if (distSq <= bestDistSq) {
        best = p;
        bestDistSq = distSq;
      }
    }
    return best;
  }

  update({ phase, players, ownPlayerId, ownTeam, cooldown }) {
    this._players = players || [];
    this._ownPlayerId = ownPlayerId;
    this._cooldown = Math.max(0, cooldown || 0);

    if (phase !== "playing" || ownTeam !== "chaos_agents" || !ownPlayerId) {
      this.btn.classList.add("hidden");
      return;
    }
    const me = this._players.find((p) => p.id === ownPlayerId);
    if (!me || me.isAlive === false) {
      this.btn.classList.add("hidden");
      return;
    }
    const target = this._closestValidTarget();
    if (!target) {
      this.btn.classList.add("hidden");
      return;
    }
    this.btn.classList.remove("hidden");
    if (this._cooldown > 0) {
      this.btn.disabled = true;
      this.btn.textContent = `Force-Reboot (${Math.ceil(this._cooldown)}s)`;
    } else {
      this.btn.disabled = false;
      this.btn.textContent = "Force-Reboot";
    }
  }
}
