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
from .proc import CommandResult

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


def _bind_effectively_ok(res: CommandResult) -> bool:
    """A bind is useful if it succeeded OR the device was already bound/shared."""
    if res.ok:
        return True
    m = (res.stderr + res.stdout).lower()
    return "already bound" in m or "already shared" in m


def bind(busid: str):
    if _DEMO:
        r = demo.bind(busid)
        _invalidate()
        return r
    if _IS_WINDOWS:
        r = usbip_windows.bind(busid)
        _invalidate()
        return r
    # Exporting needs the usbipd server listening on :3240, or peers fail to attach with
    # "usbip: error: tcp connect". Start it if nothing else already did.
    ready = usbip_linux.ensure_usbipd()
    if not ready.ok:
        return CommandResult(False, "", ready.stderr or "usbipd is not running", ready.code)
    r = usbip_linux.bind(busid)
    if _bind_effectively_ok(r):
        # Binding is only half the job: usbipd must also *serve* the device to peers.
        # Verify the daemon exports it (healing a stuck daemon if needed) so a following
        # remote attach can't fail with "Attach Request ... failed - Request Failed".
        r = usbip_linux.ensure_exportable(busid)
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
