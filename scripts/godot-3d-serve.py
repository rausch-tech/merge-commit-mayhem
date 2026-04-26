#!/usr/bin/env python3
"""Lightweight HTTP server that serves Godot Web exports with the
Cross-Origin-Isolation headers Godot 4 needs for SharedArrayBuffer.

Usage:
    cd godot-3d/exports
    python3 ../../scripts/godot-3d-serve.py [port]

Defaults to port 8080.
"""

import http.server
import socketserver
import sys


class CORIRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    with socketserver.TCPServer(("", port), CORIRequestHandler) as httpd:
        print(f"Serving on http://127.0.0.1:{port}/  (COEP+COOP isolation headers)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")


if __name__ == "__main__":
    main()
