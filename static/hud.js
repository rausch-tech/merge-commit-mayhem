export class Hud {
  constructor() {
    this.timerEl = document.getElementById("hud-timer");
    this.roleEl = document.getElementById("hud-role");
    this.playersEl = document.getElementById("hud-players");
  }

  setTimer(seconds) {
    const m = Math.max(0, Math.floor(seconds / 60));
    const s = Math.max(0, Math.floor(seconds % 60));
    this.timerEl.textContent = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  setRole(role, team) {
    const label = role === "vibe_coder" ? "Vibe Coder (Chaos)" : role;
    this.roleEl.textContent = `Rolle: ${label}`;
    if (team === "chaos_agents") {
      this.roleEl.style.background = "#4a1e1e";
    }
  }

  setPlayers(players) {
    this.playersEl.textContent = `Spieler: ${players.length}`;
  }
}
