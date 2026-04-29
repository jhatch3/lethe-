"""LetheRegistry — unified anchor + findings + dispute + appeal + provider stats + rulebook pointer.

Replaces the previous 5-contract surface (BillRegistry · PatternRegistry ·
StorageIndex · ProviderReputation · NCCIRulebook) with a single contract address.
The DisputeRegistry / AppealRegistry methods (`recordDispute`, `recordAppealSent`)
still target this same contract on Sepolia via KeeperHub workflows; only the
deployment topology consolidated.

Stub fallback at every layer so the pipeline keeps running when chain config
is missing (judge demos without a wallet still work).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, Dict, Iterable, List, Optional

from config import settings

log = logging.getLogger("lethe.chain.lethe_registry")


# === Verdict enum mirrors LetheRegistry.sol — keep in sync. ===
_VERDICT_ENUM = {"none": 0, "dispute": 1, "approve": 2, "clarify": 3}
_VERDICT_REVERSE = {v: k for k, v in _VERDICT_ENUM.items()}


# === Minimal ABI: only the methods + events the coordinator actually uses. ===
_ABI: List[Dict[str, Any]] = [
    {
        "type": "function", "name": "anchor", "stateMutability": "nonpayable",
        "inputs": [
            {"name": "billHash", "type": "bytes32"},
            {"name": "verdict", "type": "uint8"},
            {"name": "agreeCount", "type": "uint8"},
            {"name": "totalAgents", "type": "uint8"},
            {"name": "npiHash", "type": "bytes32"},
            {"name": "storageRoot", "type": "bytes32"},
            {"name": "rulebookVersion", "type": "uint16"},
            {"name": "flaggedCents", "type": "uint64"},
        ],
        "outputs": [],
    },
    {
        "type": "function", "name": "indexFindings", "stateMutability": "nonpayable",
        "inputs": [
            {"name": "billHash", "type": "bytes32"},
            {"name": "codes", "type": "bytes32[]"},
            {"name": "actions", "type": "bytes16[]"},
            {"name": "severities", "type": "bytes8[]"},
            {"name": "amountsCents", "type": "uint64[]"},
            {"name": "voters", "type": "uint8[]"},
        ],
        "outputs": [],
    },
    {
        "type": "function", "name": "recordDispute", "stateMutability": "nonpayable",
        "inputs": [
            {"name": "billHash", "type": "bytes32"},
            {"name": "reason", "type": "uint8"},
            {"name": "note", "type": "string"},
        ],
        "outputs": [],
    },
    {
        "type": "function", "name": "recordAppealSent", "stateMutability": "nonpayable",
        "inputs": [
            {"name": "billHash", "type": "bytes32"},
            {"name": "recipientHash", "type": "bytes32"},
        ],
        "outputs": [],
    },
    {
        "type": "function", "name": "publishRulebook", "stateMutability": "nonpayable",
        "inputs": [
            {"name": "version", "type": "uint16"},
            {"name": "manifestRoot", "type": "bytes32"},
        ],
        "outputs": [],
    },
    {
        "type": "function", "name": "anchors", "stateMutability": "view",
        "inputs": [{"name": "", "type": "bytes32"}],
        "outputs": [
            {"name": "verdict", "type": "uint8"},
            {"name": "agreeCount", "type": "uint8"},
            {"name": "totalAgents", "type": "uint8"},
            {"name": "npiHash", "type": "bytes32"},
            {"name": "storageRoot", "type": "bytes32"},
            {"name": "rulebookVersion", "type": "uint16"},
            {"name": "anchoredAt", "type": "uint64"},
            {"name": "anchoredBy", "type": "address"},
        ],
    },
    {
        "type": "function", "name": "providerStats", "stateMutability": "view",
        "inputs": [{"name": "", "type": "bytes32"}],
        "outputs": [
            {"name": "totalAudits", "type": "uint32"},
            {"name": "disputeCount", "type": "uint32"},
            {"name": "clarifyCount", "type": "uint32"},
            {"name": "approveCount", "type": "uint32"},
            {"name": "totalFlaggedCents", "type": "uint128"},
        ],
    },
    {
        "type": "function", "name": "rulebookManifest", "stateMutability": "view",
        "inputs": [{"name": "", "type": "uint16"}],
        "outputs": [{"name": "", "type": "bytes32"}],
    },
    {
        "type": "function", "name": "currentRulebookVersion", "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint16"}],
    },
    {
        "type": "function", "name": "isAnchored", "stateMutability": "view",
        "inputs": [{"name": "billHash", "type": "bytes32"}],
        "outputs": [{"type": "bool"}],
    },
    # Events (for eth_getLogs)
    {
        "type": "event", "name": "BillAnchored", "anonymous": False,
        "inputs": [
            {"name": "billHash", "type": "bytes32", "indexed": True},
            {"name": "npiHash", "type": "bytes32", "indexed": True},
            {"name": "verdict", "type": "uint8", "indexed": False},
            {"name": "agreeCount", "type": "uint8", "indexed": False},
            {"name": "totalAgents", "type": "uint8", "indexed": False},
            {"name": "storageRoot", "type": "bytes32", "indexed": False},
            {"name": "rulebookVersion", "type": "uint16", "indexed": False},
            {"name": "flaggedCents", "type": "uint64", "indexed": False},
            {"name": "anchoredAt", "type": "uint64", "indexed": False},
            {"name": "anchoredBy", "type": "address", "indexed": True},
        ],
    },
    {
        "type": "event", "name": "Finding", "anonymous": False,
        "inputs": [
            {"name": "billHash", "type": "bytes32", "indexed": True},
            {"name": "code", "type": "bytes32", "indexed": True},
            {"name": "action", "type": "bytes16", "indexed": False},
            {"name": "severity", "type": "bytes8", "indexed": False},
            {"name": "amountCents", "type": "uint64", "indexed": False},
            {"name": "voters", "type": "uint8", "indexed": False},
            {"name": "indexedBy", "type": "address", "indexed": True},
            {"name": "indexedAt", "type": "uint64", "indexed": False},
        ],
    },
]


# === Helpers ===

def _hex_to_bytes32(hex_or_prefixed: str) -> bytes:
    s = hex_or_prefixed.lower().removeprefix("0x")
    if len(s) != 64:
        raise ValueError(f"expected 32-byte hex, got len={len(s)}")
    return bytes.fromhex(s)


def _bytes_to_left_padded(s: str, width: int) -> bytes:
    """Pack an ASCII string into left-padded bytes (matches Solidity bytes32/16/8 zero-pad)."""
    b = s.encode("ascii", errors="ignore")[:width]
    return b + b"\x00" * (width - len(b))


def _stub(sha256: str, reason: str, kind: str = "anchor") -> Dict[str, Any]:
    tx = "0x" + hashlib.sha256(f"{kind}:{sha256}:{reason}".encode()).hexdigest()
    return {
        "network": "0g-galileo-testnet",
        "bill_sha256": sha256,
        "anchor_tx": tx,
        "executor": f"stub ({reason})",
        "status": "confirmed",
        "live": False,
    }


def _registry_address() -> Optional[str]:
    """Resolve the LetheRegistry address from settings, prefer new env var, fall back to legacy."""
    addr = getattr(settings, "lethe_registry_address", None)
    if not addr:
        # Backward-compat shim: until LETHE_REGISTRY_ADDRESS is set, fall back
        # to BILL_REGISTRY_ADDRESS (treated as the unified registry on Galileo).
        addr = getattr(settings, "bill_registry_address", None)
    return addr or None


# === Sync (web3.py) workers — run inside asyncio.to_thread ===

def _build_w3():
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url))
    if not w3.is_connected():
        raise RuntimeError(f"0G RPC unreachable: {settings.zg_rpc_url}")
    return w3


def _contract(w3):
    from web3 import Web3
    return w3.eth.contract(
        address=Web3.to_checksum_address(_registry_address()),
        abi=_ABI,
    )


def _do_anchor_sync(
    sha256_hex: str,
    verdict: str,
    agree_count: int,
    total_agents: int,
    npi_hash_hex: str,
    storage_root_hex: str,
    rulebook_version: int,
    flagged_cents: int,
) -> Dict[str, Any]:
    from eth_account import Account

    w3 = _build_w3()
    chain_id = w3.eth.chain_id
    acct = Account.from_key(settings.zg_private_key)
    contract = _contract(w3)

    bill_bytes = _hex_to_bytes32(sha256_hex)
    npi_bytes = _hex_to_bytes32(npi_hash_hex) if npi_hash_hex else b"\x00" * 32
    root_bytes = _hex_to_bytes32(storage_root_hex) if storage_root_hex else b"\x00" * 32

    verdict_int = _VERDICT_ENUM.get(verdict.lower(), 0)
    if verdict_int == 0:
        return _stub(sha256_hex, f"verdict={verdict} not anchored")

    agree = max(1, min(int(agree_count), int(total_agents)))
    total = max(agree, int(total_agents))

    tx = contract.functions.anchor(
        bill_bytes, verdict_int, agree, total,
        npi_bytes, root_bytes, int(rulebook_version), int(flagged_cents),
    ).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
        "chainId": chain_id,
        "type": 2,
        "maxFeePerGas": w3.to_wei(6, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(4, "gwei"),
        "gas": 350_000,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=2)

    onchain = contract.functions.anchors(bill_bytes).call()
    tx_hex = tx_hash.hex()
    return {
        "network": "0g-galileo-testnet",
        "chain_id": chain_id,
        "bill_sha256": sha256_hex,
        "anchor_tx": tx_hex if tx_hex.startswith("0x") else "0x" + tx_hex,
        "block_number": receipt.blockNumber,
        "registry_address": _registry_address(),
        "executor": "lethe-registry-direct",
        "status": "confirmed" if receipt.status == 1 else "reverted",
        "gas_used": receipt.gasUsed,
        "onchain": {
            "verdict": _VERDICT_REVERSE.get(int(onchain[0]), "unknown"),
            "verdict_int": int(onchain[0]),
            "agree_count": int(onchain[1]),
            "total_agents": int(onchain[2]),
            "npi_hash": "0x" + onchain[3].hex(),
            "storage_root": "0x" + onchain[4].hex(),
            "rulebook_version": int(onchain[5]),
            "anchored_at": int(onchain[6]),
            "anchored_by": onchain[7],
        },
        "live": True,
    }


def _do_index_findings_sync(sha256_hex: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    from eth_account import Account

    w3 = _build_w3()
    chain_id = w3.eth.chain_id
    acct = Account.from_key(settings.zg_private_key)
    contract = _contract(w3)

    bill_bytes = _hex_to_bytes32(sha256_hex)
    codes      = [_bytes_to_left_padded(str(f.get("code", "")),     32) for f in findings]
    actions    = [_bytes_to_left_padded(str(f.get("action", "")),   16) for f in findings]
    severities = [_bytes_to_left_padded(str(f.get("severity", "")),  8) for f in findings]
    amounts    = [int(round(float(f.get("amount_usd") or 0) * 100))     for f in findings]
    voters     = [int(f.get("voters_bitmask") or 0)                     for f in findings]

    if not codes:
        return {"executor": "noop (no findings)", "live": False, "count": 0}

    tx = contract.functions.indexFindings(
        bill_bytes, codes, actions, severities, amounts, voters,
    ).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
        "chainId": chain_id,
        "type": 2,
        "maxFeePerGas": w3.to_wei(6, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(4, "gwei"),
        "gas": 200_000 + 80_000 * len(codes),
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120, poll_latency=2)
    tx_hex = tx_hash.hex()
    return {
        "executor": "lethe-registry-direct",
        "tx_hash": tx_hex if tx_hex.startswith("0x") else "0x" + tx_hex,
        "block_number": receipt.blockNumber,
        "registry_address": _registry_address(),
        "count": len(codes),
        "gas_used": receipt.gasUsed,
        "live": True,
    }


def _read_anchor_sync(sha256_hex: str) -> Dict[str, Any]:
    w3 = _build_w3()
    contract = _contract(w3)
    bill_bytes = _hex_to_bytes32(sha256_hex)
    rec = contract.functions.anchors(bill_bytes).call()
    return {
        "verdict": _VERDICT_REVERSE.get(int(rec[0]), "unknown"),
        "verdict_int": int(rec[0]),
        "agree_count": int(rec[1]),
        "total_agents": int(rec[2]),
        "npi_hash": "0x" + rec[3].hex(),
        "storage_root": "0x" + rec[4].hex(),
        "rulebook_version": int(rec[5]),
        "anchored_at": int(rec[6]),
        "anchored_by": rec[7],
        "registry_address": _registry_address(),
        "chain_id": w3.eth.chain_id,
    }


def _read_provider_stats_sync(npi_hash_hex: str) -> Dict[str, Any]:
    w3 = _build_w3()
    contract = _contract(w3)
    npi_bytes = _hex_to_bytes32(npi_hash_hex)
    s = contract.functions.providerStats(npi_bytes).call()
    return {
        "total_audits": int(s[0]),
        "dispute_count": int(s[1]),
        "clarify_count": int(s[2]),
        "approve_count": int(s[3]),
        "total_flagged_cents": int(s[4]),
        "registry_address": _registry_address(),
    }


def _read_rulebook_manifest_sync(version: Optional[int] = None) -> Dict[str, Any]:
    w3 = _build_w3()
    contract = _contract(w3)
    if version is None:
        version = int(contract.functions.currentRulebookVersion().call())
    root = contract.functions.rulebookManifest(int(version)).call()
    return {
        "version": int(version),
        "manifest_root": "0x" + root.hex(),
        "registry_address": _registry_address(),
    }


# === Async public surface ===

async def anchor(
    sha256: str,
    *,
    verdict: str = "dispute",
    agree_count: int = 3,
    total_agents: int = 3,
    npi_hash: str = "",
    storage_root: str = "",
    rulebook_version: int = 1,
    flagged_cents: int = 0,
    simulated_delay_ms: int = 0,
) -> Dict[str, Any]:
    """Anchor a bill audit on the canonical chain. Falls back to stub on missing config."""
    if not (settings.zg_private_key and _registry_address()):
        if simulated_delay_ms:
            await asyncio.sleep(simulated_delay_ms / 1000)
        return _stub(sha256, "no key/address")
    try:
        proof = await asyncio.to_thread(
            _do_anchor_sync,
            sha256, verdict, agree_count, total_agents,
            npi_hash, storage_root, rulebook_version, flagged_cents,
        )
        log.info(
            "anchored sha=%s tx=%s verdict=%s npi=%s findings=root%s",
            sha256[:12], proof.get("anchor_tx", "")[:18], verdict,
            (npi_hash or "")[:10] or "—",
            (storage_root or "")[:10] or "—",
        )
        return proof
    except Exception as e:
        msg = str(e).lower()
        if "already anchored" in msg or "execution reverted" in msg:
            log.info("sha=%s already anchored — reading existing state", sha256[:12])
            try:
                onchain = await asyncio.to_thread(_read_anchor_sync, sha256)
                return {
                    **_stub(sha256, "duplicate"),
                    "executor": "lethe-registry-direct (duplicate)",
                    "registry_address": _registry_address(),
                    "onchain": onchain,
                    "live": True,
                }
            except Exception as inner:
                log.warning("read-back after duplicate failed: %s", inner)
        log.warning("anchor failed: %s — falling back to stub", e)
        return _stub(sha256, f"error: {type(e).__name__}")


async def index_findings(sha256: str, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Emit Finding events for each consensus finding. Replaces PatternRegistry.indexBatch."""
    if not (settings.zg_private_key and _registry_address()):
        return {"executor": "stub (no key/address)", "live": False, "count": len(findings)}
    if not findings:
        return {"executor": "noop", "live": False, "count": 0}
    try:
        return await asyncio.to_thread(_do_index_findings_sync, sha256, findings)
    except Exception as e:
        log.warning("index_findings failed: %s — degraded", e)
        return {"executor": f"error ({type(e).__name__})", "live": False, "count": len(findings)}


