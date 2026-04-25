# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Lethe is a hackathon-stage system that audits medical bills via AI consensus. A bill is parsed, sent to three independent LLM agents (GPT-4o, Claude, Gemini) communicating peer-to-peer over Gensyn AXL, and only acted on when at least two agents agree. The bill itself is held in coordinator memory only — never written to disk, never logged, never persisted on 0G. What persists is a SHA-256 hash on 0G Chain (proof of *what was analyzed*) and an anonymized pattern record on 0G Storage. Disputes are submitted on-chain via KeeperHub.

The "zero retention" guarantee is load-bearing — privacy is a product feature, not just a nice-to-have. When touching the coordinator or agent code, treat any code path that could persist a bill (logging, error reporting, caching, telemetry) as a bug.

## Repository layout

The full intended structure is documented in `README.md` under "Repository structure". Currently scaffolded:

- `frontend/` — Next.js 16 (App Router) + TypeScript + Tailwind 4 + Framer Motion. The user-facing dashboard.
- `coordinator/` — FastAPI orchestrator. Will eventually host AXL node #0 and the consensus logic.
- `assets/` — Static images for the README only. Not application assets.

Not yet scaffolded but referenced in the README: `agent/{alpha,beta,gamma}/`, `contracts/` (Foundry), `infra/`, `samples/`, `docs/`.

## Frontend

**Important:** Next.js 16 has breaking changes from older versions (the model's training data is likely Next 13–15). Before writing non-trivial Next.js code, read the relevant guide in `frontend/node_modules/next/dist/docs/01-app/` rather than relying on memory. Tailwind is v4 (uses `@import "tailwindcss"` and `@theme inline` in `globals.css`, not the v3 `@tailwind base/components/utilities` directives).

Commands (run from `frontend/`):

```bash
npm run dev       # dev server on :3000
npm run build     # production build (also runs TypeScript check)
npm run start     # serve the production build
npm run lint      # eslint
```

The page reads `NEXT_PUBLIC_API_URL` (defaulting to `http://localhost:8000`) to find the coordinator.

## Coordinator (FastAPI)

Commands (run from `coordinator/`):

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows; use source .venv/bin/activate elsewhere
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

CORS is currently open only to `http://localhost:3000`. When adding a new frontend origin (preview deploys, etc.), update the `allow_origins` list in `main.py`.

## Running the full stack locally

Two terminals: `uvicorn` in `coordinator/` on port 8000, `npm run dev` in `frontend/` on port 3000. The landing page fetches `/` from the coordinator and shows "backend offline" if it can't reach it.
