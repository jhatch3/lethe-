"""0G Chain anchor.

When `BILL_REGISTRY_ADDRESS` and `ZG_PRIVATE_KEY` are configured, anchors
the bill SHA-256 + verdict on 0G Galileo via a real `BillRegistry.anchor` call.
Falls back to a deterministic stub tx hash when chain config is missing,
so the rest of the pipeline keeps working in dev environments without keys.

Privacy:
- Only the SHA-256 (32 bytes), verdict enum, and agent counts are written.
- No PHI, no bill bytes, no findings descriptions.
- The pre-image of the SHA-256 is never persisted on-chain.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Dict

from config import settings

log = logging.getLogger("lethe.chain.zerog")


# Verdict enum mirrors BillRegistry.sol — keep in sync.
_VERDICT_ENUM = {"none": 0, "dispute": 1, "approve": 2, "clarify": 3}
_VERDICT_REVERSE = {v: k for k, v in _VERDICT_ENUM.items()}

# Minimal ABI for the methods we call. Avoids loading the full deploy artifact at runtime.
_ANCHOR_ABI = [
    {
        "type": "function",
        "name": "anchor",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "sha256Hash", "type": "bytes32"},
            {"name": "verdict", "type": "uint8"},
            {"name": "agreeCount", "type": "uint8"},
            {"name": "totalAgents", "type": "uint8"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "isAnchored",
        "stateMutability": "view",
        "inputs": [{"name": "sha256Hash", "type": "bytes32"}],
        "outputs": [{"type": "bool"}],
    },
    {
        "type": "function",
        "name": "anchors",
        "stateMutability": "view",
        "inputs": [{"name": "", "type": "bytes32"}],
        "outputs": [
            {"name": "verdict", "type": "uint8"},
            {"name": "agreeCount", "type": "uint8"},
            {"name": "totalAgents", "type": "uint8"},
            {"name": "anchoredAt", "type": "uint64"},
            {"name": "anchoredBy", "type": "address"},
        ],
    },
]


def _stub(sha256: str, reason: str) -> Dict[str, Any]:
    tx = "0x" + hashlib.sha256(("anchor:" + sha256).encode()).hexdigest()[:40]
    return {
        "network": "0g-galileo-testnet",
        "bill_sha256": sha256,
        "anchor_tx": tx,
        "executor": f"stub ({reason})",
        "status": "confirmed",
        "live": False,
    }


def _do_anchor_sync(
    sha256_hex: str,
    verdict: str,
    agree_count: int,
    total_agents: int,
) -> Dict[str, Any]:
    """Synchronous web3 call — runs inside asyncio.to_thread."""
    from web3 import Web3
    from eth_account import Account

    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url))
    if not w3.is_connected():
        raise RuntimeError(f"0G RPC unreachable: {settings.zg_rpc_url}")

    chain_id = w3.eth.chain_id
    if chain_id != settings.zg_chain_id:
        log.warning(
            "chain id mismatch: configured=%d, rpc reports=%d — using RPC value",
            settings.zg_chain_id, chain_id,
        )

    acct = Account.from_key(settings.zg_private_key)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.bill_registry_address),
        abi=_ANCHOR_ABI,
    )

    sha = "0x" + sha256_hex if not sha256_hex.startswith("0x") else sha256_hex
    sha_bytes = bytes.fromhex(sha[2:])
    verdict_int = _VERDICT_ENUM.get(verdict.lower(), 0)
    if verdict_int == 0:
        # Skip anchoring meaningless verdicts (None / unrecognized)
        return _stub(sha256_hex, f"verdict={verdict} not anchored")
    agree = max(1, min(int(agree_count), int(total_agents)))
    total = max(agree, int(total_agents))

    tx = contract.functions.anchor(sha_bytes, verdict_int, agree, total).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
        "chainId": chain_id,
        "type": 2,
        "maxFeePerGas": w3.to_wei(6, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(4, "gwei"),
        "gas": 200_000,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90, poll_latency=2)

    # Read back from the contract to confirm the on-chain state matches what we sent.
    onchain = contract.functions.anchors(sha_bytes).call()
    onchain_verdict_int = int(onchain[0])
    onchain_decoded = {
        "verdict": _VERDICT_REVERSE.get(onchain_verdict_int, "unknown"),
        "verdict_int": onchain_verdict_int,
        "agree_count": int(onchain[1]),
        "total_agents": int(onchain[2]),
        "anchored_at": int(onchain[3]),
        "anchored_by": onchain[4],
    }

    tx_hex = tx_hash.hex()
    return {
        "network": "0g-galileo-testnet",
        "chain_id": chain_id,
        "bill_sha256": sha256_hex,
        "anchor_tx": tx_hex if tx_hex.startswith("0x") else "0x" + tx_hex,
        "block_number": receipt.blockNumber,
        "registry_address": settings.bill_registry_address,
        "executor": "0g-direct",
        "status": "confirmed" if receipt.status == 1 else "reverted",
        "gas_used": receipt.gasUsed,
        "onchain": onchain_decoded,
        "live": True,
    }


async def anchor(
    sha256: str,
    simulated_delay_ms: int,
    verdict: str = "dispute",
    agree_count: int = 3,
    total_agents: int = 3,
) -> Dict[str, Any]:
    """Anchor the bill hash + verdict on 0G Galileo.

    Falls back to a deterministic stub tx if any config is missing or the
    on-chain call fails — this keeps the rest of the pipeline running.
    """
    if not (settings.zg_private_key and settings.bill_registry_address):
        await asyncio.sleep(simulated_delay_ms / 1000)
        return _stub(sha256, "no key/address")

    try:
        proof = await asyncio.to_thread(
            _do_anchor_sync, sha256, verdict, agree_count, total_agents,
        )
        log.info("anchored sha256=%s tx=%s block=%s",
                 sha256[:12], proof.get("anchor_tx", "")[:18], proof.get("block_number"))
        return proof
    except Exception as e:
        msg = str(e).lower()
        if "already anchored" in msg or "execution reverted" in msg:
            # Re-anchoring the same bill — read back what's already on-chain.
            log.info("sha256=%s already anchored — reading existing state", sha256[:12])
            try:
                existing = await asyncio.to_thread(_read_existing_sync, sha256)
                return existing
            except Exception as inner:
                log.warning("read-back after duplicate failed: %s", inner)
                return {**_stub(sha256, "duplicate"), "executor": "0g-direct (duplicate)"}
        log.warning("anchor failed: %s — falling back to stub", e)
        return _stub(sha256, f"error: {type(e).__name__}")


def _read_existing_sync(sha256_hex: str) -> Dict[str, Any]:
    """Read on-chain state for a previously-anchored bill."""
    from web3 import Web3

    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url))
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.bill_registry_address),
        abi=_ANCHOR_ABI,
    )
    sha = "0x" + sha256_hex if not sha256_hex.startswith("0x") else sha256_hex
    sha_bytes = bytes.fromhex(sha[2:])
    rec = contract.functions.anchors(sha_bytes).call()
    onchain_verdict_int = int(rec[0])
    return {
        "network": "0g-galileo-testnet",
        "chain_id": w3.eth.chain_id,
        "bill_sha256": sha256_hex,
        "anchor_tx": None,
        "block_number": None,
        "registry_address": settings.bill_registry_address,
        "executor": "0g-direct (already anchored)",
        "status": "confirmed",
        "gas_used": 0,
        "onchain": {
            "verdict": _VERDICT_REVERSE.get(onchain_verdict_int, "unknown"),
            "verdict_int": onchain_verdict_int,
            "agree_count": int(rec[1]),
            "total_agents": int(rec[2]),
            "anchored_at": int(rec[3]),
            "anchored_by": rec[4],
        },
        "live": True,
    }