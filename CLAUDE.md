# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Lethe audits medical bills via multi-agent AI consensus. Pipeline: (1) a deterministic PDF parser extracts structured data (CPT/ICD codes, modifiers, charges, DOS); (2) a PHI redactor strips all patient identifiers (name, DOB, address, MRN, account numbers) before anything leaves the coordinator; (3) three independent LLM agents (GPT-4o · Claude Sonnet 4.5 · Gemini Flash) communicate peer-to-peer over a real Gensyn AXL mesh, broadcast findings, and run a round-2 reflection with peer findings as context; (4) action only fires when ≥2 of 3 agree on the canonical billing code. The original bill is held in coordinator memory only — never written to disk, never logged, never persisted on chain, and never sent to a model provider.

What persists per audit: a SHA-256 + verdict on **0G Galileo** (`BillRegistry`), the same record mirrored to **Sepolia** via KeeperHub, anonymized findings indexed on **0G `PatternRegistry`**, the full record in **0G Storage** with the merkle root pointer recorded on the **`StorageIndex`** contract, and (on `dispute`) a filing on the Sepolia **`DisputeRegistry`**. When the user clicks "Send appeal" on the dashboard, an email goes out via Resend and KeeperHub records an attestation on the Sepolia **`AppealRegistry`** — three KeeperHub workflows total per audit.

The "zero retention" guarantee is load-bearing — privacy is the architecture, not a setting. AI agents only ever see the redacted payload. When touching the coordinator, parser, redactor, or agent code, treat any path that could persist or leak the original bill (logging, error reporting, caching, telemetry, or sending un-redacted data to a model) as a bug.

## Repository layout

- `src/frontend/` — Next.js 16 (App Router) + TypeScript + Tailwind 4 + Framer Motion · the dashboard, landing page, /verify, /patterns, /axl, /tech-stack
- `src/coordinator/` — FastAPI orchestrator: pipeline runner, parser, redactor, agents (alpha/beta/gamma + drafter), chain integrations (zerog · zerog_storage · zerog_blob · storage_priors · keeperhub · keeperhub_mcp), email_delivery, routers, store
- `src/coordinator/scripts/` — Node sidecars + provisioning: `provision:0g`, `headers:0g`, `storage:0g`, `check:0g` (compute broker SDK + storage TS SDK)
- `src/contracts/` — Solidity sources for `BillRegistry` · `PatternRegistry` · `DisputeRegistry` · `AppealRegistry` · `StorageIndex` · deployed via `deploy.py` (py-solc-x + web3.py, no Foundry)
- `infra/axl/` — Three Gensyn AXL sidecars (Dockerfile + per-peer configs + ed25519 keys)
- `data-gen/` — Sample medical bill generator + `seed_patterns.py` to pre-seed PatternRegistry
- `assets/` — Banner + dashboard screenshots for the README
- `docs/` — KeeperHub bounty assets, draft writeup, architecture rendering script

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
