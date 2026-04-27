import { ensureKindsLoaded } from "./kinds.js";
import { WsClient } from "./ws.js";
import {
  attachInput,
  attachRepairInteraction,
  attachTaskInteraction,
  attachVentInteraction,
} from "./input.js";
import { Renderer } from "./render.js";
import { Hud } from "./hud.js";
import { TaskList } from "./tasks.js";
import { SabotagePanel } from "./sabotages.js";
import { EndscreenOverlay } from "./endscreen.js";
import { playTaskComplete, wireAudioControls, wireGlobalClickSound } from "./audio.js";
import { MeetingOverlay, VotingResultToast, EmergencyMeetingBtn } from "./meetings.js";
import { EventFeed } from "./eventfeed.js";
import { TakedownButton } from "./takedown.js";
import { ReportButton } from "./report.js";
import { InGameMenu } from "./menu.js";
import { MiniGameModal } from "./minigames/base.js";
import { TouchControls } from "./touch-controls.js";
import { RoleIntroModal } from "./role_intro.js";

// Fire-and-forget: kick off /api/kinds at boot so the renderer has the
// kind→style mapping ready before the first map frame paints. A network
// blip leaves drawMapObjects in fallback mode (neutral grey), graceful
// degradation rather than a crash.
ensureKindsLoaded().catch((err) => {
  // eslint-disable-next-line no-console
  console.warn("[mcm] /api/kinds not available — neutral fills as fallback:", err);
});

const SESSION_KEY = "mcm.session";

function saveSession(roomCode, playerId) {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ roomCode, playerId }));
  } catch {
    /* ignore quota errors */
  }
}

function loadSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function clearSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}

const state = {
  playerId: null,
  isHost: false,
  roomCode: null,
  phase: "lobby",
  players: [],
  ownRole: null,
  map: null,
  bodies: [],
  takedownCooldown: 0,
  amDead: false,
  availableMaps: [],
  selectedMapId: "",
  commsDown: false,
};

const previousTaskStatus = {}; // taskId -> last seen status

const els = {
  joinForm: document.getElementById("join-form"),
  lobbyWaiting: document.getElementById("lobby-waiting"),
  lobbyRoomCode: document.getElementById("lobby-room-code"),
  lobbyPlayerList: document.getElementById("lobby-player-list"),
  btnJoin: document.getElementById("btn-join"),
  btnStart: document.getElementById("btn-start"),
  demoModeRow: document.getElementById("demo-mode-row"),
  demoMode: document.getElementById("demo-mode"),
  mapSelector: document.getElementById("map-selector"),
  mapDropdown: document.getElementById("map-dropdown"),
  inputName: document.getElementById("input-name"),
  inputRoomCode: document.getElementById("input-room-code"),
  lobbyScreen: document.getElementById("lobby-screen"),
  gameScreen: document.getElementById("game-screen"),
  errorBanner: document.getElementById("error-banner"),
  canvas: document.getElementById("game-canvas"),
  ghostBanner: document.getElementById("ghost-banner"),
};

const taskSidebarEl = document.getElementById("task-sidebar");
const taskList = new TaskList(taskSidebarEl);

const eventFeedEl = document.getElementById("event-feed");
const eventFeed = new EventFeed(eventFeedEl);

const wsUrl = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
const ws = new WsClient(wsUrl);
const hud = new Hud();
const renderer = new Renderer(els.canvas);
renderer.start();

// Initial size + react to window resize. The ResizeObserver also catches
// the display:none → block transition when the game-screen first appears,
// which window 'resize' events do not fire for. Without this the canvas
// backbuffer stays at 1×1 from the lobby and renders nothing.
const resizeRenderer = () => renderer.resize();
window.addEventListener("resize", resizeRenderer);
const canvasResizeObserver = new ResizeObserver(resizeRenderer);
canvasResizeObserver.observe(els.canvas);

const sabotagePanelEl = document.getElementById("sabotage-panel");
const sabotagePanel = new SabotagePanel(sabotagePanelEl, ws);

const endscreen = new EndscreenOverlay(document.getElementById("endscreen"), ws);
const roleIntro = new RoleIntroModal(document.getElementById("role-intro"));

// Tier 3.5: Ability button (Coffee Run / Rollback / Standup / Reproduce Bug).
const abilityBtnEl = document.getElementById("ability-btn");
if (abilityBtnEl) {
  abilityBtnEl.addEventListener("click", () => {
    if (abilityBtnEl.disabled) return;
    ws.send("use_ability", {});
  });
}

