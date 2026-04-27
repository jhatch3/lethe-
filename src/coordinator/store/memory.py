"""In-memory job store with TTL eviction.

The original bill bytes live ONLY here, keyed by job_id. They are never written
to disk, never logged, and are zeroed out as soon as the pipeline finishes (and
again by a periodic sweeper as a belt-and-suspenders measure).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Job:
    job_id: str
    filename: str
    sha256: str
    created_at: float
    expires_at: float
    bill_bytes: Optional[bytes] = None
    redacted_payload: Optional[Dict[str, Any]] = None
    status: str = "queued"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    stage_timings: Dict[str, int] = field(default_factory=dict)

    def public_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "filename": self.filename,
            "sha256": self.sha256,
            "status": self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "stage_timings_ms": self.stage_timings,
            "result": self.result,
            "error": self.error,
        }


class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create(self, *, filename: str, sha256: str, bill_bytes: bytes, ttl_seconds: int) -> Job:
        now = time.time()
        job = Job(
            job_id=uuid.uuid4().hex,
            filename=filename,
            sha256=sha256,
            created_at=now,
            expires_at=now + ttl_seconds,
            bill_bytes=bill_bytes,
        )
        async with self._lock:
            self._jobs[job.job_id] = job
        return job

    async def get(self, job_id: str) -> Optional[Job]:
        async with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            return None
        # Active jobs are never auto-evicted by reads.
        if job.status in ("queued", "running"):
            return job
        if job.status != "expired" and time.time() > job.expires_at:
            await self._evict(job.job_id)
            return None
        return job

    async def clear_bill_bytes(self, job_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.bill_bytes = None

    async def delete(self, job_id: str) -> bool:
        return await self._evict(job_id)

    async def _evict(self, job_id: str) -> bool:
        async with self._lock:
            job = self._jobs.pop(job_id, None)
        if job is None:
            return False
        job.bill_bytes = None
        job.redacted_payload = None
        job.status = "expired"
        return True

    async def sweep(self) -> int:
        # Don't evict jobs that are still running — the pipeline updates
        # expires_at when it transitions to done/error.
        now = time.time()
        async with self._lock:
            expired_ids = [
                jid for jid, j in self._jobs.items()
                if now > j.expires_at and j.status not in ("queued", "running")
            ]
        for jid in expired_ids:
            await self._evict(jid)
        return len(expired_ids)


store = JobStore()


async def sweeper_loop(interval_seconds: int = 5) -> None:
    while True:
        try:
            await store.sweep()
        except Exception:
            pass
        await asyncio.sleep(interval_seconds)