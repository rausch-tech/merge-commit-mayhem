// In-memory map model + JSON serialize/deserialize for the MCM Map-Editor.
//
// The wire format mirrors what `app/game/game_map.py::load_map()` expects
// (camelCase keys). `serializeMap` and `deserializeMap` are the canonical
// boundaries between the editor's working model and the on-disk JSON.

export const blankMap = () => ({
  name: "untitled",
  size: { width: 4800, height: 3200 },
  rooms: [],
  wallLines: [],
  spawnPoints: [],
  taskAnchors: [],
  warRoomId: "",
});

// Serialize the map model to a JSON string. Preserves the canonical key order
// so diffs stay readable and round-trips remain stable.
export function serializeMap(map) {
  const ordered = {
    name: map.name,
    size: { width: map.size.width, height: map.size.height },
    rooms: (map.rooms || []).map((r) => ({
      id: r.id,
      title: r.title,
      x: r.x,
      y: r.y,
      width: r.width,
      height: r.height,
      color: r.color,
    })),
    wallLines: (map.wallLines || []).map((w) => ({
      axis: w.axis,
      position: w.position,
      doors: (w.doors || []).map((d) => ({ center: d.center, width: d.width })),
    })),
    spawnPoints: (map.spawnPoints || []).map((s) => ({ x: s.x, y: s.y })),
    taskAnchors: (map.taskAnchors || []).map((t) => ({
      taskId: t.taskId,
      x: t.x,
      y: t.y,
    })),
    warRoomId: map.warRoomId,
  };
  return JSON.stringify(ordered, null, 2);
}

// Parse a JSON string into the editor's working model. Throws if required
// top-level fields are missing. Lenient about unknown extra fields so
// forward-compatible map files still load.
export function deserializeMap(jsonText) {
  let raw;
  try {
    raw = JSON.parse(jsonText);
  } catch (err) {
    throw new Error("Ungültiges JSON: " + err.message);
  }
  if (typeof raw !== "object" || raw === null) {
    throw new Error("JSON muss ein Objekt sein.");
  }
  const required = ["name", "size", "rooms", "warRoomId"];
  for (const key of required) {
    if (!(key in raw)) {
      throw new Error(`Pflichtfeld fehlt: ${key}`);
    }
  }
  if (!raw.size || typeof raw.size.width !== "number" || typeof raw.size.height !== "number") {
    throw new Error("size.width und size.height müssen Zahlen sein.");
  }
  if (!Array.isArray(raw.rooms)) {
    throw new Error("rooms muss eine Liste sein.");
  }
  return {
    name: String(raw.name),
    size: { width: raw.size.width, height: raw.size.height },
    rooms: raw.rooms.map((r) => ({
      id: String(r.id),
      title: String(r.title),
      x: Number(r.x),
      y: Number(r.y),
      width: Number(r.width),
      height: Number(r.height),
      color: String(r.color || "#3a4560"),
    })),
    wallLines: Array.isArray(raw.wallLines)
      ? raw.wallLines.map((w) => ({
          axis: w.axis === "y" ? "y" : "x",
          position: Number(w.position),
          doors: Array.isArray(w.doors)
            ? w.doors.map((d) => ({
                center: Number(d.center),
                width: Number(d.width),
              }))
            : [],
        }))
      : [],
    spawnPoints: Array.isArray(raw.spawnPoints)
      ? raw.spawnPoints.map((s) => ({ x: Number(s.x), y: Number(s.y) }))
      : [],
    taskAnchors: Array.isArray(raw.taskAnchors)
      ? raw.taskAnchors.map((t) => ({
          taskId: String(t.taskId),
          x: Number(t.x),
          y: Number(t.y),
        }))
      : [],
    warRoomId: String(raw.warRoomId || ""),
  };
}

// Best-effort sanity checks before download. Returns a list of human-readable
// warnings; an empty list means "looks good". The caller decides whether to
// block the download or let the user proceed anyway.
export function validateMap(map) {
  const warnings = [];
  if (!map.name || !map.name.trim()) {
    warnings.push("Map-Name ist leer.");
  }
  if (!map.rooms || map.rooms.length === 0) {
    warnings.push("Keine Räume definiert.");
  }
  const roomIds = new Set((map.rooms || []).map((r) => r.id));
  if (map.warRoomId && !roomIds.has(map.warRoomId)) {
    warnings.push(`War-Room "${map.warRoomId}" existiert nicht.`);
  }
  if (!map.warRoomId) {
    warnings.push("Kein War-Room ausgewählt.");
  }
  const w = map.size.width;
  const h = map.size.height;
  for (const wl of map.wallLines || []) {
    const max = wl.axis === "x" ? w : h;
    if (wl.position < 0 || wl.position > max) {
      warnings.push(`Wand bei ${wl.axis}=${wl.position} liegt ausserhalb der Map.`);
    }
  }
  for (const sp of map.spawnPoints || []) {
    if (sp.x < 0 || sp.x > w || sp.y < 0 || sp.y > h) {
      warnings.push(`Spawn (${sp.x}, ${sp.y}) ausserhalb der Map.`);
    }
  }
  for (const ta of map.taskAnchors || []) {
    if (ta.x < 0 || ta.x > w || ta.y < 0 || ta.y > h) {
      warnings.push(`Task-Anker "${ta.taskId}" (${ta.x}, ${ta.y}) ausserhalb der Map.`);
    }
  }
  return warnings;
}
