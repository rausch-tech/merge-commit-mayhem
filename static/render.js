// Pure rendering. Holds no game state -- just takes snapshots.
// Map data is received from the server via setMap() on room_joined.

import { drawSprite, loadSheet } from "./sprites.js";

// Preload task spritesheet so it's cached before the first frame needs it.
loadSheet("/images/ui_icon_set.png");

// Preload character sheet so first frame can already use the sprite.
loadSheet("/images/figuren.png");

// Map hex color to character index (must mirror app/game/game_room.py _COLOR_PALETTE order).
const COLOR_TO_CHAR_INDEX = {
  "#4ade80": 0, // green
  "#60a5fa": 1, // blue
  "#fb923c": 2, // orange
  "#c084fc": 3, // purple
  "#facc15": 4, // yellow
  "#f87171": 5, // red
};

const CHARACTER_RENDER_SIZE = 56; // px on screen
const PLAYER_RADIUS = 12;

const WALL_THICKNESS = 8;

/**
 * Mirror of the server-side compute_walls() in app/game/game_map.py.
 * Slice-3 schema: walls are auto-derived from adjacent room edges minus
 * door cutouts. Map-perimeter edges are NOT walled (player-clamp handles
 * map boundaries on the server). Returns rectangles as [x1, y1, x2, y2].
 */
function computeWallsClient(map) {
  if (!map || !Array.isArray(map.rooms)) return [];
  const rooms = map.rooms;
  const doors = Array.isArray(map.doors) ? map.doors : [];
  const mapW = map.size?.width ?? 0;
  const mapH = map.size?.height ?? 0;
  const out = [];
  const processed = new Set();

  const wallRect = (axis, edgePos, segStart, segEnd) =>
    axis === "x"
      ? [edgePos - WALL_THICKNESS, segStart, edgePos + WALL_THICKNESS, segEnd]
      : [segStart, edgePos - WALL_THICKNESS, segEnd, edgePos + WALL_THICKNESS];

  const isMapEdge = (axis, edgePos) =>
    axis === "x" ? edgePos === 0 || edgePos === mapW : edgePos === 0 || edgePos === mapH;

  const intervalSubtract = (start, end, cutouts) => {
    if (start >= end) return [];
    if (!cutouts.length) return [[start, end]];
    const clipped = cutouts
      .map(([a, b]) => [Math.max(a, start), Math.min(b, end)])
      .filter(([a, b]) => a < b)
      .sort((p, q) => p[0] - q[0]);
    const result = [];
    let cursor = start;
    for (const [a, b] of clipped) {
      if (a > cursor) result.push([cursor, a]);
      cursor = Math.max(cursor, b);
    }
    if (cursor < end) result.push([cursor, end]);
    return result;
  };

  const edgeOverlap = (other, axis, edgePos, start, end) => {
    if (axis === "x") {
      if (other.x !== edgePos && other.x + other.width !== edgePos) return null;
      const a = Math.max(start, other.y);
      const b = Math.min(end, other.y + other.height);
      return a < b ? [a, b] : null;
    }
    if (other.y !== edgePos && other.y + other.height !== edgePos) return null;
    const a = Math.max(start, other.x);
    const b = Math.min(end, other.x + other.width);
    return a < b ? [a, b] : null;
  };

  for (const room of rooms) {
    const edges = [
      ["y", room.y, room.x, room.x + room.width],
      ["y", room.y + room.height, room.x, room.x + room.width],
      ["x", room.x, room.y, room.y + room.height],
      ["x", room.x + room.width, room.y, room.y + room.height],
    ];
    for (const [axis, edgePos, start, end] of edges) {
      const sharedList = [];
      for (const other of rooms) {
        if (other.id === room.id) continue;
        const ovl = edgeOverlap(other, axis, edgePos, start, end);
        if (ovl) sharedList.push([other.id, ovl]);
      }
      // Shared portions, dedup per pair.
      for (const [otherId, ovl] of sharedList) {
        const pairKey = [room.id, otherId].sort();
        const key = `${axis}|${edgePos}|${pairKey[0]}|${pairKey[1]}|${ovl[0]}|${ovl[1]}`;
        if (processed.has(key)) continue;
        processed.add(key);
        const cutouts = [];
        for (const door of doors) {
          const dPair = [door.betweenRoomA, door.betweenRoomB].sort();
          if (dPair[0] !== pairKey[0] || dPair[1] !== pairKey[1]) continue;
          if (door.position < ovl[0] || door.position > ovl[1]) continue;
          const half = Math.floor((door.width ?? 240) / 2);
          cutouts.push([door.position - half, door.position + half]);
        }
        for (const [segStart, segEnd] of intervalSubtract(ovl[0], ovl[1], cutouts)) {
          out.push(wallRect(axis, edgePos, segStart, segEnd));
        }
      }
      // Perimeter portions — skip if the edge is on the map outer boundary.
      if (!isMapEdge(axis, edgePos)) {
        const sharedCuts = sharedList.map(([, ovl]) => ovl);
        for (const [segStart, segEnd] of intervalSubtract(start, end, sharedCuts)) {
          out.push(wallRect(axis, edgePos, segStart, segEnd));
        }
      }
    }
  }
  return out;
}

