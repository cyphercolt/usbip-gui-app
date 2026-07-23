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
    host: str = "127.0.0.1"  # address for usbip (port 3240) + API
    port: int = 4820  # API port
    reachable: bool = True


class NodeState(BaseModel):
    """Everything a fleet card needs about one machine."""

    info: NodeInfo
    shareable: list[Device] = []
    attached: list[AttachedDevice] = []


class CommandResponse(BaseModel):
    ok: bool
    message: str = ""


class OrchestrateAttach(BaseModel):
    """Attach a device exported by one machine onto another, driven from the phone."""

    source_node_id: str
    busid: str
    dest_node_id: str


class BusidRequest(BaseModel):
    busid: str


class AttachRequest(BaseModel):
    remote_host: str
    busid: str


class DetachRequest(BaseModel):
    port: str


class PeerRef(BaseModel):
    url: str  # base URL, e.g. http://192.168.2.50:4820
