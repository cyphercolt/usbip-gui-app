"""Reconcile-loop tests: stale-import cleanup and orphan-bind cleanup, with a faked peer HTTP
client and faked local usbip layer — no hardware, no network."""

import httpx
import pytest

from usbip_node import autoreconnect
from usbip_node.autoreconnect import _drop_stale_imports, _free_orphaned_binds
from usbip_node.config import NodeConfig
from usbip_node.core import local
from usbip_node.core.models import AttachedDevice
from usbip_node.core.proc import CommandResult


CFG = NodeConfig(
    node_id="me", node_key="k", display_name="me", port=4820, advertise_host="10.0.0.1"
)


class FakeResp:
    def __init__(self, data, status=200):
        self._data = data
        self._status = status

    def raise_for_status(self):
        if self._status != 200:
            raise httpx.HTTPStatusError("boom", request=None, response=None)

    def json(self):
        return self._data


class FakeClient:
    """Maps URL -> FakeResp | Exception. Unknown URLs raise ConnectError."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    async def get(self, url, **_kw):
        self.calls.append(url)
        hit = self.routes.get(url)
        if hit is None:
            raise httpx.ConnectError("unreachable")
        if isinstance(hit, Exception):
            raise hit
        return hit


def _attached(host="10.0.0.2", busid="1-1", port="00"):
    return [AttachedDevice(port=port, busid=busid, description="dev", remote_host=host)]


@pytest.fixture()
def detached(monkeypatch):
    calls = []
    monkeypatch.setattr(local, "detach", lambda port: calls.append(port) or CommandResult(True, "", "", 0))
    return calls


@pytest.fixture()
def unbound(monkeypatch):
    calls = []
    monkeypatch.setattr(local, "unbind", lambda busid: calls.append(busid) or CommandResult(True, "", "", 0))
    return calls


async def test_stale_import_detached_after_strikes(detached):
    client = FakeClient({
        "http://10.0.0.2:4820/api/local/bound": FakeResp({"running": True, "busids": []}),
    })
    strikes = {}
    for i in range(autoreconnect._STALE_STRIKES - 1):
        assert not await _drop_stale_imports(CFG, client, _attached(), strikes)
        assert detached == []  # patience: no detach before the strike threshold
    assert await _drop_stale_imports(CFG, client, _attached(), strikes)
    assert detached == ["00"]
    assert strikes == {}


async def test_healthy_import_resets_strikes(detached):
    stale = FakeResp({"running": True, "busids": []})
    healthy = FakeResp({"running": True, "busids": ["1-1"]})
    strikes = {}
    await _drop_stale_imports(CFG, FakeClient({"http://10.0.0.2:4820/api/local/bound": stale}), _attached(), strikes)
    assert strikes != {}
    await _drop_stale_imports(CFG, FakeClient({"http://10.0.0.2:4820/api/local/bound": healthy}), _attached(), strikes)
    assert strikes == {}
    assert detached == []


async def test_unreachable_or_unknown_source_is_left_alone(detached):
    strikes = {}
    # unreachable source: no evidence, no strikes
    await _drop_stale_imports(CFG, FakeClient({}), _attached(), strikes)
    # platform that can't report (busids=None): same
    client = FakeClient({"http://10.0.0.2:4820/api/local/bound": FakeResp({"running": True, "busids": None})})
    await _drop_stale_imports(CFG, client, _attached(), strikes)
    assert strikes == {} and detached == []


async def test_dead_usbipd_counts_as_stale(detached):
    client = FakeClient({
        "http://10.0.0.2:4820/api/local/bound": FakeResp({"running": False, "busids": ["1-1"]}),
    })
    strikes = {}
    for _ in range(autoreconnect._STALE_STRIKES):
        await _drop_stale_imports(CFG, client, _attached(), strikes)
    assert detached == ["00"]


async def test_orphan_unbound_when_all_peers_visible(monkeypatch, unbound):
    monkeypatch.setattr(local, "bound_busids", lambda: ["1-1"])
    monkeypatch.setattr(autoreconnect, "local_addresses", lambda _h: ["10.0.0.1"])
    client = FakeClient({"http://10.0.0.9:4820/api/state": FakeResp({"attached": []})})
    strikes = {}
    for _ in range(autoreconnect._ORPHAN_STRIKES - 1):
        assert not await _free_orphaned_binds(CFG, client, ["http://10.0.0.9:4820"], [], strikes)
        assert unbound == []
    assert await _free_orphaned_binds(CFG, client, ["http://10.0.0.9:4820"], [], strikes)
    assert unbound == ["1-1"]


async def test_orphan_kept_when_a_peer_claims_it(monkeypatch, unbound):
    monkeypatch.setattr(local, "bound_busids", lambda: ["1-1"])
    monkeypatch.setattr(autoreconnect, "local_addresses", lambda _h: ["10.0.0.1"])
    peer_state = {"attached": [{"port": "00", "busid": "1-1", "description": "d", "remote_host": "10.0.0.1"}]}
    client = FakeClient({"http://10.0.0.9:4820/api/state": FakeResp(peer_state)})
    strikes = {}
    for _ in range(autoreconnect._ORPHAN_STRIKES + 1):
        await _free_orphaned_binds(CFG, client, ["http://10.0.0.9:4820"], [], strikes)
    assert unbound == [] and strikes == {}


async def test_orphan_kept_when_any_peer_unreachable(monkeypatch, unbound):
    # A sleeping laptop can't report its attachment — never pull the device out from under it.
    monkeypatch.setattr(local, "bound_busids", lambda: ["1-1"])
    monkeypatch.setattr(autoreconnect, "local_addresses", lambda _h: ["10.0.0.1"])
    client = FakeClient({"http://10.0.0.9:4820/api/state": FakeResp({"attached": []})})
    strikes = {}
    for _ in range(autoreconnect._ORPHAN_STRIKES + 1):
        await _free_orphaned_binds(
            CFG, client, ["http://10.0.0.9:4820", "http://10.0.0.7:4820"], [], strikes
        )
    assert unbound == []


def test_bound_busids_filters_sysfs_names(monkeypatch):
    from usbip_node.core import usbip_linux

    monkeypatch.setattr(
        usbip_linux.os, "listdir", lambda _p: ["1-1", "3-2.4", "bind", "unbind", "module", "uevent"]
    )
    assert usbip_linux.bound_busids() == ["1-1", "3-2.4"]
