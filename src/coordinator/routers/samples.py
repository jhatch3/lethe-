"""Sample bills: list and run.

The frontend dashboard chips POST to `/api/samples/{name}/run`. The handler
loads the file from disk, treats it identically to an upload, and kicks off
the pipeline.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException

from config import settings
from pipeline import runner
from pipeline.events import bus
from store.memory import store
from store.stats import stats

router = APIRouter(prefix="/api/samples", tags=["samples"])


ALLOWED_EXTS = {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".webp"}


def _list_files() -> List[Path]:
    if not settings.samples_dir.exists():
        return []
    return sorted(
        p for p in settings.samples_dir.iterdir()
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTS
    )


@router.get("")
def list_samples():
    files = _list_files()
    return {
        "samples": [
            {
                "name": p.stem,
                "ext": p.suffix.lstrip(".").lower(),
                "filename": p.name,
                "size_bytes": p.stat().st_size,
            }
            for p in files
        ]
    }


@router.post("/{name}/run")
async def run_sample(name: str, background_tasks: BackgroundTasks):
    # name is the stem (e.g. "general-hospital-er"); resolve to a real file
    candidates = [p for p in _list_files() if p.stem == name]
    if not candidates:
        raise HTTPException(status_code=404, detail=f"sample not found: {name}")
    path = candidates[0]

    # path traversal guard — the resolved path must remain under samples_dir
    try:
        path.resolve().relative_to(settings.samples_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid sample path")

    body = path.read_bytes()
    if len(body) == 0:
        raise HTTPException(status_code=400, detail="sample is empty")

    sha256 = hashlib.sha256(body).hexdigest()
    ttl = await stats.suggested_ttl_seconds(
        default_seconds=settings.job_ttl_seconds,
        buffer_seconds=settings.job_ttl_buffer_seconds,
    )

    job = await store.create(filename=path.name, sha256=sha256, bill_bytes=body, ttl_seconds=ttl)
    await bus.open(job.job_id)
    background_tasks.add_task(runner.run, job.job_id)
    return {
        "job_id": job.job_id,
        "filename": job.filename,
        "sha256": "0x" + job.sha256,
        "ttl_seconds": ttl,
        "stream_url": f"/api/jobs/{job.job_id}/stream",
        "sample": name,
    }