"""Local USB/IP operations on Linux (Raspberry Pi included).

The node process is privileged (systemd as root, or a scoped NOPASSWD sudoers rule), so we invoke
`usbip` directly with argv lists -- no shell, no sudo password, no SSH. Read-only listing works
today; bind/attach are wired to real commands here and exercised for real in Phase 1.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from . import validate
from .models import AttachedDevice, Device

_BUSID_LINE = re.compile(r"^\s*-\s*busid\s+(\S+)\s*\((\S+)\)")
_PORT_LINE = re.compile(r"^Port\s+(\d+):")
_REMOTE_URL = re.compile(r"usbip://([^:/]+)")


@dataclass
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    code: int


def _run(argv: list[str], timeout: float = 15.0) -> CommandResult:
    try:
        proc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode)
    except FileNotFoundError:
        return CommandResult(False, "", "usbip binary not found", 127)
    except subprocess.TimeoutExpired:
        return CommandResult(False, "", "usbip command timed out", 124)


def usbip_available() -> bool:
    return shutil.which("usbip") is not None


def list_shareable() -> list[Device]:
    """Devices on this machine that can be exported (`usbip list -l`)."""
    res = _run(["usbip", "list", "-l"])
    devices: list[Device] = []
    pending_busid: str | None = None
    pending_ids: str = ""
    for raw in res.stdout.splitlines():
        m = _BUSID_LINE.match(raw)
        if m:
            pending_busid = m.group(1)
            pending_ids = m.group(2)
            continue
        line = raw.strip()
        if pending_busid and line:
            # The description line already ends with "(vid:pid)"; only append if it's missing.
            desc = line if pending_ids in line else f"{line} ({pending_ids})"
            devices.append(Device(busid=pending_busid, description=desc))
            pending_busid = None
    return devices


def list_attached() -> list[AttachedDevice]:
    """Devices this machine has imported (`usbip port`)."""
    res = _run(["usbip", "port"])
    attached: list[AttachedDevice] = []
    current_port: str | None = None
    desc = ""
    for raw in res.stdout.splitlines():
        m = _PORT_LINE.match(raw.strip())
        if m:
            if current_port is not None:
                attached.append(AttachedDevice(port=current_port, busid="", description=desc.strip()))
            current_port = m.group(1)
            desc = ""
            continue
        if current_port is not None:
            url = _REMOTE_URL.search(raw)
            if url:
                busid_m = re.search(r"/(\d+-[\d.]+)\s*$", raw.strip())
                attached.append(
                    AttachedDevice(
                        port=current_port,
                        busid=busid_m.group(1) if busid_m else "",
                        description=desc.strip(),
                        remote_host=url.group(1),
                    )
                )
                current_port = None
            else:
                desc += " " + raw.strip()
    if current_port is not None:
        attached.append(AttachedDevice(port=current_port, busid="", description=desc.strip()))
    return attached


def bind(busid: str) -> CommandResult:
    if not validate.is_valid_busid(busid):
        return CommandResult(False, "", f"invalid busid: {busid}", 22)
    return _run(["usbip", "bind", "-b", busid])


def unbind(busid: str) -> CommandResult:
    if not validate.is_valid_busid(busid):
        return CommandResult(False, "", f"invalid busid: {busid}", 22)
    return _run(["usbip", "unbind", "-b", busid])


def attach(remote_host: str, busid: str) -> CommandResult:
    if not validate.is_valid_host(remote_host):
        return CommandResult(False, "", f"invalid host: {remote_host}", 22)
    if not validate.is_valid_busid(busid):
        return CommandResult(False, "", f"invalid busid: {busid}", 22)
    return _run(["usbip", "attach", "-r", remote_host, "-b", busid])


def detach(port: str) -> CommandResult:
    if not validate.is_valid_port(port):
        return CommandResult(False, "", f"invalid port: {port}", 22)
    return _run(["usbip", "detach", "-p", port])
