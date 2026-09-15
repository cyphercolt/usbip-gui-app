"""Run the node service: `python -m usbip_node` or the `usbip-node` console script."""

from __future__ import annotations

import sys

import uvicorn

from .config import NodeConfig, state_dir
from .server import create_app


def _redirect_missing_std_streams() -> bool:
    """Give pythonw.exe (the Windows boot task) somewhere to write. It starts with
    sys.stdout/stderr = None, and uvicorn's log formatter calls .isatty() on them, so startup
    crashes. Returns True when output now goes to <state dir>/usbip-node.log -- the only place to
    read the node's output on Windows. Truncated each start so it can't grow without bound."""
    if sys.stdout is not None and sys.stderr is not None:
        return False
    log = open(state_dir() / "usbip-node.log", "w", buffering=1, encoding="utf-8")
    sys.stdout = sys.stdout or log
    sys.stderr = sys.stderr or log
    return True


def main() -> None:
    headless = _redirect_missing_std_streams()
    cfg = NodeConfig.load()
    app = create_app(cfg)
    print(f"usbip-node '{cfg.display_name}' ({cfg.node_id}) on http://{cfg.host}:{cfg.port}")
    # The UI polls constantly; per-request access lines would bloat the headless log file.
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info", access_log=not headless)


if __name__ == "__main__":
    main()
