"""Persistent list of peer nodes (their API base URLs).

Phase 1: peers are added manually (POST /api/peers). Phase 2 populates this automatically from
mDNS discovery. Stored as JSON in the node's state dir.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import state_dir


class PeerRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (state_dir() / "peers.json")
        self._urls: list[str] = self._load()

    def _load(self) -> list[str]:
        try:
            data = json.loads(self._path.read_text())
            if isinstance(data, list):
                return [str(u).rstrip("/") for u in data]
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def _save(self) -> None:
        try:
            self._path.write_text(json.dumps(self._urls))
        except OSError:
            pass

    def urls(self) -> list[str]:
        return list(self._urls)

    def add(self, url: str) -> None:
        url = url.rstrip("/")
        if url and url not in self._urls:
            self._urls.append(url)
            self._save()

    def remove(self, url: str) -> None:
        url = url.rstrip("/")
        if url in self._urls:
            self._urls.remove(url)
            self._save()
