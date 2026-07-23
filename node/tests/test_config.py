"""Advertise-IP selection: must prefer the real LAN NIC and reject VPN (100.64/10) + docker/bridges."""

from usbip_node.config import _score_ip


def test_lan_beats_vpn_and_docker():
    lan = _score_ip("enp10s0", "192.168.2.216")
    vpn = _score_ip("nordlynx", "100.117.80.6")  # NordLynx/Tailscale CGNAT range
    docker = _score_ip("docker0", "172.17.0.1")
    bridge = _score_ip("br-abc123", "172.18.0.1")
    assert lan > vpn
    assert lan > docker
    assert lan > bridge
    assert vpn < 0 and docker < 0 and bridge < 0


def test_prefers_192_over_10():
    assert _score_ip("eth0", "192.168.1.5") >= _score_ip("eth0", "10.0.0.5")
