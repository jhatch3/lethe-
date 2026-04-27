"""Rolling timing stats per pipeline stage.

Keeps the last N durations per stage and exposes mean / p50 / p95.
No PHI here — only stage names and millisecond integers.
"""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Deque, Dict


class TimingStats:
    def __init__(self, window: int = 50) -> None:
        self._window = window
        self._stages: Dict[str, Deque[int]] = {}
        self._jobs: Deque[int] = deque(maxlen=window)
        self._lock = asyncio.Lock()

    async def record_stage(self, stage: str, duration_ms: int) -> None:
        async with self._lock:
            buf = self._stages.setdefault(stage, deque(maxlen=self._window))
            buf.append(duration_ms)

    async def record_job(self, total_ms: int) -> None:
        async with self._lock:
            self._jobs.append(total_ms)

    @staticmethod
    def _summary(values: Deque[int]) -> Dict[str, int]:
        if not values:
            return {"n": 0, "mean_ms": 0, "p50_ms": 0, "p95_ms": 0}
        sorted_values = sorted(values)
        n = len(sorted_values)
        mean = sum(sorted_values) // n
        p50 = sorted_values[n // 2]
        p95_idx = max(0, min(n - 1, int(round(0.95 * (n - 1)))))
        p95 = sorted_values[p95_idx]
        return {"n": n, "mean_ms": mean, "p50_ms": p50, "p95_ms": p95}

    async def snapshot(self) -> Dict[str, Dict[str, int]]:
        async with self._lock:
            stages = {name: self._summary(buf) for name, buf in self._stages.items()}
            jobs = self._summary(self._jobs)
        return {"stages": stages, "jobs": jobs}

    async def suggested_ttl_seconds(self, default_seconds: int, buffer_seconds: int) -> int:
        """TTL = job p95 + buffer, falling back to default before we have data."""
        async with self._lock:
            jobs = list(self._jobs)
        if len(jobs) < 5:
            return default_seconds
        sorted_jobs = sorted(jobs)
        p95_idx = max(0, min(len(sorted_jobs) - 1, int(round(0.95 * (len(sorted_jobs) - 1)))))
        p95_ms = sorted_jobs[p95_idx]
        return max(default_seconds, (p95_ms // 1000) + buffer_seconds)


stats = TimingStats()