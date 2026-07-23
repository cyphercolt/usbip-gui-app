"""Node configuration and identity.

Phase 0: minimal, env-driven. Later phases add the pairing token / trust store here.
"""

from __future__ import annotations

import os
import platform
import socket
import uuid
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PORT = 4820
_STATE_DIR_ENV = "USBIP_NODE_STATE_DIR"


def primary_ip() -> str:
    """Best-guess LAN IP other machines can reach this one at.

    Overridable with USBIP_NODE_ADVERTISE_HOST (recommended when a box has several NICs,
    e.g. docker/tailscale interfaces). Falls back to a UDP-socket trick, then hostname.
    """
    override = os.environ.get("USBIP_NODE_ADVERTISE_HOST")
    if override:
        return override
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no packets sent; just resolves the default-route source IP
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        s.close()


def state_dir() -> Path:
    """Where the node persists its identity / trust store."""
    override = os.environ.get(_STATE_DIR_ENV)
    if override:
        return Path(override)
    # Prefer a system location when running as a service; fall back to user config.
    for candidate in ("/var/lib/usbip-node", os.path.expanduser("~/.config/usbip-node")):
        p = Path(candidate)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except (PermissionError, OSError):
            continue
    p = Path("./.usbip-node-state")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _load_or_create_node_id(directory: Path) -> str:
    id_file = directory / "node_id"
    if id_file.exists():
        return id_file.read_text().strip()
    node_id = uuid.uuid4().hex[:12]
    try:
        id_file.write_text(node_id)
    except OSError:
        pass
    return node_id


@dataclass
class NodeConfig:
    node_id: str
    display_name: str
    host: str = "0.0.0.0"  # bind address
    port: int = DEFAULT_PORT
    advertise_host: str = "127.0.0.1"  # address peers/clients use to reach usbip + API
    token: str | None = None  # optional shared secret gating command endpoints (Phase 2 -> pairing)
    os_name: str = field(default_factory=lambda: platform.system().lower())

    @classmethod
    def load(cls) -> "NodeConfig":
        directory = state_dir()
        return cls(
            node_id=_load_or_create_node_id(directory),
            display_name=os.environ.get("USBIP_NODE_NAME", socket.gethostname()),
            host=os.environ.get("USBIP_NODE_HOST", "0.0.0.0"),
            port=int(os.environ.get("USBIP_NODE_PORT", DEFAULT_PORT)),
            advertise_host=primary_ip(),
            token=os.environ.get("USBIP_NODE_TOKEN") or None,
        )
