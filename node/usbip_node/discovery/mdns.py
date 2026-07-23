"""mDNS/zeroconf peer discovery.

Each node advertises `_usbip-node._tcp` and browses for the same service, so machines find each
other automatically on the LAN — no typing peer URLs. Discovered peer URLs feed the fleet.

Uses the async zeroconf API because the node runs inside an asyncio event loop; the sync API would
block that loop (EventLoopBlocked).
"""

from __future__ import annotations

import asyncio
import socket

from zeroconf import ServiceInfo, ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from ..config import NodeConfig

SERVICE_TYPE = "_usbip-node._tcp.local."


class Discovery:
    """Advertise this node and track discovered peers (service-name -> base URL)."""

    def __init__(self, cfg: NodeConfig) -> None:
        self._cfg = cfg
        self._azc: AsyncZeroconf | None = None
        self._info: ServiceInfo | None = None
        self._browser: AsyncServiceBrowser | None = None
        self._store: dict[str, str] = {}

    async def start(self) -> None:
        # Listen on all interfaces (binding to one broke same-host discovery via multicast loopback).
        # Peer flapping from multi-NIC mDNS churn is handled by keeping discovered URLs sticky
        # (see _on_change) rather than by restricting interfaces.
        self._azc = AsyncZeroconf()
        self._info = ServiceInfo(
            SERVICE_TYPE,
            f"{self._cfg.node_id}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(self._cfg.advertise_host)],
            port=self._cfg.port,
            properties={"node_id": self._cfg.node_id, "name": self._cfg.display_name},
        )
        await self._azc.async_register_service(self._info)
        self._browser = AsyncServiceBrowser(
            self._azc.zeroconf, SERVICE_TYPE, handlers=[self._on_change]
        )

    def _on_change(self, zeroconf, service_type, name, state_change) -> None:
        # Intentionally ignore Removed: mDNS TTL churn (esp. with multiple NICs) fires spurious
        # removes for peers that are still up. We keep discovered URLs "sticky" and let actual HTTP
        # reachability in gather_fleet decide what's shown — a truly-offline peer just fails to fetch
        # and doesn't appear, with no flapping.
        if state_change is ServiceStateChange.Removed:
            return
        # Added / Updated: resolve asynchronously so we never block the event loop.
        asyncio.ensure_future(self._resolve(service_type, name))

    async def _resolve(self, service_type: str, name: str) -> None:
        if self._azc is None:
            return
        info = AsyncServiceInfo(service_type, name)
        if not await info.async_request(self._azc.zeroconf, 3000):
            return
        props = {
            (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
            for k, v in (info.properties or {}).items()
        }
        if props.get("node_id") == self._cfg.node_id:
            return  # ignore ourselves
        addrs = info.parsed_addresses()
        if addrs:
            self._store[name] = f"http://{addrs[0]}:{info.port}"

    def peer_urls(self) -> list[str]:
        return list(dict.fromkeys(self._store.values()))

    async def start_safe(self) -> None:
        try:
            await self.start()
        except OSError:
            pass  # mDNS unavailable (restricted network) — manual peers still work

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.async_cancel()
        if self._azc is not None:
            if self._info is not None:
                try:
                    await self._azc.async_unregister_service(self._info)
                except OSError:
                    pass
            await self._azc.async_close()
            self._azc = None
