"""Run the node service: `python -m usbip_node` or the `usbip-node` console script."""

from __future__ import annotations

import uvicorn

from .config import NodeConfig
from .server import create_app


def main() -> None:
    cfg = NodeConfig.load()
    app = create_app(cfg)
    print(f"usbip-node '{cfg.display_name}' ({cfg.node_id}) on http://{cfg.host}:{cfg.port}")
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
