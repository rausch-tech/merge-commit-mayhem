import { beforeEach, describe, expect, it, vi } from "vitest";

import { MeetingOverlay } from "../static/meetings.js";

const MEETING_HTML = `
  <div id="meeting-overlay" class="hidden">
    <div id="meeting-card">
      <h1 id="meeting-title"></h1>
      <p id="meeting-countdown" class="meeting-countdown"></p>
      <h3>Wer war's?</h3>
      <ul id="meeting-vote-list"></ul>
      <button id="meeting-skip-btn" type="button"></button>
      <p id="meeting-status" class="meeting-status"></p>
    </div>
  </div>
`;

function fakeWs() {
  return { send: vi.fn() };
}

function alivePlayers() {
  return [
    { id: "p1", name: "Alice", color: "#4ade80", isAlive: true },
    { id: "p2", name: "Bob", color: "#60a5fa", isAlive: true },
  ];
}

describe("MeetingOverlay", () => {
  let root;
  let ws;

  beforeEach(() => {
    document.body.innerHTML = MEETING_HTML;
    root = document.getElementById("meeting-overlay");
    ws = fakeWs();
  });

  it("renders one vote row per alive player", () => {
    const overlay = new MeetingOverlay(root, ws);
    overlay.update({
      meeting: { title: "Test", remainingSeconds: 30, votesCount: {}, alreadyVoted: [] },
      players: alivePlayers(),
      ownPlayerId: "p1",
    });
    const rows = root.querySelectorAll(".meeting-vote-row");
    expect(rows.length).toBe(2);
  });

  it("preserves vote-button DOM nodes across rapid re-renders (touch click safety)", () => {
    // Bug repro: server ticks at 20 Hz → MeetingOverlay.update() ran every 50 ms
    // and used innerHTML = "" to wipe the vote list, recreating buttons. On
    // touch, the click event lands ~100-300 ms after touchstart, so the button
    // node could be replaced mid-tap and the click fired into the void.
    const overlay = new MeetingOverlay(root, ws);
    const payload = (votes) => ({
      meeting: { title: "Test", remainingSeconds: 30, votesCount: votes, alreadyVoted: [] },
      players: alivePlayers(),
      ownPlayerId: "p1",
    });
    overlay.update(payload({}));
    const firstBtn = root.querySelector(".meeting-vote-row button.meeting-vote-btn");
    expect(firstBtn).not.toBeNull();
    // Simulate many ticks with changing vote counts.
    for (let i = 1; i <= 5; i++) {
      overlay.update(payload({ p1: i }));
    }
    const sameBtn = root.querySelector(".meeting-vote-row button.meeting-vote-btn");
    expect(sameBtn).toBe(firstBtn); // SAME node, not a recreated one
    expect(sameBtn.textContent).toContain("5"); // text updated in place
  });

  it("vote button click sends cast_vote with the right player id", () => {
    const overlay = new MeetingOverlay(root, ws);
    overlay.update({
      meeting: { title: "Test", remainingSeconds: 30, votesCount: {}, alreadyVoted: [] },
      players: alivePlayers(),
      ownPlayerId: "p1",
    });
    const rows = root.querySelectorAll(".meeting-vote-row");
    rows[1].querySelector("button.meeting-vote-btn").click();
    expect(ws.send).toHaveBeenCalledWith("cast_vote", { targetPlayerId: "p2" });
  });

  it("disables all vote + skip buttons once the local player has voted", () => {
    const overlay = new MeetingOverlay(root, ws);
    overlay.update({
      meeting: { title: "Test", remainingSeconds: 30, votesCount: { p2: 1 }, alreadyVoted: ["p1"] },
      players: alivePlayers(),
      ownPlayerId: "p1",
    });
    const voteBtns = root.querySelectorAll(".meeting-vote-btn");
    for (const b of voteBtns) expect(b.disabled).toBe(true);
    expect(document.getElementById("meeting-skip-btn").disabled).toBe(true);
  });

  it("rebuilds rows when the alive-player set changes (new meeting)", () => {
    const overlay = new MeetingOverlay(root, ws);
    overlay.update({
      meeting: { title: "T", remainingSeconds: 30, votesCount: {}, alreadyVoted: [] },
      players: alivePlayers(),
      ownPlayerId: "p1",
    });
    expect(root.querySelectorAll(".meeting-vote-row").length).toBe(2);
    // Simulate a new meeting in a smaller round.
    overlay.hide();
    overlay.update({
      meeting: { title: "T", remainingSeconds: 30, votesCount: {}, alreadyVoted: [] },
      players: [{ id: "p3", name: "Cara", color: "#fb923c", isAlive: true }],
      ownPlayerId: "p3",
    });
    expect(root.querySelectorAll(".meeting-vote-row").length).toBe(1);
  });
});
