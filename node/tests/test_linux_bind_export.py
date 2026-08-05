"""Tests for the bind -> verify/self-heal usbipd export path.

Regression for "Attach Request for <busid> failed - Request Failed": `usbip bind` alone
is not enough, usbipd must also *serve* the device. Covers the probe-and-restart
behavior (list_exported_busids / restart_usbipd / ensure_exportable) plus the local.bind
wiring that triggers it, all without real hardware by faking the subprocess runner.
"""

import time

import pytest

from usbip_node.core import local, usbip_linux
from usbip_node.core.proc import CommandResult


class _FakeHost:
    """Simulated OS state: the usbipd daemon and the devices it exports.

    Mirrors the real-world separation between sysfs (`usbip bind`) and what usbipd
    actually answers on OP_REQ_DEVLIST: a device can be bound without being exported.
    """

    def __init__(self, exported=(), daemon_up=True, bind_ok=True):
        self.exported = set(exported)
        self.daemon_up = daemon_up
        self.bind_ok = bind_ok
        self.calls: list[list[str]] = []
        self.probes = 0

    def run(self, argv, **_kw) -> CommandResult:
        self.calls.append(argv)
        if argv[:3] == ["pgrep", "-x", "usbipd"]:
            return CommandResult(
                self.daemon_up, "1234\n" if self.daemon_up else "", "",
                0 if self.daemon_up else 1,
            )
        if argv[:2] in (["pkill", "-x"], ["pkill", "-9", "-x"]):
            self.daemon_up = False
            return CommandResult(True, "", "", 0)
        if argv[:2] == ["usbipd", "-D"]:
            self.daemon_up = True
            return CommandResult(True, "usbipd started", "", 0)
        if argv[:3] == ["usbip", "list", "-r"]:
            self.probes += 1
            host = argv[3]
            if not self.daemon_up:
                return CommandResult(False, "", f"usbip: error: could not connect to {host}", 1)
            if not self.exported:
                return CommandResult(True, "", f"usbip: info: no exportable devices found on {host}", 0)
            listing = (
                f"Exportable USB devices\n======================\n - {host}\n"
                + "".join(
                    f"      {b}: Vendor : Product (1234:5678)\n" for b in sorted(self.exported)
                )
            )
            return CommandResult(True, listing, "", 0)
        if argv[:2] == ["usbip", "bind"] and not self.bind_ok:
            return CommandResult(False, "", "usbip: error: device is not found", 1)
        return CommandResult(True, "", "", 0)  # modprobe etc.

    def restarted(self) -> bool:
        return any(c[:2] == ["pkill", "-x"] for c in self.calls)


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(usbip_linux.time, "sleep", lambda *_a, **_k: None)


@pytest.fixture
def fake_host(monkeypatch):
    host = _FakeHost()
    monkeypatch.setattr(usbip_linux, "_run", host.run)
    monkeypatch.setattr(local, "_DEMO", False)
    # Default: usbipd started long before the bind -> local.bind must restart it.
    monkeypatch.setattr(usbip_linux, "usbipd_start_epoch", lambda: 0.0)
    return host


def test_list_exported_busids_parses_listing(monkeypatch):
    host = _FakeHost(exported={"5-1.4.4.2", "1-1"})
    monkeypatch.setattr(usbip_linux, "_run", host.run)
    assert usbip_linux.list_exported_busids() == {"5-1.4.4.2", "1-1"}


def test_list_exported_busids_none_when_daemon_down(monkeypatch):
    host = _FakeHost(daemon_up=False)
    monkeypatch.setattr(usbip_linux, "_run", host.run)
    assert usbip_linux.list_exported_busids() is None


def test_ensure_exportable_noop_when_listed(no_sleep, fake_host):
    fake_host.exported = {"5-1.4.4.2"}
    res = usbip_linux.ensure_exportable("5-1.4.4.2")
    assert res.ok
    assert "exported" in res.stdout
    assert not fake_host.restarted()


def test_ensure_exportable_restarts_stuck_usbipd(no_sleep, fake_host, monkeypatch):
    # usbipd doesn't serve the bound device; restart clears the stuck daemon state.
    def run(argv, **_kw):
        if argv[:2] == ["usbipd", "-D"]:
            fake_host.exported.add("5-1.4.4.2")
        return fake_host.run(argv, **_kw)

    monkeypatch.setattr(usbip_linux, "_run", run)
    res = usbip_linux.ensure_exportable("5-1.4.4.2")
    assert res.ok
    assert "restarted" in res.stdout
    assert fake_host.restarted()


def test_ensure_exportable_reports_failure_when_never_exported(no_sleep, fake_host):
    res = usbip_linux.ensure_exportable("5-1.4.4.2")
    assert not res.ok
    assert "does not export" in res.stderr


def test_local_bind_restarts_when_bound_but_not_exported(no_sleep, fake_host, monkeypatch):
    # Bind succeeds but usbipd doesn't serve the busid -> heal by restarting usbipd.
    def run(argv, **_kw):
        if argv[:2] == ["usbipd", "-D"]:
            fake_host.exported.add("5-1.4.4.2")
        return fake_host.run(argv, **_kw)

    monkeypatch.setattr(usbip_linux, "_run", run)
    res = local.bind("5-1.4.4.2")
    assert res.ok
    assert fake_host.restarted()
    assert fake_host.probes > 0


def test_local_bind_skips_restart_when_daemon_postdates_bind(no_sleep, monkeypatch):
    # usbipd was started after this bind (e.g. ensure_usbipd just launched it):
    # no restart needed, and the device is already served.
    host = _FakeHost(exported={"5-1.4.4.2"})
    monkeypatch.setattr(usbip_linux, "_run", host.run)
    monkeypatch.setattr(local, "_DEMO", False)
    monkeypatch.setattr(usbip_linux, "usbipd_start_epoch", lambda: time.time() + 60)
    res = local.bind("5-1.4.4.2")
    assert res.ok
    assert host.probes > 0
    assert not host.restarted()


def test_local_bind_does_not_probe_when_bind_fails(no_sleep, monkeypatch):
    host = _FakeHost(bind_ok=False)
    monkeypatch.setattr(usbip_linux, "_run", host.run)
    monkeypatch.setattr(local, "_DEMO", False)
    res = local.bind("5-1.4.4.2")
    assert not res.ok
    assert "not found" in res.stderr
    assert host.probes == 0
