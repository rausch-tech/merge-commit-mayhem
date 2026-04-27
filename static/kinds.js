// MCM frontend kinds-registry client.
//
// Single in-browser source of truth for the MapObject kind catalogue.
// Fetches /api/kinds once on first lookup, caches the result, and
// exposes synchronous getters that downstream consumers (editor palette,
// browser renderer, 3D preview) can call from hot paths.
//
// Server-side this is backed by maps/kinds.json (see app/game/
// kinds_registry.py + the Pydantic validator on MapObject.kind). Keeping
// the wire-format raw means any field the server adds later (new
// per-kind metadata, sound hints, etc.) flows through to the client
// without code changes here.
//
// Usage:
//   await ensureKindsLoaded();         // production: trigger at boot
//   seedKinds(rawRegistry);            // tests: synchronously inject
//   kindBrowser2d("desk").fill;        // any consumer can lookup
//   isLoaded();                        // tolerate render-before-fetch
//
// Failure mode: a network error keeps `_registry` null. Renderers should
// fall back to a neutral placeholder rather than crash; the next
// successful fetch (call ensureKindsLoaded again, e.g. on retry) refills
// the cache and subsequent renders pick up the right styling.

let _registry = null;
let _loadPromise = null;

/** Trigger a /api/kinds fetch if not loaded. Returns the parsed registry. */
export async function ensureKindsLoaded() {
  if (_registry) return _registry;
  if (_loadPromise) return _loadPromise;
  _loadPromise = fetch("/api/kinds")
    .then((r) => {
      if (!r.ok) throw new Error(`/api/kinds returned ${r.status}`);
      return r.json();
    })
    .then((data) => {
      _registry = data;
      _loadPromise = null;
      return data;
    })
    .catch((err) => {
      _loadPromise = null;
      throw err;
    });
  return _loadPromise;
}

/** Synchronous seed for tests. Production code goes through ensureKindsLoaded. */
export function seedKinds(registry) {
  _registry = registry;
}

/** Reset the cache. Tests use this to isolate state between cases. */
export function clearKinds() {
  _registry = null;
  _loadPromise = null;
}

/** True iff a registry is in the cache (fetched or seeded). */
export function isLoaded() {
  return _registry !== null;
}

/** Iterable over [kindName, definition] entries, excluding the `_meta` block. */
export function kindEntries() {
  if (!_registry) return [];
  return Object.entries(_registry).filter(([k]) => !k.startsWith("_"));
}

/** Per-kind definition or null if unknown / not loaded. */
export function kindByName(name) {
  if (!_registry) return null;
  if (!name || name.startsWith("_")) return null;
  return _registry[name] || null;
}

/** {fill, label} hint for the 2D browser renderer; null when missing. */
export function kindBrowser2d(name) {
  return kindByName(name)?.browser_2d || null;
}

/** Godot-side asset path (res://…) or null when the kind isn't staged. */
export function kindGodotAsset(name) {
  return kindByName(name)?.godot_asset || null;
}

/** [width_px, height_px] default placement size, or [50,50] fallback. */
export function kindDefaultSize(name) {
  return kindByName(name)?.default_size || [50, 50];
}

/** Server-side default for blocks_movement; true for safety when unknown. */
export function kindBlocksMovement(name) {
  const e = kindByName(name);
  return e?.blocks_movement ?? true;
}

/** Editor-palette display label, falls back to the kind name. */
export function kindLabel(name) {
  return kindByName(name)?.label || name || "";
}

/** Editor-palette grouping (Workstation/Server/Meeting/…). */
export function kindCategory(name) {
  return kindByName(name)?.category || "Misc";
}
