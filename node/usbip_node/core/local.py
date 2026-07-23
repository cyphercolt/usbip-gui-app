"""Platform facade: pick the right local USB/IP backend for this machine.

Linux uses `usbip`; Windows uses `usbipd` (server) + `usbip`/usbip-win2 (client).

Device listings are cached for a short TTL. Without this, every /api/state call (browser polling +
WebSocket + each peer's fleet poll) would shell out to `usbip list -l`/`usbip port`, and those slow
subprocesses under constant load cause request timeouts that make peers flap in/out of the fleet.
Commands invalidate the cache so the UI reflects changes immediately.
"""

from __future__ import annotations

import platform
import threading
import time

from . import usbip_linux, usbip_windows
from .models import AttachedDevice, Device

_IS_WINDOWS = platform.system().lower().startswith("win")

_CACHE_TTL = 1.5  # seconds
_lock = threading.Lock()
_cache: dict[str, tuple[float, object]] = {}


def _cached(key: str, producer):
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
    value = producer()  # run outside the lock so a slow usbip call doesn't serialize everyone
    with _lock:
        _cache[key] = (now + _CACHE_TTL, value)
    return value


def _invalidate() -> None:
    with _lock:
        _cache.clear()


def backend_name() -> str:
    return "windows" if _IS_WINDOWS else platform.system().lower()


def list_shareable() -> list[Device]:
    fn = usbip_windows.list_shareable if _IS_WINDOWS else usbip_linux.list_shareable
    return _cached("shareable", fn)


def list_attached() -> list[AttachedDevice]:
    # Client-side listing is identical on both platforms.
    return _cached("attached", usbip_linux.list_attached)


def bind(busid: str):
    r = usbip_windows.bind(busid) if _IS_WINDOWS else usbip_linux.bind(busid)
    _invalidate()
    return r


def unbind(busid: str):
    r = usbip_windows.unbind(busid) if _IS_WINDOWS else usbip_linux.unbind(busid)
    _invalidate()
    return r


def attach(remote_host: str, busid: str):
    r = usbip_linux.attach(remote_host, busid)
    _invalidate()
    return r


def detach(port: str):
    r = usbip_linux.detach(port)
    _invalidate()
    return r
