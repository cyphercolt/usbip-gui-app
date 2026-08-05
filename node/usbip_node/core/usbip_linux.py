"""Local USB/IP operations on Linux (Raspberry Pi included).

The node process is privileged (systemd as root, or a scoped NOPASSWD sudoers rule), so we invoke
`usbip` directly with argv lists -- no shell, no sudo password, no SSH. Read-only listing works
today; bind/attach are wired to real commands here and exercised for real in Phase 1.
"""

from __future__ import annotations

import re
import shutil
import time

from . import validate
from .models import AttachedDevice, Device
from .proc import CommandResult
from .proc import run as _run

_BUSID_LINE = re.compile(r"^\s*-\s*busid\s+(\S+)\s*\((\S+)\)")
_PORT_LINE = re.compile(r"^Port\s+(\d+):")
_REMOTE_URL = re.compile(r"usbip://([^:/]+)")
# Busid lines in `usbip list -r` output: "     5-1.4.4.2: Valve Software : ...".
_EXPORTED_BUSID = re.compile(r"^\s*(\d+-[\d.]+)\s*:")


def usbip_available() -> bool:
    return shutil.which("usbip") is not None


def usbipd_running() -> bool:
    """True if a usbipd server process is already running on this machine."""
    res = _run(["pgrep", "-x", "usbipd"])
    return res.ok and bool(res.stdout.strip())


def ensure_usbipd() -> CommandResult:
    """Start the usbipd server if it isn't running already.

    Exporting devices only works while usbipd is listening on :3240 -- `usbip bind` alone is
    not enough, and peers attaching to us get "usbip: error: tcp connect" without it. Safe to
    call repeatedly: a no-op when usbipd is already up (e.g. started by hand or by another tool
    before this app existed, like on some Pis).
    """
    if usbipd_running():
        return CommandResult(True, "usbipd already running", "", 0)
    _run(["modprobe", "usbip_host"])  # harmless if already loaded or built into the kernel
    started = _run(["usbipd", "-D"])  # -D: detach and run as a daemon
    if not started.ok:
        detail = (started.stderr or started.stdout).strip()
        return CommandResult(False, "", f"could not start usbipd: {detail}", started.code)
    if not usbipd_running():
        return CommandResult(False, "", "usbipd exited right after start (needs root?)", 1)
    return CommandResult(True, "usbipd started", "", 0)


def list_exported_busids(host: str = "127.0.0.1") -> set[str] | None:
    """Busids usbipd currently reports as attachable to clients.

    Uses the same OP_REQ_DEVLIST exchange a remote `usbip attach` performs, so this is
    exactly what a peer will see. Returns None when the daemon itself can't be queried
    (down/unreachable) -- distinct from an empty set (daemon is up but exports nothing).
    """
    res = _run(["usbip", "list", "-r", host])
    if not res.ok:
        return None
    busids: set[str] = set()
    for raw in (res.stdout + "\n" + res.stderr).splitlines():
        m = _EXPORTED_BUSID.match(raw)
        if m:
            busids.add(m.group(1))
    return busids


def restart_usbipd() -> CommandResult:
    """Kill and restart the usbipd daemon.

    Workaround for usbipd getting stuck: when a client disappears without a clean detach
    (reboot, network drop), the per-export child and the kernel-side 'usbip_sockfd' state
    can linger, and every later attach then fails with "Attach Request ... failed -
    Request Failed". Killing the daemon (and its per-export children) releases that
    state; the fresh daemon re-scans sysfs at startup and re-exports everything still
    bound to usbip-host -- kernel-side bindings survive, no rebind needed. Any device
    legitimately attached right now is disconnected, but we only restart when the
    daemon's own export list is already wrong, i.e. attaching was going to fail anyway.
    """
    _run(["pkill", "-x", "usbipd"])
    for _ in range(20):
        if not usbipd_running():
            break
        time.sleep(0.1)
    if usbipd_running():
        # A stubborn export-serving child ignored SIGTERM; force it so the port frees up.
        _run(["pkill", "-9", "-x", "usbipd"])
        for _ in range(20):
            if not usbipd_running():
                break
            time.sleep(0.1)
    return ensure_usbipd()


def ensure_exportable(busid: str) -> CommandResult:
    """Make sure usbipd will actually serve `busid` to a remote attach.

    `usbip bind` only rewrites sysfs; the *daemon* is what answers attach requests, and
    when its view is off (stuck export from a dead client, refresh hiccup) the peer fails
    later with the cryptic "Attach Request ... failed - Request Failed". Probe the
    daemon's export list; if the device is missing, restart usbipd once and re-check.
    Returns ok=True only when the daemon itself confirms the device is attachable.
    """
    for _ in range(3):
        busids = list_exported_busids()
        if busids is not None and busid in busids:
            return CommandResult(True, f"{busid} bound and exported", "", 0)
        time.sleep(0.4)
    restarted = restart_usbipd()
    if not restarted.ok:
        return CommandResult(False, "", restarted.stderr or "could not restart usbipd", restarted.code)
    for _ in range(3):
        busids = list_exported_busids()
        if busids is not None and busid in busids:
            return CommandResult(True, f"{busid} bound and exported (usbipd restarted)", "", 0)
        time.sleep(0.4)
    return CommandResult(
        False, "",
        f"{busid} is bound but usbipd does not export it, even after a daemon restart; "
        "attaching from a peer would fail",
        1,
    )


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
