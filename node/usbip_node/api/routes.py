"""REST + WebSocket routes.

Two layers of endpoints:
  * /api/local/*  act on THIS machine (bind/unbind = server role; attach/detach = client role).
    These are what a hub calls on a peer.
  * /api/fleet and /api/attach are the HUB layer: aggregate peers, and orchestrate an
    any-PC -> any-PC attach on behalf of the phone.
"""

from __future__ import annotations

import asyncio
from typing import Callable

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect

from .. import __version__
from ..config import NodeConfig
from ..core import local
from ..core.models import (
    AttachRequest,
    BusidRequest,
    CommandResponse,
    DetachRequest,
    NodeInfo,
    NodeState,
    OrchestrateAttach,
    PeerRef,
    ReleaseRequest,
)
from ..events import StateBus
from ..hub import gather_fleet, post_command
from ..peers import PeerRegistry


def _to_response(result) -> CommandResponse:
    """Adapt a core CommandResult (subprocess) to the API CommandResponse."""
    msg = (result.stderr or result.stdout or "").strip()
    return CommandResponse(ok=result.ok, message=msg)


def build_router(
    cfg: NodeConfig,
    bus: StateBus,
    registry: PeerRegistry,
    peer_urls: Callable[[], list[str]],
) -> APIRouter:
    r = APIRouter()

    def auth(authorization: str | None = Header(default=None)) -> None:
        """Gate command endpoints when a shared token is configured (Phase 2 -> real pairing)."""
        if not cfg.token:
            return
        if authorization != f"Bearer {cfg.token}":
            raise HTTPException(status_code=401, detail="missing or invalid token")

    def node_info() -> NodeInfo:
        return NodeInfo(
            node_id=cfg.node_id,
            display_name=cfg.display_name,
            os_name=cfg.os_name,
            version=__version__,
            host=cfg.advertise_host,
            port=cfg.port,
            reachable=True,
        )

    def local_state() -> NodeState:
        return NodeState(
            info=node_info(),
            shareable=local.list_shareable(),
            attached=local.list_attached(),
        )

    # ---- basic ----
    @r.get("/health")
    def _health() -> dict:
        return {"status": "ok", "service": "usbip-node", "version": __version__}

    @r.get("/api/info", response_model=NodeInfo)
    def _info() -> NodeInfo:
        return node_info()

    @r.get("/api/state", response_model=NodeState)
    def _state() -> NodeState:
        return local_state()

    # ---- peer registry ----
    @r.get("/api/peers")
    def _peers() -> list[str]:
        return registry.urls()

    @r.post("/api/peers", response_model=CommandResponse)
    def _add_peer(ref: PeerRef, _: None = Depends(auth)) -> CommandResponse:
        registry.add(ref.url)
        return CommandResponse(ok=True, message=f"added {ref.url}")

    @r.delete("/api/peers", response_model=CommandResponse)
    def _del_peer(ref: PeerRef, _: None = Depends(auth)) -> CommandResponse:
        registry.remove(ref.url)
        return CommandResponse(ok=True, message=f"removed {ref.url}")

    # ---- local commands (act on this machine) ----
    @r.post("/api/local/bind", response_model=CommandResponse)
    def _bind(req: BusidRequest, _: None = Depends(auth)) -> CommandResponse:
        resp = _to_response(local.bind(req.busid))
        bus.publish()
        return resp

    @r.post("/api/local/unbind", response_model=CommandResponse)
    def _unbind(req: BusidRequest, _: None = Depends(auth)) -> CommandResponse:
        resp = _to_response(local.unbind(req.busid))
        bus.publish()
        return resp

    @r.post("/api/local/attach", response_model=CommandResponse)
    def _attach(req: AttachRequest, _: None = Depends(auth)) -> CommandResponse:
        resp = _to_response(local.attach(req.remote_host, req.busid))
        bus.publish()
        return resp

    @r.post("/api/local/detach", response_model=CommandResponse)
    def _detach(req: DetachRequest, _: None = Depends(auth)) -> CommandResponse:
        resp = _to_response(local.detach(req.port))
        bus.publish()
        return resp

    # ---- hub layer ----
    @r.get("/api/fleet", response_model=list[NodeState])
    async def _fleet() -> list[NodeState]:
        fleet, _ = await gather_fleet(local_state(), peer_urls())
        return fleet

    @r.post("/api/attach", response_model=CommandResponse)
    async def _orchestrate(req: OrchestrateAttach) -> CommandResponse:
        """Bind the device on the source, then attach it on the destination."""
        fleet, id_to_url = await gather_fleet(local_state(), peer_urls())
        by_id = {n.info.node_id: n for n in fleet}
        source = by_id.get(req.source_node_id)
        dest = by_id.get(req.dest_node_id)
        if source is None or dest is None:
            raise HTTPException(status_code=404, detail="source or destination node not found")

        async with httpx.AsyncClient() as client:
            # 1) ensure the device is shared on the source
            if source.info.node_id == cfg.node_id:
                bind_res = _to_response(local.bind(req.busid))
            else:
                bind_res = await post_command(
                    client, id_to_url[source.info.node_id], "/api/local/bind",
                    {"busid": req.busid}, cfg.token,
                )
            if not bind_res.ok:
                return CommandResponse(ok=False, message=f"bind on source failed: {bind_res.message}")

            # 2) attach it on the destination, pointing at the source's usbip host
            if dest.info.node_id == cfg.node_id:
                attach_res = _to_response(local.attach(source.info.host, req.busid))
            else:
                attach_res = await post_command(
                    client, id_to_url[dest.info.node_id], "/api/local/attach",
                    {"remote_host": source.info.host, "busid": req.busid}, cfg.token,
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
        """Detach on the destination AND unbind on the source, so 'detach' fully frees the device
        to be sent elsewhere — the user never touches share/unshare."""
        fleet, id_to_url = await gather_fleet(local_state(), peer_urls())
        by_id = {n.info.node_id: n for n in fleet}
        dest = by_id.get(req.dest_node_id)
        if dest is None:
            raise HTTPException(status_code=404, detail="destination node not found")
        attached = next((a for a in dest.attached if a.port == req.port), None)

        async with httpx.AsyncClient() as client:
            # 1) detach on the destination
            if dest.info.node_id == cfg.node_id:
                detach_res = _to_response(local.detach(req.port))
            else:
                detach_res = await post_command(
                    client, id_to_url[dest.info.node_id], "/api/local/detach",
                    {"port": req.port}, cfg.token,
                )
            # 2) best-effort unbind on the source (found by matching its advertised host)
            unbound = ""
            if attached and attached.remote_host and attached.busid:
                source = next((n for n in fleet if n.info.host == attached.remote_host), None)
                if source is not None:
                    if source.info.node_id == cfg.node_id:
                        u = _to_response(local.unbind(attached.busid))
                    else:
                        u = await post_command(
                            client, id_to_url[source.info.node_id], "/api/local/unbind",
                            {"busid": attached.busid}, cfg.token,
                        )
                    unbound = " and freed on source" if u.ok else " (source still bound)"

        bus.publish()
        if not detach_res.ok:
            return CommandResponse(ok=False, message=f"detach failed: {detach_res.message}")
        return CommandResponse(ok=True, message=f"detached{unbound}")

    # ---- per-node commands via the hub (browser talks only to the node serving the page) ----
    async def _resolve(node_id: str) -> tuple[bool, str | None]:
        """Map a node_id to (is_self, peer_url). peer_url is None if self or not found."""
        if node_id == cfg.node_id:
            return True, None
        _, id_to_url = await gather_fleet(local_state(), peer_urls())
        return False, id_to_url.get(node_id)

    async def _run_on(node_id: str, local_fn, path: str, payload: dict) -> CommandResponse:
        is_self, url = await _resolve(node_id)
        if is_self:
            resp = _to_response(local_fn())
        elif url:
            async with httpx.AsyncClient() as client:
                resp = await post_command(client, url, path, payload, cfg.token)
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

    # ---- live state ----
    @r.websocket("/ws")
    async def _ws(ws: WebSocket) -> None:
        await ws.accept()
        q = bus.subscribe()
        try:
            await ws.send_json(local_state().model_dump())  # initial snapshot
            while True:
                try:
                    await asyncio.wait_for(q.get(), timeout=2.0)  # event OR periodic refresh
                except asyncio.TimeoutError:
                    pass
                await ws.send_json(local_state().model_dump())
        except WebSocketDisconnect:
            return
        finally:
            bus.unsubscribe(q)

    return r
