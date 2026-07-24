"""Auto-reconnect: a node keeps chosen devices attached to itself.

Armed on a device that's attached to THIS machine (dest). A background loop periodically checks
whether each armed device is still attached; if it dropped (reboot, replug, network blip), it
re-binds it on the source and re-attaches it here. A manual detach disarms it (so the user can
actually let go of a device).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from .config import NodeConfig, state_dir
from .core import local
from .events import StateBus
from .hub import identity_headers

_INTERVAL = 5.0  # seconds between reconnect sweeps


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


async def _sweep(cfg: NodeConfig, store: AutoReconnectStore, bus: StateBus) -> None:
    entries = store.list()
    if not entries:
        return
    loop = asyncio.get_event_loop()
    attached = await loop.run_in_executor(None, local.list_attached)
    have = {(a.remote_host, a.busid) for a in attached}
    headers = identity_headers(cfg.node_id, cfg.node_key)

    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
        for e in entries:
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
                bus.publish()


async def run_loop(cfg: NodeConfig, store: AutoReconnectStore, bus: StateBus) -> None:
    """Background task; cancelled on shutdown."""
    while True:
        try:
            await _sweep(cfg, store, bus)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass  # never let the loop die
        await asyncio.sleep(_INTERVAL)
