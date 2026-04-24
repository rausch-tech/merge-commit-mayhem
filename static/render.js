// Pure rendering. Holds no game state — just takes snapshots.
// ROOM_LAYOUT mirrors app/game/rooms.py (must match until moved to config).

const ROOM_LAYOUT = [
  { id: "open_space", title: "Open Space", x: 0, y: 0, width: 300, height: 200, color: "#3a4560" },
  { id: "meeting_room", title: "Meeting Room", x: 300, y: 0, width: 300, height: 200, color: "#5a3a70" },
  { id: "kitchen", title: "Kitchen", x: 600, y: 0, width: 300, height: 200, color: "#7a5030" },
  { id: "server_room", title: "Server Room", x: 0, y: 200, width: 300, height: 200, color: "#2a4a70" },
  { id: "war_room", title: "War Room", x: 300, y: 200, width: 300, height: 200, color: "#2a607a" },
  { id: "legacy_basement", title: "Legacy Basement", x: 600, y: 200, width: 300, height: 200, color: "#3a6a3a" },
];

const PLAYER_RADIUS = 12;

export class Renderer {
  constructor(canvas) {
    this.ctx = canvas.getContext("2d");
    this.canvas = canvas;
    this.players = [];
    this.ownPlayerId = null;
    this._running = false;
  }

  setOwnPlayerId(id) { this.ownPlayerId = id; }
  setPlayers(players) { this.players = players; }

  start() {
    this._running = true;
    const loop = () => {
      if (!this._running) return;
      this._draw();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  stop() { this._running = false; }

  _draw() {
    const { ctx, canvas } = this;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Rooms.
    for (const room of ROOM_LAYOUT) {
      ctx.fillStyle = room.color;
      ctx.fillRect(room.x, room.y, room.width, room.height);
      ctx.strokeStyle = "#0b0f1f";
      ctx.lineWidth = 2;
      ctx.strokeRect(room.x, room.y, room.width, room.height);

      ctx.fillStyle = "rgba(230,236,255,0.85)";
      ctx.font = "12px system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText(room.title.toUpperCase(), room.x + 8, room.y + 8);
    }

    // Players.
    for (const player of this.players) {
      ctx.beginPath();
      ctx.arc(player.x, player.y, PLAYER_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = player.color;
      ctx.fill();

      if (player.id === this.ownPlayerId) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 3;
        ctx.stroke();
      } else {
        ctx.strokeStyle = "rgba(0,0,0,0.4)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      ctx.fillStyle = "#e6ecff";
      ctx.font = "12px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillText(player.name, player.x, player.y - PLAYER_RADIUS - 4);
    }
  }
}
