"""Local USB/IP operations on Windows.

Two separate tools are involved (same split the old app used):
  * SERVER side (sharing this machine's devices): usbipd-win -> `usbipd list/bind/unbind`.
  * CLIENT side (attaching a remote device here): usbip-win2 -> `usbip attach/detach/port`,
    whose syntax is identical to Linux, so those are reused from usbip_linux.

The node runs as a LocalSystem/admin Windows service, so no UAC prompt is needed.

STATUS: ported from the old app's known-good command syntax but NOT yet verified on real
Windows hardware — see packaging/install-windows.ps1.
"""

from __future__ import annotations

import re
import shutil

from . import validate
from .models import Device
from .proc import CommandResult
from .proc import run as _run

# Reuse the client-side operations verbatim — usbip-win2 mirrors Linux usbip.
from .usbip_linux import attach, detach, list_attached  # noqa: F401  (re-exported)


def usbipd_available() -> bool:
    return shutil.which("usbipd") is not None


def list_shareable() -> list[Device]:
    """Parse `usbipd list` (the Connected: section). Format:

        Connected:
        BUSID  VID:PID    DEVICE                              STATE
        1-4    1234:5678  USB Input Device                    Not shared
    """
    res = _run(["usbipd", "list"])
    devices: list[Device] = []
    in_connected = False
    for raw in res.stdout.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("Connected:"):
            in_connected = True
            continue
        if stripped.startswith("Persisted:") or stripped.startswith("GUID"):
            in_connected = False
            continue
        if not in_connected or not stripped or stripped.startswith("BUSID"):
            continue

        parts = stripped.split(None, 1)
        if len(parts) < 2:
            continue
        busid, rest = parts[0], parts[1]
        vidpid_split = rest.split(None, 1)
        vidpid = vidpid_split[0]
        remainder = vidpid_split[1] if len(vidpid_split) > 1 else ""
        # DEVICE name and STATE are separated by 2+ spaces.
        cols = re.split(r"\s{2,}", remainder.strip())
        device_name = cols[0] if cols else "USB Device"
        state = cols[1].lower() if len(cols) > 1 else ""
        shared = "shared" in state and "not shared" not in state or "attached" in state
        desc = f"{device_name} ({vidpid})" if ":" in vidpid else device_name
        devices.append(Device(busid=busid, description=desc, shared=shared))
    return devices


def bind(busid: str) -> CommandResult:
    if not validate.is_valid_busid(busid):
        return CommandResult(False, "", f"invalid busid: {busid}", 22)
    return _run(["usbipd", "bind", "--busid", busid])


def unbind(busid: str) -> CommandResult:
    if not validate.is_valid_busid(busid):
        return CommandResult(False, "", f"invalid busid: {busid}", 22)
    return _run(["usbipd", "unbind", "--busid", busid])
