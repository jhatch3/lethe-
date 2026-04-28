"""Public verify endpoint — comprehensive on-chain audit lookup.

Anyone with a bill's SHA-256 can recover the full audit picture across all
chains and storage layers without contacting Lethe directly. The contracts
on 0G Galileo + Ethereum Sepolia are the source of truth.

Routes:
    GET /api/verify/{sha256}   — Returns everything: BillRegistry anchor,
                                 PatternRegistry findings, StorageIndex
                                 pointers, Sepolia mirror, DisputeRegistry
                                 filings, AppealRegistry attestations,
                                 and (when the storage sidecar is up) the
                                 full anonymized audit blob from 0G Storage.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException

from chain.zerog import _ANCHOR_ABI, _VERDICT_REVERSE
from config import settings

router = APIRouter(prefix="/api/verify", tags=["verify"])
log = logging.getLogger("lethe.verify")


# === helpers =================================================================

def _normalize_sha(sha: str) -> str:
    s = sha.strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if not all(c in "0123456789abcdef" for c in s):
        raise HTTPException(status_code=400, detail="invalid sha256 (non-hex characters)")
    if len(s) != 64:
        raise HTTPException(status_code=400, detail=f"sha256 must be 64 hex chars (got {len(s)})")
    return s


def _safe_topic(text: str) -> str:
    from web3 import Web3
    h = Web3.keccak(text=text).hex()
    return h if h.startswith("0x") else "0x" + h


def _b32_to_str(b: bytes) -> str:
    """Strip trailing nulls, decode ascii. Used for bytes32 code/action fields."""
    try:
        return b.rstrip(b"\x00").decode("ascii", errors="replace")
    except Exception:
        return b.hex()


# === Galileo: BillRegistry anchor =============================================

def _read_galileo_anchor_sync(sha256_hex: str) -> Dict[str, Any]:
    from web3 import Web3
    if not settings.bill_registry_address:
        return {"anchored": False, "reason": "registry not configured"}
    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url, request_kwargs={"timeout": 8}))
    if not w3.is_connected():
        return {"anchored": False, "reason": "rpc unreachable"}
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.bill_registry_address),
        abi=_ANCHOR_ABI,
    )
    rec = contract.functions.anchors(bytes.fromhex(sha256_hex)).call()
    if int(rec[3]) == 0:
        return {"anchored": False, "registry_address": settings.bill_registry_address, "chain_id": w3.eth.chain_id}
    return {
        "anchored": True,
        "verdict": _VERDICT_REVERSE.get(int(rec[0]), "unknown"),
        "verdict_int": int(rec[0]),
        "agree_count": int(rec[1]),
        "total_agents": int(rec[2]),
        "anchored_at": int(rec[3]),
        "anchored_by": rec[4],
        "registry_address": settings.bill_registry_address,
        "chain_id": w3.eth.chain_id,
    }


# === Galileo: PatternRegistry events filtered by billHash ====================

def _read_pattern_events_sync(sha256_hex: str) -> List[Dict[str, Any]]:
    from web3 import Web3
    if not settings.pattern_registry_address:
        return []
    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url, request_kwargs={"timeout": 8}))
    if not w3.is_connected():
        return []
    sha = sha256_hex if sha256_hex.startswith("0x") else "0x" + sha256_hex
    topic = _safe_topic("PatternIndexed(bytes32,bytes32,bytes16,bytes8,uint64,uint8)")
    try:
        latest = w3.eth.block_number
        from_block = max(0, latest - 200_000)
        logs = w3.eth.get_logs({
            "address": Web3.to_checksum_address(settings.pattern_registry_address),
            "topics": [topic, sha],
            "fromBlock": from_block, "toBlock": "latest",
        })
    except Exception as e:
        log.debug("pattern getLogs failed: %s", e)
        return []
    out: List[Dict[str, Any]] = []
    for entry in logs:
        try:
            data = entry["data"]
            if hasattr(data, "hex"):
                data = data.hex()
            data = data.lstrip("0x") if isinstance(data, str) else ""
            # 6 ABI words = 6 * 64 hex chars; we only decode the readable codes
            if len(data) >= 64:
                code_hex = data[:64]
                code = _b32_to_str(bytes.fromhex(code_hex))
            else:
                code = "?"
            out.append({
                "code": code,
                "tx_hash": "0x" + entry["transactionHash"].hex(),
                "block_number": int(entry["blockNumber"]),
            })
        except Exception:
            continue
    return out


# === Galileo: StorageIndex events ============================================

def _read_storage_pointers_sync(sha256_hex: str) -> List[Dict[str, Any]]:
    from web3 import Web3
    if not settings.storage_index_address:
        return []
    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url, request_kwargs={"timeout": 8}))
    if not w3.is_connected():
        return []
    sha = sha256_hex if sha256_hex.startswith("0x") else "0x" + sha256_hex
    topic = _safe_topic("RootIndexed(bytes32,bytes32,uint64,address,uint256)")
    try:
        latest = w3.eth.block_number
        from_block = max(0, latest - 200_000)
        logs = w3.eth.get_logs({
            "address": Web3.to_checksum_address(settings.storage_index_address),
            "topics": [topic, sha],
            "fromBlock": from_block, "toBlock": "latest",
        })
    except Exception as e:
        log.debug("storage-index getLogs failed: %s", e)
        return []
    out: List[Dict[str, Any]] = []
    for entry in logs:
        try:
            root_hex = entry["topics"][2].hex()
            out.append({
                "storage_root": root_hex if root_hex.startswith("0x") else "0x" + root_hex,
                "tx_hash": "0x" + entry["transactionHash"].hex(),
                "block_number": int(entry["blockNumber"]),
            })
        except Exception:
            continue
    return out


# === Sepolia: BillRegistry mirror, DisputeRegistry, AppealRegistry ===========

def _read_sepolia_events_sync(sha256_hex: str) -> Dict[str, Any]:
    from web3 import Web3
    if not settings.sepolia_rpc_url:
        return {}
    w3 = Web3(Web3.HTTPProvider(settings.sepolia_rpc_url, request_kwargs={"timeout": 10}))
    if not w3.is_connected():
        return {}
    sha = sha256_hex if sha256_hex.startswith("0x") else "0x" + sha256_hex

    def _filter(addr: Optional[str], topic_sig: str) -> List[Dict[str, Any]]:
        if not addr:
            return []
        try:
            logs = w3.eth.get_logs({
                "address": Web3.to_checksum_address(addr),
                "topics": [_safe_topic(topic_sig), sha],
                "fromBlock": "earliest", "toBlock": "latest",
            })
        except Exception as e:
            log.debug("sepolia getLogs %s failed: %s", topic_sig, e)
            return []
        return [
            {
                "tx_hash": "0x" + entry["transactionHash"].hex(),
                "block_number": int(entry["blockNumber"]),
            }
            for entry in logs
        ]

    return {
        "chain_id": 11155111,
        "mirror": _filter(
            settings.bill_registry_address_sepolia,
            "Anchored(bytes32,uint8,uint8,uint8,uint64,address)",
        ),
        "disputes": _filter(
            settings.dispute_registry_address_sepolia,
            "DisputeFiled(bytes32,uint8,string,uint64,address,uint256)",
        ),
        "appeals": _filter(
            settings.appeal_registry_address_sepolia,
            "AppealSent(bytes32,bytes32,uint64,address,uint256)",
        ),
    }


# === 0G Storage: download the latest blob via the sidecar ====================

async def _download_latest_storage_blob(roots: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not roots or not settings.zg_storage_sidecar_url:
        return None
    latest = max(roots, key=lambda r: r.get("block_number", 0))
    root = latest.get("storage_root")
    if not root:
        return None
    sidecar = settings.zg_storage_sidecar_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(f"{sidecar}/download", params={"root": root})
            if r.status_code != 200:
                return None
            try:
                blob = json.loads(r.content.decode("utf-8"))
            except Exception:
                return None
            return {"root_hash": root, "blob": blob}
    except Exception as e:
        log.debug("storage download failed: %s", e)
        return None


# === route ==================================================================

@router.get("/{sha256}")
async def verify(sha256: str) -> Dict[str, Any]:
    """Comprehensive lookup — every artifact this hash produced, fanned out
    in parallel across both chains. Frontend renders the whole picture.
    """
    sha = _normalize_sha(sha256)
    sha_0x = "0x" + sha

    galileo_anchor, pattern_events, storage_pointers, sepolia = await asyncio.gather(
        asyncio.to_thread(_read_galileo_anchor_sync, sha),
        asyncio.to_thread(_read_pattern_events_sync, sha),
        asyncio.to_thread(_read_storage_pointers_sync, sha),
        asyncio.to_thread(_read_sepolia_events_sync, sha),
    )

    storage_blob = await _download_latest_storage_blob(storage_pointers)

    # Top-level "anchored" stays in the response so existing UI keeps working.
    return {
        "sha256": sha_0x,
        "anchored": galileo_anchor.get("anchored", False),
        # Legacy flat fields (for compatibility with the old verify UI)
        "verdict": galileo_anchor.get("verdict"),
        "verdict_int": galileo_anchor.get("verdict_int"),
        "agree_count": galileo_anchor.get("agree_count"),
        "total_agents": galileo_anchor.get("total_agents"),
        "anchored_at": galileo_anchor.get("anchored_at"),
        "anchored_by": galileo_anchor.get("anchored_by"),
        "registry_address": galileo_anchor.get("registry_address") or settings.bill_registry_address,
        "network": "0g-galileo-testnet",
        "chain_id": galileo_anchor.get("chain_id"),
        # Comprehensive data
        "galileo": {
            "anchor": galileo_anchor,
            "pattern_registry": {
                "address": settings.pattern_registry_address or None,
                "findings": pattern_events,
                "count": len(pattern_events),
            },
            "storage_index": {
                "address": settings.storage_index_address or None,
                "pointers": storage_pointers,
                "count": len(storage_pointers),
            },
        },
        "sepolia": sepolia,
        "storage": storage_blob,
    }