function clamp(v, lo, hi) {
  return v < lo ? lo : v > hi ? hi : v;
}

// --- MapObject rendering (Tier 4) ------------------------------------------
//
// The server sends ``map.mapObjects`` as an array of axis-aligned props with
// a logical ``kind`` string. The browser draws each as a coloured rectangle
// with a short label — this is intentionally placeholder-grade. Godot's
// 3D client (separate branch) maps the same ``kind`` to a real .gltf scene.

// kind → {fill, label}. New kinds added to the server should also land here
// so the placeholder stays meaningful. Unknown kinds fall back to a neutral
// grey + the kind string itself as label.
const MAP_OBJECT_STYLE = {
  // Workstation cluster
  desk: { fill: "#7c5a3a", label: "DESK" },
  desk_large: { fill: "#7c5a3a", label: "DESK" },
  desk_decorated: { fill: "#7c5a3a", label: "DESK" },
  chair_desk: { fill: "#3f3128", label: "" },
  monitor: { fill: "#1f2937", label: "MON" },
  keyboard: { fill: "#1f2937", label: "" },
  mouse_pad: { fill: "#1f2937", label: "" },
  mug: { fill: "#a16207", label: "" },
  lamp_desk: { fill: "#fbbf24", label: "" },

  // Server room
  server_rack: { fill: "#1e293b", label: "RACK" },
  monitoring_panel: { fill: "#0ea5e9", label: "PANEL" },
  cabinet: { fill: "#3f3f46", label: "" },

  // Meeting / War Room
  meeting_table: { fill: "#52525b", label: "TABLE" },
  presentation_screen: { fill: "#1e1b4b", label: "SCRN" },
  chair_meeting: { fill: "#3f3128", label: "" },

  // Kitchen
  kitchen_counter: { fill: "#9ca3af", label: "CNTR" },
  kitchen_corner: { fill: "#9ca3af", label: "CNTR" },
  kitchen_sink: { fill: "#94a3b8", label: "SINK" },
  coffee_machine: { fill: "#854d0e", label: "COFFEE" },
  fridge: { fill: "#cbd5e1", label: "FRIDGE" },
  chair_stool: { fill: "#3f3128", label: "" },

  // Decor (blocks_movement usually false)
  plant_cactus: { fill: "#15803d", label: "" },
  picture_frame: { fill: "#a78bfa", label: "" },
  rug: { fill: "#7e22ce", label: "" },
  cup_pencils: { fill: "#a16207", label: "" },

  // Legacy basement
  crate: { fill: "#78350f", label: "CRATE" },
  old_workstation: { fill: "#44403c", label: "OLD" },
};

function drawMapObjects(ctx, mapObjects) {
  if (!Array.isArray(mapObjects)) return;
  for (const obj of mapObjects) {
    const x = obj.x ?? 0;
    const y = obj.y ?? 0;
    const w = obj.width ?? 0;
    const h = obj.height ?? 0;
    const rotation = obj.rotation ?? 0;
    // 90 / 270 swap dimensions visually too — the client mirrors the server's
    // map_object_aabb() so collision and render line up exactly.
    const dw = rotation === 90 || rotation === 270 ? h : w;
    const dh = rotation === 90 || rotation === 270 ? w : h;
    const style = MAP_OBJECT_STYLE[obj.kind] || { fill: "#475569", label: obj.kind || "?" };

    ctx.fillStyle = style.fill;
    ctx.globalAlpha = obj.blocksMovement === false ? 0.5 : 1;
    ctx.fillRect(x - dw / 2, y - dh / 2, dw, dh);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = "#0b0f1f";
    ctx.lineWidth = 1;
    ctx.strokeRect(x - dw / 2, y - dh / 2, dw, dh);

    if (style.label && Math.min(dw, dh) >= 30) {
      ctx.fillStyle = "rgba(255,255,255,0.85)";
      ctx.font = "bold 10px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(style.label, x, y);
    }
  }
}

