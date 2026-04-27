"""AXL transport adapter — wraps the local AXL sidecar's HTTP API.

When LETHE_AXL_ENABLED=true, every agent's `analyze()` call publishes its
redacted_payload + finished vote across the AXL mesh BEFORE returning. This
makes the "P2P consensus" claim concrete and verifiable:

  1. Each agent has its own AXL sidecar with its own ed25519 keypair.
  2. The redacted payload travels through the Yggdrasil mesh from one
     sidecar to the others (not asyncio.gather in-process).
  3. Each agent's vote is broadcast to its peers' sidecars.
  4. The coordinator can `curl /topology` on each sidecar and see three
     distinct ed25519 public keys with peer connections.

Privacy: only the redacted_payload (no PHI by construction) crosses the mesh.

API used (per https://blog.gensyn.ai/introducing-axl/):
    POST /send  X-Destination-Peer-Id: <hex>   body: arbitrary bytes
    GET  /recv                                  → 204 empty or 200 + X-From-Peer-Id
    GET  /topology                              → {our_public_key, peers: [...]}
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from config import settings

log = logging.getLogger("lethe.axl")


# Public-key map: agent name → ed25519 hex (the peer ID).
# Loaded from infra/axl/keys/peer_ids.json so the coordinator and the sidecars
# always agree on identities.
_PEER_IDS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "infra" / "axl" / "keys" / "peer_ids.json"


def _load_peer_ids() -> Dict[str, str]:
    if not _PEER_IDS_FILE.exists():
        return {}
    try:
        data = json.loads(_PEER_IDS_FILE.read_text())
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception as e:
        log.warning("could not load peer_ids.json: %s", e)
        return {}


PEER_IDS: Dict[str, str] = _load_peer_ids()


def _sidecar_url(agent: str) -> Optional[str]:
    return {
        "alpha": settings.axl_alpha_url,
        "beta":  settings.axl_beta_url,
        "gamma": settings.axl_gamma_url,
    }.get(agent)


def is_enabled() -> bool:
    return bool(settings.axl_enabled and PEER_IDS and all(_sidecar_url(a) for a in PEER_IDS))


async def topology(agent: str) -> Dict[str, Any]:
    """Read the sidecar's view of the mesh — useful for `/api/status` + demos."""
    url = _sidecar_url(agent)
    if not url:
        return {"error": "no sidecar url"}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{url}/topology", timeout=4.0)
            if r.status_code == 200:
                return r.json()
            return {"error": f"http {r.status_code}", "body": r.text[:160]}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:160]}"}


async def broadcast_payload(from_agent: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Broadcast a payload from `from_agent`'s sidecar to the other two peers.

    Fire-and-forget — the sidecar's /send is fire-and-forget, no ack. Returns
    a manifest of what was attempted so the coordinator can emit observability
    events.
    """
    src_url = _sidecar_url(from_agent)
    if not src_url:
        return {"sent": False, "reason": "no sidecar"}

    body = json.dumps(payload).encode("utf-8")
    targets = [name for name in PEER_IDS if name != from_agent]
    sent_to = []
    errors = []

    async with httpx.AsyncClient() as client:
        for target in targets:
            peer_pubkey = PEER_IDS[target]
            try:
                r = await client.post(
                    f"{src_url}/send",
                    content=body,
                    headers={
                        "X-Destination-Peer-Id": peer_pubkey,
                        "Content-Type": "application/octet-stream",
                    },
                    timeout=6.0,
                )
                if r.status_code == 200:
                    sent_to.append(target)
                else:
                    errors.append({"target": target, "status": r.status_code, "body": r.text[:80]})
            except Exception as e:
                errors.append({"target": target, "error": f"{type(e).__name__}: {str(e)[:80]}"})

    return {
        "sent": len(sent_to) > 0,
        "from_agent": from_agent,
        "from_peer_id": PEER_IDS.get(from_agent),
        "delivered_to": sent_to,
        "errors": errors,
        "payload_bytes": len(body),
    }


async def gather_topology() -> Dict[str, Any]:
    """One topology call per agent — for /api/status."""
    if not PEER_IDS:
        return {"enabled": False, "reason": "no peer_ids.json"}
    results = await asyncio.gather(*(topology(a) for a in PEER_IDS), return_exceptions=False)
    return {
        "enabled": is_enabled(),
        "peers": {
            name: {
                "expected_pubkey": pubkey,
                "sidecar_url": _sidecar_url(name),
                "topology": results[i],
            }
            for i, (name, pubkey) in enumerate(PEER_IDS.items())
        },
    }
