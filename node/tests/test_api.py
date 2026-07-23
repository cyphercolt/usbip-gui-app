"""API smoke tests + validators. Each test gets an isolated state dir so the persistent peer
registry never leaks between tests or reaches out to dead peer URLs."""

import pytest
from fastapi.testclient import TestClient

from usbip_node.config import NodeConfig
from usbip_node.core import validate
from usbip_node.server import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("USBIP_NODE_STATE_DIR", str(tmp_path))
    cfg = NodeConfig(
        node_id="abc123",
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
    body = client.get("/api/state").json()
    assert set(body) >= {"info", "shareable", "attached"}
    assert isinstance(body["shareable"], list)


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
    r = client.post("/api/local/bind", json={"busid": "2-1; rm -rf /"})
    body = r.json()
    assert body["ok"] is False
    assert "invalid busid" in body["message"]


def test_local_attach_rejects_bad_host(client):
    r = client.post("/api/local/attach", json={"remote_host": "bad host!", "busid": "2-1"})
    assert r.json()["ok"] is False


def test_orchestrate_unknown_nodes_404(client):
    r = client.post(
        "/api/attach",
        json={"source_node_id": "nope", "busid": "2-1", "dest_node_id": "nada"},
    )
    assert r.status_code == 404


def test_token_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("USBIP_NODE_STATE_DIR", str(tmp_path))
    cfg = NodeConfig(node_id="tok", display_name="t", token="s3cret", os_name="linux")
    c = TestClient(create_app(cfg))
    # command endpoints require the token now
    assert c.post("/api/local/bind", json={"busid": "2-1"}).status_code == 401
    ok = c.post(
        "/api/local/bind",
        json={"busid": "2-1"},
        headers={"Authorization": "Bearer s3cret"},
    )
    assert ok.status_code == 200
    # read-only endpoints stay open
    assert c.get("/api/state").status_code == 200


def test_busid_validation():
    assert validate.is_valid_busid("2-1.4")
    assert not validate.is_valid_busid("2-1; rm -rf /")


def test_host_validation():
    assert validate.is_valid_host("192.168.2.216")
    assert validate.is_valid_host("pi.local")
    assert not validate.is_valid_host("bad host!")
