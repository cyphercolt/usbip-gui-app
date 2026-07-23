"""Node-to-node trust, Syncthing-style.

Two modes:
  * "locked" (default) — a peer must be explicitly paired before it can see devices or issue
    commands. Discovery still finds machines, but unpaired ones show as "pending" until approved.
  * "open"  — any node on the LAN is trusted; nothing to pair (frictionless, less safe).

Each node presents its own secret `node_key` on every node-to-node call; a peer that has stored that
key (via pairing) trusts the caller.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from ..config import state_dir

OPEN = "open"
LOCKED = "locked"


class TrustStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (state_dir() / "trust.json")
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        try:
            data = json.loads(self._path.read_text())
            data.setdefault("mode", LOCKED)  # secure by default: pairing required
            data.setdefault("trusted", {})
            data.setdefault("pending_in", {})
            data.setdefault("pending_out", {})
            return data
        except (OSError, json.JSONDecodeError):
            return {"mode": LOCKED, "trusted": {}, "pending_in": {}, "pending_out": {}}

    def _save(self) -> None:
        try:
            self._path.write_text(json.dumps(self._data, indent=2))
        except OSError:
            pass

    # ---- mode ----
    def mode(self) -> str:
        return self._data.get("mode", OPEN)

    def set_mode(self, mode: str) -> None:
        with self._lock:
            self._data["mode"] = LOCKED if mode == LOCKED else OPEN
            self._save()

    def locked(self) -> bool:
        return self.mode() == LOCKED

    # ---- verification ----
    def is_trusted(self, node_id: str | None, key: str | None) -> bool:
        if not node_id or not key:
            return False
        entry = self._data["trusted"].get(node_id)
        return bool(entry) and entry.get("key") == key

    # ---- reads ----
    def trusted(self) -> dict:
        return dict(self._data["trusted"])

    def pending_in(self) -> dict:
        return dict(self._data["pending_in"])

    # ---- mutations ----
    def add_trusted(self, node_id: str, name: str, key: str) -> None:
        with self._lock:
            self._data["trusted"][node_id] = {"name": name, "key": key}
            self._data["pending_in"].pop(node_id, None)
            self._save()

    def remove_trusted(self, node_id: str) -> None:
        with self._lock:
            self._data["trusted"].pop(node_id, None)
            self._save()

    def add_pending_in(
        self, node_id: str, name: str, key: str, host: str = "", port: int = 0
    ) -> None:
        with self._lock:
            if node_id not in self._data["trusted"]:
                self._data["pending_in"][node_id] = {
                    "name": name,
                    "key": key,
                    "host": host,
                    "port": port,
                }
                self._save()

    def pop_pending_in(self, node_id: str) -> dict | None:
        with self._lock:
            entry = self._data["pending_in"].pop(node_id, None)
            if entry:
                self._save()
            return entry

    # ---- outgoing pairing (we initiated) ----
    def add_pending_out(self, node_id: str) -> None:
        with self._lock:
            self._data["pending_out"][node_id] = True
            self._save()

    def has_pending_out(self, node_id: str) -> bool:
        return node_id in self._data["pending_out"]

    def pop_pending_out(self, node_id: str) -> bool:
        with self._lock:
            existed = self._data["pending_out"].pop(node_id, None) is not None
            if existed:
                self._save()
            return existed
