// Tiny audio helper. No global volume control yet — clicks fixed at 0.3.
// All Audio elements are pre-loaded so first-trigger latency is low.

const VOLUME = 0.3;

function preload(url) {
  const a = new Audio(url);
  a.volume = VOLUME;
  a.preload = "auto";
  return a;
}

const sounds = {
  click: preload("/sounds/kenney_ui_audio/click1.wav"),
  taskComplete: preload("/sounds/kenney_ui_audio/switch3.wav"),
};

function play(key) {
  const original = sounds[key];
  if (!original) return;
  // Clone so rapid repeats don't restart the same playback.
  const clone = original.cloneNode(true);
  clone.volume = VOLUME;
  clone.play().catch(() => {
    /* user-gesture-not-yet-given is fine */
  });
}

export function playClick() {
  play("click");
}
export function playTaskComplete() {
  play("taskComplete");
}

/**
 * Wire ALL <button> elements that are present right now (or get rendered
 * by the time this is called) for click sounds via event delegation.
 * Idempotent — call once.
 */
export function wireGlobalClickSound() {
  if (window.__mcmClickSoundWired) return;
  window.__mcmClickSoundWired = true;
  document.addEventListener(
    "click",
    (e) => {
      const target = e.target;
      if (target instanceof HTMLElement && target.closest("button")) {
        playClick();
      }
    },
    true // capture phase so it fires before button-handlers stop propagation
  );
}