// Tier 3.5: lobby role-preference dropdown.
const roleDropdownEl = document.getElementById("role-dropdown");
if (roleDropdownEl) {
  roleDropdownEl.addEventListener("change", () => {
    const v = roleDropdownEl.value || null;
    ws.send("set_preferred_role", { role: v });
  });
}

function warRoomBoundsFromMap(map) {
  if (!map) return null;
  const room = (map.rooms || []).find((r) => r.id === map.warRoomId);
  if (!room) return null;
  return { xMin: room.x, yMin: room.y, xMax: room.x + room.width, yMax: room.y + room.height };
}

const meetingOverlay = new MeetingOverlay(document.getElementById("meeting-overlay"), ws);
const votingResultToast = new VotingResultToast(document.getElementById("voting-result-toast"));
const emergencyBtn = new EmergencyMeetingBtn(document.getElementById("emergency-meeting-btn"), ws);
const takedownBtn = new TakedownButton(document.getElementById("takedown-btn"), ws);
const reportBtn = new ReportButton(document.getElementById("report-btn"), ws);

const miniGameModal = new MiniGameModal(document.getElementById("mini-game-modal"), ws);

ws.on("mini_game_started", (payload) => miniGameModal.onStarted(payload));
ws.on("mini_game_state", (payload) => miniGameModal.onState(payload));
ws.on("mini_game_completed", (payload) => miniGameModal.onCompleted(payload));

const menu = new InGameMenu(
  document.getElementById("in-game-menu"),
  document.getElementById("audio-controls"),
  {
    onLeave: () => {
      ws.send("leave_room", {});
      clearSession();
      // Reset client state and bring the join form back. The server has
      // already removed our player record; staying connected on the WS is
      // fine — the next join_room creates a fresh identity.
      state.playerId = null;
      state.isHost = false;
      state.roomCode = null;
      state.phase = "lobby";
      state.players = [];
      state.ownRole = null;
      state.map = null;
      state.bodies = [];
      state.amDead = false;
      renderer.setOwnPlayerId(null);
      renderer.setMap(null);
      renderer.setPlayers([]);
      els.gameScreen.classList.add("hidden");
      els.lobbyScreen.classList.remove("hidden");
      els.lobbyWaiting.classList.add("hidden");
      els.joinForm.classList.remove("hidden");
      els.ghostBanner.classList.add("hidden");
      endscreen.hide();
      meetingOverlay.hide();
      sabotagePanel.setAvailable([]);
    },
    onAbort: () => {
      ws.send("abort_round", {});
    },
  }
);

function _refreshMenu(tasks) {
  menu.update({
    inRoom: !!state.playerId,
    isHost: state.isHost,
    phase: state.phase,
    ownRole: state.ownRole,
    tasks: tasks || [],
  });
}

function showError(msg) {
  els.errorBanner.textContent = msg;
  els.errorBanner.classList.remove("hidden");
  setTimeout(() => els.errorBanner.classList.add("hidden"), 4000);
}

function renderLobby() {
  els.lobbyPlayerList.innerHTML = "";
  for (const p of state.players) {
    const li = document.createElement("li");
    const dot = document.createElement("span");
    dot.className = "color-dot";
    dot.style.background = p.color;
    li.appendChild(dot);
    const text = document.createElement("span");
    let suffix = "";
    if (p.isHost) suffix += "  (Host)";
    if (p.preferredRole) {
      const niceRole =
        {
          developer: "Developer",
          devops_engineer: "DevOps",
          qa_lead: "QA",
          scrum_master: "Scrum",
          caffeine_collector: "Caffeine",
        }[p.preferredRole] || p.preferredRole;
      suffix += `  · will: ${niceRole}`;
    }
    text.textContent = p.name + suffix;
    li.appendChild(text);
    els.lobbyPlayerList.appendChild(li);
  }
  els.btnStart.classList.toggle("hidden", !state.isHost);
  els.demoModeRow.classList.toggle("hidden", !state.isHost);
  renderMapSelector();
}

function renderMapSelector() {
  if (!els.mapDropdown || !els.mapSelector) return;
  const maps = state.availableMaps || [];
  // Rebuild options only when the list contents changed.
  const signature = maps.map((m) => `${m.id}:${m.name}`).join("|");
  if (els.mapDropdown.dataset.signature !== signature) {
    els.mapDropdown.innerHTML = "";
    for (const m of maps) {
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.name;
      els.mapDropdown.appendChild(opt);
    }
    els.mapDropdown.dataset.signature = signature;
  }
  if (state.selectedMapId) {
    els.mapDropdown.value = state.selectedMapId;
  }
  // Host only — non-hosts see no selector at all.
  els.mapSelector.classList.toggle("hidden", !state.isHost || maps.length === 0);
}

