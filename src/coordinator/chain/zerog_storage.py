"""0G Chain pattern indexer.

After consensus, posts each finding's anonymized pattern to the on-chain
`PatternRegistry`. The bill SHA-256 is the join key (links back to BillRegistry);
the rest is generic billing-error metadata that contains no PHI.

Why on-chain events instead of 0G Storage SDK:
    The official 0G Storage Python SDK on PyPI ships broken — its modules use
    relative imports beyond the top-level package and a `config.py` shim that
    isn't included. We use Galileo Chain events as the persistence layer
    instead. Same network, indexable, queryable, sponsor-defensible.
    Migrating to 0G Storage proper is straightforward once the SDK is fixed.

Privacy:
    - Codes are public taxonomy (CPT 99214, HCPCS J3490, REV 0450, etc.).
    - Severity, action, amount are aggregated audit metadata, not patient data.
    - No descriptions, names, dates, or any free-text are written.
    - The `voters` field is a 3-bit mask (alpha=1, beta=2, gamma=4) — no PII.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Tuple

from config import settings

log = logging.getLogger("lethe.chain.patterns")


_PATTERN_ABI = [
    {
        "type": "function",
        "name": "indexBatch",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "billHash", "type": "bytes32"},
            {"name": "codes", "type": "bytes32[]"},
            {"name": "actions", "type": "bytes16[]"},
            {"name": "severities", "type": "bytes8[]"},
            {"name": "amountsUsd", "type": "uint64[]"},
            {"name": "voters", "type": "uint8[]"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "totalPatterns",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "uint64"}],
    },
]


_AGENT_BIT = {"alpha": 1, "beta": 2, "gamma": 4}


def _to_bytes32_str(s: str) -> bytes:
    """Encode a short ASCII string into bytes32 (right-padded with zeros).

    Falls back to truncating long strings — codes like 'CPT 99214' are short.
    """
    raw = s.encode("ascii", errors="replace")[:32]
    return raw + b"\x00" * (32 - len(raw))


def _to_bytesN_str(s: str, n: int) -> bytes:
    raw = s.encode("ascii", errors="replace")[:n]
    return raw + b"\x00" * (n - len(raw))


def _voters_mask(voted_by: List[str]) -> int:
    return sum(_AGENT_BIT.get(a, 0) for a in (voted_by or []))


def _stub(reason: str) -> Dict[str, Any]:
    return {"executor": f"stub ({reason})", "live": False, "patterns_indexed": 0}


def _build_args(consensus: Dict[str, Any], sha256_hex: str) -> Tuple[bytes, list, list, list, list, list]:
    sha = sha256_hex[2:] if sha256_hex.startswith("0x") else sha256_hex
    bill_hash = bytes.fromhex(sha)

    findings: List[Dict[str, Any]] = consensus.get("findings", []) or []
    codes, actions, severities, amounts, voters = [], [], [], [], []
    for f in findings:
        codes.append(_to_bytes32_str(str(f.get("code", "") or "")))
        actions.append(_to_bytesN_str(str(f.get("action", "") or "info"), 16))
        severities.append(_to_bytesN_str(str(f.get("severity", "") or "info"), 8))
        # Convert dollar amount → cents (uint64). $185.00 → 18500
        amt = float(f.get("amount_usd", 0) or 0)
        amounts.append(int(round(amt * 100)))
        voters.append(_voters_mask(f.get("voted_by", []) or []))
    return bill_hash, codes, actions, severities, amounts, voters


def _do_index_sync(consensus: Dict[str, Any], sha256_hex: str) -> Dict[str, Any]:
    from web3 import Web3
    from eth_account import Account

    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url))
    if not w3.is_connected():
        raise RuntimeError("0G RPC unreachable")

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.pattern_registry_address),
        abi=_PATTERN_ABI,
    )
    bill_hash, codes, actions, severities, amounts, voters = _build_args(consensus, sha256_hex)
    if not codes:
        return _stub("no findings to index")

    acct = Account.from_key(settings.zg_private_key)
    chain_id = w3.eth.chain_id

    tx = contract.functions.indexBatch(
        bill_hash, codes, actions, severities, amounts, voters,
    ).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
        "chainId": chain_id,
        "type": 2,
        "maxFeePerGas": w3.to_wei(6, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(4, "gwei"),
        "gas": 80_000 + 35_000 * len(codes),
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90, poll_latency=2)

    tx_hex = tx_hash.hex()
    return {
        "executor": "0g-direct-pattern",
        "live": True,
        "patterns_indexed": len(codes),
        "tx": tx_hex if tx_hex.startswith("0x") else "0x" + tx_hex,
        "block_number": receipt.blockNumber,
        "registry_address": settings.pattern_registry_address,
        "network": "0g-galileo-testnet",
        "chain_id": chain_id,
        "gas_used": receipt.gasUsed,
        "status": "confirmed" if receipt.status == 1 else "reverted",
    }


async def index_patterns(consensus: Dict[str, Any], sha256_hex: str) -> Dict[str, Any]:
    """Persist anonymized findings to PatternRegistry on 0G Galileo.

    Falls back to a stub result if the registry isn't configured or the call
    fails — the rest of the pipeline keeps working.
    """
    if not (settings.zg_private_key and settings.pattern_registry_address):
        return _stub("no key/address")
    try:
        result = await asyncio.to_thread(_do_index_sync, consensus, sha256_hex)
        log.info(
            "indexed %d patterns sha=%s tx=%s block=%s",
            result.get("patterns_indexed", 0),
            sha256_hex[:12],
            (result.get("tx") or "")[:18],
            result.get("block_number"),
        )
        return result
    except Exception as e:
        log.warning("pattern index failed: %s — stubbing", e)
        return {**_stub(f"error: {type(e).__name__}"), "error": str(e)[:200]}
