"""Input validation / injection defense.

Ported from src/security/validator.py. Every value that reaches a shell/argv must pass through here.
Because the node runs usbip via argv lists (never shell strings) these are defense-in-depth plus a
way to reject obviously bogus input early with a clear error.
"""

from __future__ import annotations

import ipaddress
import re

BUSID_PATTERN = re.compile(r"^[0-9]+-[0-9]+(\.[0-9]+)*$")
PORT_PATTERN = re.compile(r"^[0-9]{1,3}$")
NODE_ID_PATTERN = re.compile(r"^[0-9a-f]{6,32}$")


def is_valid_busid(busid: str) -> bool:
    """USB bus id like '2-1.4'."""
    return bool(busid) and len(busid) <= 20 and bool(BUSID_PATTERN.match(busid))


def is_valid_port(port: str) -> bool:
    """vhci port number as reported by `usbip port` (e.g. '00', '3')."""
    return bool(port) and bool(PORT_PATTERN.match(port))


def is_valid_host(address: str) -> bool:
    """An IP address or a hostname reachable on the LAN."""
    if not address or len(address) > 253:
        return False
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        pass
    # Hostname: labels of alnum/hyphen, optionally dotted.
    return bool(re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9-]+)*$", address))


def is_valid_node_id(node_id: str) -> bool:
    return bool(node_id) and bool(NODE_ID_PATTERN.match(node_id))
