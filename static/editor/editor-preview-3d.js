// MCM Map-Editor — 3D Preview Pane.
//
// Renders the same map JSON the 2D editor edits as a Three.js scene, so
// designers see roughly what the map will look like in the Godot client.
//
// Read-only: this module never mutates the map. The 2D canvas stays the
// source of truth for placement; this is a visual cross-check.
//
// Asset strategy:
//   - Floors per room as flat PlaneGeometry tinted by room.color
//   - Walls auto-derived from doors (mirrors render.js:computeWallsClient,
//     which itself mirrors app/game/game_map.compute_walls)
//   - mapObjects: GLTFLoader for kinds with staged meshes (desk,
//     chair_desk, monitor); coloured BoxGeometry fallback for the rest
//   - taskAnchors as small floating yellow diamonds
//   - spawnPoints[0] gets a Player-Placeholder Box so size feels right
//
// World scale matches the Godot client (Protocol.WORLD_SCALE = 0.01) so
// imported .glb assets sit at native size and the camera distances feel
// the same as in-game. Server-pixel (x, y) maps to Godot/Three (x*S, 0,
// y*S) with the Y axis pointing up in Three.js.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { kindBrowser2d, kindGodotAsset } from "/static/kinds.js";

const WORLD_SCALE = 0.01;
const WALL_HEIGHT = 2.6;
const WALL_THICKNESS = 0.12;
const FLOOR_THICKNESS = 0.02;
const PLAYER_HEIGHT = 1.7;
const PLAYER_RADIUS = 0.35;

// Mirrors app/game/game_map.py WALL_THICKNESS for the auto-derived walls
// (server-pixels). Used by computeWallsLocal which is a verbatim copy of
// render.js:computeWallsClient — duplicated here to keep this module
// self-contained without exporting from render.js.
const WALL_THICKNESS_SERVER_PX = 8;

// Godot publishes GLTF paths as ``res://assets/...``. The browser preview
// serves them under ``/assets/3d/...`` (FastAPI mount on godot-3d/assets).
// One small string swap, kept inline so the kinds.json schema stays
// uniform across all consumers.
const GODOT_RES_PREFIX = "res://";
const BROWSER_ASSET_PREFIX = "/assets/3d/";

function godotAssetToBrowserUrl(godotAsset) {
  if (!godotAsset || !godotAsset.startsWith(GODOT_RES_PREFIX)) return null;
  return BROWSER_ASSET_PREFIX + godotAsset.slice(GODOT_RES_PREFIX.length);
}

// Approximate height (Godot units) per kind for the fallback box. Decor
// stays low; furniture is desk-height; racks tall. Picked by eye —
// designers care about silhouette, not exact dimensions.
//
// 3D-only metadata; lives here because kinds.json is a 2D-flavour schema.
// If a future Godot kind ships a real .gltf this height is unused.
const KIND_FALLBACK_HEIGHT = {
  server_rack: 1.8,
  monitoring_panel: 1.4,
  cabinet: 1.0,
  meeting_table: 0.8,
  presentation_screen: 1.2,
  kitchen_counter: 0.9,
  kitchen_corner: 0.9,
  kitchen_sink: 0.9,
  coffee_machine: 0.5,
  fridge: 1.6,
  plant_cactus: 0.6,
  picture_frame: 0.05,
  rug: 0.02,
  crate: 0.7,
  old_workstation: 0.8,
  keyboard: 0.05,
  mug: 0.12,
  lamp_desk: 0.5,
};

const ROOM_TINT_OVERRIDE = {
  open_space: 0x6b7a96,
  meeting_room: 0x807395,
  kitchen: 0x9c7e58,
  server_room: 0x537090,
  war_room: 0x538595,
  legacy_basement: 0x6b8a6b,
};

// --- Wall auto-derive (mirrors render.js:computeWallsClient) --------------

