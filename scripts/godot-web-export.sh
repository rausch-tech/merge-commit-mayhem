#!/usr/bin/env bash
# Godot Web-Export builder fuer den MCM 3D-Client.
#
# Produces: godot-3d/exports/{index.html, index.js, index.wasm, index.pck,
#           index.png, index.audio.worklet.js, index.audio.position.worklet.js}
#
# Output ist gitignored (siehe .gitignore: "godot-3d/exports/"). Lokal bauen,
# dann mit dem laufenden Backend serven (FastAPI mountet "/godot/" auf das
# exports-Verzeichnis und setzt COOP/COEP-Headers fuer SharedArrayBuffer).
#
# Usage:
#   scripts/godot-web-export.sh             # release build
#   scripts/godot-web-export.sh -d          # debug build (zeigt console-logs)
#   scripts/godot-web-export.sh --serve     # build + dev-server auf 8000
#
# Setup-Voraussetzung: Godot 4.6 + Web-Export-Templates installiert. Templates
# kommen mit dem Standard-Godot-Setup (siehe docs/GODOT_HANDOFF.md). Skript
# scheitert mit klarer Meldung wenn was fehlt.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT="$REPO_ROOT/godot-3d"
OUTPUT="$PROJECT/exports/index.html"

if ! command -v godot >/dev/null 2>&1; then
    echo "ERROR: 'godot' nicht im PATH. Install: siehe docs/GODOT_HANDOFF.md." >&2
    exit 2
fi

# Web-Templates muessen am Standard-Pfad liegen, sonst fehlt die .wasm-Quelle.
TPL_ROOT="${HOME}/.local/share/godot/export_templates/4.6.stable"
if [[ ! -f "$TPL_ROOT/web_release.zip" ]]; then
    echo "ERROR: Godot 4.6 Web-Export-Template fehlt unter $TPL_ROOT/web_release.zip." >&2
    echo "Im Godot-Editor: Editor > Manage Export Templates > Download and Install." >&2
    exit 2
fi

mode="release"
serve=0
for arg in "$@"; do
    case "$arg" in
        -d|--debug) mode="debug" ;;
        --serve)    serve=1 ;;
        *)          echo "WARN: unknown arg '$arg'" >&2 ;;
    esac
done

mkdir -p "$(dirname "$OUTPUT")"

echo "[godot-web-export] Building Godot Web ($mode) -> $OUTPUT"
if [[ "$mode" == "debug" ]]; then
    godot --headless --path "$PROJECT" --export-debug "Web" "$OUTPUT"
else
    godot --headless --path "$PROJECT" --export-release "Web" "$OUTPUT"
fi

echo "[godot-web-export] Output:"
ls -lh "$PROJECT/exports/" | awk 'NR>1 {printf "  %-12s %s\n", $5, $9}'

if [[ "$serve" -eq 1 ]]; then
    echo ""
    echo "[godot-web-export] Starte Backend mit /godot/-Mount auf Port 8000."
    echo "  -> http://localhost:8000/godot/"
    cd "$REPO_ROOT"
    exec uv run uvicorn app.main:app --port 8000 --reload
fi