ws.on("room_joined", (payload) => {
  state.playerId = payload.playerId;
  state.isHost = payload.isHost;
  state.roomCode = payload.roomCode;
  state.map = payload.map || null;
  saveSession(payload.roomCode, payload.playerId);
  renderer.setOwnPlayerId(payload.playerId);
  renderer.setMap(payload.map || null);
  renderer.resize();
  els.joinForm.classList.add("hidden");
  els.lobbyWaiting.classList.remove("hidden");
  els.lobbyRoomCode.textContent = payload.roomCode;
  _refreshMenu();
});

ws.on("lobby_state", (payload) => {
  state.players = payload.players;
  state.availableMaps = payload.availableMaps || [];
  state.selectedMapId = payload.selectedMapId || "";
  if (payload.map && Object.keys(payload.map).length > 0) {
    state.map = payload.map;
    renderer.setMap(payload.map);
  }
  state.phase = "lobby";
  state.amDead = false;
  els.ghostBanner.classList.add("hidden");
  endscreen.hide();
  meetingOverlay.hide();
  emergencyBtn.reset();
  // If we were on the game screen (post-round reset), swap back to lobby.
  els.gameScreen.classList.add("hidden");
  els.lobbyScreen.classList.remove("hidden");
  els.joinForm.classList.add("hidden"); // already joined
  els.lobbyWaiting.classList.remove("hidden");
  // Also make sure sabotage panel hides until next start.
  sabotagePanel.setAvailable([]);
  // Reset role recap; a new round assigns a fresh role.
  state.ownRole = null;
  renderLobby();
  _refreshMenu();
});

ws.on("game_ended", (payload) => {
  endscreen.show(payload, state.isHost);
  // Tier 3.7: finalSummary travels via game_state. Stash + apply if present
  // (game_state usually arrives just after game_ended on the same tick).
  if (state._lastFinalSummary) {
    endscreen.applyFinalSummary(state._lastFinalSummary);
  }
  // Reset the role-intro dedupe so the next round shows the modal again.
  roleIntro.reset();
});

ws.on("private_role", (payload) => {
  state.ownRole = payload;
  hud.setRole(payload.title || payload.role, payload.team);
  sabotagePanel.setAvailable(payload.availableSabotages || []);
  renderer.setOwnTeam(payload.team || null);
  // Tier 3.5: highlight personal tasks in the sidebar + strength categories.
  taskList.setPersonal(payload.assignedTaskIds || [], payload.strengthCategories || []);
  _refreshMenu();
  // Tier 3.5: Role-Intro modal (auto-deduped within a round).
  roleIntro.show(payload);
  // Tier 3.5: ability button visibility.
  _updateAbilityButton();
});

function _updateAbilityButton() {
  if (!abilityBtnEl) return;
  const role = state.ownRole;
  if (!role || !role.abilityId || state.amDead || state.phase !== "playing") {
    abilityBtnEl.classList.add("hidden");
    return;
  }
  abilityBtnEl.classList.remove("hidden");
  abilityBtnEl.textContent = role.abilityLabel || "Ability";
  abilityBtnEl.disabled = !!state.abilityUsed;
  abilityBtnEl.title = role.abilityHint || "";
}

