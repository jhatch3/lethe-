from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import appeal, jobs, payer, providers, rules, samples, status, verify
from store.memory import sweeper_loop

# Surface the pipeline's structured events in the uvicorn terminal.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(name)-18s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("lethe.pipeline").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sweeper_task = asyncio.create_task(sweeper_loop(interval_seconds=5))
    # Loud startup banner — if AXL is disabled, judges/users running the
    # coordinator without `docker compose up axl-*` get an unmissable hint.
    # Track 1's cross-node-communication claim depends on AXL being live.
    try:
        from agents import transport_axl
        if not transport_axl.is_enabled():
            log = logging.getLogger("lethe.startup")
            if not settings.axl_enabled:
                reason = "LETHE_AXL_ENABLED=false"
            elif not transport_axl.PEER_IDS:
                reason = "infra/axl/keys/peer_ids.json missing"
            else:
                reason = "missing axl_*_url settings"
            log.warning("=" * 72)
            log.warning("AXL DISABLED · using in-process asyncio.gather (%s)", reason)
            log.warning("Track 1 (Gensyn AXL) cross-node claim is INACTIVE in this state.")
            log.warning("To enable: `docker compose up -d axl-alpha axl-beta axl-gamma` then restart.")
            log.warning("=" * 72)
    except Exception:
        pass
    try:
        yield
    finally:
        sweeper_task.cancel()


app = FastAPI(title="Lethe Coordinator", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(samples.router)
app.include_router(status.router)
app.include_router(verify.router)
app.include_router(appeal.router)
app.include_router(providers.router)
app.include_router(rules.router)
app.include_router(payer.router)


@app.get("/")
def root():
    return {"message": "Hello, world!", "service": "lethe-coordinator", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}