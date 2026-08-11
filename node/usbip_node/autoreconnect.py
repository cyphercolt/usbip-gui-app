"""Auto-reconnect + state reconciliation: a node keeps its USB/IP state honest.

Three jobs, all in one background sweep:
  * auto-reconnect: armed devices that dropped (reboot, replug, network blip) are re-bound on the
    source and re-attached here. A manual detach disarms it.
  * stale-import cleanup (client side): after a SOURCE reboots, our vhci import can linger as a
    zombie — `usbip port` still lists it, so the UI says "attached" and auto-reconnect thinks all
    is well. If the source is reachable but says the device is no longer bound (or its usbipd is
    gone), we detach the dead import; auto-reconnect then brings it back for real if armed.
  * orphan-bind cleanup (source side): after a CLIENT reboots without detaching, our device stays
    bound to usbip-host forever — dead to the machine it's plugged into. If every peer is
    reachable and none claims the device for a while, we unbind it.

Both cleanups require several consecutive strikes so a transient blip (usbipd restarting, a slow
peer) never rips out a working device, and both do nothing when the fleet can't be fully observed.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Callable

import httpx

from .config import NodeConfig, local_addresses, state_dir
from .core import local
from .events import StateBus
from .hub import identity_headers

_INTERVAL = 5.0  # seconds between reconnect sweeps
_STALE_STRIKES = 3  # ~15s of "source says not bound" before detaching a zombie import
_ORPHAN_STRIKES = 6  # ~30s of "no peer attached" before freeing an orphaned bind


class AutoReconnectStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (state_dir() / "autoreconnect.json")
        self._items: list[dict] = self._load()

    def _load(self) -> list[dict]:
        try:
            data = json.loads(self._path.read_text())
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def _save(self) -> None:
        try:
            self._path.write_text(json.dumps(self._items, indent=2))
        except OSError:
            pass

    def list(self) -> list[dict]:
        return list(self._items)

    def contains(self, remote_host: str, busid: str) -> bool:
        return any(i["remote_host"] == remote_host and i["busid"] == busid for i in self._items)

    def add(self, remote_host: str, busid: str, description: str = "") -> None:
        if not self.contains(remote_host, busid):
            self._items.append(
                {"remote_host": remote_host, "busid": busid, "description": description}
            )
            self._save()

    def remove(self, remote_host: str, busid: str) -> None:
        before = len(self._items)
        self._items = [
            i for i in self._items if not (i["remote_host"] == remote_host and i["busid"] == busid)
        ]
        if len(self._items) != before:
            self._save()


async def _drop_stale_imports(
    cfg: NodeConfig,
    client: httpx.AsyncClient,
    attached: list,
    strikes: dict[tuple[str, str], int],
) -> bool:
    """Detach imports whose source is reachable but no longer serves the device (it rebooted, or
    its usbipd died). Returns True if anything was detached."""
    headers = identity_headers(cfg.node_id, cfg.node_key)
    loop = asyncio.get_event_loop()
    changed = False
    seen: set[tuple[str, str]] = set()
    for a in attached:
        if not a.remote_host or not a.busid:
            continue
        key = (a.remote_host, a.busid)
        seen.add(key)
        try:
            resp = await client.get(f"http://{a.remote_host}:{cfg.port}/api/local/bound", headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            continue  # unreachable or an older node: no evidence either way, leave it alone
        busids = data.get("busids")
        if busids is None:
            continue  # source can't report bind state on its platform
        if data.get("running", True) and a.busid in busids:
            strikes.pop(key, None)  # healthy
            continue
        strikes[key] = strikes.get(key, 0) + 1
        if strikes[key] >= _STALE_STRIKES:
            strikes.pop(key, None)
            res = await loop.run_in_executor(None, local.detach, a.port)
            changed = changed or res.ok
    for key in list(strikes):
        if key not in seen:
            strikes.pop(key, None)
    return changed


async def _free_orphaned_binds(
    cfg: NodeConfig,
    client: httpx.AsyncClient,
    peer_urls: list[str],
    attached: list,
    strikes: dict[str, int],
) -> bool:
    """Unbind our devices that no one is attached to anymore (a client rebooted or vanished
    without a clean detach). Only acts when EVERY peer answered, so a sleeping client whose
    attachment we simply can't see never gets its device pulled. Returns True on any unbind."""
    loop = asyncio.get_event_loop()
    bound = await loop.run_in_executor(None, local.bound_busids)
    if not bound:
        strikes.clear()
        return False
    headers = identity_headers(cfg.node_id, cfg.node_key)
    my_addrs = set(local_addresses(cfg.advertise_host))
    claimed = {a.busid for a in attached if a.remote_host in my_addrs}  # self-imports count too
    all_visible = True
    for url in peer_urls:
        try:
            resp = await client.get(f"{url}/api/state", headers=headers)
            resp.raise_for_status()
            state = resp.json()
        except (httpx.HTTPError, ValueError):
            all_visible = False
            continue
        for a in state.get("attached", []):
            if a.get("remote_host") in my_addrs and a.get("busid"):
                claimed.add(a["busid"])
    if not all_visible:
        return False
    changed = False
    for busid in bound:
        if busid in claimed:
            strikes.pop(busid, None)
            continue
        strikes[busid] = strikes.get(busid, 0) + 1
        if strikes[busid] >= _ORPHAN_STRIKES:
            strikes.pop(busid, None)
            res = await loop.run_in_executor(None, local.unbind, busid)
            changed = changed or res.ok
    for busid in list(strikes):
        if busid not in bound:
            strikes.pop(busid, None)
    return changed


async def _sweep(
    cfg: NodeConfig,
    store: AutoReconnectStore,
    bus: StateBus,
    peer_urls: Callable[[], list[str]],
    stale_strikes: dict[tuple[str, str], int],
    orphan_strikes: dict[str, int],
) -> None:
    loop = asyncio.get_event_loop()
    attached = await loop.run_in_executor(None, local.list_attached)
    headers = identity_headers(cfg.node_id, cfg.node_key)
    changed = False

    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
        if await _drop_stale_imports(cfg, client, attached, stale_strikes):
            changed = True
            attached = await loop.run_in_executor(None, local.list_attached)
        if await _free_orphaned_binds(cfg, client, peer_urls(), attached, orphan_strikes):
            changed = True

        have = {(a.remote_host, a.busid) for a in attached}
        for e in store.list():
            host, busid = e["remote_host"], e["busid"]
            if not host or (host, busid) in have:
                continue
            # ensure the device is shared on the source (tolerate "already bound")
            try:
                await client.post(
                    f"http://{host}:{cfg.port}/api/local/bind",
                    json={"busid": busid}, headers=headers,
                )
            except httpx.HTTPError:
                continue  # source unreachable right now; try again next sweep
            res = await loop.run_in_executor(None, local.attach, host, busid)
            if res.ok:
                changed = True

    if changed:
        bus.publish()


async def run_loop(
    cfg: NodeConfig,
    store: AutoReconnectStore,
    bus: StateBus,
    peer_urls: Callable[[], list[str]] = lambda: [],
) -> None:
    """Background task; cancelled on shutdown."""
    stale_strikes: dict[tuple[str, str], int] = {}
    orphan_strikes: dict[str, int] = {}
    while True:
        try:
            await _sweep(cfg, store, bus, peer_urls, stale_strikes, orphan_strikes)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # never let the loop die
        await asyncio.sleep(_INTERVAL)
