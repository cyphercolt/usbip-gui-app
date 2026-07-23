#!/usr/bin/env bash
# Dev runner for the v3 rewrite (node service + web app).
# Starts the Python node backend and the Vite dev server (which proxies /api and /ws to the backend).
#
# Usage: scripts/dev-node.sh
#   Backend:  http://127.0.0.1:4820   (also serves web/dist if you've built it)
#   Frontend: http://localhost:5173   (hot-reloading dev UI -> use this while developing)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --- backend ---
if [ ! -d node/.venv ]; then
  echo "Creating node venv..."
  python3 -m venv node/.venv
fi
# shellcheck disable=SC1091
source node/.venv/bin/activate
pip install --quiet -e "./node[dev]"

USBIP_NODE_PORT="${USBIP_NODE_PORT:-4820}" python -m usbip_node &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT INT TERM

# --- frontend ---
cd web
[ -d node_modules ] || npm install --no-audit --no-fund
npm run dev
