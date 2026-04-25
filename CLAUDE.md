# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Lethe is a hackathon-stage system that audits medical bills via AI consensus. The pipeline is: (1) a deterministic PDF parser extracts structured data from the uploaded bill (CPT/ICD codes, modifiers, charges, DOS); (2) a PHI redactor strips all patient identifiers (name, DOB, address, MRN, account numbers) before anything leaves the coordinator; (3) the redacted payload is sent to three independent LLM agents (GPT-4o, Claude, Gemini) communicating peer-to-peer over Gensyn AXL; (4) action is taken only when at least two agents agree. The original bill is held in coordinator memory only — never written to disk, never logged, never persisted on 0G, and never sent to a model provider. What persists is a SHA-256 hash on 0G Chain (proof of *what was analyzed*) and an anonymized pattern record on 0G Storage. Disputes are submitted on-chain via KeeperHub.

The "zero retention" guarantee is load-bearing — privacy is a product feature, not just a nice-to-have. AI agents must only ever see the redacted payload, never the original bill. When touching the coordinator, parser, redactor, or agent code, treat any path that could persist or leak a bill (logging, error reporting, caching, telemetry, or sending un-redacted data to a model) as a bug.

## Repository layout

The full intended structure is documented in `README.md` under "Repository structure". Currently scaffolded:

- `src/frontend/` — Next.js 16 (App Router) + TypeScript + Tailwind 4 + Framer Motion. The user-facing dashboard.
- `src/coordinator/` — FastAPI orchestrator. Will eventually host AXL node #0 and the consensus logic.
- `src/agent/{alpha,beta,gamma}/` — Per-LLM agent containers (scaffolded, not yet implemented).
- `src/contracts/` — Foundry project for `BillRegistry` / `ConsensusVote` (scaffolded, not yet implemented).
- `assets/` — Static images for the README only. Not application assets.
- `docs/`, `infra/`, `samples/` — Scaffolded, not yet populated.

## Frontend

**Important:** Next.js 16 has breaking changes from older versions (the model's training data is likely Next 13–15). Before writing non-trivial Next.js code, read the relevant guide in `frontend/node_modules/next/dist/docs/01-app/` rather than relying on memory. Tailwind is v4 (uses `@import "tailwindcss"` and `@theme inline` in `globals.css`, not the v3 `@tailwind base/components/utilities` directives).

Commands (run from `src/frontend/`):

```bash
npm run dev       # dev server on :3000
npm run build     # production build (also runs TypeScript check)
npm run start     # serve the production build
npm run lint      # eslint
```

The page reads `NEXT_PUBLIC_API_URL` (defaulting to `http://localhost:8000`) to find the coordinator.

## Coordinator (FastAPI)

Commands (run from `src/coordinator/`):

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows; use source .venv/bin/activate elsewhere
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

CORS is currently open only to `http://localhost:3000`. When adding a new frontend origin (preview deploys, etc.), update the `allow_origins` list in `main.py`.

## Running the full stack locally

Two terminals: `uvicorn` in `src/coordinator/` on port 8000, `npm run dev` in `src/frontend/` on port 3000. The landing page fetches `/` from the coordinator and shows "backend offline" if it can't reach it.
