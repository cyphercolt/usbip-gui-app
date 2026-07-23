# v3 rewrite — developer notes

The v3 architecture replaces the PyQt desktop app with **one symmetric LAN service per machine**
("the node" = agent + hub + webserver in a single process) plus a **React web UI** it serves over
plain HTTP. Full design: `../../.claude/plans/i-d-like-to-remote-piped-creek.md`. Branch: `v3-rewrite`.

## Layout

- `node/` — Python (FastAPI + uvicorn) service.
  - `usbip_node/core/` — headless USB/IP logic (`usbip_linux.py`, `local.py`, `validate.py`, `models.py`).
  - `usbip_node/api/routes.py` — REST + WebSocket.
  - `usbip_node/discovery/`, `usbip_node/trust/` — mDNS + pairing (Phase 2 stubs).
  - `usbip_node/server.py` — builds the app and serves `web/dist`.
- `web/` — Vite + React + TypeScript + Tailwind SPA.

## Run it

Dev (hot-reloading UI, Vite proxies `/api` + `/ws` to the backend):

```bash
scripts/dev-node.sh          # backend :4820, dev UI :5173  -> open :5173
```

Production-style (node serves the built UI on one port):

```bash
cd web && npm install && npm run build          # -> web/dist
cd ../node && python3 -m venv .venv && . .venv/bin/activate && pip install -e .
python -m usbip_node                             # open http://<lan-ip>:4820
```

Environment knobs: `USBIP_NODE_PORT` (default 4820), `USBIP_NODE_NAME` (default hostname),
`USBIP_NODE_STATE_DIR` (identity/trust store location).

## Test

```bash
cd node && pytest -q          # API smoke + validators
cd web && npm run build       # typecheck + bundle
```

## Status

Phase 0 (scaffolding) complete: node serves the SPA + real local USB/IP listing, live state over
WebSocket, `/api/fleet` returns this node. Next: Phase 1 two-machine vertical slice (bind on one
machine, attach on another) — see the plan.
