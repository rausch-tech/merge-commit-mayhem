// MCM Map-Editor — kind-library thumbnails.
//
// Pro MapObject-Kind ein kleines 3D-Thumbnail offscreen rendern, sodass die
// linke Bibliotheks-Leiste das echte Mesh zeigt statt einer farbigen Box.
//
// Architektur: ein einziger WebGLRenderer + Scene + Camera, geteilt über alle
// Kinds — keine 25 WebGL-Kontexte. Render-Aufträge serialisieren wir, damit
// die Drawing-Buffer-Snapshots nicht gegenseitig durcheinander rendern.
// GLTFLoader kriegt einen kleinen URL-Cache, damit der gleiche Pack-Mesh nicht
// zweimal geparst wird (Browser-HTTP-Cache spart den Fetch, wir sparen das
// Parse). Errors fangen wir leise — der Aufrufer behält seinen Color-Swatch.
//
// Pivot-Konvention: Die Pipeline (Tier 4.0.2) vendored .gltf-Files mit
// (X-Center, Y-Bottom, Z-Center)-Pivot — siehe docs/ASSET_SPEC.md §5. Wir
// framing daher nach der konkreten BoundingBox, nicht nach Annahmen.

import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const SIZE = 96;
const GODOT_RES_PREFIX = "res://";
const BROWSER_ASSET_PREFIX = "/assets/3d/";

let _renderer = null;
let _scene = null;
let _camera = null;
let _loader = null;
const _gltfCache = new Map(); // url -> Promise<gltf.scene>
let _renderQueue = Promise.resolve();

function _ensureRig() {
  if (_renderer) return;

  // alpha:true + Clear-Color (0,0,0,0) macht das Thumbnail transparent, sodass
  // der Tile-Background im Editor durchscheint und Selected/Hover-States
  // weiterhin sichtbar bleiben.
  _renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: true,
    preserveDrawingBuffer: true, // toDataURL braucht persistente Frame-Buffer
  });
  _renderer.setSize(SIZE, SIZE);
  _renderer.setPixelRatio(1); // fixe Auflösung — kein Retina-Cost auf Boot
  _renderer.setClearColor(0x000000, 0);

  _scene = new THREE.Scene();
  const hemi = new THREE.HemisphereLight(0xffffff, 0x4a4a4a, 1.1);
  _scene.add(hemi);
  const dir = new THREE.DirectionalLight(0xffffff, 1.1);
  dir.position.set(2.5, 4, 3);
  _scene.add(dir);

  _camera = new THREE.PerspectiveCamera(35, 1, 0.05, 100);

  _loader = new GLTFLoader();
}

function _godotAssetToUrl(godotAsset) {
  if (!godotAsset || !godotAsset.startsWith(GODOT_RES_PREFIX)) return null;
  return BROWSER_ASSET_PREFIX + godotAsset.slice(GODOT_RES_PREFIX.length);
}

function _loadCached(url) {
  if (!_gltfCache.has(url)) {
    const promise = new Promise((resolve, reject) => {
      _loader.load(url, (gltf) => resolve(gltf.scene), undefined, reject);
    });
    _gltfCache.set(url, promise);
  }
  return _gltfCache.get(url);
}

function _frameAndRender(prototype) {
  // Kopie, damit wir den Cache-Prototypen nicht in der Welt platzieren.
  // GLTFLoader-Cache: clone() teilt Geometry/Material — kein Memory-Leak.
  const obj = prototype.clone();

  _scene.add(obj);

  const box = new THREE.Box3().setFromObject(obj);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());

  // Mesh in den Origin verschieben, Boden bei y=0.
  obj.position.x -= center.x;
  obj.position.z -= center.z;
  obj.position.y -= box.min.y;

  // Kamera-Distanz nach dem groessten Halb-Achsen-Wert berechnen, damit das
  // Mesh im 35° FOV nicht abschneidet. 1.45-Faktor laesst etwas Padding.
  const radius = Math.max(size.x, size.y, size.z) * 0.5;
  const fovRad = (_camera.fov * Math.PI) / 180;
  const camDist = (radius / Math.tan(fovRad / 2)) * 1.45;

  // 35° elevation, 35° azimuth — leichte 3/4-Ansicht, zeigt Top + zwei Seiten.
  const elev = (35 * Math.PI) / 180;
  const azim = (35 * Math.PI) / 180;
  _camera.position.set(
    Math.sin(azim) * Math.cos(elev) * camDist,
    Math.sin(elev) * camDist + size.y * 0.5,
    Math.cos(azim) * Math.cos(elev) * camDist
  );
  _camera.lookAt(0, size.y * 0.4, 0);

  _renderer.render(_scene, _camera);
  const dataUrl = _renderer.domElement.toDataURL("image/png");

  _scene.remove(obj);
  return dataUrl;
}

/**
 * Rendert ein Thumbnail fuer den gegebenen `godot_asset`-Pfad
 * (`res://assets/...`) und gibt eine Data-URL zurueck. Liefert `null` wenn
 * kein Pfad oder GLTF-Load schlaegt fehl — Aufrufer behaelt seinen
 * Color-Swatch in dem Fall.
 *
 * Render-Aufrufe werden global serialisiert — der gemeinsame Renderer haelt
 * nur einen Drawing-Buffer.
 */
export function renderKindThumbnail(godotAsset) {
  const url = _godotAssetToUrl(godotAsset);
  if (!url) return Promise.resolve(null);

  const job = _renderQueue.then(async () => {
    try {
      _ensureRig();
      const proto = await _loadCached(url);
      return _frameAndRender(proto);
    } catch (err) {
      console.warn(`[kind-thumbnails] failed to render ${url}`, err);
      return null;
    }
  });

  // Queue an die letzte Promise haengen, aber Fehler im Job nicht in die
  // Queue durchsickern lassen — sonst blockt ein Failure die Folge-Kinds.
  _renderQueue = job.catch(() => null);
  return job;
}
