"""0G Storage read-back loop — bidirectional Storage usage.

Two functions:

1. `index_storage_root_on_chain(bill_hash, storage_root)` — after the storage
   sidecar uploads a blob, write its merkle root to the on-chain `StorageIndex`
   contract on Galileo. This closes the loop: the chain now has a queryable
   pointer to every audit's full record.

2. `fetch_recent_storage_priors(limit=10)` — query recent `RootIndexed` events,
   download each blob via the storage sidecar, parse, and format as a richer
   prior context block for agent prompts. This is what makes Storage genuinely
   bidirectional rather than write-only cold archive.

Falls back to empty/stub at every layer when something isn't configured.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from config import settings

log = logging.getLogger("lethe.chain.storage_priors")


_STORAGE_INDEX_ABI = [
    {
        "type": "function",
        "name": "recordStorageRoot",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "billHash",    "type": "bytes32"},
            {"name": "storageRoot", "type": "bytes32"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "rootCount",
        "stateMutability": "view",
        "inputs": [{"name": "billHash", "type": "bytes32"}],
        "outputs": [{"type": "uint256"}],
    },
    # Event ABI for log decoding — keccak topic computed at query time.
    {
        "type": "event",
        "name": "RootIndexed",
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "billHash",    "type": "bytes32"},
            {"indexed": True,  "name": "storageRoot", "type": "bytes32"},
            {"indexed": False, "name": "indexedAt",   "type": "uint64"},
            {"indexed": True,  "name": "indexedBy",   "type": "address"},
            {"indexed": False, "name": "rootIndex",   "type": "uint256"},
        ],
    },
]


def _stub(reason: str) -> Dict[str, Any]:
    return {"executor": f"stub ({reason})", "live": False}


# -------- WRITE: record storage root on chain --------

def _do_index_sync(bill_hash_hex: str, storage_root_hex: str) -> Dict[str, Any]:
    from web3 import Web3
    from eth_account import Account

    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url))
    if not w3.is_connected():
        raise RuntimeError("0G RPC unreachable")

    sha = bill_hash_hex[2:] if bill_hash_hex.startswith("0x") else bill_hash_hex
    root = storage_root_hex[2:] if storage_root_hex.startswith("0x") else storage_root_hex

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.storage_index_address),
        abi=_STORAGE_INDEX_ABI,
    )
    acct = Account.from_key(settings.zg_private_key)

    tx = contract.functions.recordStorageRoot(
        bytes.fromhex(sha), bytes.fromhex(root),
    ).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
        "chainId": w3.eth.chain_id,
        "type": 2,
        "maxFeePerGas": w3.to_wei(6, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(4, "gwei"),
        "gas": 95_000,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90, poll_latency=2)

    tx_hex = tx_hash.hex()
    return {
        "executor": "0g-direct-storage-index",
        "live": True,
        "tx": tx_hex if tx_hex.startswith("0x") else "0x" + tx_hex,
        "block_number": receipt.blockNumber,
        "registry_address": settings.storage_index_address,
        "status": "confirmed" if receipt.status == 1 else "reverted",
    }


async def index_storage_root_on_chain(
    bill_hash_hex: str, storage_root_hex: str,
) -> Dict[str, Any]:
    """Write the (billHash → storageRoot) pointer to the on-chain StorageIndex."""
    if not (settings.zg_private_key and settings.storage_index_address):
        return _stub("no key/address")
    if not storage_root_hex:
        return _stub("no storage root")
    try:
        result = await asyncio.to_thread(_do_index_sync, bill_hash_hex, storage_root_hex)
        log.info(
            "storage-index sha=%s root=%s tx=%s block=%s",
            bill_hash_hex[:12], storage_root_hex[:12],
            (result.get("tx") or "")[:18], result.get("block_number"),
        )
        return result
    except Exception as e:
        log.warning("storage-index failed: %s — stubbing", e)
        return {**_stub(f"error: {type(e).__name__}"), "error": str(e)[:200]}


# -------- READ: fetch recent blobs back from storage --------

async def _download_blob(client: httpx.AsyncClient, sidecar_url: str, root_hex: str) -> Optional[Dict[str, Any]]:
    """Pull one blob from the sidecar; returns the parsed JSON dict or None."""
    try:
        r = await client.get(
            f"{sidecar_url}/download",
            params={"root": root_hex if root_hex.startswith("0x") else "0x" + root_hex},
            timeout=20.0,
        )
        if r.status_code != 200:
            log.debug("download %s: http %d", root_hex[:12], r.status_code)
            return None
        try:
            return json.loads(r.content.decode("utf-8"))
        except Exception as e:
            log.debug("download %s: non-JSON body (%s)", root_hex[:12], e)
            return None
    except Exception as e:
        log.debug("download %s err: %s", root_hex[:12], e)
        return None


def _recent_roots_sync(limit: int) -> List[str]:
    """Query RootIndexed events on Galileo, return the `limit` most-recent roots."""
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url, request_kwargs={"timeout": 10}))
    if not w3.is_connected():
        return []
    addr = Web3.to_checksum_address(settings.storage_index_address)
    topic = "0x" + Web3.keccak(
        text="RootIndexed(bytes32,bytes32,uint64,address,uint256)"
    ).hex().lstrip("0x")
    try:
        latest = w3.eth.block_number
        from_block = max(0, latest - 100_000)
        logs = w3.eth.get_logs({
            "address": addr,
            "topics": [topic],
            "fromBlock": from_block,
            "toBlock": "latest",
        })
    except Exception as e:
        log.debug("eth_getLogs failed: %s", e)
        return []
    # Most recent first.
    logs = sorted(logs, key=lambda l: int(l["blockNumber"]), reverse=True)
    roots: List[str] = []
    for entry in logs[:limit]:
        # topics[2] is `storageRoot` (third indexed param after the event sig + billHash)
        try:
            root_hex = entry["topics"][2].hex()
            roots.append(root_hex if root_hex.startswith("0x") else "0x" + root_hex)
        except Exception:
            continue
    return roots


async def fetch_recent_storage_priors(limit: int = 8) -> List[Dict[str, Any]]:
    """Pull the N most-recent audit blobs from 0G Storage, parsed."""
    if not (settings.storage_index_address and settings.zg_storage_sidecar_url):
        return []
    try:
        roots = await asyncio.to_thread(_recent_roots_sync, limit)
    except Exception as e:
        log.debug("recent_roots failed: %s", e)
        return []
    if not roots:
        return []

    sidecar = settings.zg_storage_sidecar_url.rstrip("/")
    started = time.perf_counter()
    blobs: List[Dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *(_download_blob(client, sidecar, r) for r in roots),
            return_exceptions=False,
        )
    for blob in results:
        if blob and isinstance(blob, dict):
            blobs.append(blob)
    log.info(
        "storage priors: fetched %d/%d blobs in %dms",
        len(blobs), len(roots), int((time.perf_counter() - started) * 1000),
    )
    return blobs


def format_storage_priors_for_prompt(blobs: List[Dict[str, Any]], max_chars: int = 1800) -> str:
    """Compact-format recent storage blobs as a richer-than-events priors block.

    Each blob carries the FULL anonymized record (full code strings, voter
    agent names, schema-versioned), unlike the truncated bytes32 fields in the
    PatternRegistry events. Format keeps it short and prompt-friendly.
    """
    if not blobs:
        return ""

    # Aggregate: per code, how many times we've seen each action.
    from collections import Counter, defaultdict
    code_actions: Dict[str, Counter] = defaultdict(Counter)
    code_severities: Dict[str, Counter] = defaultdict(Counter)
    code_voters: Dict[str, Counter] = defaultdict(Counter)
    total = 0
    for b in blobs:
        for f in (b.get("findings") or []):
            code = str(f.get("code") or "").strip()
            if not code:
                continue
            total += 1
            code_actions[code][str(f.get("action") or "info")] += 1
            code_severities[code][str(f.get("severity") or "info")] += 1
            for v in (f.get("voted_by") or []):
                code_voters[code][str(v)] += 1

    if total == 0:
        return ""

    # Top codes by total observations.
    by_count = sorted(code_actions.items(), key=lambda kv: -sum(kv[1].values()))[:8]
    lines = [
        "STORAGE PRIORS (richer context from past audits, fetched from 0G Storage):",
    ]
    for code, actions in by_count:
        n = sum(actions.values())
        a_str = " ".join(f"{a}={c}" for a, c in actions.most_common(3))
        sev_str = ",".join(s for s, _ in code_severities[code].most_common(2))
        v_str = "/".join(v for v, _ in code_voters[code].most_common(3))
        lines.append(f"  {code:14s}  n={n}  {a_str}  sev={sev_str}  voted_by={v_str}")
    lines.append(f"  ({len(blobs)} prior audits, {total} total findings)")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n  …(truncated)"
    return text
