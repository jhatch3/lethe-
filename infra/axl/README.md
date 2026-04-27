# Lethe · AXL P2P sidecars

This folder runs three [Gensyn AXL](https://blog.gensyn.ai/introducing-axl/)
nodes — one per audit agent. Each has its own ed25519 keypair, listens on its
own port, and peers with the public Gensyn bootstrap nodes via Yggdrasil.

## What's in here

- `keys/{alpha,beta,gamma}.pem` — private ed25519 keys (gitignored)
- `keys/peer_ids.json` — public ed25519 hex (committed; the coordinator reads this)
- `configs/{alpha,beta,gamma}.json` — one config per node, each pointing at its private key
- `Dockerfile` — multi-stage build for the AXL `node` Go binary
- The three services in `../../docker-compose.yml` mount these in

## Why Docker

AXL needs Go 1.25.5 + gVisor + openssl. Native-Windows builds fight the gVisor
userspace TCP stack. Building inside a Linux container sidesteps that.

## Run them

```bash
# From the repo root:
docker compose build axl-alpha axl-beta axl-gamma
docker compose up -d axl-alpha axl-beta axl-gamma

# Verify each sidecar — three distinct ed25519 peer IDs:
curl localhost:9002/topology   # alpha
curl localhost:9012/topology   # beta
curl localhost:9022/topology   # gamma
```

Expected output per sidecar:

```json
{
  "our_public_key": "c4737e1652ed8b8450a1afea70996dad76d68e602f8a79c2e9ac3bcdbf417598",
  "peers": [
    { "public_key": "...", "addr": "..." }
  ]
}
```

The `our_public_key` should match `peer_ids.json` for that agent.

## Wire it into the coordinator

Set `LETHE_AXL_ENABLED=true` in `.env` and restart `uvicorn`. From then on, every
agent's redacted payload is broadcast across the AXL mesh before the LLM call,
and the SSE stream emits `axl.broadcast` events with the real peer IDs.

```bash
# Verify from the coordinator side:
curl http://localhost:8000/api/axl | jq
curl http://localhost:8000/api/status | jq .axl
```

## Generate fresh keys (if you need to)

```bash
cd keys
for n in alpha beta gamma; do
  openssl genpkey -algorithm ed25519 -out $n.pem
done

# Re-derive the public-key hex map:
python - <<'PY'
import json, subprocess, pathlib
out = {}
for n in ["alpha", "beta", "gamma"]:
    der = subprocess.check_output(["openssl","pkey","-in",f"{n}.pem","-pubout","-outform","DER"])
    out[n] = der[-32:].hex()  # last 32 bytes of DER pubkey = raw ed25519
pathlib.Path("peer_ids.json").write_text(json.dumps({"_comment":"...", **out}, indent=2))
PY
```

## Architecture

```
coordinator (FastAPI)
  ├── agents/transport_axl.py
  │     POST http://axl-alpha:9002/send  (X-Destination-Peer-Id: <beta_pubkey>)
  │     POST http://axl-alpha:9002/send  (X-Destination-Peer-Id: <gamma_pubkey>)
  │     ...
  ▼
axl-alpha    axl-beta    axl-gamma
  │            │            │
  └─ Yggdrasil ─ public Gensyn bootstrap nodes ─ Yggdrasil ─┘
```

Each sidecar's `/send` is fire-and-forget. The coordinator broadcasts
each agent's redacted payload to the other two peers before the LLM call.
This makes the "P2P consensus" claim concrete and verifiable via
`curl /topology` on any sidecar.

## Privacy

Only the **redacted** payload (no PHI by construction) crosses the mesh.
The original bill bytes were zeroed at the parse stage; what travels over
Yggdrasil is the same data the LLM agents see — codes, charges, modifiers.
