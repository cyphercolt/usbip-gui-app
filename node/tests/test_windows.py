"""Windows backend parser test — verifiable without real Windows by feeding canned `usbipd list`
output. (Real end-to-end Windows behavior still needs hardware verification.)"""

from usbip_node.core import usbip_windows
from usbip_node.core.proc import CommandResult

SAMPLE = """\
Connected:
BUSID  VID:PID    DEVICE                                                        STATE
1-4    1234:5678  USB Input Device                                              Not shared
2-1    abcd:ef01  USB Mass Storage Device                                       Shared
5-2    28de:1142  Valve Wireless Steam Controller                               Attached

Persisted:
GUID                                  DEVICE
"""


def test_parse_usbipd_list(monkeypatch):
    monkeypatch.setattr(
        usbip_windows, "_run", lambda *_a, **_k: CommandResult(True, SAMPLE, "", 0)
    )
    devices = usbip_windows.list_shareable()
    assert len(devices) == 3

    by_busid = {d.busid: d for d in devices}
    assert by_busid["1-4"].description == "USB Input Device (1234:5678)"
    assert by_busid["1-4"].shared is False
    assert by_busid["2-1"].shared is True
    assert by_busid["5-2"].shared is True  # "Attached" counts as in-use/shared
    assert "Steam Controller" in by_busid["5-2"].description


def test_bind_rejects_bad_busid(monkeypatch):
    monkeypatch.setattr(
        usbip_windows, "_run", lambda *_a, **_k: CommandResult(True, "", "", 0)
    )
    res = usbip_windows.bind("1-4; shutdown")
    assert res.ok is False
    assert "invalid busid" in res.stderr
