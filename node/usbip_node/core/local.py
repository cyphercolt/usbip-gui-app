"""Platform facade: pick the right local USB/IP backend for this machine.

Linux uses `usbip`; Windows uses `usbipd` (server) + `usbip`/usbip-win2 (client).
"""

from __future__ import annotations

import platform

from . import usbip_linux, usbip_windows
from .models import AttachedDevice, Device

_IS_WINDOWS = platform.system().lower().startswith("win")


def backend_name() -> str:
    return "windows" if _IS_WINDOWS else platform.system().lower()


def list_shareable() -> list[Device]:
    return usbip_windows.list_shareable() if _IS_WINDOWS else usbip_linux.list_shareable()


def list_attached() -> list[AttachedDevice]:
    # Client-side listing is identical on both platforms.
    return usbip_linux.list_attached()


def bind(busid: str):
    return usbip_windows.bind(busid) if _IS_WINDOWS else usbip_linux.bind(busid)


def unbind(busid: str):
    return usbip_windows.unbind(busid) if _IS_WINDOWS else usbip_linux.unbind(busid)


def attach(remote_host: str, busid: str):
    return usbip_linux.attach(remote_host, busid)


def detach(port: str):
    return usbip_linux.detach(port)
