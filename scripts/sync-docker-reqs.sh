#!/usr/bin/env bash
# sync-docker-reqs.sh — Regenerates requirements.docker.txt from requirements.txt
# by stripping macOS-only packages and platform-specific builds.
#
# Usage: ./scripts/sync-docker-reqs.sh
#
# requirements.docker.txt is maintained manually but this script helps
# detect drift. Run it, then diff to see what changed.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/requirements.txt"
DST="$REPO_ROOT/requirements.docker.txt"

if [ ! -f "$SRC" ]; then
    echo "ERROR: $SRC not found"
    exit 1
fi

# Packages to strip (macOS-only, GPU torch, or problematic in Docker)
STRIP_PATTERNS=(
    "^pyobjc"
    "^ocrmac"
    "^torch=="
    "^torchvision=="
    "^pyodbc=="
    "^cryptography=="
)

REGEX=$(printf "|%s" "${STRIP_PATTERNS[@]}")
REGEX="${REGEX:1}"

echo "# Auto-generated from requirements.txt — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "# Stripped: pyobjc, ocrmac, torch (use CPU wheel), pyodbc, cryptography"
echo "# Review and commit manually after running this script."
echo ""
grep -vE "$REGEX" "$SRC"

echo ""
echo "# --- Add these manually in Dockerfile or before pip install ---"
echo "# pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu"
