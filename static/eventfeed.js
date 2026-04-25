export class EventFeed {
  constructor(rootEl) {
    this.root = rootEl;
    this.lastSeq = 0;
  }

  render(events) {
    if (!this.root) return;
    const list = events || [];
    const maxSeq = list.reduce((acc, e) => (e.seq > acc ? e.seq : acc), 0);
    const hasNew = maxSeq > this.lastSeq;

    this.root.innerHTML = "";
    const heading = document.createElement("h3");
    heading.textContent = "Eventfeed";
    this.root.appendChild(heading);

    const ul = document.createElement("ul");
    if (list.length === 0) {
      const empty = document.createElement("li");
      empty.className = "event-empty";
      empty.textContent = "Noch nichts passiert.";
      ul.appendChild(empty);
    } else {
      for (const e of list) {
        const li = document.createElement("li");
        li.className = `event-row event-row-${e.severity}`;
        li.textContent = e.message;
        ul.appendChild(li);
      }
    }
    this.root.appendChild(ul);

    if (hasNew) {
      this.root.scrollTop = this.root.scrollHeight;
    }
    this.lastSeq = maxSeq;
  }
}
