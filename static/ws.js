// Minimal WebSocket wrapper. No reconnection state restore — a closed socket
// requires re-joining from the lobby. The server is the source of truth.

const RECONNECT_DELAY_MS = 3000;

export class WsClient {
  constructor(url) {
    this.url = url;
    this.handlers = new Map(); // type -> fn(payload)
    this.socket = null;
    this.shouldReconnect = true;
    this._onOpen = null;
  }

  on(type, fn) {
    this.handlers.set(type, fn);
  }

  onOpen(fn) {
    this._onOpen = fn;
  }

  connect() {
    this.socket = new WebSocket(this.url);
    this.socket.addEventListener("open", () => {
      if (this._onOpen) this._onOpen();
    });
    this.socket.addEventListener("message", (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      const handler = this.handlers.get(msg.type);
      if (handler) handler(msg.payload);
    });
    this.socket.addEventListener("close", () => {
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(), RECONNECT_DELAY_MS);
      }
    });
  }

  send(type, payload) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    this.socket.send(JSON.stringify({ type, payload: payload ?? {} }));
  }
}
