// Pure rendering. Holds no game state -- just takes snapshots.
// Map data is received from the server via setMap() on room_joined.

import { drawSprite, loadSheet } from "./sprites.js";

// Preload task spritesheet so it's cached before the first frame needs it.
loadSheet("/images/ui_icon_set.png");

// Preload character sheet so first frame can already use the sprite.
loadSheet("/images/figuren.png");

// Map hex color to character index (must mirror app/game/game_room.py _COLOR_PALETTE order).
const COLOR_TO_CHAR_INDEX = {
  "#4ade80": 0,  // green
  "#60a5fa": 1,  // blue
  "#fb923c": 2,  // orange
  "#c084fc": 3,  // purple
  "#facc15": 4,  // yellow
  "#f87171": 5,  // red
};

const CHARACTER_RENDER_SIZE = 56;  // px on screen
const PLAYER_RADIUS = 12;

const WALL_THICKNESS = 8;

/**
 * Mirror of the server-side compute_walls() in app/game/game_map.py.
 * Accepts the map JSON received in room_joined and returns wall rectangles
 * as [x1, y1, x2, y2] arrays.
 */
function computeWallsClient(map) {
  if (!map || !map.wallLines) return [];
  const out = [];
  const mapW = map.size?.width ?? 0;
  const mapH = map.size?.height ?? 0;
  for (const line of map.wallLines) {
    const doors = [...(line.doors || [])].sort((a, b) => a.center - b.center);
    if (line.axis === "x") {
      // Vertical wall line at x=line.position
      let lastY = 0;
      for (const d of doors) {
        const top = d.center - Math.floor(d.width / 2);
        if (top > lastY) {
          out.push([line.position - WALL_THICKNESS, lastY, line.position + WALL_THICKNESS, top]);
        }
        lastY = d.center + Math.floor(d.width / 2);
      }
      if (lastY < mapH) {
        out.push([line.position - WALL_THICKNESS, lastY, line.position + WALL_THICKNESS, mapH]);
      }
    } else {
      // Horizontal wall line at y=line.position
      let lastX = 0;
      for (const d of doors) {
        const left = d.center - Math.floor(d.width / 2);
        if (left > lastX) {
          out.push([lastX, line.position - WALL_THICKNESS, left, line.position + WALL_THICKNESS]);
        }
        lastX = d.center + Math.floor(d.width / 2);
      }
      if (lastX < mapW) {
        out.push([lastX, line.position - WALL_THICKNESS, mapW, line.position + WALL_THICKNESS]);
      }
    }
  }
  return out;
}

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
    this.map = null;     // populated via setMap()
    this._walls = [];    // computed when setMap is called
  }

  setOwnPlayerId(id) { this.ownPlayerId = id; }
  setPlayers(players) { this.players = players; }
  setTasks(tasks) { this.tasks = tasks; }

  setMap(map) {
    this.map = map;
    this._walls = computeWallsClient(map);
  }

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
    if (!this.map) return;  // not yet received

    const mapW = this.map.size.width;
    const mapH = this.map.size.height;

    // Camera centered on local player, clamped to map bounds.
    const local = this._localPlayer();
    const cameraX = local
      ? clamp(local.x - canvas.width / 2, 0, Math.max(0, mapW - canvas.width))
      : 0;
    const cameraY = local
      ? clamp(local.y - canvas.height / 2, 0, Math.max(0, mapH - canvas.height))
      : 0;

    ctx.save();
    ctx.translate(-cameraX, -cameraY);

    // Rooms.
    for (const room of this.map.rooms) {
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
    for (const [wx1, wy1, wx2, wy2] of this._walls) {
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

      // Cooldown overlay -- semi-transparent black.
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
      const isDead = player.isAlive === false;
      const charIndex = COLOR_TO_CHAR_INDEX[player.color] ?? 0;
      const half = CHARACTER_RENDER_SIZE / 2;
      ctx.save();
      ctx.globalAlpha = isDead ? 0.35 : 1.0;

      // Colored ring at feet (player identity color stays visible).
      ctx.beginPath();
      ctx.ellipse(
        player.x, player.y + half * 0.85,
        half * 0.7, half * 0.22,
        0, 0, Math.PI * 2
      );
      ctx.fillStyle = player.color;
      ctx.globalAlpha = isDead ? 0.35 * 0.55 : 0.55;
      ctx.fill();
      ctx.globalAlpha = isDead ? 0.35 : 1.0;
      ctx.strokeStyle = "#0b0f1f";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Sprite -- fallback to colored circle while loading.
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

      // Name above the head -- moved up so it doesn't clip the sprite.
      ctx.fillStyle = "#e6ecff";
      ctx.font = "13px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "bottom";
      ctx.fillText(player.name, player.x, player.y - half - 6);

      ctx.restore();
    }

    ctx.restore();
  }
}