async def fetch_anchor(sha256: str) -> Optional[Dict[str, Any]]:
    """Read the on-chain anchor record for a bill. Returns None if not anchored or no config."""
    if not _registry_address():
        return None
    try:
        rec = await asyncio.to_thread(_read_anchor_sync, sha256)
        if rec.get("anchored_at") == 0:
            return None
        return rec
    except Exception as e:
        log.warning("fetch_anchor failed: %s", e)
        return None


async def fetch_provider_stats(npi_hash: str) -> Optional[Dict[str, Any]]:
    """Read aggregate provider stats by NPI hash. Returns None if no config."""
    if not _registry_address():
        return None
    try:
        return await asyncio.to_thread(_read_provider_stats_sync, npi_hash)
    except Exception as e:
        log.warning("fetch_provider_stats failed: %s", e)
        return None


async def fetch_rulebook_manifest(version: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Read the rulebook manifest pointer for a version (or current if None)."""
    if not _registry_address():
        return None
    try:
        return await asyncio.to_thread(_read_rulebook_manifest_sync, version)
    except Exception as e:
        log.warning("fetch_rulebook_manifest failed: %s", e)
        return None


def hash_npi(npi: str, salt: str = "lethe-npi-v1") -> str:
    """Derive the bytes32 NPI hash that gets stored on chain (salted SHA-256)."""
    npi_clean = "".join(c for c in (npi or "") if c.isdigit())
    if len(npi_clean) != 10:
        return ""
    digest = hashlib.sha256(f"{salt}:{npi_clean}".encode()).hexdigest()
    return "0x" + digest


def voters_bitmask(voted_by: Iterable[str]) -> int:
    """alpha=bit0, beta=bit1, gamma=bit2 — matches LetheRegistry.Finding.voters."""
    bit = {"alpha": 1, "beta": 2, "gamma": 4}
    mask = 0
    for v in voted_by or []:
        mask |= bit.get(str(v).lower(), 0)
    return mask
