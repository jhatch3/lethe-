"""ProviderReputation chain writes.

Records every audit's outcome against the provider's hashed NPI to the
public on-chain reputation contract on 0G Galileo. Anyone can query the
contract's stats[npiHash] for total audits + dispute / clarify / approve
counts + total flagged cents — a censorship-resistant provider scoring
system that doesn't depend on any centralized rating service.

Privacy:
    NPI is public registry data (cms.gov NPPES), not PHI. We hash it
    before storage so explorers don't show plaintext provider tax IDs,
    and use a process-wide salt so different deployments produce
    different hashes for the same NPI (avoids cross-deploy leakage).

Behavior:
    Stub-fallback when the contract isn't configured or an NPI can't
    be extracted from the audit. Pipeline always continues.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from typing import Any, Dict, Optional

from config import settings

log = logging.getLogger("lethe.chain.provider_reputation")


_VERDICT_TO_INT = {"none": 0, "dispute": 1, "approve": 2, "clarify": 3}

_PROVIDER_REPUTATION_ABI = [
    {
        "type": "function",
        "name": "recordAudit",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "npiHash",      "type": "bytes32"},
            {"name": "billHash",     "type": "bytes32"},
            {"name": "verdict",      "type": "uint8"},
            {"name": "agreeCount",   "type": "uint8"},
            {"name": "totalAgents",  "type": "uint8"},
            {"name": "flaggedCents", "type": "uint64"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "stats",
        "stateMutability": "view",
        "inputs": [{"name": "npiHash", "type": "bytes32"}],
        "outputs": [
            {"name": "totalAudits",       "type": "uint32"},
            {"name": "disputeCount",      "type": "uint32"},
            {"name": "clarifyCount",      "type": "uint32"},
            {"name": "approveCount",      "type": "uint32"},
            {"name": "totalFlaggedCents", "type": "uint128"},
        ],
    },
]


# 10-digit NPI per CMS spec. Surface area is intentionally tight — we
# don't want to false-positive on random 10-digit numbers in the bill.
_NPI_PATTERN = re.compile(r"\bNPI[\s:]*\(?(\d{10})\)?", re.IGNORECASE)


def extract_npi(bill_text: str) -> Optional[str]:
    """Best-effort NPI extraction from parsed bill text. Returns None when
    no plausible NPI is found (e.g. anonymized or unstructured bills)."""
    if not bill_text:
        return None
    m = _NPI_PATTERN.search(bill_text)
    return m.group(1) if m else None


def hash_npi(npi: str, salt: str = "lethe-npi-v1") -> str:
    """Salted keccak-style hash of an NPI string. We use SHA-256 here
    instead of keccak to avoid a web3 import in the redactor module —
    the contract treats it as opaque bytes32."""
    h = hashlib.sha256(f"{salt}:{npi.strip()}".encode("utf-8")).hexdigest()
    return "0x" + h


def _stub(reason: str) -> Dict[str, Any]:
    return {"executor": f"stub ({reason})", "live": False}


def _do_record_sync(
    npi_hash_hex: str,
    bill_hash_hex: str,
    verdict_int: int,
    agree_count: int,
    total_agents: int,
    flagged_cents: int,
) -> Dict[str, Any]:
    from web3 import Web3
    from eth_account import Account

    w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url))
    if not w3.is_connected():
        raise RuntimeError("0G RPC unreachable")
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(settings.provider_reputation_address),
        abi=_PROVIDER_REPUTATION_ABI,
    )
    acct = Account.from_key(settings.zg_private_key)

    sha = bill_hash_hex[2:] if bill_hash_hex.startswith("0x") else bill_hash_hex
    npi_h = npi_hash_hex[2:] if npi_hash_hex.startswith("0x") else npi_hash_hex

    tx = contract.functions.recordAudit(
        bytes.fromhex(npi_h),
        bytes.fromhex(sha),
        verdict_int,
        max(0, min(255, agree_count)),
        max(0, min(255, total_agents)),
        max(0, min((1 << 64) - 1, flagged_cents)),
    ).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
        "chainId": w3.eth.chain_id,
        "type": 2,
        "maxFeePerGas": w3.to_wei(6, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(4, "gwei"),
        # 5 SSTOREs into a cold slot (~41k each first time) plus event emit
        # plus call overhead. 110k was an OOG silent revert — bumping past
        # the worst-case cold-write budget.
        "gas": 300_000,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90, poll_latency=2)
    tx_hex = tx_hash.hex()
    if receipt.status != 1:
        raise RuntimeError(
            f"recordAudit reverted on-chain (gas_used={receipt.gasUsed}/{300_000} "
            f"tx={tx_hex if tx_hex.startswith('0x') else '0x' + tx_hex})"
        )
    return {
        "executor": "0g-direct-provider-reputation",
        "live": True,
        "tx": tx_hex if tx_hex.startswith("0x") else "0x" + tx_hex,
        "block_number": receipt.blockNumber,
        "registry_address": settings.provider_reputation_address,
        "npi_hash": npi_hash_hex,
        "status": "confirmed",
    }


async def record_audit(
    *,
    bill_text: str,
    bill_hash_hex: str,
    consensus: Dict[str, Any],
) -> Dict[str, Any]:
    """Record this audit against the provider's NPI in the on-chain reputation
    contract. No-ops when contract isn't configured or NPI isn't found."""
    if not (settings.zg_private_key and settings.provider_reputation_address):
        return _stub("not configured")

    npi = extract_npi(bill_text or "")
    if not npi:
        return _stub("no npi found")

    npi_hash = hash_npi(npi)
    verdict = str(consensus.get("verdict", "")).lower()
    verdict_int = _VERDICT_TO_INT.get(verdict, 0)
    if verdict_int == 0:
        return _stub(f"verdict={verdict}")

    flagged_usd = float(consensus.get("flagged_total_usd", 0.0) or 0.0)
    flagged_cents = int(round(flagged_usd * 100))
    agree = int(consensus.get("agree_count", 0) or 0)
    total = int(consensus.get("total_agents", 3) or 3)

    started = time.perf_counter()
    try:
        result = await asyncio.to_thread(
            _do_record_sync,
            npi_hash, bill_hash_hex, verdict_int, agree, total, flagged_cents,
        )
        result["duration_ms"] = int((time.perf_counter() - started) * 1000)
        result["npi_extracted"] = npi  # for SSE/UI display only
        log.info(
            "provider rep npi=%s verdict=%s tx=%s",
            npi, verdict, (result.get("tx") or "")[:18],
        )
        return result
    except Exception as e:
        log.warning("provider reputation record failed: %s", e)
        return {**_stub(f"error: {type(e).__name__}"), "error": str(e)[:200]}


async def fetch_stats(npi: str) -> Dict[str, Any]:
    """Read aggregate stats for a given NPI. Used by the public providers page
    and by the audit pipeline to surface provider history before agents reason.
    """
    if not settings.provider_reputation_address:
        log.info("fetch_stats(%s): contract not configured", npi)
        return {"configured": False}
    npi_hash = hash_npi(npi)

    def _read_sync():
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(settings.zg_rpc_url, request_kwargs={"timeout": 8}))
        if not w3.is_connected():
            return None
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(settings.provider_reputation_address),
            abi=_PROVIDER_REPUTATION_ABI,
        )
        h = npi_hash[2:] if npi_hash.startswith("0x") else npi_hash
        result = contract.functions.stats(bytes.fromhex(h)).call()
        return {
            "total_audits": int(result[0]),
            "dispute_count": int(result[1]),
            "clarify_count": int(result[2]),
            "approve_count": int(result[3]),
            "total_flagged_cents": int(result[4]),
        }

    try:
        s = await asyncio.to_thread(_read_sync)
        if s is None:
            log.warning("fetch_stats(%s) hash=%s: rpc unreachable", npi, npi_hash[:18])
            return {"configured": True, "error": "rpc unreachable"}
        log.info(
            "fetch_stats(%s) hash=%s → total=%d dispute=%d clarify=%d approve=%d flagged_cents=%d",
            npi, npi_hash[:18],
            s["total_audits"], s["dispute_count"], s["clarify_count"],
            s["approve_count"], s["total_flagged_cents"],
        )
        s["npi"] = npi
        s["npi_hash"] = npi_hash
        s["dispute_rate_pct"] = round(
            (s["dispute_count"] / s["total_audits"]) * 100, 2
        ) if s["total_audits"] else 0.0
        s["total_flagged_usd"] = round(s["total_flagged_cents"] / 100, 2)
        s["registry_address"] = settings.provider_reputation_address
        s["configured"] = True
        return s
    except Exception as e:
        log.warning("fetch_stats(%s) hash=%s failed: %s", npi, npi_hash[:18], e)
        return {"configured": True, "error": str(e)[:200], "npi": npi}


def format_history_for_prompt(stats: Dict[str, Any]) -> str:
    """Compact-format provider reputation stats for the agent prompt.

    Returns "" when stats are missing/zero so callers can join blocks
    without empty placeholder noise.
    """
    if not stats or not stats.get("configured") or stats.get("error"):
        return ""
    total = int(stats.get("total_audits", 0) or 0)
    if total == 0:
        return ""
    disp = int(stats.get("dispute_count", 0) or 0)
    clar = int(stats.get("clarify_count", 0) or 0)
    appr = int(stats.get("approve_count", 0) or 0)
    flagged_usd = float(stats.get("total_flagged_usd", 0.0) or 0.0)
    rate = stats.get("dispute_rate_pct", 0.0)
    return (
        "PROVIDER HISTORY (on-chain ProviderReputation, NPI hash "
        f"{stats.get('npi_hash', '')[:18]}…):\n"
        f"- prior audits: {total}\n"
        f"- disputed: {disp} ({rate}%)  clarify: {clar}  approve: {appr}\n"
        f"- total prior flagged: ${flagged_usd:,.2f}\n"
        "Use this as a prior on this provider's billing patterns; "
        "do not let it override evidence in the current bill.\n"
    )