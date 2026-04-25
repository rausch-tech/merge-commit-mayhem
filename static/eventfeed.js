export class EventFeed {
  constructor(rootEl) {
    this.root = rootEl;
    this.lastSeq = 0;
    this.renderedEmpty = false;
  }

  render(events) {
    if (!this.root) return;
    const list = events || [];

    if (list.length === 0) {
      // Render the empty state once, or whenever seq has been reset
      // (reset_for_new_round() drops events and restarts seq at 1).
      if (this.lastSeq !== 0 || !this.renderedEmpty) {
        this._renderEmpty();
        this.renderedEmpty = true;
        this.lastSeq = 0;
      }
      return;
    }

    // Events arrive oldest -> newest, so the last entry has the max seq.
    const maxSeq = list[list.length - 1].seq;
    if (maxSeq <= this.lastSeq) return;

    this._renderList(list);
    this.lastSeq = maxSeq;
    this.renderedEmpty = false;
    this.root.scrollTop = this.root.scrollHeight;
  }

  _renderEmpty() {
    this.root.innerHTML = "";
    const heading = document.createElement("h3");
    heading.textContent = "Eventfeed";
    this.root.appendChild(heading);

    const ul = document.createElement("ul");
    const empty = document.createElement("li");
    empty.className = "event-empty";
    empty.textContent = "Noch nichts passiert.";
    ul.appendChild(empty);
    this.root.appendChild(ul);
  }

  _renderList(list) {
    this.root.innerHTML = "";
    const heading = document.createElement("h3");
    heading.textContent = "Eventfeed";
    this.root.appendChild(heading);

    const ul = document.createElement("ul");
    for (const e of list) {
      const li = document.createElement("li");
      li.className = `event-row event-row-${e.severity}`;
      li.textContent = e.message;
      ul.appendChild(li);
    }
    this.root.appendChild(ul);
  }
}
