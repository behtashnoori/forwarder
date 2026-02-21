#!/usr/bin/env bash
# Canonical dev launcher: runs backend via python -m backend.run (fixed port, no silent exit).
# From project root so backend package is importable.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi
PORT="${PORT:-8000}"
if command -v lsof >/dev/null 2>&1; then
  PIDS=$(lsof -ti ":$PORT" 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "Port $PORT is already in use. Please stop the process using it."
    echo "  PIDs: $PIDS"
    echo "  lsof -ti:$PORT | xargs kill"
    exit 1
  fi
fi
# Optional: pass --reload to enable reloader (default: off)
exec python3 -m backend.run "$@"