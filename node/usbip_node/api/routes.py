"""REST + WebSocket routes.

Endpoint layers:
  * /api/local/*  act on THIS machine (node-to-node; gated by node identity in locked mode).
  * /api/state    this machine's devices (node-to-node; gated in locked mode).
  * hub layer (/api/fleet, /api/attach, /api/detach, /api/node/*) — browser-facing; the node acts
    as hub and forwards to peers, presenting its own identity.
  * pairing (/api/identity, /api/security, /api/pair/*) — Syncthing-style approval.
"""

from __future__ import annotations

import asyncio
import time
from typing import Callable
from urllib.parse import urlparse

import httpx
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)

from .. import __version__
from ..autoreconnect import AutoReconnectStore
from ..config import NodeConfig, local_addresses
from ..core import local
from ..core.proc import CommandResult
from ..core.models import (
    AttachRequest,
    AuthConfigMessage,
    AuthStatus,
    AutoReconnectRequest,
    BusidRequest,
    CommandResponse,
    DetachRequest,
    Identity,
    LoginRequest,
    ModeRequest,
    NodeIdRequest,
    NodeInfo,
    NodeState,
    OrchestrateAttach,
    PairedRef,
    PairMessage,
    PeerRef,
    ReleaseRequest,
    SecurityState,
    SetAuthRequest,
    SetAuthResponse,
    UpdateLogEntry,
    UpdateState,
)
from ..events import StateBus
from ..hub import gather_fleet, identity_headers, peer_get_json, post_command
from ..peers import PeerRegistry
from ..trust import LOCKED, OPEN, TrustStore
from ..updater import Updater
from ..webauth import COOKIE, WebAuthStore


def _to_response(result) -> CommandResponse:
    msg = (result.stderr or result.stdout or "").strip()
    return CommandResponse(ok=result.ok, message=msg)


def _bind_ok(resp: CommandResponse) -> bool:
    """Treat an already-shared device as a successful bind — it's ready to attach either way."""
    if resp.ok:
        return True
    m = resp.message.lower()
    return "already bound" in m or "already shared" in m


def _api_host(url: str | None) -> str | None:
    """Hostname from a peer API URL. Used as the usbip attach target because it is the address
    the destination already used successfully to talk to the source's API; the source's self-
    reported advertise_host may be on a different/unreachable interface."""
    if not url:
        return None
    host = urlparse(url).hostname
    return host if host else None


