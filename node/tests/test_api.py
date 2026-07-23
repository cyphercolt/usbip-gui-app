"""Phase 0 API smoke tests + validator tests."""

from fastapi.testclient import TestClient

from usbip_node.config import NodeConfig
from usbip_node.core import validate
from usbip_node.server import create_app


def _client() -> TestClient:
    cfg = NodeConfig(node_id="abc123", display_name="testnode", port=4820, os_name="linux")
    return TestClient(create_app(cfg))


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_info():
    r = _client().get("/api/info")
    assert r.status_code == 200
    body = r.json()
    assert body["node_id"] == "abc123"
    assert body["display_name"] == "testnode"


def test_state_shape():
    r = _client().get("/api/state")
    assert r.status_code == 200
    body = r.json()
    assert "info" in body and "shareable" in body and "attached" in body
    assert isinstance(body["shareable"], list)
    assert isinstance(body["attached"], list)


def test_fleet_contains_self():
    r = _client().get("/api/fleet")
    assert r.status_code == 200
    fleet = r.json()
    assert len(fleet) == 1
    assert fleet[0]["info"]["node_id"] == "abc123"


def test_busid_validation():
    assert validate.is_valid_busid("2-1.4")
    assert validate.is_valid_busid("3-1")
    assert not validate.is_valid_busid("2-1; rm -rf /")
    assert not validate.is_valid_busid("")


def test_host_validation():
    assert validate.is_valid_host("192.168.2.216")
    assert validate.is_valid_host("pi.local")
    assert not validate.is_valid_host("bad host!")