function computeWallsLocal(map) {
  if (!map || !Array.isArray(map.rooms)) return [];
  const rooms = map.rooms;
  const doors = Array.isArray(map.doors) ? map.doors : [];
  const mapW = map.size?.width ?? 0;
  const mapH = map.size?.height ?? 0;
  const out = [];
  const processed = new Set();

  const wallRect = (axis, edgePos, segStart, segEnd) =>
    axis === "x"
      ? [edgePos - WALL_THICKNESS_SERVER_PX, segStart, edgePos + WALL_THICKNESS_SERVER_PX, segEnd]
      : [segStart, edgePos - WALL_THICKNESS_SERVER_PX, segEnd, edgePos + WALL_THICKNESS_SERVER_PX];

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

// --- Three.js scene wrapper ------------------------------------------------

export class MapPreview3D {
  constructor(host) {
    this.host = host;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a0c0f);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(this.renderer.domElement);

    this.camera = new THREE.PerspectiveCamera(50, 1, 0.1, 500);
    this.camera.position.set(30, 30, 30);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;

    this._addLights();

    // Group that holds everything map-derived. Cleared and rebuilt on each
    // applyMap() — simpler than diffing and fast enough at <500 nodes.
    this.mapGroup = new THREE.Group();
    this.scene.add(this.mapGroup);

    this.gltfLoader = new GLTFLoader();
    this.gltfCache = new Map(); // url -> Promise<gltf.scene>

    // Materials shared across many meshes. Building them once costs less GPU
    // memory and keeps re-builds snappy.
    this.wallMaterial = this._makeWallMaterial();
    this.floorMaterials = this._makeFloorMaterials();
    this.doorFrameMaterials = this._makeDoorFrameMaterials();

    // Epoch counter — async GLTF loads check it on resolution so a stale
    // load from a previous applyMap() can't pollute the new mapGroup with
    // ghost objects from an earlier map state.
    this._epoch = 0;

    this._loop = this._loop.bind(this);
    this._resizeObserver = new ResizeObserver(() => this._onResize());
    this._resizeObserver.observe(host);
    this._onResize();
    this._loop();
  }

  _addLights() {
    const ambient = new THREE.AmbientLight(0xa6b4c8, 0.45);
    this.scene.add(ambient);

    const sun = new THREE.DirectionalLight(0xfff6ea, 0.9);
    sun.position.set(20, 40, 12);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -40;
    sun.shadow.camera.right = 40;
    sun.shadow.camera.top = 40;
    sun.shadow.camera.bottom = -40;
    sun.shadow.camera.near = 1;
    sun.shadow.camera.far = 100;
    this.scene.add(sun);

    const fill = new THREE.DirectionalLight(0xb0c8ff, 0.3);
    fill.position.set(-15, 12, -20);
    this.scene.add(fill);
  }

  _onResize() {
    const w = this.host.clientWidth;
    const h = this.host.clientHeight;
    if (w < 1 || h < 1) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  _loop() {
    if (this._disposed) return;
    requestAnimationFrame(this._loop);
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  // Replace the entire map group. Cheap rebuild — for <500 nodes it stays
  // well below 16ms even in dev tools, and incremental diff is not worth
  // the complexity at this scale.
  applyMap(map) {
    this._epoch += 1;
    const epoch = this._epoch;
    this._disposeChildren(this.mapGroup);
    if (!map || !Array.isArray(map.rooms)) return { stats: this._emptyStats() };

    this._buildFloors(map);
    const wallCount = this._buildWalls(map);
    const doorCount = this._buildDoorFrames(map);
    const objStats = this._buildMapObjects(map, epoch);
    const taskCount = this._buildTaskAnchors(map);
    this._buildPlayerPlaceholder(map);
    this._frameMap(map);

    return {
      stats: {
        rooms: map.rooms.length,
        doors: doorCount,
        walls: wallCount,
        mapObjects: (map.mapObjects || []).length,
        taskAnchors: taskCount,
        meshLoaded: objStats.meshLoaded,
        meshFallback: objStats.meshFallback,
      },
    };
  }

  _emptyStats() {
    return {
      rooms: 0,
      doors: 0,
      walls: 0,
      mapObjects: 0,
      taskAnchors: 0,
      meshLoaded: 0,
      meshFallback: 0,
    };
  }

  _buildFloors(map) {
    for (const room of map.rooms) {
      const w = (room.width || 0) * WORLD_SCALE;
      const d = (room.height || 0) * WORLD_SCALE;
      if (w <= 0 || d <= 0) continue;
      const geom = new THREE.BoxGeometry(w, FLOOR_THICKNESS, d);
      // UV-tile the floor so the procedural texture repeats roughly once
      // every 4 Godot-units (~4m). Without this scaling a 14m server-room
      // would stretch the noise pattern visibly.
      const uvU = Math.max(1, w / 4);
      const uvV = Math.max(1, d / 4);
      this._scaleBoxUVs(geom, uvU, uvV);
      const matKey = room.floorMaterial || "office";
      const mat = this.floorMaterials[matKey] || this.floorMaterials.office;
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.set(
        (room.x + room.width / 2) * WORLD_SCALE,
        -FLOOR_THICKNESS / 2,
        (room.y + room.height / 2) * WORLD_SCALE
      );
      mesh.receiveShadow = true;
      this.mapGroup.add(mesh);
    }
  }

  _buildWalls(map) {
    const walls = computeWallsLocal(map);
    for (const [x1, y1, x2, y2] of walls) {
      const w = (x2 - x1) * WORLD_SCALE;
      const d = (y2 - y1) * WORLD_SCALE;
      if (w <= 0 || d <= 0) continue;
      const geom = new THREE.BoxGeometry(w, WALL_HEIGHT, d);
      // UV-scale the texture so each ~2m of wall ~= one texture tile,
      // independent of the wall's actual length. Without per-mesh UVs
      // long walls would stretch the noise pattern visibly.
      const uvScaleU = Math.max(0.5, Math.max(w, d) / 2);
      const uvScaleV = WALL_HEIGHT / 2;
      this._scaleBoxUVs(geom, uvScaleU, uvScaleV);
      const mesh = new THREE.Mesh(geom, this.wallMaterial);
      mesh.position.set(
        (x1 + x2) * 0.5 * WORLD_SCALE,
        WALL_HEIGHT / 2,
        (y1 + y2) * 0.5 * WORLD_SCALE
      );
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.mapGroup.add(mesh);
    }
    return walls.length;
  }

  // BoxGeometry's default UVs go 0..1 per face. For a tiled texture we
  // want larger numbers so the texture repeats. Set per-vertex UVs by
  // scaling the existing 0..1 values.
  _scaleBoxUVs(geom, scaleU, scaleV) {
    const uvAttr = geom.attributes.uv;
    if (!uvAttr) return;
    const arr = uvAttr.array;
    for (let i = 0; i < arr.length; i += 2) {
      arr[i] = arr[i] * scaleU;
      arr[i + 1] = arr[i + 1] * scaleV;
    }
    uvAttr.needsUpdate = true;
  }

  _buildMapObjects(map, epoch) {
    const objects = Array.isArray(map.mapObjects) ? map.mapObjects : [];
    let meshLoaded = 0;
    let meshFallback = 0;
    for (const obj of objects) {
      const placed = this._placeMapObject(obj, epoch);
      if (placed === "mesh") meshLoaded += 1;
      else if (placed === "fallback") meshFallback += 1;
    }
    return { meshLoaded, meshFallback };
  }

  _placeMapObject(obj, epoch) {
    const url = godotAssetToBrowserUrl(kindGodotAsset(obj.kind));
    if (url) {
      this._loadGltfInstance(url).then(
        (root) => {
          // Drop stale loads: applyMap() may have been called again while
          // we were loading. Skipping prevents a previous map's furniture
          // from leaking into the current scene.
          if (this._disposed || epoch !== this._epoch) return;
          this._positionObject(root, obj);
          this.mapGroup.add(root);
        },
        // GLTF load failed — fall back to a coloured box so the slot at
        // least has something visible. Logged so it's debuggable.
        (err) => {
          // eslint-disable-next-line no-console
          console.error(`[preview-3d] GLTF load failed for ${obj.kind} (${url})`, err);
          if (this._disposed || epoch !== this._epoch) return;
          this._placeFallbackBox(obj);
        }
      );
      return "mesh";
    }
    return this._placeFallbackBox(obj);
  }

  _placeFallbackBox(obj) {
    const w =
      ((obj.rotation === 90 || obj.rotation === 270 ? obj.height : obj.width) || 0) * WORLD_SCALE;
    const d =
      ((obj.rotation === 90 || obj.rotation === 270 ? obj.width : obj.height) || 0) * WORLD_SCALE;
    const h = KIND_FALLBACK_HEIGHT[obj.kind] ?? 0.4;
    if (w <= 0 || d <= 0) return "skipped";
    // Tint comes from the kinds.json browser_2d.fill — keeps the 3D box
    // colour-coded the same as the 2D editor library tile. Falls back to
    // neutral steel-blue when the kind isn't in the registry yet.
    const fillHex = kindBrowser2d(obj.kind)?.fill;
    const colour = fillHex ? this._parseHex(fillHex, 0x556070) : 0x556070;
    const mat = new THREE.MeshStandardMaterial({
      color: colour,
      roughness: 0.75,
      metalness: 0.05,
      transparent: obj.blocksMovement === false,
      opacity: obj.blocksMovement === false ? 0.55 : 1,
    });
    const geom = new THREE.BoxGeometry(w, h, d);
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set((obj.x || 0) * WORLD_SCALE, h / 2, (obj.y || 0) * WORLD_SCALE);
    if (obj.blocksMovement !== false) {
      mesh.castShadow = true;
      mesh.receiveShadow = true;
    }
    this.mapGroup.add(mesh);
    return "fallback";
  }

  _positionObject(root, obj) {
    root.position.set((obj.x || 0) * WORLD_SCALE, 0, (obj.y || 0) * WORLD_SCALE);
    // Server rotations are in degrees, clockwise from +X. Three.js Y-rotation
    // is counter-clockwise around +Y, so negate.
    if (obj.rotation) {
      root.rotation.y = THREE.MathUtils.degToRad(-obj.rotation);
    }
    root.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
      }
    });
  }

  _loadGltfInstance(url) {
    if (!this.gltfCache.has(url)) {
      const promise = new Promise((resolve, reject) => {
        this.gltfLoader.load(
          url,
          (gltf) => resolve(gltf.scene),
          undefined,
          (err) => reject(err)
        );
      });
      this.gltfCache.set(url, promise);
    }
    return this.gltfCache.get(url).then((proto) => {
      // Mark the clone so _disposeChildren skips disposing its geometry/
      // material — those are SHARED with the cached prototype, and disposing
      // them once would empty the cache for every subsequent clone.
      const clone = proto.clone(true);
      clone.userData.fromGltf = true;
      return clone;
    });
  }

  _buildTaskAnchors(map) {
    const anchors = Array.isArray(map.taskAnchors) ? map.taskAnchors : [];
    const mat = new THREE.MeshStandardMaterial({
      color: 0xfacc15,
      emissive: 0xfacc15,
      emissiveIntensity: 0.4,
      roughness: 0.4,
    });
    for (const a of anchors) {
      const geom = new THREE.OctahedronGeometry(0.18, 0);
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.set((a.x || 0) * WORLD_SCALE, 1.2, (a.y || 0) * WORLD_SCALE);
      this.mapGroup.add(mesh);
    }
    return anchors.length;
  }

  _buildPlayerPlaceholder(map) {
    const spawn = (map.spawnPoints || [])[0];
    if (!spawn) return;
    const geom = new THREE.CapsuleGeometry(PLAYER_RADIUS, PLAYER_HEIGHT - PLAYER_RADIUS * 2, 4, 8);
    const mat = new THREE.MeshStandardMaterial({
      color: 0x4ade80,
      emissive: 0x064e1a,
      roughness: 0.6,
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.position.set(
      (spawn.x || 0) * WORLD_SCALE,
      PLAYER_HEIGHT / 2,
      (spawn.y || 0) * WORLD_SCALE
    );
    mesh.castShadow = true;
    mesh.userData.role = "player-placeholder";
    this.mapGroup.add(mesh);
  }

  _frameMap(map) {
    // Only auto-frame on first applyMap so user-orbit doesn't get reset
    // every keystroke. Track via a flag on the controls object.
    if (this.controls.userData?.framed) return;
    const w = (map.size?.width ?? 4800) * WORLD_SCALE;
    const d = (map.size?.height ?? 3200) * WORLD_SCALE;
    const cx = w / 2;
    const cz = d / 2;
    this.controls.target.set(cx, 0, cz);
    const radius = Math.max(w, d);
    this.camera.position.set(cx + radius * 0.5, radius * 0.7, cz + radius * 0.7);
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.controls.userData = { framed: true };
  }

  _disposeChildren(group) {
    // Set of materials we share across many meshes — these must NEVER be
    // disposed in the per-rebuild cleanup, otherwise the next applyMap()
    // would render with disposed-out textures.
    const shared = new Set([this.wallMaterial, ...Object.values(this.floorMaterials)]);
    for (const m of Object.values(this.doorFrameMaterials)) shared.add(m);

    while (group.children.length > 0) {
      const child = group.children[0];
      group.remove(child);
      // GLTF clones SHARE geometry/material with the cached prototype. Disposing
      // them would invalidate the cache so subsequent clones render as empty
      // — the bug that made all furniture vanish on the second applyMap().
      const isShared = child.userData?.fromGltf === true;
      if (isShared) continue;
      child.traverse?.((node) => {
        if (node.geometry) node.geometry.dispose();
        if (node.material && !shared.has(node.material)) {
          if (Array.isArray(node.material)) node.material.forEach((m) => m.dispose());
          else node.material.dispose();
        }
      });
    }
  }

  // --- Floor materials (procedural, per `room.floorMaterial`) ----------------
  //
  // Four flavours map onto the GameMap.floorMaterial enum:
  //   - "office"  → warm beige carpet (default)
  //   - "kitchen" → cool tiles with grid lines
  //   - "server"  → grey concrete with speckle
  //   - "legacy"  → dim olive carpet (legacy basement)
  //
  // Each is a CanvasTexture seeded with the same RNG-style speckle pass
  // we use for walls, biased per-flavour. Tiled via UV-scaling per floor
  // patch (~one tile per ~4m), wrapping cleanly on RepeatWrapping.

  _makeFloorMaterials() {
    return {
      office: this._buildOfficeFloor(),
      kitchen: this._buildKitchenFloor(),
      server: this._buildServerFloor(),
      legacy: this._buildLegacyFloor(),
    };
  }

  _floorCanvas(size = 256) {
    const c = document.createElement("canvas");
    c.width = size;
    c.height = size;
    return { canvas: c, ctx: c.getContext("2d"), size };
  }

  _floorMaterial(canvas, { roughness, metalness }) {
    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
    return new THREE.MeshStandardMaterial({
      map: tex,
      color: 0xffffff,
      roughness,
      metalness,
    });
  }

  _buildOfficeFloor() {
    const { canvas, ctx, size } = this._floorCanvas();
    ctx.fillStyle = "#a78d6a";
    ctx.fillRect(0, 0, size, size);
    // Carpet weave — many small flecks slightly warm, slightly cool
    for (let i = 0; i < 2400; i++) {
      const x = Math.random() * size;
      const y = Math.random() * size;
      const r = 0.4 + Math.random() * 0.7;
      const tint = 150 + Math.floor(Math.random() * 60);
      ctx.fillStyle = `rgba(${tint + 25}, ${tint + 5}, ${tint - 15}, 0.32)`;
      ctx.fillRect(x, y, r, r);
    }
    return this._floorMaterial(canvas, { roughness: 0.92, metalness: 0.02 });
  }

  _buildKitchenFloor() {
    const { canvas, ctx, size } = this._floorCanvas();
    ctx.fillStyle = "#cfd6dc";
    ctx.fillRect(0, 0, size, size);
    // 4×4 tiles with subtle per-tile colour variation + dark grout lines
    const grid = 4;
    const tile = size / grid;
    for (let i = 0; i < grid; i++) {
      for (let j = 0; j < grid; j++) {
        const tint = 215 + Math.floor(Math.random() * 25);
        ctx.fillStyle = `rgba(${tint - 5}, ${tint}, ${tint + 5}, 0.55)`;
        ctx.fillRect(i * tile + 2, j * tile + 2, tile - 4, tile - 4);
      }
    }
    ctx.strokeStyle = "rgba(60, 70, 80, 0.55)";
    ctx.lineWidth = 2;
    for (let i = 0; i <= grid; i++) {
      ctx.beginPath();
      ctx.moveTo(i * tile, 0);
      ctx.lineTo(i * tile, size);
      ctx.moveTo(0, i * tile);
      ctx.lineTo(size, i * tile);
      ctx.stroke();
    }
    return this._floorMaterial(canvas, { roughness: 0.45, metalness: 0.06 });
  }

  _buildServerFloor() {
    const { canvas, ctx, size } = this._floorCanvas();
    ctx.fillStyle = "#6c7480";
    ctx.fillRect(0, 0, size, size);
    // Concrete: many small dark + light flecks, low contrast
    for (let i = 0; i < 3200; i++) {
      const x = Math.random() * size;
      const y = Math.random() * size;
      const r = Math.random() * 1.5;
      const grey = 90 + Math.floor(Math.random() * 90);
      ctx.fillStyle = `rgba(${grey}, ${grey + 4}, ${grey + 8}, 0.28)`;
      ctx.fillRect(x, y, r, r);
    }
    return this._floorMaterial(canvas, { roughness: 0.88, metalness: 0.12 });
  }

  _buildLegacyFloor() {
    const { canvas, ctx, size } = this._floorCanvas();
    ctx.fillStyle = "#5e7548";
    ctx.fillRect(0, 0, size, size);
    // Old, "stained" carpet — uneven flecks, a few darker patches
    for (let i = 0; i < 2000; i++) {
      const x = Math.random() * size;
      const y = Math.random() * size;
      const r = 0.4 + Math.random() * 0.9;
      const tint = 70 + Math.floor(Math.random() * 60);
      ctx.fillStyle = `rgba(${tint + 30}, ${tint + 50}, ${tint + 10}, 0.4)`;
      ctx.fillRect(x, y, r, r);
    }
    // Stains: a handful of darker blobs
    for (let i = 0; i < 12; i++) {
      const x = Math.random() * size;
      const y = Math.random() * size;
      const r = 8 + Math.random() * 14;
      const g = ctx.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, "rgba(40, 50, 30, 0.35)");
      g.addColorStop(1, "rgba(40, 50, 30, 0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
    return this._floorMaterial(canvas, { roughness: 0.95, metalness: 0.02 });
  }

  // --- Door frames -----------------------------------------------------------
  //
  // The wall-derive logic stamps a gap into the wall at each door's
  // position. Without anything filling that gap visually, doors read as
  // "missing wall section" rather than "doorway". This adds a slim
  // lintel beam at the top of each gap, materialised per `doorKind`.

  _makeDoorFrameMaterials() {
    return {
      office_door: new THREE.MeshStandardMaterial({
        color: 0x4a3722,
        roughness: 0.85,
        metalness: 0.05,
      }),
      glass_panel: new THREE.MeshStandardMaterial({
        color: 0x88aacc,
        transparent: true,
        opacity: 0.55,
        roughness: 0.2,
        metalness: 0.4,
      }),
      vault: new THREE.MeshStandardMaterial({
        color: 0x32363c,
        roughness: 0.4,
        metalness: 0.85,
      }),
    };
  }

  _buildDoorFrames(map) {
    const rooms = map.rooms || [];
    const doors = map.doors || [];
    if (!doors.length) return 0;

    const lintelHeight = 0.25;
    const frameThick = 0.2;
    let placed = 0;

    for (const door of doors) {
      const kind = door.doorKind || "office_door";
      if (kind === "none") continue;
      const mat = this.doorFrameMaterials[kind] || this.doorFrameMaterials.office_door;
      const edge = this._findSharedEdge(rooms, door.betweenRoomA, door.betweenRoomB);
      if (!edge) continue;

      const w = (door.width || 240) * WORLD_SCALE;
      const xPos = (edge.axis === "x" ? edge.edgePos : door.position) * WORLD_SCALE;
      const zPos = (edge.axis === "y" ? edge.edgePos : door.position) * WORLD_SCALE;

      // Lintel runs along the door span, perpendicular to it goes through
      // the wall (frameThick covers the wall thickness with a little overhang).
      const geom =
        edge.axis === "x"
          ? new THREE.BoxGeometry(frameThick, lintelHeight, w)
          : new THREE.BoxGeometry(w, lintelHeight, frameThick);
      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.set(xPos, WALL_HEIGHT - lintelHeight / 2, zPos);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.mapGroup.add(mesh);
      placed += 1;
    }
    return placed;
  }

  // Find which edge two rooms share. Two adjacent rooms either share a
  // vertical edge (one's right wall = other's left wall, axis="x") or a
  // horizontal edge (one's bottom = other's top, axis="y"). Returns null
  // for rooms that don't actually touch.
  _findSharedEdge(rooms, idA, idB) {
    const a = rooms.find((r) => r.id === idA);
    const b = rooms.find((r) => r.id === idB);
    if (!a || !b) return null;
    if (a.x + a.width === b.x) return { axis: "x", edgePos: b.x };
    if (b.x + b.width === a.x) return { axis: "x", edgePos: a.x };
    if (a.y + a.height === b.y) return { axis: "y", edgePos: b.y };
    if (b.y + b.height === a.y) return { axis: "y", edgePos: a.y };
    return null;
  }

  // Procedural drywall material — subtle off-white with low-frequency speckle
  // and faint horizontal banding for "office wall" feel without shipping an
  // image asset. Tiled via per-wall UV scaling in _buildWalls.
  _makeWallMaterial() {
    const size = 256;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");

    // Base gradient: slightly warmer near the floor, cooler near the ceiling.
    const grad = ctx.createLinearGradient(0, 0, 0, size);
    grad.addColorStop(0, "#f1ede4");
    grad.addColorStop(1, "#e5dfd1");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);

    // Speckle: many tiny semi-transparent dots scattered across the surface.
    for (let i = 0; i < 1600; i++) {
      const x = Math.random() * size;
      const y = Math.random() * size;
      const r = 0.3 + Math.random() * 0.9;
      const grey = 200 + Math.floor(Math.random() * 30);
      ctx.fillStyle = `rgba(${grey}, ${grey - 6}, ${grey - 16}, 0.18)`;
      ctx.fillRect(x, y, r, r);
    }

    // Faint horizontal banding for drywall sheet seams. Stays subtle so it
    // reads as texture, not as obvious stripes.
    ctx.strokeStyle = "rgba(40, 30, 20, 0.05)";
    ctx.lineWidth = 1;
    for (let y = size / 4; y < size; y += size / 4) {
      ctx.beginPath();
      ctx.moveTo(0, y + Math.random() * 2 - 1);
      ctx.lineTo(size, y + Math.random() * 2 - 1);
      ctx.stroke();
    }

    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 4;
    return new THREE.MeshStandardMaterial({
      map: tex,
      color: 0xffffff,
      roughness: 0.9,
      metalness: 0.02,
    });
  }

  _parseHex(hex, fallback) {
    if (typeof hex !== "string") return fallback;
    const h = hex.startsWith("#") ? hex.slice(1) : hex;
    const n = parseInt(h, 16);
    return Number.isFinite(n) ? n : fallback;
  }

  dispose() {
    this._disposed = true;
    this._resizeObserver.disconnect();
    this._disposeChildren(this.mapGroup);
    this.renderer.dispose();
    if (this.renderer.domElement.parentElement) {
      this.renderer.domElement.parentElement.removeChild(this.renderer.domElement);
    }
  }
}