export class Renderer {
  constructor(canvas) {
    this.ctx = canvas.getContext("2d");
    this.canvas = canvas;
    this.players = [];
    this.ownPlayerId = null;
    this.tasks = [];
    this.bodies = [];
    this.localPlayerInRange = null; // task-id of the task within interaction radius for the local player, else null
    this.localPlayerNearPanel = null; // sabotage-id of an active repair panel within reach, else null (Tier 2.4)
    this.activePanels = []; // [{sabotageId, x, y}] for currently-broken sabotages
    this.lightsOff = false; // toggles the radial vignette (Tier 2.4)
    this.vents = []; // [{id, x, y, connectedTo: [...]}] (Tier 2.3)
    this.ownTeam = null; // 'release_team' | 'chaos_agents' | null
    this.localPlayerNearVent = null; // vent object the local chaos player is in reach of, else null
    // Tier 2.7 rework: per-sabotage proximity. Map of sabotageId → bool, true
    // when the local chaos player stands in reach of any matching task anchor.
    this.sabotageObjectAvailability = {};
    this._running = false;
    this.map = null; // populated via setMap()
    this._walls = []; // computed when setMap is called
  }

  setOwnPlayerId(id) {
    this.ownPlayerId = id;
  }
  setPlayers(players) {
    this.players = players;
  }
  setTasks(tasks) {
    this.tasks = tasks;
  }
  setBodies(bodies) {
    this.bodies = bodies || [];
  }
  setActivePanels(panels) {
    this.activePanels = panels || [];
  }
  setLightsOff(value) {
    this.lightsOff = !!value;
  }
  setVents(vents) {
    this.vents = vents || [];
  }
  setSabotagesPayload(sabotages) {
    // Tier 2.7 rework: server tells us which sabotages exist + their allowed
    // anchor positions. We compute per-sabotage proximity locally each frame
    // (cheap — handful of distance checks) and feed sabotages.js for button
    // enable/disable.
    this._sabotagePayload = sabotages || [];
  }
  setOwnTeam(team) {
    this.ownTeam = team || null;
  }

  setMap(map) {
    this.map = map;
    this._walls = computeWallsClient(map);
  }

