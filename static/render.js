// Pure rendering. Holds no game state — just takes snapshots.
// ROOM_LAYOUT mirrors app/game/rooms.py (must match until moved to config).

const ROOM_LAYOUT = [
  { id: "open_space",      title: "Open Space",      x: 0,    y: 0,    width: 800, height: 800, color: "#3a4560" },
  { id: "meeting_room",    title: "Meeting Room",    x: 800,  y: 0,    width: 800, height: 800, color: "#5a3a70" },
  { id: "kitchen",         title: "Kitchen",         x: 1600, y: 0,    width: 800, height: 800, color: "#7a5030" },
  { id: "server_room",     title: "Server Room",     x: 0,    y: 800,  width: 800, height: 800, color: "#2a4a70" },
  { id: "war_room",        title: "War Room",        x: 800,  y: 800,  width: 800, height: 800, color: "#2a607a" },
  { id: "legacy_basement", title: "Legacy Basement", x: 1600, y: 800,  width: 800, height: 800, color: "#3a6a3a" },
];

const PLAYER_RADIUS = 12;
const MAP_WIDTH = 2400;
const MAP_HEIGHT = 1600;

function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }

export class Renderer {
  constructor(canvas) {
    this.ctx = canvas.getContext("2d");
    this.canvas = canvas;
    this.players = [];
    this.ownPlayerId = null;
    this.tasks = [];
    this.localPlayerInRange = null;  // task-id of the task within interaction radius for the local player, else null
    this._running = false;
  }

  setOwnPlayerId(id) { this.ownPlayerId = id; }
  setPlayers(players) { this.players = players; }
  setTasks(tasks) { this.tasks = tasks; }

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

  _localPlayer() {
    if (!this.ownPlayerId) return null;
    return this.players.find((p) => p.id === this.ownPlayerId) || null;
  }

  _draw() {
    const { ctx, canvas } = this;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Camera centered on local player, clamped to map bounds.
    const local = this._localPlayer();
    const cameraX = local
      ? clamp(local.x - canvas.width / 2, 0, Math.max(0, MAP_WIDTH - canvas.width))
      : 0;
    const cameraY = local
      ? clamp(local.y - canvas.height / 2, 0, Math.max(0, MAP_HEIGHT - canvas.height))
      : 0;

    ctx.save();
    ctx.translate(-cameraX, -cameraY);

    // Rooms.
    for (const room of ROOM_LAYOUT) {
      ctx.fillStyle = room.color;
      ctx.fillRect(room.x, room.y, room.width, room.height);
      ctx.strokeStyle = "#0b0f1f";
      ctx.lineWidth = 2;
      ctx.strokeRect(room.x, room.y, room.width, room.height);

      ctx.fillStyle = "rgba(230,236,255,0.85)";
      ctx.font = "16px system-ui, sans-serif";
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillText(room.title.toUpperCase(), room.x + 12, room.y + 12);
    }

    // Tasks.
    let inRange = null;
    const TASK_RADIUS = 14;
    const INTERACT_RADIUS = 40;
    for (const task of this.tasks) {
      let fill = "#4ade80";
      if (task.status === "in_progress") fill = "#60a5fa";
      else if (task.status === "cooldown") fill = "#475569";

      ctx.beginPath();
      ctx.arc(task.x, task.y, TASK_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.strokeStyle = "#0b0f1f";
      ctx.lineWidth = 2;
      ctx.stroke();

      if (task.status === "in_progress" && task.progress > 0) {
        ctx.beginPath();
        ctx.arc(
          task.x, task.y, TASK_RADIUS + 4,
          -Math.PI / 2,
          -Math.PI / 2 + (task.progress * Math.PI * 2)
        );
        ctx.strokeStyle = "#facc15";
        ctx.lineWidth = 3;
        ctx.stroke();
      }

      ctx.fillStyle = "#0b0f1f";
      ctx.font = "bold 10px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(task.title.slice(0, 2).toUpperCase(), task.x, task.y);

      if (local && task.status !== "cooldown") {
        const dx = local.x - task.x;
        const dy = local.y - task.y;
        if (dx * dx + dy * dy <= INTERACT_RADIUS * INTERACT_RADIUS) {
          ctx.beginPath();
          ctx.arc(task.x, task.y, TASK_RADIUS + 8, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(250, 204, 21, 0.7)";
          ctx.lineWidth = 2;
          ctx.setLineDash([4, 3]);
          ctx.stroke();
          ctx.setLineDash([]);
          if (!inRange) inRange = task.id;
        }
      }
    }
    this.localPlayerInRange = inRange;

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

    ctx.restore();
  }
}
