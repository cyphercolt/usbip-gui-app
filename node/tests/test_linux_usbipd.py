"""Linux usbipd ensure tests — verifiable without real hardware by faking the subprocess runner.
Covers the "is usbipd already running? yes -> leave it, no -> start it" behavior that keeps
peers able to attach to this machine's exports."""

from usbip_node.core import usbip_linux
from usbip_node.core.proc import CommandResult


def _fake_run(responses):
    """Build a _run replacement that maps argv prefixes to canned CommandResults."""
    calls: list[list[str]] = []

    def fake(argv, **_kw):
        calls.append(argv)
        for prefix, result in responses:
            if argv[: len(prefix)] == prefix:
                return result
        return CommandResult(True, "", "", 0)

    return fake, calls


def test_ensure_usbipd_noop_when_already_running(monkeypatch):
    fake, calls = _fake_run([(["pgrep", "-x", "usbipd"], CommandResult(True, "1234\n", "", 0))])
    monkeypatch.setattr(usbip_linux, "_run", fake)
    res = usbip_linux.ensure_usbipd()
    assert res.ok is True
    assert "already running" in res.stdout
    # Must not try to start a second usbipd (e.g. a Pi that had one before this app existed).
    assert not any(call[0] == "usbipd" for call in calls)


def test_ensure_usbipd_starts_when_not_running(monkeypatch):
    state = {"up": False}

    def fake(argv, **_kw):
        if argv[:3] == ["pgrep", "-x", "usbipd"]:
            return CommandResult(state["up"], "4321\n" if state["up"] else "", "", 0 if state["up"] else 1)
        if argv[:2] == ["usbipd", "-D"]:
            state["up"] = True
            return CommandResult(True, "", "", 0)
        return CommandResult(True, "", "", 0)  # modprobe

    monkeypatch.setattr(usbip_linux, "_run", fake)
    res = usbip_linux.ensure_usbipd()
    assert res.ok is True
    assert "started" in res.stdout


def test_ensure_usbipd_reports_start_failure(monkeypatch):
    fake, _calls = _fake_run(
        [
            (["pgrep", "-x", "usbipd"], CommandResult(False, "", "", 1)),
            (["usbipd", "-D"], CommandResult(False, "", "usbipd: must be run as root", 1)),
        ]
    )
    monkeypatch.setattr(usbip_linux, "_run", fake)
    res = usbip_linux.ensure_usbipd()
    assert res.ok is False
    assert "could not start usbipd" in res.stderr
    assert "must be run as root" in res.stderr


def test_ensure_usbipd_detects_immediate_exit(monkeypatch):
    # usbipd -D returns 0 but no process is around afterwards (e.g. crashed on daemonize).
    fake, _calls = _fake_run([(["pgrep", "-x", "usbipd"], CommandResult(False, "", "", 1))])
    monkeypatch.setattr(usbip_linux, "_run", fake)
    res = usbip_linux.ensure_usbipd()
    assert res.ok is False
    assert "exited right after start" in res.stderr
