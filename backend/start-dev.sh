#!/usr/bin/env bash
# Start backend with env from project root. Backend always runs on PORT from .env (default 8000).
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi
cd "$SCRIPT_DIR"
exec python wsgi.py
