"""Tiny in-process pub/sub so WebSocket clients get an immediate push after any state change,
instead of only on a timer. Each subscriber gets a 1-slot queue; publish() nudges them all.
"""

from __future__ import annotations

import asyncio


class StateBus:
    def __init__(self) -> None:
        self._subs: set[asyncio.Queue[None]] = set()

    def subscribe(self) -> "asyncio.Queue[None]":
        q: asyncio.Queue[None] = asyncio.Queue(maxsize=1)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: "asyncio.Queue[None]") -> None:
        self._subs.discard(q)

    def publish(self) -> None:
        for q in self._subs:
            if q.empty():
                q.put_nowait(None)
