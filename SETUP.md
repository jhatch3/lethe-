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

### Optional sponsor-track upgrades

These two are off by default and the system falls back gracefully when they're not configured. Enable them to satisfy the **strict** reading of each sponsor track's qualification criteria:

- **0G Compute** (Track 2 boost) — runs agent γ on 0G's decentralized inference network instead of Google Gemini. Requires Node.js (for the one-time `0g-compute-cli` provisioning). See **§7. Optional: 0G Compute** below.
- **KeeperHub MCP** (Track 3 strict-qualification) — routes the Sepolia mirror anchor through KeeperHub's MCP server instead of the Direct Execution REST API. Requires `pip install -r requirements.txt` (which now includes the `mcp` package). See **§8. Optional: KeeperHub MCP** below.

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

## 7. Optional: 0G Compute (decentralized inference for agent γ)

Off by default. When configured, agent γ runs on **0G Compute** (default model `GLM-5-FP8`) instead of Google Gemini. This proves real use of 0G's inference layer, not just 0G Chain.

### Prerequisites
- Node.js 20+
- A funded EVM wallet with native 0G tokens. **Empirically the on-chain `MinimumDepositRequired` is 0.1 OG** (some 0G docs claim 3 OG; that's outdated). Plan for ≥0.105 OG.

### One-time provisioning

The package on npm is **`@0glabs/0g-serving-broker`** (NOT `@0glabs/0g-compute-cli`, which doesn't exist). The broker's CLI is bundled inside it. We use it via a small TypeScript wrapper in `src/coordinator/scripts/`:

```bash
cd src/coordinator/scripts
npm install                  # installs broker + ethers + tsx

# Set your wallet env (use a dedicated wallet, never your mainnet)
export ZG_PRIVATE_KEY=0x...

# Read-only sanity check — wallet balance, ledger state, provider metadata
npm run check:0g

# Provisioning: picks a provider, deposits 0.1 OG to ledger, acknowledges
# TEE signer, funds sub-account, prints the env vars to paste into .env
npm run provision:0g

# Long-running header-signing sidecar (each request signed against body hash —
# 0G Compute does NOT use static bearer tokens, so a sidecar is required)
npm run headers:0g           # leave running on :8787
```

After `provision:0g` prints the env vars, paste them into `.env` — but point the endpoint at the **sidecar**, not the raw provider URL:

```ini
LETHE_0G_COMPUTE_ENDPOINT=http://localhost:8787/v1
LETHE_0G_COMPUTE_TOKEN=sidecar-handles-auth     # any non-empty string
LETHE_0G_COMPUTE_MODEL=GLM-5-FP8                # or whatever provision printed
LETHE_0G_COMPUTE_PROVIDER=0xPROVIDER_ADDRESS_HERE
LETHE_0G_COMPUTE_SIDECAR=true                   # cosmetic — /api/status reports "via sidecar"
```

Faucet status: `https://faucet.0g.ai/` 301-redirects to `https://hub.0g.ai/faucet` which gates on X login (account 30+ days, 10+ followers). Working alternatives: [Google Cloud Web3 Faucet](https://cloud.google.com/application/web3/faucet/0g/galileo) (Google account only), [Faucet.trade](https://faucet.trade/), [Chainlink Faucet](https://faucets.chain.link/0g-testnet-galileo).

### Verify

Restart uvicorn (in another terminal — leave `npm run headers:0g` running) and run:

```bash
curl localhost:8000/api/status
```

`config.zg_compute_configured` should be `true` and `config.zg_compute_transport` should be `"sidecar"`. The `agents.audit[]` entry for `gamma` should show `provider: "0g-compute"` and `model: "GLM-5-FP8 · 0g compute · sidecar · 0xABCDEF12…"`. Run a sample audit; the γ terminal will stream tokens from your 0G provider.

If anything goes wrong (provider down, ledger empty, bad endpoint, sidecar offline), γ silently falls back to Google Gemini — the pipeline never breaks.

---

## 7b. Optional: 0G Storage (full anonymized record)

Off by default. When enabled, every audit's anonymized pattern record is uploaded to **0G Storage** in parallel with the on-chain `PatternRegistry` write. The chain event is cheap and indexable; the storage blob carries the full structured JSON record (full code strings, voter agent names, schema-versioned) that bytes32/16/8 chain fields can't fit. Together: 0G Chain + 0G Storage = three pillars including 0G Compute.

The official 0G Storage Python SDK on PyPI is broken (relative-import issues). The TS SDK works, so we run a tiny Node sidecar.

### Setup

```bash
cd src/coordinator/scripts
# (deps already installed if you ran npm run provision:0g earlier)
npm run storage:0g           # leave running on :8788
```

In `.env`:
```ini
LETHE_0G_STORAGE_SIDECAR_URL=http://localhost:8788
```

### Verify

`/api/status.chain.pattern_storage` flips to `"0g-storage-sidecar"`. After running an audit, the `storage.uploaded` SSE event includes the merkle `root_hash` and on-chain commitment `tx_hash`. The dashboard receipt's `0G STORAGE (anonymized record)` block shows both.

---

## 7c. Optional: Pre-seed PatternRegistry for the demo

The "each audit gets smarter via on-chain shared memory" claim only fires once `PatternRegistry` has events to read back. On a fresh deploy, there are no priors. To make the very first demo audit show real on-chain priors influencing agent reasoning, pre-seed the registry with synthetic historical patterns:

```bash
# Dry run first — shows what would be written, no tx
python data-gen/scripts/seed_patterns.py --dry-run --count 20

# Real run — costs gas (~0.001 OG per audit × 20 = ~0.02 OG)
python data-gen/scripts/seed_patterns.py --count 20

# Verify
curl localhost:8000/api/patterns | jq '.total_observations'
```

The seed pool is in `data-gen/scripts/seed_patterns.py:SEED_PATTERNS` — anonymized billing-error patterns (CPT 99213/99214 downcodes, 74177 unbundling, J3490 modifier, etc.) with realistic dispute / clarify / approve mixes. No PHI; codes are public taxonomy.

---

## 8. Optional: KeeperHub MCP (Track 3 strict qualification)

Off by default. When enabled, the Sepolia mirror anchor goes through KeeperHub's MCP server instead of the REST API. The KeeperHub track's prize text specifies "MCP server or CLI" as the integration vector — this flag satisfies the strict reading.

### Setup

`mcp` is now in `requirements.txt`. Reinstall to pick it up:

```powershell
cd C:\Users\Justin\lethe-\src\coordinator
.venv\Scripts\activate
pip install -r requirements.txt
python -c "import mcp; print('mcp', mcp.__version__)"
```

Then flip the flag in `.env`:

```ini
LETHE_KEEPERHUB_USE_MCP=true
LETHE_KEEPERHUB_MCP_URL=https://app.keeperhub.com/mcp
```

Restart uvicorn.

### How it falls back

The runner attempts MCP first. If the hosted MCP endpoint rejects header auth (KeeperHub may require browser OAuth on the hosted endpoint, in which case header-based bearer auth won't work), or any other MCP error fires, the runner **automatically falls back to the existing REST path** with a warning in the uvicorn log:

```
WARNING  keeperhub MCP returned stub (...) — falling back to REST
```

The audit still completes — the Sepolia tx still gets written. You just won't get the MCP-strict qualification credit for that run.

### Verify

`/api/status.config.keeperhub_transport` reports `"mcp"` when the flag is on. After a successful real audit, the `mirror.confirmed` SSE event has `executor: "keeperhub-mcp"` (not `"keeperhub"`).

If header auth doesn't work on the hosted endpoint, the alternative is to run a **local KeeperHub MCP Docker container** with `KEEPERHUB_API_KEY` as an env var, then point `LETHE_KEEPERHUB_MCP_URL` at `http://localhost:<port>/mcp`. See [KeeperHub MCP docs](https://docs.keeperhub.com/ai-tools).

---

## 8b. Optional: Dispute auto-file (KeeperHub workflow #2)

When consensus = `dispute`, a **second** KeeperHub Direct Execution fires against a configurable Sepolia `DisputeRegistry` contract. This is a different contract, different method, different verdict gate from the mirror anchor — it demonstrates KH as an *execution platform*, not a single hardcoded API call.

By default the dispute filer is stubbed (no contract address configured), so it appears in `/api/status` as `keeperhub_dispute_filer: "stub"` and the receipt skips the dispute block. To go live:

### 1. Deploy a `DisputeRegistry` contract on Sepolia

Any contract exposing `recordDispute(bytes32 billHash, uint8 reason, string note)` works. A minimal stub:

```solidity
contract DisputeRegistry {
    event DisputeFiled(bytes32 indexed billHash, uint8 reason, string note, address indexed by, uint256 ts);
    function recordDispute(bytes32 billHash, uint8 reason, string calldata note) external {
        emit DisputeFiled(billHash, reason, note, msg.sender, block.timestamp);
    }
}
```

Deploy via your preferred path (Remix, Foundry, `src/contracts/deploy.py` extension). Funded Sepolia EOA needed; KeeperHub's auto-provisioned wallet at `0xC33E920102d53Bf2B4286361c23E63D93FeB02ee` will be the `msg.sender` after deploy if you choose to wire it.

### 2. Configure the env

```ini
LETHE_DISPUTE_REGISTRY_ADDRESS_SEPOLIA=0xYOUR_DEPLOYED_DISPUTE_REGISTRY
LETHE_DISPUTE_FUNCTION_NAME=recordDispute        # change if your contract uses a different name
```

### Verify

`/api/status.config.keeperhub_dispute_filer` flips to `"live"`. Run an audit on `samples/general-hospital-er/run` (planted disputes). The pipeline emits a `dispute.filed` SSE event with the Sepolia tx hash, and the receipt's `DISPUTE FILED (KeeperHub workflow #2)` block links to etherscan.

---

## 9. Project commands cheatsheet

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