def build_router(
    cfg: NodeConfig,
    bus: StateBus,
    registry: PeerRegistry,
    peer_urls: Callable[[], list[str]],
    trust: TrustStore,
    auto_store: AutoReconnectStore,
    webauth: WebAuthStore,
    updater: Updater,
) -> APIRouter:
    r = APIRouter()

    def node_auth(
        x_node_id: str | None = Header(default=None),
        x_node_key: str | None = Header(default=None),
    ) -> None:
        """Gate node-to-node endpoints. Open mode = allow all; locked = require a paired peer."""
        if not trust.locked():
            return
        if not trust.is_trusted(x_node_id, x_node_key):
            raise HTTPException(status_code=401, detail="node not paired")

    def node_info() -> NodeInfo:
        return NodeInfo(
            node_id=cfg.node_id,
            display_name=cfg.display_name,
            os_name=cfg.os_name,
            version=__version__,
            host=cfg.advertise_host,
            hosts=local_addresses(cfg.advertise_host),
            port=cfg.port,
            reachable=True,
            paired=True,
        )

    def local_state() -> NodeState:
        attached = local.list_attached()
        for a in attached:
            if a.remote_host:
                a.auto = auto_store.contains(a.remote_host, a.busid)
        return NodeState(
            info=node_info(),
            shareable=local.list_shareable(),
            attached=attached,
            update=updater.state,
        )

    def our_pair_msg() -> dict:
        return PairMessage(
            node_id=cfg.node_id,
            display_name=cfg.display_name,
            key=cfg.node_key,
            host=cfg.advertise_host,
            port=cfg.port,
        ).model_dump()

    async def _fleet_now() -> tuple[list[NodeState], dict[str, str]]:
        return await gather_fleet(local_state(), peer_urls(), cfg.node_id, cfg.node_key)

    # ---- basic ----
    @r.get("/health")
    def _health() -> dict:
        return {"status": "ok", "service": "usbip-node", "version": __version__}

    @r.get("/api/identity", response_model=Identity)
    def _identity() -> Identity:
        return Identity(node_id=cfg.node_id, display_name=cfg.display_name, os_name=cfg.os_name)

    @r.get("/api/info", response_model=NodeInfo)
    def _info() -> NodeInfo:
        return node_info()

    @r.get("/api/state", response_model=NodeState)
    def _state(_: None = Depends(node_auth)) -> NodeState:
        return local_state()

    # ---- peer registry (manual fallback; browser-facing) ----
    @r.get("/api/peers")
    def _peers() -> list[str]:
        return registry.urls()

    @r.post("/api/peers", response_model=CommandResponse)
    def _add_peer(ref: PeerRef) -> CommandResponse:
        registry.add(ref.url)
        return CommandResponse(ok=True, message=f"added {ref.url}")

    @r.delete("/api/peers", response_model=CommandResponse)
    def _del_peer(ref: PeerRef) -> CommandResponse:
        registry.remove(ref.url)
        return CommandResponse(ok=True, message=f"removed {ref.url}")

    # ---- local commands (node-to-node; gated in locked mode) ----
    @r.post("/api/local/bind", response_model=CommandResponse)
    def _bind(req: BusidRequest, _: None = Depends(node_auth)) -> CommandResponse:
        resp = _to_response(local.bind(req.busid))
        bus.publish()
        return resp

    @r.post("/api/local/unbind", response_model=CommandResponse)
    def _unbind(req: BusidRequest, _: None = Depends(node_auth)) -> CommandResponse:
        resp = _to_response(local.unbind(req.busid))
        bus.publish()
        return resp

    @r.post("/api/local/attach", response_model=CommandResponse)
    def _attach(req: AttachRequest, _: None = Depends(node_auth)) -> CommandResponse:
        resp = _to_response(local.attach(req.remote_host, req.busid))
        bus.publish()
        return resp

    @r.post("/api/local/detach", response_model=CommandResponse)
    def _detach(req: DetachRequest, _: None = Depends(node_auth)) -> CommandResponse:
        # A manual detach disarms auto-reconnect for that device, else the loop would re-grab it.
        for a in local.list_attached():
            if a.port == req.port and a.remote_host:
                auto_store.remove(a.remote_host, a.busid)
        resp = _to_response(local.detach(req.port))
        bus.publish()
        return resp

    @r.get("/api/local/bound")
    def _bound(_: None = Depends(node_auth)) -> dict:
        """Server-side bind health, for peers reconciling stale imports after we reboot.
        busids=None means this platform can't report it — peers must not act on that."""
        return {"running": local.usbip_server_running(), "busids": local.bound_busids()}

    @r.post("/api/local/autoreconnect", response_model=CommandResponse)
    def _local_autoreconnect(req: AutoReconnectRequest, _: None = Depends(node_auth)) -> CommandResponse:
        if req.enabled:
            auto_store.add(req.remote_host, req.busid, req.description)
        else:
            auto_store.remove(req.remote_host, req.busid)
        bus.publish()
        return CommandResponse(ok=True, message="auto-reconnect " + ("on" if req.enabled else "off"))

    # ---- hub layer (browser-facing) ----
    _recent: dict[str, tuple[float, NodeState]] = {}  # smooths transient blips in the fleet display

    async def _fleet_with_updates() -> list[NodeState]:
        fleet, id_to_url = await _fleet_now()
        # Fetch update status from each peer and merge it into their NodeState.
        peer_nodes = [
            n for n in fleet
            if n.info.node_id != cfg.node_id and n.info.node_id in id_to_url
        ]
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(*[
                peer_get_json(
                    client, id_to_url[n.info.node_id], "/api/local/update/status",
                    cfg.node_id, cfg.node_key,
                )
                for n in peer_nodes
            ]) if peer_nodes else []
        peer_state = {
            n.info.node_id: data
            for n, data in zip(peer_nodes, results)
            if data
        }
        for n in fleet:
            if n.info.node_id == cfg.node_id:
                n.update = updater.state
            elif n.info.node_id in peer_state:
                try:
                    n.update = UpdateState.model_validate(peer_state[n.info.node_id])
                except ValueError:
                    n.update = None
        return fleet

    @r.get("/api/fleet", response_model=list[NodeState])
    async def _fleet() -> list[NodeState]:
        fleet = await _fleet_with_updates()
        now = time.monotonic()
        present = {n.info.node_id for n in fleet}
        for n in fleet:
            _recent[n.info.node_id] = (now, n)
        # Keep recently-seen machines in the list as "offline" (reachable=false) for up to 60s
        # instead of vanishing — no flicker, and the UI can show/notify offline state.
        for nid, (ts, n) in list(_recent.items()):
            if nid in present:
                continue
            if now - ts < 60:
                offline = n.model_copy(deep=True)
                offline.info.reachable = False
                fleet.append(offline)
            else:
                _recent.pop(nid, None)
        return fleet

    @r.post("/api/attach", response_model=CommandResponse)
    async def _orchestrate(req: OrchestrateAttach) -> CommandResponse:
        fleet, id_to_url = await _fleet_now()
        by_id = {n.info.node_id: n for n in fleet}
        source = by_id.get(req.source_node_id)
        dest = by_id.get(req.dest_node_id)
        if source is None or dest is None:
            raise HTTPException(status_code=404, detail="source or destination node not found")

        # Use the address we actually reach the source API on for the usbip attach target. The
        # source's advertise_host can be on a different subnet/interface (Wi-Fi vs Ethernet, VPN,
        # Docker, etc.) and fail with "tcp connect" even though API calls succeed.
        source_attach_host = _api_host(id_to_url.get(source.info.node_id)) or source.info.host

        async with httpx.AsyncClient() as client:
            if source.info.node_id == cfg.node_id:
                bind_res = _to_response(local.bind(req.busid))
            else:
                bind_res = await post_command(
                    client, id_to_url[source.info.node_id], "/api/local/bind",
                    {"busid": req.busid}, cfg.node_id, cfg.node_key,
                )
            if not _bind_ok(bind_res):
                return CommandResponse(ok=False, message=f"bind on source failed: {bind_res.message}")

            if dest.info.node_id == cfg.node_id:
                attach_res = _to_response(local.attach(source_attach_host, req.busid))
            else:
                attach_res = await post_command(
                    client, id_to_url[dest.info.node_id], "/api/local/attach",
                    {"remote_host": source_attach_host, "busid": req.busid}, cfg.node_id, cfg.node_key,
                )

        bus.publish()
        if not attach_res.ok:
            return CommandResponse(ok=False, message=f"attach on dest failed: {attach_res.message}")
        return CommandResponse(
            ok=True,
            message=f"attached {req.busid} from {source.info.display_name} to {dest.info.display_name}",
        )

    @r.post("/api/detach", response_model=CommandResponse)
    async def _release(req: ReleaseRequest) -> CommandResponse:
        fleet, id_to_url = await _fleet_now()
        by_id = {n.info.node_id: n for n in fleet}
        dest = by_id.get(req.dest_node_id)
        if dest is None:
            raise HTTPException(status_code=404, detail="destination node not found")
        attached = next((a for a in dest.attached if a.port == req.port), None)

        async with httpx.AsyncClient() as client:
            if dest.info.node_id == cfg.node_id:
                detach_res = _to_response(local.detach(req.port))
            else:
                detach_res = await post_command(
                    client, id_to_url[dest.info.node_id], "/api/local/detach",
                    {"port": req.port}, cfg.node_id, cfg.node_key,
                )
            # Always unbind on the source too: it frees the device to be sent elsewhere AND lets it
            # work again on the machine it's physically plugged into. Do this by the source's address
            # so it works even if the source flapped out of the current fleet snapshot.
            unbound = ""
            if attached and attached.remote_host and attached.busid:
                # Match by ANY of the node's addresses: the attach may have used a different
                # interface than the one the node advertises (see _api_host above).
                source = next(
                    (
                        n
                        for n in fleet
                        if attached.remote_host == n.info.host or attached.remote_host in n.info.hosts
                    ),
                    None,
                )
                if source is not None and source.info.node_id == cfg.node_id:
                    u = _to_response(local.unbind(attached.busid))
                else:
                    src_url = (
                        id_to_url.get(source.info.node_id)
                        if source is not None
                        else f"http://{attached.remote_host}:{cfg.port}"
                    )
                    u = await post_command(
                        client, src_url, "/api/local/unbind",
                        {"busid": attached.busid}, cfg.node_id, cfg.node_key,
                    )
                unbound = " and freed on source" if u.ok else " (source still bound)"

        bus.publish()
        if not detach_res.ok:
            return CommandResponse(ok=False, message=f"detach failed: {detach_res.message}")
        return CommandResponse(ok=True, message=f"detached{unbound}")

    async def _resolve(node_id: str) -> tuple[bool, str | None]:
        if node_id == cfg.node_id:
            return True, None
        _, id_to_url = await _fleet_now()
        return False, id_to_url.get(node_id)

    async def _run_on(node_id: str, local_fn, path: str, payload: dict) -> CommandResponse:
        is_self, url = await _resolve(node_id)
        if is_self:
            resp = _to_response(local_fn())
        elif url:
            async with httpx.AsyncClient() as client:
                resp = await post_command(client, url, path, payload, cfg.node_id, cfg.node_key)
        else:
            raise HTTPException(status_code=404, detail="node not found")
        bus.publish()
        return resp

    @r.post("/api/node/{node_id}/bind", response_model=CommandResponse)
    async def _node_bind(node_id: str, req: BusidRequest) -> CommandResponse:
        return await _run_on(node_id, lambda: local.bind(req.busid), "/api/local/bind",
                             {"busid": req.busid})

    @r.post("/api/node/{node_id}/unbind", response_model=CommandResponse)
    async def _node_unbind(node_id: str, req: BusidRequest) -> CommandResponse:
        return await _run_on(node_id, lambda: local.unbind(req.busid), "/api/local/unbind",
                             {"busid": req.busid})

    @r.post("/api/node/{node_id}/detach", response_model=CommandResponse)
    async def _node_detach(node_id: str, req: DetachRequest) -> CommandResponse:
        return await _run_on(node_id, lambda: local.detach(req.port), "/api/local/detach",
                             {"port": req.port})

    @r.post("/api/node/{node_id}/autoreconnect", response_model=CommandResponse)
    async def _node_autoreconnect(node_id: str, req: AutoReconnectRequest) -> CommandResponse:
        def _local():
            if req.enabled:
                auto_store.add(req.remote_host, req.busid, req.description)
            else:
                auto_store.remove(req.remote_host, req.busid)
            return CommandResult(True, "", "", 0)

        return await _run_on(node_id, _local, "/api/local/autoreconnect", req.model_dump())

    # ---- update / fleet self-update ----
    # Browser-facing local endpoints (no node_auth; gated by web-login middleware when enabled).
    @r.get("/api/update/status", response_model=UpdateState)
    def _update_status() -> UpdateState:
        return updater.state

    @r.post("/api/update/check", response_model=UpdateState)
    async def _update_check() -> UpdateState:
        # Refresh this node immediately, then trigger checks on all reachable peers in the background.
        # Peers will update their own state; the next /api/fleet poll will pick up the fresh status.
        local_state = await updater.check_now()
        fleet, id_to_url = await _fleet_now()
        peer_targets = [
            id_to_url[n.info.node_id]
            for n in fleet
            if n.info.node_id != cfg.node_id
            and n.info.node_id in id_to_url
            and n.info.paired
            and n.info.reachable
        ]
        if peer_targets:
            async def _poke_peers(urls: list[str]) -> None:
                async with httpx.AsyncClient() as client:
                    await asyncio.gather(*[
                        post_command(client, url, "/api/local/update/check", {}, cfg.node_id, cfg.node_key)
                        for url in urls
                    ], return_exceptions=True)

            asyncio.create_task(_poke_peers(peer_targets))
        return local_state

    @r.post("/api/update/start", response_model=UpdateState)
    async def _update_start() -> UpdateState:
        return await updater.start_update()

    @r.get("/api/update/logs", response_model=list[UpdateLogEntry])
    def _update_logs() -> list[UpdateLogEntry]:
        return updater.logs()

    # Hub proxies: browser calls these, node forwards to the peer's /api/local/update/*.
    @r.get("/api/node/{node_id}/update/status", response_model=UpdateState)
    async def _node_update_status(node_id: str) -> UpdateState:
        is_self, url = await _resolve(node_id)
        if is_self:
            return updater.state
        if not url:
            raise HTTPException(status_code=404, detail="node not found")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{url}/api/local/update/status",
                    headers=identity_headers(cfg.node_id, cfg.node_key),
                    timeout=httpx.Timeout(8.0),
                )
                resp.raise_for_status()
                return UpdateState.model_validate(resp.json())
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"peer unreachable: {e}")
            except ValueError as e:
                raise HTTPException(status_code=502, detail=f"bad response from peer: {e}")

    @r.post("/api/node/{node_id}/update/check", response_model=UpdateState)
    async def _node_update_check(node_id: str) -> UpdateState:
        is_self, url = await _resolve(node_id)
        if is_self:
            return await updater.check_now()
        if not url:
            raise HTTPException(status_code=404, detail="node not found")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{url}/api/local/update/check",
                    json={},
                    headers=identity_headers(cfg.node_id, cfg.node_key),
                    timeout=httpx.Timeout(20.0),
                )
                resp.raise_for_status()
                return UpdateState.model_validate(resp.json())
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"peer unreachable: {e}")
            except ValueError as e:
                raise HTTPException(status_code=502, detail=f"bad response from peer: {e}")

    @r.post("/api/node/{node_id}/update/start", response_model=UpdateState)
    async def _node_update_start(node_id: str) -> UpdateState:
        is_self, url = await _resolve(node_id)
        if is_self:
            return await updater.start_update()
        if not url:
            raise HTTPException(status_code=404, detail="node not found")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{url}/api/local/update/start",
                    json={},
                    headers=identity_headers(cfg.node_id, cfg.node_key),
                    timeout=httpx.Timeout(20.0),
                )
                resp.raise_for_status()
                return UpdateState.model_validate(resp.json())
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"peer unreachable: {e}")
            except ValueError as e:
                raise HTTPException(status_code=502, detail=f"bad response from peer: {e}")

    @r.get("/api/node/{node_id}/update/logs", response_model=list[UpdateLogEntry])
    async def _node_update_logs(node_id: str) -> list[UpdateLogEntry]:
        is_self, url = await _resolve(node_id)
        if is_self:
            return updater.logs()
        if not url:
            raise HTTPException(status_code=404, detail="node not found")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{url}/api/local/update/logs",
                    headers=identity_headers(cfg.node_id, cfg.node_key),
                    timeout=httpx.Timeout(8.0),
                )
                resp.raise_for_status()
                return [UpdateLogEntry.model_validate(x) for x in resp.json()]
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail=f"peer unreachable: {e}")
            except ValueError as e:
                raise HTTPException(status_code=502, detail=f"bad response from peer: {e}")

    # Node-to-node endpoints (gated by node_auth) used by the hub proxies below.
    @r.get("/api/local/update/status", response_model=UpdateState)
    def _local_update_status(_: None = Depends(node_auth)) -> UpdateState:
        return updater.state

    @r.post("/api/local/update/check", response_model=UpdateState)
    async def _local_update_check(_: None = Depends(node_auth)) -> UpdateState:
        return await updater.check_now()

    @r.post("/api/local/update/start", response_model=UpdateState)
    async def _local_update_start(_: None = Depends(node_auth)) -> UpdateState:
        return await updater.start_update()

    @r.get("/api/local/update/logs", response_model=list[UpdateLogEntry])
    def _local_update_logs(_: None = Depends(node_auth)) -> list[UpdateLogEntry]:
        return updater.logs()

    @r.post("/api/update/start-all", response_model=CommandResponse)
    async def _update_start_all() -> CommandResponse:
        fleet, id_to_url = await _fleet_now()
        targets: list[tuple[str, str | None]] = [
            (n.info.node_id, id_to_url.get(n.info.node_id))
            for n in fleet
            if n.info.paired and n.info.reachable
        ]
        # Start self first via the local endpoint so the page gets a response before this node
        # potentially restarts. Peers are started via proxy.
        if any(nid == cfg.node_id for nid, _ in targets):
            try:
                await updater.start_update()
            except Exception as e:
                # Self-start failure is non-fatal; record it and continue with peers.
                pass

        started: list[str] = []
        failed: list[str] = []
        peer_targets = [(nid, url) for nid, url in targets if nid != cfg.node_id and url]
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(*[
                client.post(
                    f"{url}/api/local/update/start",
                    json={},
                    headers=identity_headers(cfg.node_id, cfg.node_key),
                    timeout=httpx.Timeout(20.0),
                )
                for _, url in peer_targets
            ]) if peer_targets else []
        for (nid, _), resp in zip(peer_targets, results):
            if isinstance(resp, Exception):
                failed.append(f"{nid}: {resp}")
                continue
            try:
                resp.raise_for_status()
                UpdateState.model_validate(resp.json())
                started.append(nid)
            except (httpx.HTTPError, ValueError) as e:
                failed.append(f"{nid}: {e}")

        # We always count self as "started" if it was in the target list, because the local helper
        # runs out-of-process and will restart us momentarily.
        if any(nid == cfg.node_id for nid, _ in targets):
            started.append(cfg.node_id)
        return CommandResponse(
            ok=len(failed) == 0,
            message=f"started {len(started)} node(s); failed: {', '.join(failed) if failed else 'none'}",
        )

    # ---- security / pairing ----
    @r.get("/api/security", response_model=SecurityState)
    def _security() -> SecurityState:
        return SecurityState(
            mode=trust.mode(),
            this_node=PairedRef(node_id=cfg.node_id, name=cfg.display_name),
            trusted=[PairedRef(node_id=i, name=e["name"]) for i, e in trust.trusted().items()],
            pending=[PairedRef(node_id=i, name=e["name"]) for i, e in trust.pending_in().items()],
        )

    @r.post("/api/security/mode", response_model=CommandResponse)
    def _set_mode(req: ModeRequest) -> CommandResponse:
        trust.set_mode(req.mode)
        bus.publish()
        return CommandResponse(ok=True, message=f"security mode: {trust.mode()}")

    async def _send_pair(url: str, path: str, payload: dict) -> CommandResponse:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(f"{url}{path}", json=payload, timeout=httpx.Timeout(8.0))
                if resp.status_code == 200:
                    return CommandResponse.model_validate(resp.json())
                return CommandResponse(ok=False, message=f"peer returned {resp.status_code}")
            except (httpx.HTTPError, ValueError) as e:
                return CommandResponse(ok=False, message=f"pair call failed: {e}")

    @r.post("/api/pair/initiate/{peer_node_id}", response_model=CommandResponse)
    async def _pair_initiate(peer_node_id: str) -> CommandResponse:
        """User asks to pair with a discovered peer. Send our identity; they approve on their end."""
        _, id_to_url = await _fleet_now()
        url = id_to_url.get(peer_node_id)
        if not url:
            raise HTTPException(status_code=404, detail="peer not found on the network")
        trust.add_pending_out(peer_node_id)
        res = await _send_pair(url, "/api/pair/request", our_pair_msg())
        bus.publish()
        return res

    @r.post("/api/pair/request", response_model=CommandResponse)
    async def _pair_request(msg: PairMessage) -> CommandResponse:
        """Incoming pairing request from a peer (unauthenticated — this bootstraps trust)."""
        if trust.mode() == OPEN:
            trust.add_trusted(msg.node_id, msg.display_name, msg.key)
            # confirm back so the initiator trusts us too
            asyncio.ensure_future(
                _send_pair(f"http://{msg.host}:{msg.port}", "/api/pair/confirm", our_pair_msg())
            )
            bus.publish()
            return CommandResponse(ok=True, message="accepted")
        trust.add_pending_in(msg.node_id, msg.display_name, msg.key, msg.host, msg.port)
        bus.publish()
        return CommandResponse(ok=True, message="pending")

    @r.post("/api/pair/confirm", response_model=CommandResponse)
    async def _pair_confirm(msg: PairMessage) -> CommandResponse:
        """Peer accepted our request. Only honor it if we actually initiated with them."""
        if trust.pop_pending_out(msg.node_id) or trust.mode() == OPEN:
            trust.add_trusted(msg.node_id, msg.display_name, msg.key)
            if msg.host and msg.port:
                await _push_auth_to(f"http://{msg.host}:{msg.port}")  # sync our login to them
            bus.publish()
            return CommandResponse(ok=True, message="paired")
        raise HTTPException(status_code=401, detail="unsolicited pairing confirm")

    @r.post("/api/pair/accept", response_model=CommandResponse)
    async def _pair_accept(req: NodeIdRequest) -> CommandResponse:
        entry = trust.pop_pending_in(req.node_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="no pending request from that node")
        trust.add_trusted(req.node_id, entry["name"], entry["key"])
        # tell them we accepted, so they trust us
        host, port = entry.get("host"), entry.get("port")
        if host and port:
            await _send_pair(f"http://{host}:{port}", "/api/pair/confirm", our_pair_msg())
            await _push_auth_to(f"http://{host}:{port}")  # sync our login to them
        bus.publish()
        return CommandResponse(ok=True, message=f"paired with {entry['name']}")

    @r.post("/api/pair/reject", response_model=CommandResponse)
    def _pair_reject(req: NodeIdRequest) -> CommandResponse:
        trust.pop_pending_in(req.node_id)
        bus.publish()
        return CommandResponse(ok=True, message="rejected")

    @r.delete("/api/pair/{node_id}", response_model=CommandResponse)
    def _unpair(node_id: str) -> CommandResponse:
        trust.remove_trusted(node_id)
        bus.publish()
        return CommandResponse(ok=True, message="unpaired")

    # ---- web login ----
    async def _push_auth_to(url: str) -> None:
        if not webauth.enabled():
            return
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    f"{url}/api/auth/sync",
                    json={"config": webauth.export_config()},
                    headers=identity_headers(cfg.node_id, cfg.node_key),
                    timeout=httpx.Timeout(6.0),
                )
            except httpx.HTTPError:
                pass

    async def _push_auth_to_peers() -> None:
        for url in peer_urls():
            await _push_auth_to(url)

    @r.get("/api/auth/status", response_model=AuthStatus)
    def _auth_status(request: Request) -> AuthStatus:
        authed = (not webauth.enabled()) or webauth.valid_session(request.cookies.get(COOKIE))
        return AuthStatus(
            enabled=webauth.enabled(),
            authed=authed,
            totp_enabled=webauth.totp_enabled(),
            username=webauth.username(),
        )

    @r.post("/api/auth/login", response_model=CommandResponse)
    def _login(req: LoginRequest, response: Response) -> CommandResponse:
        if not webauth.verify(req.username, req.password, req.code):
            raise HTTPException(status_code=401, detail="invalid credentials")
        token = webauth.create_session()
        response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=30 * 86400)
        return CommandResponse(ok=True, message="logged in")

    @r.post("/api/auth/logout", response_model=CommandResponse)
    def _logout(request: Request, response: Response) -> CommandResponse:
        webauth.drop_session(request.cookies.get(COOKIE))
        response.delete_cookie(COOKIE)
        return CommandResponse(ok=True, message="logged out")

    @r.post("/api/auth/set", response_model=SetAuthResponse)
    async def _set_auth(req: SetAuthRequest, response: Response) -> SetAuthResponse:
        secret = webauth.set_credential(req.username, req.password, req.totp_enabled)
        # keep the setter logged in
        response.set_cookie(
            COOKIE, webauth.create_session(), httponly=True, samesite="lax", max_age=30 * 86400
        )
        await _push_auth_to_peers()  # sync to paired machines
        uri = (
            f"otpauth://totp/usbip-node:{req.username}?secret={secret}&issuer=usbip-node"
            if secret
            else None
        )
        return SetAuthResponse(ok=True, message="login set", totp_secret=secret, otpauth_uri=uri)

    @r.post("/api/auth/disable", response_model=CommandResponse)
    async def _disable_auth() -> CommandResponse:
        webauth.disable()
        await _push_auth_to_peers()
        return CommandResponse(ok=True, message="login disabled")

    @r.post("/api/auth/sync", response_model=CommandResponse)
    def _auth_sync(msg: AuthConfigMessage, _: None = Depends(node_auth)) -> CommandResponse:
        webauth.import_config(msg.config)
        return CommandResponse(ok=True, message="auth synced")

    # ---- live state ----
    @r.websocket("/ws")
    async def _ws(ws: WebSocket) -> None:
        if webauth.enabled() and not webauth.valid_session(ws.cookies.get(COOKIE)):
            await ws.close(code=1008)
            return
        await ws.accept()
        q = bus.subscribe()
        try:
            await ws.send_json(local_state().model_dump())
            while True:
                try:
                    await asyncio.wait_for(q.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    pass
                await ws.send_json(local_state().model_dump())
        except WebSocketDisconnect:
            return
        finally:
            bus.unsubscribe(q)

    return r
