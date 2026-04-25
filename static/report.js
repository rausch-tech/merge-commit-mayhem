// Body-Report button: visible only when the local player is alive, the room
// is in PLAYING phase, AND there is at least one body within REPORT_RADIUS
// pixels. Server validates; client uses the radius only to decide UI visibility.

const REPORT_RADIUS = 40.0;

export class ReportButton {
  constructor(btnEl, wsClient) {
    this.btn = btnEl;
    this.ws = wsClient;
    this._players = [];
    this._bodies = [];
    this._ownPlayerId = null;
    this.btn.addEventListener("click", () => this._onClick());
  }

  _onClick() {
    if (this.btn.disabled) return;
    const body = this._closestValidBody();
    if (!body) return;
    this.ws.send("report_body", { bodyId: body.id });
  }

  _closestValidBody() {
    if (!this._ownPlayerId) return null;
    const me = this._players.find((p) => p.id === this._ownPlayerId);
    if (!me) return null;
    let best = null;
    let bestDistSq = REPORT_RADIUS * REPORT_RADIUS;
    for (const b of this._bodies) {
      const dx = me.x - b.x;
      const dy = me.y - b.y;
      const distSq = dx * dx + dy * dy;
      if (distSq <= bestDistSq) {
        best = b;
        bestDistSq = distSq;
      }
    }
    return best;
  }

  update({ phase, players, ownPlayerId, bodies }) {
    this._players = players || [];
    this._bodies = bodies || [];
    this._ownPlayerId = ownPlayerId;

    if (phase !== "playing" || !ownPlayerId) {
      this.btn.classList.add("hidden");
      return;
    }
    const me = this._players.find((p) => p.id === ownPlayerId);
    if (!me || me.isAlive === false) {
      this.btn.classList.add("hidden");
      return;
    }
    const body = this._closestValidBody();
    if (!body) {
      this.btn.classList.add("hidden");
      return;
    }
    this.btn.classList.remove("hidden");
    this.btn.disabled = false;
    this.btn.textContent = "Body melden";
  }
}
