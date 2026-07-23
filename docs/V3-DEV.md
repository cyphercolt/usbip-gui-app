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

## Deploy as a service (Linux / Raspberry Pi)

On each machine (build the web UI first on a dev box, or let the script build it if `npm` is present):

```bash
sudo packaging/install-linux.sh      # installs usbip + a root systemd service on :4820
```

The service runs as root, so `usbip` bind/attach need **no sudo password**. Then on any machine's
fleet view, "+ Add a machine" and enter another node's URL (e.g. `http://192.168.2.50:4820`) — until
Phase 2 wires up mDNS auto-discovery.

## API shape

- `GET /api/state` / `GET /api/fleet` — this node / this node + peers.
- `POST /api/local/{bind,unbind,attach,detach}` — act on THIS machine (what a hub calls on a peer).
- `POST /api/node/{node_id}/{bind,unbind,detach}` — hub forwards to the right machine.
- `POST /api/attach` `{source_node_id, busid, dest_node_id}` — orchestrated any→any attach
  (binds the source, attaches the dest). The user never touches share/unshare.
- `POST /api/detach` `{dest_node_id, port}` — full release: detach on the dest AND unbind on the
  source, so the device is immediately free to send elsewhere.
- `GET/POST/DELETE /api/peers` — manual peer registry (fallback; mDNS auto-discovers peers).
- `WS /ws` — live state push for the connected node (UI uses it as a refetch nudge).

## Status

- **Phase 0** (scaffolding) — done.
- **Phase 1** (two-machine vertical slice) — done: local + hub-proxied bind/unbind/attach/detach,
  any→any attach orchestration, peer registry, fleet view + machine view + "Send to…" attach flow,
  systemd packaging (root service = no sudo prompts). Verified across two local instances.
- **Phase 2** (auto-discovery) — done: mDNS advertise+browse (async zeroconf) so machines appear
  automatically; fleet dedupes by node_id; "detach" now fully releases (detach dest + unbind source),
  and share/unshare is hidden from the user.
- **Next: Phase 3** — Windows node (usbipd-win / usbip-win2) + Windows service. Then Phase 4 polish
  (auto-reconnect, themes, notifications) and optional pairing/token lockdown.
