from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import jobs, samples, status, verify
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


@app.get("/")
def root():
    return {"message": "Hello, world!", "service": "lethe-coordinator", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}