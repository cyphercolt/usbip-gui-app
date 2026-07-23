"""Shared data shapes for the API and core. The FastAPI OpenAPI schema is generated from these,
and the web app's TypeScript types are generated from that schema.
"""

from __future__ import annotations

from pydantic import BaseModel


class Device(BaseModel):
    busid: str
    description: str
    # server-side sharing state (this node exports it)
    shared: bool = False


class AttachedDevice(BaseModel):
    port: str
    busid: str
    description: str
    remote_host: str | None = None


class NodeInfo(BaseModel):
    node_id: str
    display_name: str
    os_name: str
    version: str
    reachable: bool = True


class NodeState(BaseModel):
    """Everything a fleet card needs about one machine."""

    info: NodeInfo
    shareable: list[Device] = []
    attached: list[AttachedDevice] = []
