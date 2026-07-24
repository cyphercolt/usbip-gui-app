"""Platform facade: pick the right local USB/IP backend for this machine.

Linux uses `usbip`; Windows uses `usbipd` (server) + `usbip`/usbip-win2 (client).

Device listings are cached for a short TTL. Without this, every /api/state call (browser polling +
WebSocket + each peer's fleet poll) would shell out to `usbip list -l`/`usbip port`, and those slow
subprocesses under constant load cause request timeouts that make peers flap in/out of the fleet.
Commands invalidate the cache so the UI reflects changes immediately.
"""

from __future__ import annotations

import os
import platform
import threading
import time

from . import usbip_linux, usbip_windows
from .models import AttachedDevice, Device

_IS_WINDOWS = platform.system().lower().startswith("win")
_DEMO = os.environ.get("USBIP_NODE_DEMO") == "1"
if _DEMO:
    from . import demo

# TTL must be >= the UI poll interval or every poll is a cache miss and re-runs usbip. On a slow
# Pi that caused fetch timeouts and made the node flap in/out of the fleet.
_CACHE_TTL = 5.0  # seconds
_cache: dict[str, tuple[float, object]] = {}
_cache_lock = threading.Lock()
_key_locks: dict[str, threading.Lock] = {}


def _key_lock(key: str) -> threading.Lock:
    with _cache_lock:
        return _key_locks.setdefault(key, threading.Lock())


def _cached(key: str, producer):
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
    # Single-flight: only one thread runs the (slow) usbip call; concurrent callers wait then reuse.
    with _key_lock(key):
        now = time.monotonic()
        with _cache_lock:
            hit = _cache.get(key)
            if hit and hit[0] > now:
                return hit[1]
        value = producer()
        with _cache_lock:
            _cache[key] = (now + _CACHE_TTL, value)
        return value


def _invalidate() -> None:
    with _cache_lock:
        _cache.clear()


def backend_name() -> str:
    return "windows" if _IS_WINDOWS else platform.system().lower()


def list_shareable() -> list[Device]:
    if _DEMO:
        return demo.list_shareable()
    fn = usbip_windows.list_shareable if _IS_WINDOWS else usbip_linux.list_shareable
    return _cached("shareable", fn)


def list_attached() -> list[AttachedDevice]:
    if _DEMO:
        return demo.list_attached()
    # Client-side listing is identical on both platforms.
    return _cached("attached", usbip_linux.list_attached)


def bind(busid: str):
    r = demo.bind(busid) if _DEMO else (usbip_windows.bind(busid) if _IS_WINDOWS else usbip_linux.bind(busid))
    _invalidate()
    return r


def unbind(busid: str):
    r = demo.unbind(busid) if _DEMO else (usbip_windows.unbind(busid) if _IS_WINDOWS else usbip_linux.unbind(busid))
    _invalidate()
    return r


def attach(remote_host: str, busid: str):
    r = demo.attach(remote_host, busid) if _DEMO else usbip_linux.attach(remote_host, busid)
    _invalidate()
    return r


def detach(port: str):
    r = demo.detach(port) if _DEMO else usbip_linux.detach(port)
    _invalidate()
    return r
