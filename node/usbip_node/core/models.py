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
    auto: bool = False  # auto-reconnect armed for this device on this machine


class NodeInfo(BaseModel):
    node_id: str
    display_name: str
    os_name: str
    version: str
    host: str = "127.0.0.1"  # address for usbip (port 3240) + API
    port: int = 4820  # API port
    reachable: bool = True
    paired: bool = True  # in locked mode, false = discovered but not yet approved


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


class AutoReconnectRequest(BaseModel):
    remote_host: str
    busid: str
    description: str = ""
    enabled: bool


class ReleaseRequest(BaseModel):
    """Fully release an attached device: detach on the destination AND unbind on the source,
    so the user never thinks about sharing/binding. Just send and detach."""

    dest_node_id: str
    port: str


class PeerRef(BaseModel):
    url: str  # base URL, e.g. http://192.168.2.50:4820


# ---- pairing / security ----
class Identity(BaseModel):
    node_id: str
    display_name: str
    os_name: str


class PairMessage(BaseModel):
    """Sent node->node during pairing; carries the sender's identity + secret key + call-back addr."""

    node_id: str
    display_name: str
    key: str
    host: str = ""
    port: int = 0


class PairedRef(BaseModel):
    node_id: str
    name: str


class SecurityState(BaseModel):
    mode: str  # "open" | "locked"
    this_node: PairedRef
    trusted: list[PairedRef] = []
    pending: list[PairedRef] = []  # incoming requests awaiting approval


class ModeRequest(BaseModel):
    mode: str


class NodeIdRequest(BaseModel):
    node_id: str


# ---- web login ----
class LoginRequest(BaseModel):
    username: str
    password: str
    code: str | None = None  # TOTP, if 2FA enabled


class SetAuthRequest(BaseModel):
    username: str
    password: str
    totp_enabled: bool = False


class AuthStatus(BaseModel):
    enabled: bool
    authed: bool
    totp_enabled: bool = False
    username: str = ""


class SetAuthResponse(BaseModel):
    ok: bool
    message: str = ""
    totp_secret: str | None = None  # returned once when enabling 2FA
    otpauth_uri: str | None = None


class AuthConfigMessage(BaseModel):
    config: dict