ws.on("game_state", (payload) => {
  if (state.phase !== "playing" && payload.phase === "playing") {
    els.lobbyScreen.classList.add("hidden");
    els.gameScreen.classList.remove("hidden");
    // The canvas was hidden until just now, so its first measurable size
    // happens here. ResizeObserver alone misses some display:none → block
    // transitions, so resize explicitly on the phase switch.
    renderer.resize();
  }
  state.phase = payload.phase;
  state.players = payload.players;
  state.bodies = payload.bodies || [];
  // Tier 3.7: stash the final summary so game_ended can pick it up.
  state._lastFinalSummary = payload.finalSummary || null;
  if (payload.phase === "ended" && payload.finalSummary) {
    endscreen.applyFinalSummary(payload.finalSummary);
  }

  // Detect ghost transition. Server sends personalized state — alive viewers
  // see only alive players (themselves included), so own entry is always
  // present with isAlive=true. A ghost viewer sees everyone, themselves with
  // isAlive=false. If our entry is transiently missing (mid-disconnect race),
  // we keep the previous amDead state on this tick rather than flicker.
  const me = (payload.players || []).find((p) => p.id === state.playerId);
  const wasDead = state.amDead;
  if (me) state.amDead = me.isAlive === false;
  if (state.amDead !== wasDead) {
    els.ghostBanner.classList.toggle("hidden", !state.amDead);
  }
  renderer.setPlayers(payload.players);
  renderer.setTasks(payload.tasks || []);
  renderer.setBodies(state.bodies);
  // Tier 2.4: lights-out vignette + visible repair panels for active sabotages.
  const activeSabotageIds = new Set(
    (payload.sabotages || []).filter((s) => s.active).map((s) => s.id)
  );
  const activePanels = (payload.sabotagePanels || []).filter((p) =>
    activeSabotageIds.has(p.sabotageId)
  );
  renderer.setActivePanels(activePanels);
  renderer.setLightsOff(!!payload.lightsOff);
  // Tier 2.3: vents are part of the static map snapshot but the server now
  // re-broadcasts them in every game_state for client-side simplicity.
  renderer.setVents(payload.vents || []);
  // Tier 2.7 rework: per-sabotage proximity. Each sabotage carries its
  // allowed anchors; renderer computes per-sabotage availability locally.
  renderer.setSabotagesPayload(payload.sabotages || []);
  // Tier 2.5: Slack-Down — clear the task sidebar visually and flag the
  // sabotage panel so chaos buttons gray out.
  state.commsDown = !!payload.commsDown;
  // Tier 2.5: when comms are down the release team can't see their tasks.
  // The list still exists server-side; we just hide it client-side until
  // someone repairs the comms panel.
  taskList.render(payload.commsDown ? [] : payload.tasks || []);
  for (const t of payload.tasks || []) {
    const prev = previousTaskStatus[t.id];
    if (prev === "in_progress" && t.status === "cooldown") {
      playTaskComplete();
    }
    previousTaskStatus[t.id] = t.status;
  }
  hud.setTimer(payload.remainingSeconds);
  hud.setStats({
    releaseProgress: payload.releaseProgress,
    pipelineStability: payload.pipelineStability,
    coffeeLevel: payload.coffeeLevel,
    incidents: payload.incidents,
  });
  sabotagePanel.updateFromGameState(payload.sabotages || [], {
    disabledByOwnDeath: state.amDead,
    disabledByCommsDown: !!payload.commsDown,
    objectAvailability: renderer.sabotageObjectAvailability,
  });
  eventFeed.render(payload.events || []);

  // Meeting overlay shows during MEETING phase, hides otherwise.
  meetingOverlay.update({
    meeting: payload.meeting,
    players: payload.players,
    ownPlayerId: state.playerId,
  });

  // Emergency button visibility recomputed each tick.
  emergencyBtn.update({
    phase: payload.phase,
    players: payload.players,
    ownPlayerId: state.playerId,
    warRoomBounds: warRoomBoundsFromMap(state.map),
  });

  // Take-Down (chaos-only) and Report (anyone) visibility — both server-gated.
  takedownBtn.update({
    phase: payload.phase,
    players: payload.players,
    ownPlayerId: state.playerId,
    ownTeam: state.ownRole?.team || null,
    cooldown: state.takedownCooldown,
  });
  reportBtn.update({
    phase: payload.phase,
    players: payload.players,
    ownPlayerId: state.playerId,
    bodies: state.bodies,
  });

  _refreshMenu(payload.tasks);
});

ws.on("private_state", (payload) => {
  state.takedownCooldown = payload.takedownCooldownRemaining || 0;
  // Tier 3.5: per-viewer coffee energy + ability used.
  state.coffeeEnergy = payload.coffeeEnergy ?? 100;
  state.coffeeMax = payload.coffeeMax ?? 100;
  state.abilityUsed = !!payload.abilityUsed;
  hud.setMyCoffee(state.coffeeEnergy, state.coffeeMax);
  _updateAbilityButton();
  takedownBtn.update({
    phase: state.phase,
    players: state.players,
    ownPlayerId: state.playerId,
    ownTeam: state.ownRole?.team || null,
    cooldown: state.takedownCooldown,
  });
});

ws.on("voting_result", (payload) => {
  votingResultToast.show(payload, state.players);
});

ws.on("error", (payload) => {
  showError(`${payload.code}: ${payload.message}`);
  if (payload.code === "NO_MEETING_LEFT") {
    emergencyBtn.markMeetingUsed();
  }
  if (payload.code === "REJOIN_NOT_AVAILABLE") {
    clearSession();
    // Bring the user back to the join form.
    els.joinForm.classList.remove("hidden");
    els.lobbyWaiting.classList.add("hidden");
    state.playerId = null;
    state.roomCode = null;
  }
});

