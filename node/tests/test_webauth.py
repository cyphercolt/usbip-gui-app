"""Web-UI login: set credential -> browser endpoints require a session -> login unlocks. Plus TOTP."""

import pytest
from fastapi.testclient import TestClient

from usbip_node.config import NodeConfig
from usbip_node.server import create_app
from usbip_node.webauth import WebAuthStore, totp_code


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("USBIP_NODE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("USBIP_NODE_DISABLE_MDNS", "1")
    cfg = NodeConfig(node_id="n1", node_key="k1", display_name="n1", os_name="linux")
    return TestClient(create_app(cfg))


def test_no_auth_by_default(client):
    assert client.get("/api/auth/status").json()["enabled"] is False
    # browser endpoints open when no login is configured
    assert client.get("/api/fleet").status_code == 200


def test_login_gates_browser_endpoints(client):
    client.post("/api/auth/set", json={"username": "colt", "password": "hunter2"})
    # setter is auto-logged-in (cookie on the client); status reflects enabled+authed
    st = client.get("/api/auth/status").json()
    assert st["enabled"] is True and st["authed"] is True

    # a fresh client (no cookie) is locked out of browser endpoints but can still see status/login
    fresh = TestClient(client.app)
    fresh.cookies.clear()
    assert fresh.get("/api/fleet").status_code == 401
    assert fresh.get("/api/auth/status").status_code == 200
    assert fresh.post("/api/auth/login", json={"username": "colt", "password": "wrong"}).status_code == 401
    ok = fresh.post("/api/auth/login", json={"username": "colt", "password": "hunter2"})
    assert ok.status_code == 200
    assert fresh.get("/api/fleet").status_code == 200


def test_totp_required_when_enabled(client):
    resp = client.post(
        "/api/auth/set",
        json={"username": "colt", "password": "pw", "totp_enabled": True},
    ).json()
    secret = resp["totp_secret"]
    assert secret and resp["otpauth_uri"].startswith("otpauth://")

    fresh = TestClient(client.app)
    fresh.cookies.clear()
    # password alone is rejected without a code
    assert fresh.post("/api/auth/login", json={"username": "colt", "password": "pw"}).status_code == 401
    good = fresh.post(
        "/api/auth/login",
        json={"username": "colt", "password": "pw", "code": totp_code(secret)},
    )
    assert good.status_code == 200


def test_session_survives_store_restart(tmp_path):
    """Sessions must be persisted so a service restart doesn't force re-login."""
    path = tmp_path / "webauth.json"
    store = WebAuthStore(path)
    store.set_credential("colt", "hunter2", totp_enabled=False)
    token = store.create_session()
    assert store.valid_session(token)

    # Simulate service restart: new WebAuthStore instance reads the same file.
    restarted = WebAuthStore(path)
    assert restarted.valid_session(token)

    # Logging out invalidates the token on the running instance and persists it,
    # so a future restart won't accept it.
    restarted.drop_session(token)
    assert not restarted.valid_session(token)
    future = WebAuthStore(path)
    assert not future.valid_session(token)
