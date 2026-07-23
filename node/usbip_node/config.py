"""Node configuration and identity.

Phase 0: minimal, env-driven. Later phases add the pairing token / trust store here.
"""

from __future__ import annotations

import ipaddress
import os
import platform
import socket
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PORT = 4820
_STATE_DIR_ENV = "USBIP_NODE_STATE_DIR"

# Tailscale hands out CGNAT addresses in this range; we must NOT advertise those to LAN peers.
_TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")
# Interface name prefixes that are not the real LAN NIC.
_VIRTUAL_IFACES = ("tailscale", "docker", "br-", "veth", "virbr", "zt", "tun", "tap", "lo")


def _enumerate_ipv4() -> list[tuple[str, str]]:
    """Return [(iface_name, ipv4), ...] for global-scope addresses (Linux via `ip`)."""
    out = []
    try:
        res = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", "scope", "global"],
            capture_output=True, text=True, timeout=3,
        )
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            iface = parts[1]
            for i, tok in enumerate(parts):
                if tok == "inet" and i + 1 < len(parts):
                    out.append((iface, parts[i + 1].split("/")[0]))
    except (OSError, subprocess.SubprocessError):
        pass
    return out


def _score_ip(iface: str, ip: str) -> int:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return -1000
    score = 0
    low = iface.lower()
    if any(low.startswith(p) for p in _VIRTUAL_IFACES):
        score -= 100
    if addr in _TAILSCALE_CGNAT:
        score -= 100  # never advertise the tailnet address to LAN peers
    elif ip.startswith("192.168."):
        score += 30
    elif ip.startswith("10."):
        score += 25
    elif addr.is_private:
        score += 15  # 172.16/12 etc.
    if any(low.startswith(p) for p in ("eth", "en", "eno", "enp", "wl", "wlan", "wlp")):
        score += 5
    return score


def primary_ip() -> str:
    """Best-guess LAN IP other machines can reach this one at.

    Overridable with USBIP_NODE_ADVERTISE_HOST. Otherwise prefers a real LAN NIC and explicitly
    avoids Tailscale (100.64/10) and docker/bridge/virtual interfaces. Falls back to the UDP-socket
    trick, then hostname.
    """
    override = os.environ.get("USBIP_NODE_ADVERTISE_HOST")
    if override:
        return override

    candidates = _enumerate_ipv4()
    if candidates:
        iface, ip = max(candidates, key=lambda c: _score_ip(*c))
        if _score_ip(iface, ip) > 0:
            return ip

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no packets sent; resolves the default-route source IP
        ip = s.getsockname()[0]
        if ipaddress.ip_address(ip) not in _TAILSCALE_CGNAT:
            return ip
    except OSError:
        pass
    finally:
        s.close()
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


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


def _load_or_create_node_key(directory: Path) -> str:
    """This node's secret identity key. A peer stores it when pairing; we present it on every
    node-to-node call so the peer can verify us (Syncthing-style device identity)."""
    key_file = directory / "node_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = uuid.uuid4().hex + uuid.uuid4().hex
    try:
        key_file.write_text(key)
        os.chmod(key_file, 0o600)
    except OSError:
        pass
    return key


@dataclass
class NodeConfig:
    node_id: str
    node_key: str  # this node's secret identity (presented to peers)
    display_name: str
    host: str = "0.0.0.0"  # bind address
    port: int = DEFAULT_PORT
    advertise_host: str = "127.0.0.1"  # address peers/clients use to reach usbip + API
    os_name: str = field(default_factory=lambda: platform.system().lower())

    @classmethod
    def load(cls) -> "NodeConfig":
        directory = state_dir()
        return cls(
            node_id=_load_or_create_node_id(directory),
            node_key=_load_or_create_node_key(directory),
            display_name=os.environ.get("USBIP_NODE_NAME", socket.gethostname()),
            host=os.environ.get("USBIP_NODE_HOST", "0.0.0.0"),
            port=int(os.environ.get("USBIP_NODE_PORT", DEFAULT_PORT)),
            advertise_host=primary_ip(),
        )