els.btnJoin.addEventListener("click", () => {
  const name = els.inputName.value.trim();
  const roomCode = els.inputRoomCode.value.trim().toUpperCase();
  if (!name || !roomCode) {
    showError("Name und Raumcode sind Pflicht.");
    return;
  }
  ws.send("join_room", { roomCode, playerName: name });
});

els.btnStart.addEventListener("click", () => {
  const demo = !!els.demoMode.checked;
  ws.send("start_game", { demo });
});

if (els.mapDropdown) {
  els.mapDropdown.addEventListener("change", () => {
    if (!state.isHost) return;
    const mapId = els.mapDropdown.value;
    if (!mapId || mapId === state.selectedMapId) return;
    ws.send("select_map", { mapId });
  });
}

attachInput(ws);
attachTaskInteraction(ws, renderer, () => miniGameModal.isOpen());
attachRepairInteraction(ws, renderer);
attachVentInteraction(ws, renderer);

// Quick-hack mobile controls. Activated only when the device exposes a
// coarse pointer (touchscreen). Maps onto the same WS messages as keyboard.
const isTouch = window.matchMedia?.("(pointer: coarse)").matches ?? false;
if (isTouch) {
  document.body.classList.add("touch-active");
  const touchEl = document.getElementById("touch-controls");
  touchEl.classList.remove("hidden");

  // Off-canvas drawer toggles for tasks-sidebar (left) and sabotage-panel (right).
  // Mutually exclusive — opening one closes the other.
  const tabTasksEl = document.getElementById("mobile-tab-tasks");
  const tabSaboEl = document.getElementById("mobile-tab-sabo");
  const setDrawer = (name) => {
    const body = document.body;
    const isOpen = name && body.classList.contains(`drawer-${name}-open`);
    body.classList.remove("drawer-tasks-open", "drawer-sabo-open");
    tabTasksEl?.setAttribute("aria-pressed", "false");
    tabSaboEl?.setAttribute("aria-pressed", "false");
    if (name && !isOpen) {
      body.classList.add(`drawer-${name}-open`);
      const tab = name === "tasks" ? tabTasksEl : tabSaboEl;
      tab?.setAttribute("aria-pressed", "true");
    }
  };
  tabTasksEl?.addEventListener("click", () => setDrawer("tasks"));
  tabSaboEl?.addEventListener("click", () => setDrawer("sabo"));

  // Show the sabotage edge-tab only when the player actually has chaos abilities.
  // We hook into setAvailable so the existing call sites (private_role, lobby
  // resets) drive the tab visibility automatically.
  const _origSetAvailable = sabotagePanel.setAvailable.bind(sabotagePanel);
  sabotagePanel.setAvailable = (ids) => {
    _origSetAvailable(ids);
    const has = (ids || []).length > 0;
    tabSaboEl?.classList.toggle("hidden", !has);
    if (!has && document.body.classList.contains("drawer-sabo-open")) {
      setDrawer(null);
    }
  };

  let lastTaskHoldId = null;
  new TouchControls(touchEl, {
    onMove: (axis) => ws.send("player_input", axis),
    onTaskDown: () => {
      const taskId = renderer.localPlayerInRange;
      if (!taskId) return;
      lastTaskHoldId = taskId;
      ws.send("task_hold_start", { taskId });
    },
    onTaskUp: () => {
      if (lastTaskHoldId === null) return;
      // While a mini-game modal is open, the cancel-button owns the stop;
      // suppress here as on keyboard E-up.
      const stoppedId = lastTaskHoldId;
      lastTaskHoldId = null;
      if (miniGameModal.isOpen()) return;
      ws.send("task_hold_stop", { taskId: stoppedId });
    },
    onRepair: () => {
      const sabotageId = renderer.localPlayerNearPanel;
      if (!sabotageId) return;
      ws.send("repair_sabotage", { sabotageId });
    },
    onVent: () => {
      const vent = renderer.localPlayerNearVent;
      if (!vent || !vent.connectedTo?.length) return;
      // Cycle locally: pick first connection on each tap (server validates).
      const targetVentId = vent.connectedTo[0];
      ws.send("use_vent", { targetVentId });
    },
    onMenu: () => menu.toggle(),
  });
}
ws.onOpen(() => {
  const session = loadSession();
  if (session && session.roomCode && session.playerId) {
    ws.send("rejoin", { roomCode: session.roomCode, playerId: session.playerId });
  }
  // If no saved session: do nothing — wait for user to click Join.
});
ws.connect();
wireGlobalClickSound();
wireAudioControls(document.getElementById("audio-controls"));
