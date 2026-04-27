# Coordinator

FastAPI orchestrator for Lethe. Hosts the consensus coordinator and (eventually) AXL node #0.

## Setup

```bash
cd src/coordinator
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload --port 8000
```

## Routes

### Liveness
- `GET /` — hello
- `GET /health` — `{ status: "ok" }`
- `GET /docs` — interactive OpenAPI

### Jobs (the core flow)
- `POST /api/jobs` — multipart upload (`file`: pdf/txt/png/jpg). Returns `{ job_id, sha256, ttl_seconds, stream_url }` and kicks off the pipeline.
- `GET /api/jobs/{id}/stream` — Server-Sent Events stream of pipeline events: `open`, `job.started`, `step.started`, `step.completed`, `agent.handshake`, `agent.started`, `agent.completed`, `consensus.reached`, `anchor.confirmed`, `done`, `error`.
- `GET /api/jobs/{id}` — full result once `done`. Returns 410 once the TTL has expired.
- `DELETE /api/jobs/{id}` — explicit purge.

### Samples
- `GET /api/samples` — list canned bills shipped under `samples/`.
- `POST /api/samples/{name}/run` — load a canned bill and run it through the same pipeline. `{name}` is the file stem.

### Status
- `GET /api/status` — coordinator state, AXL peer count, agent/chain provider info, rolling timing stats (mean / p50 / p95 per stage and per job), suggested TTL.

## Pipeline

Six stages, each timed and emitted on the SSE stream:

1. **parse** — extract structured bill (CPT/ICD/charges) from upload
2. **redact** — strip patient identifiers (name, DOB, address, MRN, account)
3. **broadcast** — open AXL connections to the three agents
4. **reason** — agents analyze the redacted payload in parallel
5. **consensus** — tally votes; a finding survives only with ≥2/3 quorum
6. **anchor** — write the bill SHA-256 to 0G Chain via KeeperHub

Phase 1 stages are stubbed but emit real measured durations. Phase 2 swaps in real model providers, real PDF parsing/OCR, and real on-chain anchors without changing the SSE contract.

## Privacy invariants

- Bill bytes live only in `store/memory.py`, keyed by job_id, and are zeroed immediately after the parse stage.
- A background sweeper purges any job past TTL even if the pipeline crashed.
- Only the **redacted** payload is passed to agents.
- Events emitted on the SSE bus carry no bill content — only stage names, durations, vote counts, and hashes.
- The bill SHA-256 is computed before redaction so the on-chain hash identifies what was analyzed without persisting the pre-image.
