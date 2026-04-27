# Lethe — Setup Guide

Two paths: **Docker Compose** (recommended, full stack in one command) or **Local dev** (uvicorn + `npm run dev`, with the AXL sidecars still in Docker because they need a Linux Go build).

---

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker Desktop | latest | Required even for local dev — the AXL sidecars must run in Linux containers |
| Node.js | 20+ | for the Next.js frontend |
| Python | 3.11+ | for the FastAPI coordinator |
| Git | any | |

You will also need:

- **OpenAI API key** (`OPENAI_API_KEY`) — for agent α (GPT-4o) and the LLM redactor sweep
- **Anthropic API key** (`ANTHROPIC_API_KEY`) — for agent β (Claude Sonnet 4.5) and the drafter
- **Google AI Studio key** (`GOOGLE_API_KEY`) — for agent γ (Gemini Flash)
- **0G Galileo testnet wallet + funded private key** — get test tokens at [docs.0g.ai](https://docs.0g.ai). You need a small balance to pay gas for `BillRegistry` and `PatternRegistry` writes (chain ID `16602`).
- **KeeperHub account + API key + project ID** — sign up at [keeperhub.com](https://keeperhub.com). Used for the Sepolia mirror anchor.

---

## 2. Clone + configure environment

```bash
git clone https://github.com/Justyhatch3/lethe-.git
cd lethe-
cp .env.example .env
```

Edit `.env` and fill in real values:

```ini
# --- LLM provider keys ---
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# --- 0G Chain (Galileo testnet, chain ID 16602) ---
ZG_RPC_URL=https://evmrpc-testnet.0g.ai
ZG_CHAIN_ID=16602
ZG_PRIVATE_KEY=0x...                    # 32 bytes; testnet only
ZG_STORAGE_ENDPOINT=https://indexer-storage-testnet-turbo.0g.ai

# --- Deployed contract addresses (already deployed on Galileo) ---
BILL_REGISTRY_ADDRESS=0xf6B4C9CA2e8C8a3CE2DE77baa119004d6B51B457
PATTERN_REGISTRY_ADDRESS=0x7665c9692b1c4e6ef90495a584288604b735e23f
BILL_REGISTRY_ADDRESS_SEPOLIA=0xf6B4C9CA2e8C8a3CE2DE77baa119004d6B51B457

# --- KeeperHub (Sepolia mirror anchor) ---
KEEPERHUB_API_KEY=kh_...
KEEPERHUB_PROJECT_ID=...

# --- Coordinator + frontend ---
COORDINATOR_PORT=8000
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000

# --- Gensyn AXL transport (set true to enable real P2P broadcasting) ---
LETHE_AXL_ENABLED=true
```

> **Re-deploying contracts:** the addresses above are already live on Galileo. To redeploy your own copies, run `python src/contracts/deploy.py` (uses `py-solc-x` + `web3.py`, no Foundry required).

---

## 3a. Path A — Docker Compose (recommended)

```bash
docker compose up --build
```

This starts five containers:

| Service | Port | Purpose |
|---------|------|---------|
| `axl-alpha` | `:9002 → 9100` | Gensyn AXL sidecar with ed25519 key for agent α |
| `axl-beta` | `:9012 → 9100` | Sidecar for agent β |
| `axl-gamma` | `:9022 → 9100` | Sidecar for agent γ |
| `coordinator` | `:8000` | FastAPI orchestrator |
| `frontend` | `:3000` | Next.js dashboard |

Open `http://localhost:3000`.

> **Note on the port mapping:** AXL's HTTP API binds to `127.0.0.1:9002` inside the container regardless of config. The Dockerfile starts a `socat` forwarder on `0.0.0.0:9100`, which Compose maps out to host port `9002`/`9012`/`9022`.

---

## 3b. Path B — Local dev (uvicorn + npm run dev)

You still need the three AXL sidecars running in Docker, since the `node` binary must be built for Linux.

```bash
docker compose up -d axl-alpha axl-beta axl-gamma
```

**Terminal 1 — coordinator:**

```bash
cd src/coordinator
python -m venv .venv
.venv\Scripts\activate                 # Windows PowerShell
# source .venv/bin/activate            # macOS / Linux
pip install -r requirements.txt
$env:LETHE_AXL_ENABLED = "true"        # PowerShell; bash: export LETHE_AXL_ENABLED=true
uvicorn main:app --reload --port 8000
```

**Terminal 2 — frontend:**

```bash
cd src/frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

> `--reload` only watches Python files, **not** `.env`. If you change an env var, fully kill and restart uvicorn — a reload is not enough.

---

## 4. Verify everything is wired up

In a third terminal, hit the status endpoints:

```bash
curl localhost:8000/api/status
curl localhost:8000/api/axl
```

What to look for:

- `axl.transport: "axl-live"` and `axl.enabled: true` — AXL sidecars are reachable
- `chain.primary_anchor: "0g-direct"` — 0G key + BillRegistry are configured
- `chain.mirror_anchor: "keeperhub-sepolia"` — KeeperHub is configured
- `chain.pattern_index: "0g-direct"` — PatternRegistry is configured
- `agents.audit[].live: true` for all three (`alpha`, `beta`, `gamma`)
- `drafter.live: true`
- `/api/axl` shows three peer cards with `our_public_key` matching the expected pubkeys (`c4737e16…`, `fc40f9dd…`, `739dd219…`) and at least 2 connected upstream peers

If any of those are missing, see **Troubleshooting** below.

---

## 5. Run a real audit

1. Open `http://localhost:3000/dashboard`.
2. Click any **sample bill chip** (e.g., *ortho-clinic-mri*).
3. Watch the SSE pipeline run all seven stages: parse → redact → broadcast → reason → consensus → anchor → patterns → draft.
4. During `reason`, each agent terminal emits real AXL chatter lines (`⇆ axl · sent NB → β γ · ed25519:c4737e16…`) before LLM tokens stream in.
5. After completion, copy the 0G anchor tx and paste it into [chainscan-galileo.0g.ai](https://chainscan-galileo.0g.ai) — or use the in-app `/verify` page.
6. The Sepolia mirror tx is on the standard [Sepolia explorer](https://sepolia.etherscan.io).

---

## 6. Troubleshooting

### `Empty reply from server` when curling `localhost:9002/topology`

The AXL sidecar's HTTP API bound to `127.0.0.1:9002` inside the container, but `socat` failed to set up the host-port forwarder (or Docker BuildKit cached a stale `start.sh`). Force a clean rebuild:

```bash
docker compose down
docker rmi lethe-axl:latest
docker compose build --no-cache axl-alpha
docker compose up -d axl-alpha axl-beta axl-gamma
docker compose logs axl-alpha --tail 15
```

You should see `[start.sh] starting socat 0.0.0.0:9100 -> 127.0.0.1:9002` on the last line.

### `/api/axl` returns `{ "enabled": false, ... }` even though sidecars are up

`LETHE_AXL_ENABLED` is not set in the uvicorn process. Two ways this happens:

1. **uvicorn was running before you set the env var.** Fully kill it (`Ctrl+C` until it exits, or `Get-Process uvicorn,python | Stop-Process -Force` on Windows), then restart with the env var set.
2. **Stale shell env var overrides `.env`.** Pydantic-settings reads OS env vars *before* `.env` files. Run `echo $env:LETHE_AXL_ENABLED` (PowerShell) or `echo $LETHE_AXL_ENABLED` (bash) — if it's empty/false, set it explicitly: `$env:LETHE_AXL_ENABLED = "true"` before launching uvicorn.

### `open /config/alpha.json: no such file or directory` in axl-alpha logs

Docker Desktop file-sharing is not enabled for the drive containing the repo. Open Docker Desktop → Settings → Resources → File Sharing → add the parent of `lethe-/`.

### `curl` is a PowerShell alias, not the real curl

On Windows PowerShell, `curl` is aliased to `Invoke-WebRequest`. Use `curl.exe` instead, or use `Invoke-RestMethod`.

### 0G anchor fails with `insufficient funds`

Your `ZG_PRIVATE_KEY` wallet doesn't have any Galileo testnet tokens. Get them from the faucet at [docs.0g.ai](https://docs.0g.ai). Each anchor costs a fraction of a cent in test gas.

### KeeperHub mirror returns `stub (...)` instead of a tx hash

Either `KEEPERHUB_API_KEY` is missing/wrong, `BILL_REGISTRY_ADDRESS_SEPOLIA` is unset, or the verdict is `clarify` (not `dispute`/`approve`) — only finalized verdicts mirror. Check `/api/status.config` and `keeperhub_configured: true`.

---

## 7. Project commands cheatsheet

| Where | Command | What it does |
|-------|---------|--------------|
| repo root | `docker compose up --build` | Full stack |
| repo root | `docker compose logs axl-alpha --tail 20` | AXL sidecar logs |
| `src/coordinator/` | `uvicorn main:app --reload --port 8000` | Coordinator only |
| `src/coordinator/` | `pytest` | Coordinator tests |
| `src/frontend/` | `npm run dev` | Frontend dev server |
| `src/frontend/` | `npm run build` | Production build (also typechecks) |
| `src/frontend/` | `npm run lint` | ESLint |
| `src/contracts/` | `python deploy.py` | Re-deploy `BillRegistry` + `PatternRegistry` to 0G |
| `src/contracts/` | `python verify.py <txhash>` | Verify a bill anchor tx by hash |

---

For architecture and design-decision context, see [README.md](./README.md).
