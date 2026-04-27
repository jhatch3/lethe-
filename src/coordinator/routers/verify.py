"""Public verify endpoint.

Anyone with a bill's SHA-256 can confirm whether (and when, and how) it was
audited via Lethe. The bill itself never crosses the wire — only the hash.
This is what makes the anchor useful long after Lethe's servers are gone:
the contract on 0G Galileo is the source of truth.

Routes:
    GET /api/verify/{sha256}   — Returns the on-chain anchor record, or { anchored: false }.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from chain.zerog import _ANCHOR_ABI, _VERDICT_REVERSE
from config import settings

router = APIRouter(prefix="/api/verify", tags=["verify"])
log = logging.getLogger("lethe.verify")


def _normalize_sha(sha: str) -> str:
    s = sha.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if not all(c in "0123456789abcdef" for c in s):
        raise HTTPException(status_code=400, detail="invalid sha256 (non-hex characters)")
    if len(s) != 64:
        raise HTTPException(status_code=400, detail=f"sha256 must be 64 hex chars (got {len(s)})")
    return s


def _read_anchor_sync(sha256_hex: str) -> Dict[str, Any]:
    from web3 import Web3

    if not settings.bill_registry_address:
        raise HTTPException(status_code=503, detail="bill registry not configured on this coordinator")

    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url))
    if not w3.is_connected():
        raise HTTPException(status_code=503, detail="0G RPC unreachable")

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.bill_registry_address),
        abi=_ANCHOR_ABI,
    )
    sha_bytes = bytes.fromhex(sha256_hex)
    rec = contract.functions.anchors(sha_bytes).call()
    chain_id = w3.eth.chain_id

    if int(rec[3]) == 0:  # anchoredAt == 0 → never anchored
        return {
            "anchored": False,
            "sha256": "0x" + sha256_hex,
            "registry_address": settings.bill_registry_address,
            "network": "0g-galileo-testnet",
            "chain_id": chain_id,
        }

    return {
        "anchored": True,
        "sha256": "0x" + sha256_hex,
        "verdict": _VERDICT_REVERSE.get(int(rec[0]), "unknown"),
        "verdict_int": int(rec[0]),
        "agree_count": int(rec[1]),
        "total_agents": int(rec[2]),
        "anchored_at": int(rec[3]),
        "anchored_by": rec[4],
        "registry_address": settings.bill_registry_address,
        "network": "0g-galileo-testnet",
        "chain_id": chain_id,
    }


@router.get("/{sha256}")
async def verify(sha256: str) -> Dict[str, Any]:
    """Look up an anchor by its SHA-256 hash.

    Returns:
      - 200 + { anchored: true, verdict, agree_count, ..., anchored_at, anchored_by }
      - 200 + { anchored: false, sha256, registry_address }  if never anchored
      - 400  if sha256 is malformed
      - 503  if RPC is down or registry isn't configured
    """
    sha = _normalize_sha(sha256)
    return await asyncio.to_thread(_read_anchor_sync, sha)
