"""Demo backend: fake USB devices with the real flow (bind/attach/detach) + lifelike delays.

Enable with USBIP_NODE_DEMO=1. Lets you run a self-contained pretend fleet (no real usbip, no real
hardware) for screenshots, demos, and trying the UI. Devices for a node come from
USBIP_NODE_DEMO_DEVICES (comma-separated busids from CATALOG).
"""

from __future__ import annotations

import os
import threading
import time

from .models import AttachedDevice, Device

# busid -> friendly product name (shared across the demo fleet so an attached device shows its name).
CATALOG: dict[str, str] = {
    "1-1.1": "Logitech G Pro Wireless Mouse",
    "1-1.2": "Keychron K8 Mechanical Keyboard",
    "1-2": "Sony DualSense Controller",
    "2-1": "Blue Yeti USB Microphone",
    "2-2": "Elgato Stream Deck",
    "3-1": "SanDisk Ultra 128GB Flash Drive",
    "3-2": "Logitech Brio 4K Webcam",
    "4-1": "Xbox Wireless Controller",
}

_lock = threading.Lock()
_bound: set[str] = set()
_attached: list[AttachedDevice] = []


def _my_busids() -> list[str]:
    raw = os.environ.get("USBIP_NODE_DEMO_DEVICES", "")
    return [b.strip() for b in raw.split(",") if b.strip() in CATALOG]


def list_shareable() -> list[Device]:
    return [Device(busid=b, description=CATALOG[b], shared=(b in _bound)) for b in _my_busids()]


def list_attached() -> list[AttachedDevice]:
    with _lock:
        return list(_attached)


class _R:
    def __init__(self, ok: bool, msg: str = "") -> None:
        self.ok, self.stdout, self.stderr = ok, msg, "" if ok else msg


def bind(busid: str):
    time.sleep(0.4)
    _bound.add(busid)
    return _R(True, f"shared {busid}")


def unbind(busid: str):
    _bound.discard(busid)
    return _R(True, f"unshared {busid}")


def attach(remote_host: str, busid: str):
    time.sleep(1.0)  # lifelike "connecting…" delay
    with _lock:
        port = f"{len(_attached):02d}"
        _attached.append(
            AttachedDevice(
                port=port,
                busid=busid,
                description=CATALOG.get(busid, "USB Device"),
                remote_host=remote_host,
            )
        )
    return _R(True, f"attached {busid}")


def detach(port: str):
    with _lock:
        _attached[:] = [a for a in _attached if a.port != port]
    return _R(True, f"detached port {port}")
