/**
 * Meeting overlay: shown while the room is in MEETING phase.
 * Lets the local player cast a vote OR skip exactly once.
 *
 * Inputs to update():
 *   payload.meeting = { title, callerId, remainingSeconds, votesCount: {targetId: count}, alreadyVoted: [playerId] }
 *   payload.players = [{id, name, color, isAlive, ...}]
 *   ownPlayerId = the local player's id
 */
export class MeetingOverlay {
  constructor(rootEl, wsClient) {
    this.root = rootEl;
    this.ws = wsClient;
    this.titleEl = rootEl.querySelector("#meeting-title");
    this.countdownEl = rootEl.querySelector("#meeting-countdown");
    this.voteListEl = rootEl.querySelector("#meeting-vote-list");
    this.skipBtn = rootEl.querySelector("#meeting-skip-btn");
    this.statusEl = rootEl.querySelector("#meeting-status");

    this.skipBtn.addEventListener("click", () => {
      if (this._localHasVoted) return;
      this.ws.send("skip_vote", {});
    });
  }

  hide() {
    this.root.classList.add("hidden");
    this._localHasVoted = false;
  }

  /**
   * Update the meeting view. Called every game_state during MEETING phase.
   *
   * If `meeting` is null (phase != MEETING), the overlay hides itself.
   */
  update({ meeting, players, ownPlayerId }) {
    if (!meeting) {
      this.hide();
      return;
    }
    this.root.classList.remove("hidden");

    this.titleEl.textContent = meeting.title || "Emergency Meeting";
    const sec = Math.max(0, Math.floor(meeting.remainingSeconds || 0));
    this.countdownEl.textContent = `${sec} s`;

    const alreadyVoted = new Set(meeting.alreadyVoted || []);
    this._localHasVoted = alreadyVoted.has(ownPlayerId);

    // Build the vote list from alive players.
    this.voteListEl.innerHTML = "";
    const alive = (players || []).filter((p) => p.isAlive !== false);
    for (const p of alive) {
      const li = document.createElement("li");
      li.className = "meeting-vote-row";
      const dot = document.createElement("span");
      dot.className = "color-dot";
      dot.style.background = p.color;
      const name = document.createElement("span");
      name.className = "meeting-vote-name";
      name.textContent = p.name;
      const voteBtn = document.createElement("button");
      voteBtn.type = "button";
      voteBtn.className = "meeting-vote-btn";
      const count = (meeting.votesCount || {})[p.id] || 0;
      voteBtn.textContent = count > 0 ? `Vote (${count})` : "Vote";
      voteBtn.disabled = this._localHasVoted;
      voteBtn.addEventListener("click", () => {
        if (this._localHasVoted) return;
        this.ws.send("cast_vote", { targetPlayerId: p.id });
      });
      li.appendChild(dot);
      li.appendChild(name);
      li.appendChild(voteBtn);
      this.voteListEl.appendChild(li);
    }

    // Skip count + skip button state.
    const skipCount = (meeting.votesCount || {})[""] || 0;
    this.skipBtn.textContent =
      skipCount > 0 ? `Skip — niemand entfernen (${skipCount})` : "Skip — niemand entfernen";
    this.skipBtn.disabled = this._localHasVoted;

    // Status line — how many of the alive have voted.
    const totalAlive = alive.length;
    const votesCast = (meeting.alreadyVoted || []).length;
    this.statusEl.textContent = this._localHasVoted
      ? `Du hast abgestimmt. ${votesCast}/${totalAlive} fertig.`
      : `${votesCast}/${totalAlive} haben abgestimmt.`;
  }
}

export class VotingResultToast {
  constructor(rootEl) {
    this.root = rootEl;
    this.textEl = rootEl.querySelector("#voting-result-text");
    this._timeoutId = null;
  }

  show(payload, players) {
    let text;
    if (payload.removedPlayerId) {
      const teamLabel = payload.wasChaosAgent ? "Chaos-Agent" : "kein Chaos-Agent";
      text = `${payload.removedPlayerName || "Spieler"} wurde entfernt — war ${teamLabel}.`;
    } else if (payload.skipped) {
      text = "Skip gewonnen — niemand wurde entfernt.";
    } else if (payload.tie) {
      text = "Stimmengleichheit — niemand wurde entfernt.";
    } else {
      text = "Niemand wurde entfernt.";
    }
    this.textEl.textContent = text;
    this.root.classList.remove("hidden");
    if (this._timeoutId) clearTimeout(this._timeoutId);
    this._timeoutId = setTimeout(() => {
      this.root.classList.add("hidden");
      this._timeoutId = null;
    }, 5000);
  }
}

export class EmergencyMeetingBtn {
  /**
   * Visibility logic: the button is shown ONLY when:
   *   - phase is PLAYING
   *   - local player exists in players list and isAlive
   *   - local player is inside the war room AABB
   *   - local player has not yet used their emergency meeting this round
   */
  constructor(btnEl, wsClient) {
    this.btn = btnEl;
    this.ws = wsClient;
    this._meetingAvailable = true; // server is ultimate authority; this is a pre-check optimization
    this.btn.addEventListener("click", () => {
      this.ws.send("call_emergency_meeting", {});
    });
  }

  /** Server-side error indicates we used our meeting. Disable button until reset. */
  markMeetingUsed() {
    this._meetingAvailable = false;
    this.btn.classList.add("hidden");
  }

  /** Reset on lobby_state (new round). */
  reset() {
    this._meetingAvailable = true;
  }

  update({ phase, players, ownPlayerId, warRoomBounds }) {
    if (!warRoomBounds || !this._meetingAvailable || phase !== "playing") {
      this.btn.classList.add("hidden");
      return;
    }
    const me = (players || []).find((p) => p.id === ownPlayerId);
    if (!me || me.isAlive === false) {
      this.btn.classList.add("hidden");
      return;
    }
    const inWarRoom =
      me.x >= warRoomBounds.xMin &&
      me.x <= warRoomBounds.xMax &&
      me.y >= warRoomBounds.yMin &&
      me.y <= warRoomBounds.yMax;
    this.btn.classList.toggle("hidden", !inWarRoom);
  }
}
