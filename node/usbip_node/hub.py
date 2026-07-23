"""Hub role: talk to peer nodes over HTTP and orchestrate cross-machine attach.

Every node can act as hub for the browser that connected to it. It aggregates its own state with
each peer's `/api/state`, and orchestrates attach by calling the source's bind endpoint then the
destination's attach endpoint.
"""

from __future__ import annotations

import httpx

from .core.models import CommandResponse, NodeState

_TIMEOUT = httpx.Timeout(8.0)


def _auth_headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


async def fetch_peer_state(client: httpx.AsyncClient, url: str) -> NodeState | None:
    """Return a peer's NodeState, or a stub marked unreachable if it can't be reached."""
    try:
        resp = await client.get(f"{url}/api/state", timeout=_TIMEOUT)
        resp.raise_for_status()
        return NodeState.model_validate(resp.json())
    except (httpx.HTTPError, ValueError):
        return None


async def post_command(
    client: httpx.AsyncClient, url: str, path: str, payload: dict, token: str | None
) -> CommandResponse:
    try:
        resp = await client.post(
            f"{url}{path}", json=payload, headers=_auth_headers(token), timeout=_TIMEOUT
        )
        resp.raise_for_status()
        return CommandResponse.model_validate(resp.json())
    except httpx.HTTPError as e:
        return CommandResponse(ok=False, message=f"peer {url} unreachable: {e}")
    except ValueError as e:
        return CommandResponse(ok=False, message=f"bad response from {url}: {e}")


async def gather_fleet(
    self_state: NodeState, peer_urls: list[str]
) -> tuple[list[NodeState], dict[str, str]]:
    """Aggregate self + peers, de-duplicated by node_id (a node can be reachable via both a
    manual URL and mDNS). Returns (fleet, node_id -> base_url for reachable peers)."""
    fleet = [self_state]
    id_to_url: dict[str, str] = {}
    seen = {self_state.info.node_id}
    async with httpx.AsyncClient() as client:
        for url in peer_urls:
            state = await fetch_peer_state(client, url)
            if state is None:
                continue
            nid = state.info.node_id
            if nid in seen:
                id_to_url.setdefault(nid, url)  # already have this node; just remember a URL
                continue
            seen.add(nid)
            id_to_url[nid] = url
            fleet.append(state)
    return fleet, id_to_url
