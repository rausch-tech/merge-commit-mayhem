import { WsClient } from "./ws.js";
import { attachInput } from "./input.js";
import { Renderer } from "./render.js";
import { Hud } from "./hud.js";

const state = {
  playerId: null,
  isHost: false,
  roomCode: null,
  phase: "lobby",
  players: [],
  ownRole: null,
};

const els = {
  joinForm: document.getElementById("join-form"),
  lobbyWaiting: document.getElementById("lobby-waiting"),
  lobbyRoomCode: document.getElementById("lobby-room-code"),
  lobbyPlayerList: document.getElementById("lobby-player-list"),
  btnJoin: document.getElementById("btn-join"),
  btnStart: document.getElementById("btn-start"),
  inputName: document.getElementById("input-name"),
  inputRoomCode: document.getElementById("input-room-code"),
  lobbyScreen: document.getElementById("lobby-screen"),
  gameScreen: document.getElementById("game-screen"),
  errorBanner: document.getElementById("error-banner"),
  canvas: document.getElementById("game-canvas"),
};

const wsUrl = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
const ws = new WsClient(wsUrl);
const hud = new Hud();
const renderer = new Renderer(els.canvas);
renderer.start();

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
}

ws.on("room_joined", (payload) => {
  state.playerId = payload.playerId;
  state.isHost = payload.isHost;
  state.roomCode = payload.roomCode;
  renderer.setOwnPlayerId(payload.playerId);
  els.joinForm.classList.add("hidden");
  els.lobbyWaiting.classList.remove("hidden");
  els.lobbyRoomCode.textContent = payload.roomCode;
});

ws.on("lobby_state", (payload) => {
  state.players = payload.players;
  renderLobby();
});

ws.on("private_role", (payload) => {
  state.ownRole = payload;
  hud.setRole(payload.role, payload.team);
});

ws.on("game_state", (payload) => {
  if (state.phase !== "playing" && payload.phase === "playing") {
    els.lobbyScreen.classList.add("hidden");
    els.gameScreen.classList.remove("hidden");
  }
  state.phase = payload.phase;
  state.players = payload.players;
  renderer.setPlayers(payload.players);
  hud.setTimer(payload.remainingSeconds);
  hud.setPlayers(payload.players);
});

ws.on("error", (payload) => {
  showError(`${payload.code}: ${payload.message}`);
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
  ws.send("start_game", {});
});

attachInput(ws);
ws.connect();
