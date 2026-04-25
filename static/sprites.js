// Sprite-sheet metadata: which sheet contains which logical icon, and its
// (col, row, cols, rows) location in the sheet's grid.

export const SPRITES = {
  // task icons (ui_icon_set.png is 4 cols x 3 rows)
  task_fix_unit_tests:    { sheet: "/images/ui_icon_set.png", cols: 4, rows: 3, col: 0, row: 0 },
  task_review_pr:         { sheet: "/images/ui_icon_set.png", cols: 4, rows: 3, col: 1, row: 0 },
  task_refill_coffee:     { sheet: "/images/ui_icon_set.png", cols: 4, rows: 3, col: 2, row: 0 },
  task_repair_deployment: { sheet: "/images/ui_icon_set.png", cols: 4, rows: 3, col: 0, row: 1 },

  // sabotage icons (sabotage_icons.png is 5 cols x 2 rows)
  sabotage_ci_cd_red:         { sheet: "/images/sabotage_icons.png", cols: 5, rows: 2, col: 0, row: 0 },
  sabotage_coffee_outage:     { sheet: "/images/sabotage_icons.png", cols: 5, rows: 2, col: 1, row: 0 },
  sabotage_mandatory_meeting: { sheet: "/images/sabotage_icons.png", cols: 5, rows: 2, col: 2, row: 0 },

  // role badges (role_badges.png is 5 cols x 2 rows)
  role_developer:  { sheet: "/images/role_badges.png", cols: 5, rows: 2, col: 0, row: 0 },
  role_vibe_coder: { sheet: "/images/role_badges.png", cols: 5, rows: 2, col: 4, row: 0 },
};

/**
 * Compute CSS background-image properties for a sprite key.
 * Apply by setting `el.style.backgroundImage = ...`, etc.
 */
export function spriteCss(key) {
  const s = SPRITES[key];
  if (!s) return null;
  const sizeX = s.cols * 100;
  const sizeY = s.rows * 100;
  // Edge case: with cols=1 or rows=1, position math divides by zero.
  const posX = s.cols > 1 ? (s.col / (s.cols - 1)) * 100 : 0;
  const posY = s.rows > 1 ? (s.row / (s.rows - 1)) * 100 : 0;
  return {
    backgroundImage: `url(${s.sheet})`,
    backgroundSize: `${sizeX}% ${sizeY}%`,
    backgroundPosition: `${posX}% ${posY}%`,
    backgroundRepeat: "no-repeat",
  };
}

/** Apply spriteCss to an element, mutating its style. */
export function applySprite(el, key) {
  const css = spriteCss(key);
  if (!css || !el) return;
  Object.assign(el.style, css);
}

// --- canvas variant (for render.js) ---

const _imageCache = new Map();

export function loadSheet(url) {
  let img = _imageCache.get(url);
  if (!img) {
    img = new Image();
    img.src = url;
    _imageCache.set(url, img);
  }
  return img;
}

/**
 * Draw a sprite onto a canvas context at world coords (x, y) sized (w, h).
 * The image is loaded asynchronously; if not yet loaded, this function
 * returns false so the caller can render a fallback.
 */
export function drawSprite(ctx, key, x, y, w, h) {
  const s = SPRITES[key];
  if (!s) return false;
  const img = loadSheet(s.sheet);
  if (!img.complete || !img.naturalWidth) return false;
  const tileW = img.naturalWidth / s.cols;
  const tileH = img.naturalHeight / s.rows;
  ctx.drawImage(
    img,
    s.col * tileW, s.row * tileH, tileW, tileH,  // source
    x - w / 2, y - h / 2, w, h                    // destination (centered)
  );
  return true;
}
