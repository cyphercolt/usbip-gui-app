"""Platform facade: pick the right local USB/IP backend for this machine.

Phase 0/1 implement Linux. Phase 3 adds usbip_windows and this facade dispatches to it.
"""

from __future__ import annotations

import platform

from . import usbip_linux
from .models import AttachedDevice, Device

_SYSTEM = platform.system().lower()


def backend_name() -> str:
    return _SYSTEM


def list_shareable() -> list[Device]:
    if _SYSTEM == "linux":
        return usbip_linux.list_shareable()
    return []  # windows backend arrives in Phase 3


def list_attached() -> list[AttachedDevice]:
    if _SYSTEM == "linux":
        return usbip_linux.list_attached()
    return []


def bind(busid: str):
    return usbip_linux.bind(busid)


def unbind(busid: str):
    return usbip_linux.unbind(busid)


def attach(remote_host: str, busid: str):
    return usbip_linux.attach(remote_host, busid)


def detach(port: str):
    return usbip_linux.detach(port)
