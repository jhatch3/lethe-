"""Job routes: upload, fetch result, stream progress, delete."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from config import settings
from pipeline import runner
from pipeline.events import Event, bus
from store.memory import store
from store.stats import stats

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


ALLOWED_EXTS = {".pdf", ".txt", ".png", ".jpg", ".jpeg", ".webp"}


def _validate_filename(name: str) -> str:
    lower = name.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_EXTS):
        raise HTTPException(status_code=415, detail=f"unsupported file type: {name}")
    return name


@router.post("")
async def create_job(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    filename = _validate_filename(file.filename or "upload.bin")
    body = await file.read()
    if len(body) == 0:
        raise HTTPException(status_code=400, detail="empty file")
    if len(body) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="file too large")

    sha256 = hashlib.sha256(body).hexdigest()
    ttl = await stats.suggested_ttl_seconds(
        default_seconds=settings.job_ttl_seconds,
        buffer_seconds=settings.job_ttl_buffer_seconds,
    )

    job = await store.create(filename=filename, sha256=sha256, bill_bytes=body, ttl_seconds=ttl)
    # open the per-job event queue before kicking off the runner so an
    # immediately-following SSE subscribe doesn't miss early events
    await bus.open(job.job_id)
    background_tasks.add_task(runner.run, job.job_id)
    return {
        "job_id": job.job_id,
        "filename": job.filename,
        "sha256": "0x" + job.sha256,
        "ttl_seconds": ttl,
        "stream_url": f"/api/jobs/{job.job_id}/stream",
    }


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=410, detail="job not found or expired")
    return job.public_dict()


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    ok = await store.delete(job_id)
    return {"ok": ok}


@router.get("/{job_id}/stream")
async def stream(job_id: str):
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=410, detail="job not found or expired")

    queue = await bus.open(job_id)

    async def event_gen():
        # send a hello frame so the client sees the stream opened
        yield {"event": "open", "data": json.dumps({"job_id": job_id})}
        while True:
            try:
                evt: Event = await asyncio.wait_for(queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # heartbeat to keep proxies happy
                yield {"event": "ping", "data": "{}"}
                continue
            if evt.type == "__end__":
                break
            payload = evt.to_sse()
            yield {"event": payload["event"], "data": json.dumps(payload["data"])}
            if evt.type in ("done", "error"):
                # let the client receive then close
                break

    return EventSourceResponse(event_gen())