  resize() {
    // Match canvas backbuffer to displayed size for crisp rendering.
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.max(1, Math.floor(rect.width * dpr));
    this.canvas.height = Math.max(1, Math.floor(rect.height * dpr));
    // Reset transform; the camera transform is reapplied each _draw().
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
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

  stop() {
    this._running = false;
  }

  _localPlayer() {
    if (!this.ownPlayerId) return null;
    return this.players.find((p) => p.id === this.ownPlayerId) || null;
  }

  _draw() {
    const { ctx, canvas } = this;
    const dpr = window.devicePixelRatio || 1;
    const viewW = canvas.width / dpr;
    const viewH = canvas.height / dpr;

    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // reset to CSS-px
    ctx.clearRect(0, 0, viewW, viewH);

    if (!this.map) {
      ctx.restore();
      return;
    }

    const mapW = this.map.size.width;
    const mapH = this.map.size.height;

    // Camera centered on local player, clamped to map bounds.
    const local = this._localPlayer();
    const cameraX = local ? clamp(local.x - viewW / 2, 0, Math.max(0, mapW - viewW)) : 0;
    const cameraY = local ? clamp(local.y - viewH / 2, 0, Math.max(0, mapH - viewH)) : 0;

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

    // Map objects (Tier 4 props — desks, server racks, plants).
    // Drawn between rooms and walls so a wall sitting on top of an object
    // (e.g. a desk against a room edge) wins visually.
    if (Array.isArray(this.map.mapObjects)) {
      drawMapObjects(ctx, this.map.mapObjects);
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
          task.x,
          task.y,
          TASK_RADIUS + 8,
          -Math.PI / 2,
          -Math.PI / 2 + task.progress * Math.PI * 2
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

    // Sabotage repair panels (Tier 2.4). Drawn before players so the player
    // marker can stand on top.
    const PANEL_INTERACT_RADIUS = 50; // mirror of SABOTAGE_PANEL_INTERACTION_RADIUS
    let nearPanel = null;
    for (const panel of this.activePanels) {
      ctx.save();
      // Pulsing red diamond — reads as "broken thing, fix me".
      const pulse = 0.7 + 0.3 * Math.sin(Date.now() / 220);
      ctx.translate(panel.x, panel.y);
      ctx.rotate(Math.PI / 4);
      ctx.fillStyle = `rgba(239, 68, 68, ${pulse.toFixed(3)})`;
      ctx.fillRect(-14, -14, 28, 28);
      ctx.strokeStyle = "#0b0f1f";
      ctx.lineWidth = 2;
      ctx.strokeRect(-14, -14, 28, 28);
      ctx.restore();
      ctx.save();
      ctx.fillStyle = "#fef2f2";
      ctx.font = "bold 12px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("!", panel.x, panel.y);
      ctx.restore();

      if (local) {
        const dx = local.x - panel.x;
        const dy = local.y - panel.y;
        if (dx * dx + dy * dy <= PANEL_INTERACT_RADIUS * PANEL_INTERACT_RADIUS) {
          ctx.beginPath();
          ctx.arc(panel.x, panel.y, PANEL_INTERACT_RADIUS, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(74, 222, 128, 0.85)";
          ctx.lineWidth = 2;
          ctx.setLineDash([6, 4]);
          ctx.stroke();
          ctx.setLineDash([]);
          if (!nearPanel) nearPanel = panel.sabotageId;
        }
      }
    }
    this.localPlayerNearPanel = nearPanel;

    // Vents (Tier 2.3). Drawn for everyone — they are part of the world's
    // architecture. Only chaos can interact with them. Visibility was a
    // playtest pain point: dark-on-dark backgrounds made them invisible.
    // Editor-slice-1: lighter steel finish + outer halo so they pop
    // against any room tint, and slightly bigger footprint.
    const VENT_INTERACT_RADIUS = 50;
    const VENT_HALF_W = 16;
    const VENT_HALF_H = 14;
    let nearVent = null;
    for (const vent of this.vents) {
      ctx.save();
      // Outer halo so the vent is findable on a dark room background.
      ctx.fillStyle = "rgba(148, 163, 184, 0.22)";
      ctx.beginPath();
      ctx.arc(vent.x, vent.y, VENT_HALF_W + 8, 0, Math.PI * 2);
      ctx.fill();
      // Steel grille body — lighter slate so it contrasts the dark floor.
      ctx.fillStyle = "#64748b";
      ctx.fillRect(vent.x - VENT_HALF_W, vent.y - VENT_HALF_H, VENT_HALF_W * 2, VENT_HALF_H * 2);
      ctx.strokeStyle = "#0b0f1f";
      ctx.lineWidth = 2;
      ctx.strokeRect(vent.x - VENT_HALF_W, vent.y - VENT_HALF_H, VENT_HALF_W * 2, VENT_HALF_H * 2);
      // Grates: brighter horizontal slats for legibility.
      ctx.beginPath();
      for (let i = 0; i < 4; i++) {
        const yy = vent.y - VENT_HALF_H + 4 + i * ((VENT_HALF_H * 2 - 8) / 3);
        ctx.moveTo(vent.x - VENT_HALF_W + 3, yy);
        ctx.lineTo(vent.x + VENT_HALF_W - 3, yy);
      }
      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.restore();

      if (this.ownTeam === "chaos_agents" && local) {
        const dx = local.x - vent.x;
        const dy = local.y - vent.y;
        if (dx * dx + dy * dy <= VENT_INTERACT_RADIUS * VENT_INTERACT_RADIUS) {
          ctx.beginPath();
          ctx.arc(vent.x, vent.y, VENT_INTERACT_RADIUS, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(96, 165, 250, 0.7)";
          ctx.lineWidth = 2;
          ctx.setLineDash([5, 4]);
          ctx.stroke();
          ctx.setLineDash([]);
          if (!nearVent) nearVent = vent;
        }
      }
    }
    this.localPlayerNearVent = nearVent;

    // Tier 2.7 rework: per-sabotage proximity (no dedicated "console" — chaos
    // triggers each sabotage at the same anchor that the matching task uses).
    // Compute one bool per sabotage, exposed via this.sabotageObjectAvailability.
    const SABOTAGE_OBJECT_RADIUS = 60;
    const r2 = SABOTAGE_OBJECT_RADIUS * SABOTAGE_OBJECT_RADIUS;
    const availability = {};
    if (this.ownTeam === "chaos_agents" && local) {
      for (const sab of this._sabotagePayload || []) {
        const anchors = sab.triggerAnchors || [];
        if (anchors.length === 0) {
          availability[sab.id] = true; // legacy: no binding
          continue;
        }
        let near = false;
        for (const a of anchors) {
          const dx = local.x - a.x;
          const dy = local.y - a.y;
          if (dx * dx + dy * dy <= r2) {
            near = true;
            // Faint dashed reach indicator on the matching anchor.
            ctx.beginPath();
            ctx.arc(a.x, a.y, SABOTAGE_OBJECT_RADIUS, 0, Math.PI * 2);
            ctx.strokeStyle = "rgba(248, 113, 113, 0.6)";
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 4]);
            ctx.stroke();
            ctx.setLineDash([]);
            break;
          }
        }
        availability[sab.id] = near;
      }
    }
    this.sabotageObjectAvailability = availability;

    // Bodies (rendered BEFORE players so live players draw on top).
    for (const body of this.bodies) {
      ctx.save();
      ctx.globalAlpha = 0.55;
      // Filled circle in the victim's color, slightly desaturated via alpha.
      ctx.beginPath();
      ctx.arc(body.x, body.y, PLAYER_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = body.color || "#475569";
      ctx.fill();
      // Darker outline so the body reads as inert vs a live player.
      ctx.strokeStyle = "rgba(0,0,0,0.85)";
      ctx.lineWidth = 2;
      ctx.stroke();
      // X marker so it's unmistakably "down".
      ctx.beginPath();
      ctx.moveTo(body.x - 6, body.y - 6);
      ctx.lineTo(body.x + 6, body.y + 6);
      ctx.moveTo(body.x + 6, body.y - 6);
      ctx.lineTo(body.x - 6, body.y + 6);
      ctx.strokeStyle = "rgba(15, 23, 42, 0.95)";
      ctx.lineWidth = 2.5;
      ctx.stroke();
      ctx.restore();
    }

    // Players.
    for (const player of this.players) {
      const isDead = player.isAlive === false;
      const isDisconnected = player.isConnected === false;
      const charIndex = COLOR_TO_CHAR_INDEX[player.color] ?? 0;
      const half = CHARACTER_RENDER_SIZE / 2;
      ctx.save();
      // Ghosts and disconnected players both render at 0.5 alpha; living
      // players draw fully opaque. Color stays the player's own color.
      ctx.globalAlpha = isDead || isDisconnected ? 0.5 : 1.0;

      // Colored ring at feet (player identity color stays visible).
      ctx.beginPath();
      ctx.ellipse(player.x, player.y + half * 0.85, half * 0.7, half * 0.22, 0, 0, Math.PI * 2);
      ctx.fillStyle = player.color;
      ctx.globalAlpha = isDead || isDisconnected ? 0.5 * 0.55 : 0.55;
      ctx.fill();
      ctx.globalAlpha = isDead || isDisconnected ? 0.5 : 1.0;
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
        CHARACTER_RENDER_SIZE
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
      const displayName = player.name + (isDisconnected ? " (off)" : "");
      ctx.fillText(displayName, player.x, player.y - half - 6);

      ctx.restore();
    }

    // Lights-out vignette (Tier 2.4). Applied AFTER world rendering, BEFORE
    // we restore the camera transform so the cutout can follow the player in
    // world space. Outside the cutout the canvas reads near-black; inside a
    // ~150 px radius the world remains visible.
    if (this.lightsOff && local) {
      ctx.save();
      const grad = ctx.createRadialGradient(local.x, local.y, 60, local.x, local.y, 220);
      grad.addColorStop(0, "rgba(0, 0, 0, 0)");
      grad.addColorStop(0.55, "rgba(0, 0, 0, 0.6)");
      grad.addColorStop(1, "rgba(0, 0, 0, 0.95)");
      ctx.fillStyle = grad;
      // Cover the entire visible viewport in world coordinates.
      ctx.fillRect(cameraX, cameraY, viewW, viewH);
      ctx.restore();
    }

    ctx.restore();

    // Minimap overlay — drawn in screen space, after the camera restore so it
    // stays glued to the top-right corner instead of moving with the player.
    this._drawMinimap(viewW, viewH);
  }

  /**
   * Top-right minimap. Shows only what the local player is allowed to see:
   * room layout (dim), own player position, own visible tasks, active
   * sabotage panels. Other players are intentionally NOT drawn — this is a
   * social-deduction game and the minimap must not leak position info.
   */
  _drawMinimap(viewW, viewH) {
    if (!this.map) return;
    const isTouch = document.body.classList.contains("touch-active");
    const maxSize = isTouch ? 110 : 140;
    const padding = isTouch ? 8 : 12;

    const mapW = this.map.size.width;
    const mapH = this.map.size.height;
    if (mapW <= 0 || mapH <= 0) return;
    const aspect = mapW / mapH;
    const mw = aspect >= 1 ? maxSize : maxSize * aspect;
    const mh = aspect >= 1 ? maxSize / aspect : maxSize;

    const x0 = viewW - mw - padding;
    const y0 = padding;
    const sx = mw / mapW;
    const sy = mh / mapH;
    const toX = (wx) => x0 + wx * sx;
    const toY = (wy) => y0 + wy * sy;

    const ctx = this.ctx;
    ctx.save();

    // Background panel + border.
    ctx.fillStyle = "rgba(11, 15, 31, 0.78)";
    ctx.strokeStyle = "rgba(96, 165, 250, 0.4)";
    ctx.lineWidth = 1;
    ctx.fillRect(x0 - 4, y0 - 4, mw + 8, mh + 8);
    ctx.strokeRect(x0 - 4, y0 - 4, mw + 8, mh + 8);

    // Clip remaining content to the minimap rect so room edges don't bleed.
    ctx.beginPath();
    ctx.rect(x0, y0, mw, mh);
    ctx.clip();

    // Rooms (dim, no titles).
    ctx.globalAlpha = 0.4;
    for (const room of this.map.rooms) {
      ctx.fillStyle = room.color;
      ctx.fillRect(toX(room.x), toY(room.y), room.width * sx, room.height * sy);
    }
    ctx.globalAlpha = 1;

    // Walls.
    ctx.fillStyle = "rgba(11, 15, 31, 0.9)";
    for (const [wx1, wy1, wx2, wy2] of this._walls) {
      ctx.fillRect(toX(wx1), toY(wy1), (wx2 - wx1) * sx, (wy2 - wy1) * sy);
    }

    // Own visible tasks (skip cooldowns — they aren't actionable).
    for (const task of this.tasks) {
      if (task.status === "cooldown") continue;
      ctx.beginPath();
      ctx.arc(toX(task.x), toY(task.y), 2.5, 0, Math.PI * 2);
      ctx.fillStyle = task.status === "in_progress" ? "#60a5fa" : "#4ade80";
      ctx.fill();
    }

    // Active sabotage panels — pulsing red so they read as "go fix me now".
    if (this.activePanels.length > 0) {
      const pulse = 0.55 + 0.45 * Math.sin(Date.now() / 220);
      for (const panel of this.activePanels) {
        ctx.beginPath();
        ctx.arc(toX(panel.x), toY(panel.y), 3, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(239, 68, 68, ${pulse.toFixed(3)})`;
        ctx.fill();
        ctx.strokeStyle = "rgba(239, 68, 68, 0.95)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    // Vents — small grey diamonds. Visible to everyone (they're map
    // architecture); only chaos can interact, but everyone benefits from
    // knowing where they are spatially.
    for (const vent of this.vents) {
      const vx = toX(vent.x);
      const vy = toY(vent.y);
      ctx.fillStyle = "#94a3b8";
      ctx.beginPath();
      ctx.moveTo(vx, vy - 2.5);
      ctx.lineTo(vx + 2.5, vy);
      ctx.lineTo(vx, vy + 2.5);
      ctx.lineTo(vx - 2.5, vy);
      ctx.closePath();
      ctx.fill();
    }

    // Sabotage trigger objects (Tier 2.7 rework). For chaos: amber dot on
    // each task anchor that has an object_type — reminds them where they can
    // sabotage from. Release team doesn't need this hint (anchor positions
    // are already visible as task markers).
    if (this.ownTeam === "chaos_agents") {
      for (const t of this.tasks) {
        if (!t.objectType) continue;
        ctx.fillStyle = "rgba(251, 191, 36, 0.9)";
        ctx.fillRect(toX(t.x) - 2, toY(t.y) - 2, 4, 4);
      }
    }

    // Local player — bright dot in the player's color with a white halo so
    // it's easy to spot at a glance.
    const local = this._localPlayer();
    if (local) {
      ctx.beginPath();
      ctx.arc(toX(local.x), toY(local.y), 4, 0, Math.PI * 2);
      ctx.fillStyle = local.color || "#e6ecff";
      ctx.fill();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    ctx.restore();
  }
}
