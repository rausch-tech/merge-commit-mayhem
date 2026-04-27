#!/usr/bin/env bash
# GDScript-Parse-Check fuer den Godot-Client unter godot-3d/.
# Laeuft per Headless-Godot — kein Editor noetig.
#
# Usage:
#   scripts/godot-check.sh             # checks all scripts in godot-3d/scripts/
#   scripts/godot-check.sh -v          # verbose mode (zeigt Engine-Banner)
#
# Exit-Code 0 wenn alle parsen, 1 wenn mindestens einer scheitert.
# Setup: ~/.local/bin/godot muss auf eine Godot-4.x-Binary zeigen.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT="$REPO_ROOT/godot-3d"

if [[ ! -d "$PROJECT" ]]; then
    echo "No Godot project at $PROJECT — nothing to check."
    exit 0
fi

if ! command -v godot >/dev/null 2>&1; then
    echo "ERROR: godot binary nicht im PATH. Install: siehe docs/GODOT_HANDOFF.md." >&2
    exit 2
fi

verbose=0
if [[ "${1:-}" == "-v" || "${1:-}" == "--verbose" ]]; then
    verbose=1
fi

failed=0
checked=0

for script in "$PROJECT"/scripts/*.gd; do
    rel="${script#$REPO_ROOT/}"
    out=$(godot --headless --path "$PROJECT" --check-only --script "$script" 2>&1) || true
    rc=$?
    checked=$((checked + 1))
    if [[ $rc -ne 0 ]]; then
        echo "FAIL  $rel"
        echo "$out" | grep -E "SCRIPT ERROR|Parse Error|ERROR:" || echo "$out"
        failed=$((failed + 1))
    else
        echo "OK    $rel"
        if [[ $verbose -eq 1 ]]; then
            echo "$out" | head -1 | sed 's/^/      /'
        fi
    fi
done

echo ""
if [[ $failed -gt 0 ]]; then
    echo "$failed/$checked scripts FAILED to parse."
    exit 1
fi
echo "$checked/$checked scripts OK."
