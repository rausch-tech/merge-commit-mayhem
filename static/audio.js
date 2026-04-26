// Tiny audio helper with persisted master volume + mute toggle.
// All Audio elements are pre-loaded so first-trigger latency is low.

const STORAGE_KEY_VOLUME = "mcm.volume";
const STORAGE_KEY_MUTED = "mcm.muted";
const DEFAULT_VOLUME = 0.3;

let _volume = DEFAULT_VOLUME;
let _muted = false;

(function loadFromStorage() {
  try {
    const v = localStorage.getItem(STORAGE_KEY_VOLUME);
    if (v !== null) {
      const parsed = Number.parseFloat(v);
      if (Number.isFinite(parsed) && parsed >= 0 && parsed <= 1) {
        _volume = parsed;
      }
    }
    const m = localStorage.getItem(STORAGE_KEY_MUTED);
    if (m === "true") _muted = true;
  } catch {
    /* localStorage unavailable — use defaults */
  }
})();

function effectiveVolume() {
  return _muted ? 0 : _volume;
}

export function getVolume() {
  return _volume;
}

export function setVolume(v) {
  if (!Number.isFinite(v)) return;
  _volume = Math.max(0, Math.min(1, v));
  try {
    localStorage.setItem(STORAGE_KEY_VOLUME, String(_volume));
  } catch {
    /* ignore */
  }
}

export function isMuted() {
  return _muted;
}

export function setMuted(b) {
  _muted = !!b;
  try {
    localStorage.setItem(STORAGE_KEY_MUTED, _muted ? "true" : "false");
  } catch {
    /* ignore */
  }
}

export function toggleMute() {
  setMuted(!_muted);
  return _muted;
}

function preload(url) {
  const a = new Audio(url);
  a.volume = effectiveVolume();
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
  const clone = original.cloneNode(true);
  clone.volume = effectiveVolume();
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
    true
  );
}

/**
 * Wire the audio-controls panel: mute button + volume slider.
 * Reads/writes localStorage. Idempotent.
 */
export function wireAudioControls(rootEl) {
  if (!rootEl || rootEl.dataset.wired === "true") return;
  rootEl.dataset.wired = "true";

  const muteBtn = rootEl.querySelector("#audio-mute-btn");
  const slider = rootEl.querySelector("#audio-volume-slider");

  function refresh() {
    if (muteBtn) {
      muteBtn.textContent = _muted ? "Ton an" : "Ton aus";
      muteBtn.setAttribute("aria-pressed", _muted ? "true" : "false");
    }
    if (slider) {
      slider.value = String(Math.round(_volume * 100));
      slider.disabled = _muted;
    }
  }

  if (muteBtn) {
    muteBtn.addEventListener("click", () => {
      toggleMute();
      refresh();
    });
  }
  if (slider) {
    slider.addEventListener("input", () => {
      const pct = Number.parseInt(slider.value, 10);
      if (Number.isFinite(pct)) setVolume(pct / 100);
      // Slider use implies the user wants sound; auto-unmute.
      if (_muted && pct > 0) {
        setMuted(false);
        refresh();
      }
    });
  }
  refresh();
}
