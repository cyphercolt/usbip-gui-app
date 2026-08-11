"""API smoke tests + validators. Each test gets an isolated state dir so the persistent peer
registry never leaks between tests or reaches out to dead peer URLs."""

import pytest
from fastapi.testclient import TestClient

from usbip_node.config import NodeConfig
from usbip_node.core import validate
from usbip_node.core.models import CommandResponse, NodeInfo, NodeState
from usbip_node.core.proc import CommandResult
from usbip_node.server import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("USBIP_NODE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("USBIP_NODE_DISABLE_MDNS", "1")
    cfg = NodeConfig(
        node_id="abc123",
        node_key="mykey",
        display_name="testnode",
        port=4820,
        advertise_host="10.0.0.9",
        os_name="linux",
    )
    return TestClient(create_app(cfg))


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_info(client):
    body = client.get("/api/info").json()
    assert body["node_id"] == "abc123"
    assert body["host"] == "10.0.0.9"


def test_state_shape(client):
    client.post("/api/security/mode", json={"mode": "open"})
    body = client.get("/api/state").json()
    assert set(body) >= {"info", "shareable", "attached"}
    assert isinstance(body["shareable"], list)


def test_info_reports_all_hosts(client):
    body = client.get("/api/info").json()
    # advertise_host must come first; the rest are whatever interfaces the test machine has
    assert body["hosts"][0] == "10.0.0.9"


def test_local_bound_shape(client):
    client.post("/api/security/mode", json={"mode": "open"})
    body = client.get("/api/local/bound").json()
    assert isinstance(body["running"], bool)
    assert body["busids"] is None or isinstance(body["busids"], list)


def test_fleet_contains_self(client):
    fleet = client.get("/api/fleet").json()
    assert len(fleet) == 1
    assert fleet[0]["info"]["node_id"] == "abc123"


def test_peer_registry_roundtrip(client):
    assert client.get("/api/peers").json() == []
    client.post("/api/peers", json={"url": "http://10.0.0.5:4820"})
    assert client.get("/api/peers").json() == ["http://10.0.0.5:4820"]
    client.request("DELETE", "/api/peers", json={"url": "http://10.0.0.5:4820"})
    assert client.get("/api/peers").json() == []


def test_local_bind_rejects_bad_busid(client):
    client.post("/api/security/mode", json={"mode": "open"})
    r = client.post("/api/local/bind", json={"busid": "2-1; rm -rf /"})
    body = r.json()
    assert body["ok"] is False
    assert "invalid busid" in body["message"]


def test_local_attach_rejects_bad_host(client):
    client.post("/api/security/mode", json={"mode": "open"})
    r = client.post("/api/local/attach", json={"remote_host": "bad host!", "busid": "2-1"})
    assert r.json()["ok"] is False


def test_orchestrate_unknown_nodes_404(client):
    r = client.post(
        "/api/attach",
        json={"source_node_id": "nope", "busid": "2-1", "dest_node_id": "nada"},
    )
    assert r.status_code == 404


def test_release_unknown_node_404(client):
    r = client.post("/api/detach", json={"dest_node_id": "nope", "port": "00"})
    assert r.status_code == 404


def test_autoreconnect_arm_disarm(client):
    client.post("/api/security/mode", json={"mode": "open"})
    store = client.app.state.autoreconnect
    r = client.post(
        "/api/local/autoreconnect",
        json={"remote_host": "192.168.2.144", "busid": "1-1.2", "enabled": True},
    )
    assert r.json()["ok"] is True
    assert store.contains("192.168.2.144", "1-1.2")
    client.post(
        "/api/local/autoreconnect",
        json={"remote_host": "192.168.2.144", "busid": "1-1.2", "enabled": False},
    )
    assert not store.contains("192.168.2.144", "1-1.2")


def test_security_defaults_locked(client):
    body = client.get("/api/security").json()
    assert body["mode"] == "locked"  # secure by default
    assert body["this_node"]["node_id"] == "abc123"
    # locked default: node-to-node endpoints reject unpaired callers
    assert client.get("/api/state").status_code == 401
    assert client.post("/api/local/bind", json={"busid": "2-1"}).status_code == 401


def test_open_mode_allows_unpaired(client):
    client.post("/api/security/mode", json={"mode": "open"})
    assert client.get("/api/state").status_code == 200
    assert client.post("/api/local/bind", json={"busid": "2-1"}).status_code == 200


def test_pairing_flow_locked(client):
    client.post("/api/security/mode", json={"mode": "locked"})
    # a peer requests pairing -> shows as pending
    req = client.post(
        "/api/pair/request",
        json={"node_id": "peerX", "display_name": "peer", "key": "pk",
              "host": "127.0.0.1", "port": 1},
    )
    assert req.json()["message"] == "pending"
    assert any(p["node_id"] == "peerX" for p in client.get("/api/security").json()["pending"])

    # user approves it (callback to the peer will fail silently — no server on :1)
    client.post("/api/pair/accept", json={"node_id": "peerX"})
    sec = client.get("/api/security").json()
    assert any(t["node_id"] == "peerX" for t in sec["trusted"])
    assert sec["pending"] == []

    # now the paired peer can call gated endpoints with its identity
    ok = client.get("/api/state", headers={"X-Node-Id": "peerX", "X-Node-Key": "pk"})
    assert ok.status_code == 200
    # wrong key still rejected
    bad = client.get("/api/state", headers={"X-Node-Id": "peerX", "X-Node-Key": "nope"})
    assert bad.status_code == 401


def test_busid_validation():
    assert validate.is_valid_busid("2-1.4")
    assert not validate.is_valid_busid("2-1; rm -rf /")


def test_host_validation():
    assert validate.is_valid_host("192.168.2.216")
    assert validate.is_valid_host("pi.local")
    assert not validate.is_valid_host("bad host!")


def test_orchestrate_uses_api_url_host_not_advertise_host(client, monkeypatch):
    """Regression for 3-device 'tcp connect' failures: the destination must attach to the
    address we actually reached the source API on, not the source's self-reported advertise_host.
    A machine with multiple interfaces may advertise an IP a peer cannot reach for usbip."""
    import usbip_node.api.routes as routes
    import usbip_node.core.local as local

    client.post("/api/security/mode", json={"mode": "open"})
    client.post("/api/peers", json={"url": "http://192.168.2.5:4820"})

    captured: dict = {}

    def fake_bind(busid: str) -> CommandResult:
        captured["bind_busid"] = busid
        return CommandResult(True, "", "", 0)

    def fake_attach(remote_host: str, busid: str) -> CommandResult:
        captured["attach_host"] = remote_host
        captured["attach_busid"] = busid
        return CommandResult(True, "", "", 0)

    async def fake_post_command(*args, **kwargs) -> CommandResponse:
        captured["post_path"] = args[2]
        captured["post_payload"] = args[3]
        return CommandResponse(ok=True, message="bound")

    monkeypatch.setattr(local, "bind", fake_bind)
    monkeypatch.setattr(local, "attach", fake_attach)
    monkeypatch.setattr(routes, "post_command", fake_post_command)

    async def fake_gather(self_state, peer_urls, node_id, node_key):
        fleet = [
            self_state,
            NodeState(
                info=NodeInfo(
                    node_id="peer1",
                    display_name="peer",
                    os_name="linux",
                    version="3.0.0",
                    host="10.0.0.5",  # advertised host; intentionally unreachable from dest
                    port=4820,
                    reachable=True,
                    paired=True,
                ),
                shareable=[],
                attached=[],
            ),
        ]
        return fleet, {"peer1": "http://192.168.2.5:4820"}

    monkeypatch.setattr(routes, "gather_fleet", fake_gather)

    r = client.post(
        "/api/attach",
        json={"source_node_id": "peer1", "busid": "2-1", "dest_node_id": "abc123"},
    )
    assert r.status_code == 200, r.text
    assert captured.get("post_path") == "/api/local/bind"
    assert captured.get("post_payload") == {"busid": "2-1"}
    assert captured.get("attach_busid") == "2-1"
    assert captured.get("attach_host") == "192.168.2.5", (
        f"expected the API-reachable host 192.168.2.5, got {captured.get('attach_host')!r}"
    )
