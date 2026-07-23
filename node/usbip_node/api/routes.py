"""REST + WebSocket routes.

Phase 0 exposes: health, this node's info, and this node's local state (real usbip data on Linux).
The fleet endpoint returns just this node for now; Phase 2 fills it with discovered peers.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .. import __version__
from ..config import NodeConfig
from ..core import local
from ..core.models import NodeInfo, NodeState


def _node_info(cfg: NodeConfig) -> NodeInfo:
    return NodeInfo(
        node_id=cfg.node_id,
        display_name=cfg.display_name,
        os_name=cfg.os_name,
        version=__version__,
        reachable=True,
    )


def _local_state(cfg: NodeConfig) -> NodeState:
    return NodeState(
        info=_node_info(cfg),
        shareable=local.list_shareable(),
        attached=local.list_attached(),
    )


def build_router(cfg: NodeConfig) -> APIRouter:
    """Bind routes to a concrete node config."""
    r = APIRouter()

    @r.get("/health")
    def _health() -> dict:
        return {"status": "ok", "service": "usbip-node", "version": __version__}

    @r.get("/api/info", response_model=NodeInfo)
    def _info() -> NodeInfo:
        return _node_info(cfg)

    @r.get("/api/state", response_model=NodeState)
    def _state() -> NodeState:
        return _local_state(cfg)

    @r.get("/api/fleet", response_model=list[NodeState])
    def _fleet() -> list[NodeState]:
        # Phase 2: aggregate discovered peers. For now, just this node.
        return [_local_state(cfg)]

    @r.websocket("/ws")
    async def _ws(ws: WebSocket) -> None:
        """Push local state periodically. Phase 1 switches to event-driven push."""
        await ws.accept()
        try:
            while True:
                await ws.send_json(_local_state(cfg).model_dump())
                await asyncio.sleep(3.0)
        except WebSocketDisconnect:
            return

    return r
