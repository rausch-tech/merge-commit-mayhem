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
    // Tier 3.6: meeting context block (reporter, body, recent events).
    this.contextBlock = rootEl.querySelector("#meeting-context");
    this.contextReporter = rootEl.querySelector("#meeting-context-reporter");
    this.contextBody = rootEl.querySelector("#meeting-context-body");
    this.contextEventList = rootEl.querySelector("#meeting-context-event-list");

    // Stable per-player row state. We rebuild only when the alive-player set
    // actually changes — every other update just patches text + disabled in
    // place. Wiping the DOM each tick (server runs at 20 Hz) was racing the
    // ~100-300 ms touch click dispatch and silently swallowing votes on phones.
    this._rows = new Map(); // playerId -> { btn }
    this._signature = null;

    this.skipBtn.addEventListener("click", () => {
      if (this._localHasVoted) return;
      this.ws.send("skip_vote", {});
    });
  }

  hide() {
    this.root.classList.add("hidden");
    this._localHasVoted = false;
    this._signature = null;
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

    // Tier 3.6: render context block (reporter / body / recent events).
    const ctx = meeting.context;
    if (ctx && this.contextBlock) {
      this.contextBlock.classList.remove("hidden");
      const reporter = ctx.reporterName || "?";
      this.contextReporter.textContent = `Gemeldet von: ${reporter}`;
      if (ctx.body && this.contextBody) {
        this.contextBody.textContent = `Body von ${ctx.body.victimName} im ${ctx.body.room}`;
        this.contextBody.classList.remove("hidden");
      } else {
        this.contextBody?.classList.add("hidden");
      }
      // Recent events list — re-render every meeting (small, infrequent).
      if (this.contextEventList) {
        this.contextEventList.innerHTML = "";
        for (const e of (ctx.recentEvents || []).slice(-6)) {
          const li = document.createElement("li");
          li.textContent = e.message;
          this.contextEventList.appendChild(li);
        }
      }
    } else if (this.contextBlock) {
      this.contextBlock.classList.add("hidden");
    }

    const alreadyVoted = new Set(meeting.alreadyVoted || []);
    this._localHasVoted = alreadyVoted.has(ownPlayerId);

    const alive = (players || []).filter((p) => p.isAlive !== false);

    // Rebuild only when the alive set changes (new meeting, eliminated player
    // etc.). During a single meeting this is stable.
    const signature = alive.map((p) => `${p.id}:${p.name}:${p.color}`).join("|");
    if (signature !== this._signature) {
      this._buildRows(alive);
      this._signature = signature;
    }

    // Patch each row's vote count + disabled flag in place.
    for (const p of alive) {
      const entry = this._rows.get(p.id);
      if (!entry) continue;
      const count = (meeting.votesCount || {})[p.id] || 0;
      const wantedText = count > 0 ? `Vote (${count})` : "Vote";
      if (entry.btn.textContent !== wantedText) entry.btn.textContent = wantedText;
      if (entry.btn.disabled !== this._localHasVoted) entry.btn.disabled = this._localHasVoted;
    }

    // Skip count + skip button state.
    const skipCount = (meeting.votesCount || {})[""] || 0;
    const skipText =
      skipCount > 0 ? `Skip — niemand entfernen (${skipCount})` : "Skip — niemand entfernen";
    if (this.skipBtn.textContent !== skipText) this.skipBtn.textContent = skipText;
    if (this.skipBtn.disabled !== this._localHasVoted) {
      this.skipBtn.disabled = this._localHasVoted;
    }

    // Status line — how many of the alive have voted.
    const totalAlive = alive.length;
    const votesCast = (meeting.alreadyVoted || []).length;
    const statusText = this._localHasVoted
      ? `Du hast abgestimmt. ${votesCast}/${totalAlive} fertig.`
      : `${votesCast}/${totalAlive} haben abgestimmt.`;
    if (this.statusEl.textContent !== statusText) this.statusEl.textContent = statusText;
  }

  _buildRows(alive) {
    this.voteListEl.innerHTML = "";
    this._rows = new Map();
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
      voteBtn.textContent = "Vote";
      voteBtn.addEventListener("click", () => {
        if (this._localHasVoted) return;
        this.ws.send("cast_vote", { targetPlayerId: p.id });
      });
      li.appendChild(dot);
      li.appendChild(name);
      li.appendChild(voteBtn);
      this.voteListEl.appendChild(li);
      this._rows.set(p.id, { btn: voteBtn });
    }
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
    // Tier 3.6.5: AI-flavored "last words" line, dimmed under the verdict.
    // Server omits the field on skip/tie so we never render a misleading
    // parting line for someone who didn't actually leave.
    const lastWords = payload.lastWords || "";
    if (lastWords && payload.removedPlayerId) {
      // Insert as a second line. Falls back to plain string append if the
      // wrapping element doesn't exist yet — keeps backwards-compat with
      // the older single-textEl markup.
      this.textEl.innerHTML = "";
      const verdict = document.createElement("div");
      verdict.className = "voting-result-verdict";
      verdict.textContent = text;
      const quote = document.createElement("div");
      quote.className = "voting-result-lastwords";
      quote.textContent = `„${lastWords}"`;
      this.textEl.appendChild(verdict);
      this.textEl.appendChild(quote);
    } else {
      this.textEl.textContent = text;
    }
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
