# Coordinator scripts

One-off Node + Python utilities the coordinator depends on. Kept as a
sub-project so the coordinator's Python environment stays clean.

## 0G Compute provisioning

The coordinator can route agent γ to the 0G Compute Network instead of
Google Gemini (see `src/coordinator/agents/audit_0g.py`). 0G Compute uses
**per-request signed headers**, not a static bearer token, so the Python
client cannot just hold a long-lived secret. The two scripts here solve
that:

- `provision.ts` — one-time setup: deposits OG into the on-chain ledger,
  picks a provider, acknowledges its TEE signer, funds the sub-account,
  and prints the env vars to paste into `.env`.
- `headers_sidecar.ts` — long-running local proxy on `:8787`. Accepts
  OpenAI-compatible chat-completions requests from the coordinator,
  signs them with the broker SDK, and forwards to the chosen provider.

### Prerequisites

- Node.js 20+
- A wallet's `ZG_PRIVATE_KEY` set in your environment (or `.env`)
- ~3 OG of testnet tokens in that wallet

### Getting testnet OG

Minimum for full provisioning: **~0.105 OG** (0.1 ledger floor + gas).
Empirically the on-chain `MinimumDepositRequired` is exactly 0.1 OG —
the "3 OG minimum" in some 0G docs is outdated.

The official faucet at `https://faucet.0g.ai/` 301-redirects to
`https://hub.0g.ai/faucet`, which requires an X (Twitter) account that's
30+ days old with 10+ followers. If that doesn't work for you, use one
of these instead (verified April 2026):

| Faucet | Auth | Limit |
|---|---|---|
| [Google Cloud Web3 Faucet](https://cloud.google.com/application/web3/faucet/0g/galileo) | Google account | ~0.1 OG / day / google account |
| [Faucet.trade](https://faucet.trade/) | Wallet connect | small daily drip |
| [Chainlink Faucet](https://faucets.chain.link/0g-testnet-galileo) | Wallet + ≥1 LINK on Eth mainnet | — |
| [0G Hub (official)](https://hub.0g.ai/faucet) | X (30+ days old, 10+ followers) | 0.1 OG / day |

If nothing works, the coordinator gracefully falls back to Gemini for
agent γ — leave `LETHE_0G_COMPUTE_ENDPOINT` blank and the audit pipeline
runs unchanged. You lose the "uses 0G Compute" claim but not the demo.

### Usage

```bash
# install once
npm install

# one-time provisioning — prints LETHE_0G_COMPUTE_PROVIDER, MODEL, etc.
npm run provision:0g

# long-running sidecar — leave this in its own terminal
npm run headers:0g
```

Then in `.env`:

```
LETHE_0G_COMPUTE_ENDPOINT=http://localhost:8787/v1
LETHE_0G_COMPUTE_TOKEN=sidecar-handles-auth
LETHE_0G_COMPUTE_MODEL=<from provision.ts output>
LETHE_0G_COMPUTE_PROVIDER=<from provision.ts output>
LETHE_0G_COMPUTE_SIDECAR=true
```

The full local stack at demo time is four terminals:

| Terminal | Command | Port |
|---|---|---|
| coordinator | `uvicorn main:app --reload --port 8000` | 8000 |
| frontend | `npm run dev` (in `src/frontend/`) | 3000 |
| 0G headers sidecar | `npm run headers:0g` (here) | 8787 |
| (optional) AXL sidecars | `docker compose up` (in `infra/axl/`) | 9002/9012/9022 |

### Why a sidecar instead of caching the headers?

`broker.inference.getRequestHeaders(provider, body)` returns headers that
include a billing signature over the request body hash. The provider
rejects them on any subsequent (or modified) call. There is no API to
mint a long-lived JWT-style token. So the choices are:

- (a) regenerate headers per request from inside Python (would require
  porting the broker SDK's signing logic — not feasible for a hackathon)
- (b) sidecar in Node, where the SDK already runs (this repo's choice)
- (c) drop 0G Compute and stay on Gemini (the fallback)

## Other files

- `test_keeperhub.py` — manual smoke test for the KeeperHub Direct
  Execution + MCP integration. Not part of the runtime.
