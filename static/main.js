import { WsClient } from "./ws.js";
import { attachInput, attachTaskInteraction } from "./input.js";
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
    text.textContent = p.name + (p.isHost ? "  (Host)" : "");
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
});

ws.on("private_role", (payload) => {
  state.ownRole = payload;
  hud.setRole(payload.role, payload.team);
  sabotagePanel.setAvailable(payload.availableSabotages || []);
  _refreshMenu();
});

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
  taskList.render(payload.tasks || []);
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
  // Refresh take-down button immediately so the cooldown text updates.
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
attachTaskInteraction(ws, renderer);
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
