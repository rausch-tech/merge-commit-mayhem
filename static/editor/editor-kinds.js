// MCM Map-Editor — Kind catalogue facade.
//
// Pre-2026-04-27 this file held a hardcoded copy of the 25-kind catalogue.
// The Godot team's maps/kinds.json migration (and the backend
// /api/kinds endpoint) made it the single source of truth — this file
// now derives the editor-shaped catalogue from that registry at boot.
//
// We keep the pre-existing exports (KIND_CATALOGUE, KIND_BY_NAME,
// KIND_CATEGORIES) as **mutable references** so importing modules don't
// need to re-import after the async init completes. Boot order:
//
//   await initKindsCatalogue();    // fetches /api/kinds, populates
//   renderKindLibrary();           // sees the populated catalogue
//
// Tests call _seedFromRegistryForTests() with a registry read from
// disk so they don't need a real /api/kinds endpoint.

import { ensureKindsLoaded, kindEntries, seedKinds, clearKinds } from "/static/kinds.js";

// Mutable exports — populated in-place by _populateFromRegistry.
// Importers hold the same array/Map identity across the editor lifetime.
export const KIND_CATALOGUE = [];
export const KIND_BY_NAME = new Map();
export const KIND_CATEGORIES = [];

/**
 * Trigger a /api/kinds fetch and populate the editor-shaped catalogue.
 * Call once at editor boot, before rendering anything that depends on
 * the catalogue (palette, validation, props sidebar).
 *
 * Throws on network/parse errors — caller should surface that to the UI
 * so the designer notices an empty palette is not their fault.
 */
export async function initKindsCatalogue() {
  await ensureKindsLoaded();
  _populateFromRegistry();
  return KIND_CATALOGUE;
}

/**
 * Test-only synchronous seed. Pass a parsed maps/kinds.json dict; the
 * facade re-derives the editor-shaped lists. Production code should use
 * initKindsCatalogue() (which goes through the fetch path so the cache
 * matches what's on the wire).
 */
export function _seedFromRegistryForTests(registry) {
  seedKinds(registry);
  _populateFromRegistry();
}

/** Test-only: drop everything so the next test gets a clean slate. */
export function _clearForTests() {
  clearKinds();
  KIND_CATALOGUE.length = 0;
  KIND_BY_NAME.clear();
  KIND_CATEGORIES.length = 0;
}

function _populateFromRegistry() {
  KIND_CATALOGUE.length = 0;
  KIND_BY_NAME.clear();
  KIND_CATEGORIES.length = 0;

  for (const [kind, def] of kindEntries()) {
    const entry = {
      kind,
      label: def.label || kind,
      category: def.category || "Misc",
      width: def.default_size?.[0] ?? 50,
      height: def.default_size?.[1] ?? 50,
      blocksMovement: def.blocks_movement ?? true,
      fill: def.browser_2d?.fill ?? "#888888",
    };
    KIND_CATALOGUE.push(entry);
    KIND_BY_NAME.set(kind, entry);
  }

  // Categories appear in the order their first member shows up in the
  // registry — the kinds.json layout becomes the editor-palette layout.
  const seen = new Set();
  for (const entry of KIND_CATALOGUE) {
    if (seen.has(entry.category)) continue;
    seen.add(entry.category);
    KIND_CATEGORIES.push(entry.category);
  }
}
