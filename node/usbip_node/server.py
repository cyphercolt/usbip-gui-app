"""Assemble the FastAPI app: API routes + static web UI (same origin, plain HTTP on the LAN)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api.routes import build_router
from .config import NodeConfig
from .events import StateBus
from .peers import PeerRegistry

# Location of the built web app (Vite outputs to web/dist). Overridable for dev.
_WEB_DIST_CANDIDATES = [
    Path(__file__).resolve().parent.parent.parent / "web" / "dist",
    Path("/opt/usbip-node/web"),
]


def _find_web_dist() -> Path | None:
    for p in _WEB_DIST_CANDIDATES:
        if p.is_dir() and (p / "index.html").exists():
            return p
    return None


def create_app(cfg: NodeConfig | None = None) -> FastAPI:
    cfg = cfg or NodeConfig.load()
    app = FastAPI(title="usbip-node", version=__version__)
    bus = StateBus()
    registry = PeerRegistry()
    app.state.config = cfg
    app.state.bus = bus
    app.state.peers = registry
    app.include_router(build_router(cfg, bus, registry))

    web_dist = _find_web_dist()
    if web_dist is not None:
        # Serve hashed assets, and fall back to index.html for the SPA routes.
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

        @app.get("/")
        def _index() -> FileResponse:
            return FileResponse(web_dist / "index.html")

        @app.get("/{full_path:path}")
        def _spa(full_path: str) -> FileResponse:
            candidate = web_dist / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(web_dist / "index.html")

    return app
