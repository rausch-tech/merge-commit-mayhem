// Pure rendering. Holds no game state — just takes snapshots.
// ROOM_LAYOUT mirrors app/game/rooms.py (must match until moved to config).

import { drawSprite, loadSheet } from "./sprites.js";

// Preload task spritesheet so it's cached before the first frame needs it.
loadSheet("/images/ui_icon_set.png");

// Preload character sheet so first frame can already use the sprite.
loadSheet("/images/figuren.png");

// Map hex color → character index (must mirror app/game/game_room.py _COLOR_PALETTE order).
const COLOR_TO_CHAR_INDEX = {
  "#4ade80": 0,  // green
  "#60a5fa": 1,  // blue
  "#fb923c": 2,  // orange
  "#c084fc": 3,  // purple
  "#facc15": 4,  // yellow
  "#f87171": 5,  // red
};

const CHARACTER_RENDER_SIZE = 56;  // px on screen — bigger than the old 24px circle

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

const WALL_THICKNESS = 8;
const DOOR_WIDTH = 120;

// Mirror of app/game/walls.py WALLS — same coordinates so visuals match server collision.
const WALLS = (() => {
  const list = [];
  // Vertical walls at x=800 and x=1600 with doors at y=400, 1200.
  for (const lineX of [800, 1600]) {
    let lastY = 0;
    for (const doorY of [400, 1200]) {
      const top = doorY - DOOR_WIDTH / 2;
      if (top > lastY) {
        list.push([lineX - WALL_THICKNESS, lastY, lineX + WALL_THICKNESS, top]);
      }
      lastY = doorY + DOOR_WIDTH / 2;
    }
    if (lastY < MAP_HEIGHT) {
      list.push([lineX - WALL_THICKNESS, lastY, lineX + WALL_THICKNESS, MAP_HEIGHT]);
    }
  }
  // Horizontal wall at y=800 with doors at x=400, 1200, 2000.
  let lastX = 0;
  for (const doorX of [400, 1200, 2000]) {
    const left = doorX - DOOR_WIDTH / 2;
    if (left > lastX) {
      list.push([lastX, 800 - WALL_THICKNESS, left, 800 + WALL_THICKNESS]);
    }
    lastX = doorX + DOOR_WIDTH / 2;
  }
  if (lastX < MAP_WIDTH) {
    list.push([lastX, 800 - WALL_THICKNESS, MAP_WIDTH, 800 + WALL_THICKNESS]);
  }
  return list;
})();

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

    // Walls.
    ctx.fillStyle = "#0b0f1f";
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 1;
    for (const [wx1, wy1, wx2, wy2] of WALLS) {
      ctx.fillRect(wx1, wy1, wx2 - wx1, wy2 - wy1);
      ctx.strokeRect(wx1, wy1, wx2 - wx1, wy2 - wy1);
    }

    // Tasks.
    let inRange = null;
    const TASK_RADIUS = 14;
    const INTERACT_RADIUS = 40;
    const TILE = 40;
    for (const task of this.tasks) {
      let fill = "#4ade80";
      if (task.status === "in_progress") fill = "#60a5fa";
      else if (task.status === "cooldown") fill = "#475569";

      // Background plate (status-colored halo ring).
      ctx.beginPath();
      ctx.arc(task.x, task.y, TASK_RADIUS + 6, 0, Math.PI * 2);
      ctx.fillStyle = fill;
      ctx.globalAlpha = 0.35;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = "#0b0f1f";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Sprite (or fallback colored circle + 2-letter label).
      const drew = drawSprite(ctx, `task_${task.id}`, task.x, task.y, TILE, TILE);
      if (!drew) {
        ctx.beginPath();
        ctx.arc(task.x, task.y, TASK_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = fill;
        ctx.fill();
        ctx.fillStyle = "#0b0f1f";
        ctx.font = "bold 10px system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(task.title.slice(0, 2).toUpperCase(), task.x, task.y);
      }

      // Cooldown overlay — semi-transparent black.
      if (task.status === "cooldown") {
        ctx.beginPath();
        ctx.arc(task.x, task.y, TILE / 2 + 2, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(0,0,0,0.55)";
        ctx.fill();
      }

      // Progress ring if in_progress.
      if (task.status === "in_progress" && task.progress > 0) {
        ctx.beginPath();
        ctx.arc(
          task.x, task.y, TASK_RADIUS + 8,
          -Math.PI / 2,
          -Math.PI / 2 + (task.progress * Math.PI * 2)
        );
        ctx.strokeStyle = "#facc15";
        ctx.lineWidth = 3;
        ctx.stroke();
      }

      // Hover/in-range halo.
      if (local && task.status !== "cooldown") {
        const dx = local.x - task.x;
        const dy = local.y - task.y;
        if (dx * dx + dy * dy <= INTERACT_RADIUS * INTERACT_RADIUS) {
          ctx.beginPath();
          ctx.arc(task.x, task.y, TILE / 2 + 6, 0, Math.PI * 2);
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
      const charIndex = COLOR_TO_CHAR_INDEX[player.color] ?? 0;
      const half = CHARACTER_RENDER_SIZE / 2;

      // Colored ring at feet (player identity color stays visible).
      ctx.beginPath();
      ctx.ellipse(
        player.x, player.y + half * 0.85,
        half * 0.7, half * 0.22,
        0, 0, Math.PI * 2
      );
      ctx.fillStyle = player.color;
      ctx.globalAlpha = 0.55;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = "#0b0f1f";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Sprite — fallback to colored circle while loading.
      const drew = drawSprite(
        ctx,
        `character_${charIndex}`,
        player.x,
        player.y,
        CHARACTER_RENDER_SIZE,
        CHARACTER_RENDER_SIZE,
      );
      if (!drew) {
        ctx.beginPath();
        ctx.arc(player.x, player.y, PLAYER_RADIUS, 0, Math.PI * 2);
        ctx.fillStyle = player.color;
        ctx.fill();
        ctx.strokeStyle = "rgba(0,0,0,0.4)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Local-player highlight: thin white halo around the character.
      if (player.id === this.ownPlayerId) {
        ctx.beginPath();
        ctx.arc(player.x, player.y, half + 2, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.85)";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Name above the head — moved up so it doesn't clip the sprite.
      ctx.fillStyle = "#e6ecff";
      ctx.font = "13px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillText(player.name, player.x, player.y - half - 6);
    }

    ctx.restore();
  }
}
