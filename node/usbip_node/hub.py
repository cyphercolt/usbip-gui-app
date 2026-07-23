"""Hub role: talk to peer nodes over HTTP and orchestrate cross-machine attach.

Every node can act as hub for the browser that connected to it. It aggregates its own state with
each peer's `/api/state`, and orchestrates attach by calling the source's bind endpoint then the
destination's attach endpoint.

On every node-to-node call it presents this node's identity (X-Node-Id / X-Node-Key). In locked
mode a peer only answers if it has paired with us; otherwise we fall back to /api/identity and show
that peer as "pending" (discovered but not yet approved).
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from .core.models import CommandResponse, NodeInfo, NodeState

_TIMEOUT = httpx.Timeout(8.0)


def identity_headers(node_id: str, node_key: str) -> dict[str, str]:
    return {"X-Node-Id": node_id, "X-Node-Key": node_key}


def _host_port(url: str) -> tuple[str, int]:
    p = urlparse(url)
    return p.hostname or "", p.port or 4820


async def fetch_peer_state(
    client: httpx.AsyncClient, url: str, node_id: str, node_key: str
) -> NodeState | None:
    """A peer's full state if paired/open; a 'pending' stub if it's reachable but won't share
    (locked + not paired); None if unreachable."""
    headers = identity_headers(node_id, node_key)
    try:
        resp = await client.get(f"{url}/api/state", headers=headers, timeout=_TIMEOUT)
        if resp.status_code == 200:
            return NodeState.model_validate(resp.json())
        if resp.status_code in (401, 403):
            return await _pending_stub(client, url)
        return None
    except (httpx.HTTPError, ValueError):
        return None


async def _pending_stub(client: httpx.AsyncClient, url: str) -> NodeState | None:
    try:
        resp = await client.get(f"{url}/api/identity", timeout=_TIMEOUT)
        resp.raise_for_status()
        ident = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    host, port = _host_port(url)
    return NodeState(
        info=NodeInfo(
            node_id=ident["node_id"],
            display_name=ident["display_name"],
            os_name=ident.get("os_name", ""),
            version="",
            host=host,
            port=port,
            reachable=True,
            paired=False,
        )
    )


async def post_command(
    client: httpx.AsyncClient,
    url: str,
    path: str,
    payload: dict,
    node_id: str,
    node_key: str,
) -> CommandResponse:
    try:
        resp = await client.post(
            f"{url}{path}",
            json=payload,
            headers=identity_headers(node_id, node_key),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return CommandResponse.model_validate(resp.json())
    except httpx.HTTPError as e:
        return CommandResponse(ok=False, message=f"peer {url} unreachable: {e}")
    except ValueError as e:
        return CommandResponse(ok=False, message=f"bad response from {url}: {e}")


async def gather_fleet(
    self_state: NodeState, peer_urls: list[str], node_id: str, node_key: str
) -> tuple[list[NodeState], dict[str, str]]:
    """Aggregate self + peers, de-duplicated by node_id. Returns (fleet, node_id -> base_url)."""
    fleet = [self_state]
    id_to_url: dict[str, str] = {}
    seen = {self_state.info.node_id}
    async with httpx.AsyncClient() as client:
        for url in peer_urls:
            state = await fetch_peer_state(client, url, node_id, node_key)
            if state is None:
                continue
            nid = state.info.node_id
            if nid in seen:
                id_to_url.setdefault(nid, url)
                continue
            seen.add(nid)
            id_to_url[nid] = url
            fleet.append(state)
    return fleet, id_to_url
