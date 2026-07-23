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

The service runs as root, so `usbip` bind/attach need **no sudo password**. Machines auto-discover
each other via mDNS — the manual "+ Add a machine" is only a fallback (other subnet / mDNS blocked).

### Windows (untested on hardware yet)

Needs upstream tools: **usbipd-win** (`winget install usbipd`, to share devices) and **usbip-win2**
(client driver, to attach devices). Then, in an elevated PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\packaging\install-windows.ps1     # venv + firewall rule + SYSTEM scheduled task on :4820
```

Server side uses `usbipd list/bind/unbind`; client side reuses the same `usbip attach/detach/port`
as Linux. Update later with `git pull` + re-run the script.

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
- Pairing (Syncthing-style): `GET /api/identity`, `GET /api/security`, `POST /api/security/mode`,
  `POST /api/pair/initiate/{peer_node_id}`, `POST /api/pair/request|confirm` (node↔node),
  `POST /api/pair/accept|reject`, `DELETE /api/pair/{node_id}`.

## Security model (pairing)

Each node has a persistent `node_id` + secret `node_key` (in the state dir). Two modes:

- **open** (default): any node on the LAN is trusted — nothing to pair. Existing fleets keep working.
- **locked**: a peer must be paired before it can see devices or issue commands. Unpaired discovered
  machines show as "pending" (🔒) in the fleet with a **Pair** button. Pairing is mutual-consent:
  machine A taps *Pair*, machine B sees a request and taps *Accept* (🔒 badge shows a count). Node↔node
  calls carry `X-Node-Id`/`X-Node-Key`; locked-mode `/api/state` and `/api/local/*` reject unpaired
  callers. Lock down every machine for it to matter (browser→node is still open on the LAN — a synced
  web login is Phase 5).

### Reset (to re-test pairing from scratch)

Wipes a node's identity + trust + known peers (regenerates a fresh `node_id`/`node_key`). Run on each
machine you want to reset:

```bash
sudo systemctl stop usbip-node
sudo rm -rf /var/lib/usbip-node      # node_id, node_key, trust.json, peers.json
sudo systemctl start usbip-node
```

After that, machines rediscover each other via mDNS and (in locked mode) show as pending until you
re-pair. To clear *only* pairings but keep identity: `sudo rm /var/lib/usbip-node/trust.json` then
restart (note: peers that trusted the old key must unpair/re-pair).

## Status

- **Phase 0** (scaffolding) — done.
- **Phase 1** (two-machine vertical slice) — done: local + hub-proxied bind/unbind/attach/detach,
  any→any attach orchestration, peer registry, fleet view + machine view + "Send to…" attach flow,
  systemd packaging (root service = no sudo prompts). Verified across two local instances.
- **Phase 2** (auto-discovery) — done: mDNS advertise+browse (async zeroconf) so machines appear
  automatically; fleet dedupes by node_id; "detach" now fully releases (detach dest + unbind source),
  and share/unshare is hidden from the user.
- **Phase 3** (Windows node) — code complete, **UNVERIFIED on hardware**: `core/usbip_windows.py`
  (usbipd server + usbip-win2 client, ports the old app's syntax), platform facade dispatch,
  `packaging/install-windows.ps1` (SYSTEM scheduled task + firewall). Parser unit-tested; a friend
  will test the real flow later.
- **Phase 4 (in progress):**
  - ✅ Security lockdown + Syncthing-style pairing (open/locked modes, mutual approve, live-verified
    across two nodes). Pending-request toast + 🔒 badge done.
  - ⬜ Auto-reconnect (re-attach after reboot/replug/blip), themes, richer status/notifications.
- **Phase 5** — team-synced web-UI login + optional TOTP 2FA (browser→node auth, propagated over the
  pairing mesh).
