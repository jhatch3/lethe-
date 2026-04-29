
"""Per-job event bus.

Each job has its own asyncio.Queue. The runner pushes events; the SSE endpoint
consumes them. Events carry no bill content — only structured progress.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Event:
    type: str
    job_id: str
    ts: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> Dict[str, Any]:
        return {
            "event": self.type,
            "data": {
                "job_id": self.job_id,
                "ts": self.ts,
                **self.data,
            },
        }


class EventBus:
    def __init__(self) -> None:
        self._queues: Dict[str, asyncio.Queue[Event]] = {}
        # Global fan-out subscribers (CLI dashboard, etc.). Each subscriber gets
        # its own queue; events are broadcast to every queue on publish().
        self._global_subs: list[asyncio.Queue[Event]] = []
        self._lock = asyncio.Lock()

    async def open(self, job_id: str) -> asyncio.Queue[Event]:
        async with self._lock:
            q = self._queues.get(job_id)
            if q is None:
                q = asyncio.Queue()
                self._queues[job_id] = q
            return q

    async def publish(self, event: Event) -> None:
        async with self._lock:
            q = self._queues.get(event.job_id)
            global_subs = list(self._global_subs)
        if q is not None:
            await q.put(event)
        # Fan out to global subscribers — never blocks the per-job path even
        # if a slow subscriber's queue is full (we drop their oldest event).
        for sub in global_subs:
            try:
                sub.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    sub.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    sub.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    async def close(self, job_id: str) -> None:
        async with self._lock:
            q = self._queues.pop(job_id, None)
        if q is not None:
            # signal end-of-stream to any subscriber
            await q.put(Event(type="__end__", job_id=job_id))

    async def subscriber(self, job_id: str) -> Optional[asyncio.Queue[Event]]:
        async with self._lock:
            return self._queues.get(job_id)

    async def subscribe_global(self, maxsize: int = 256) -> asyncio.Queue[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        async with self._lock:
            self._global_subs.append(q)
        return q

    async def unsubscribe_global(self, q: asyncio.Queue[Event]) -> None:
        async with self._lock:
            if q in self._global_subs:
                self._global_subs.remove(q)


bus = EventBus()